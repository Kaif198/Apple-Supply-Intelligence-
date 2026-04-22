"""Structured logging for all ASCIIP services.

- Production: JSON lines emitted to stdout via :mod:`structlog` + orjson.
- Development: pretty, coloured tables via the ``rich`` renderer.

Every log event is automatically decorated with the bound correlation ID, a
monotonic timestamp, the service name, and the build version. Call
:func:`configure_logging` exactly once at process startup, then use
:func:`get_logger` anywhere.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import orjson
import structlog
from structlog.contextvars import merge_contextvars
from structlog.processors import CallsiteParameter
from structlog.typing import EventDict, Processor

from asciip_shared.correlation import get_correlation_id


def _orjson_dumps(obj: Any, default: Any = None) -> str:
    return orjson.dumps(
        obj,
        default=default,
        option=orjson.OPT_SORT_KEYS | orjson.OPT_UTC_Z,
    ).decode()


def _inject_correlation_id(_: Any, __: str, event_dict: EventDict) -> EventDict:
    cid = get_correlation_id()
    if cid and "correlation_id" not in event_dict:
        event_dict["correlation_id"] = cid
    return event_dict


def _inject_service_metadata(service_name: str, version: str) -> Processor:
    def processor(_: Any, __: str, event_dict: EventDict) -> EventDict:
        event_dict.setdefault("service", service_name)
        event_dict.setdefault("version", version)
        return event_dict

    return processor


def configure_logging(
    *,
    level: str = "INFO",
    pretty: bool = False,
    service_name: str = "asciip",
    version: str = "0.1.0",
) -> None:
    """Install the global logging configuration.

    Idempotent: safe to call multiple times (e.g. from tests).
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared: list[Processor] = [
        merge_contextvars,
        _inject_correlation_id,
        _inject_service_metadata(service_name, version),
        structlog.stdlib.add_log_level,
        timestamper,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.CallsiteParameterAdder(
            parameters=[CallsiteParameter.MODULE, CallsiteParameter.FUNC_NAME]
        ),
    ]

    if pretty:
        renderer: Processor = structlog.dev.ConsoleRenderer(colors=True, sort_keys=True)
    else:
        renderer = structlog.processors.JSONRenderer(serializer=_orjson_dumps)

    structlog.configure(
        processors=[*shared, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy, etc.) through structlog.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    for noisy in ("uvicorn.access", "uvicorn.error", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(max(logging.INFO, root.level))


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to ``name`` (module path by default)."""
    return structlog.get_logger(name)  # type: ignore[return-value]
