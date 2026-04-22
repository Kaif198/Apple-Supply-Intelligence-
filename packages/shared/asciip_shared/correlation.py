"""Correlation-ID propagation for request tracing.

Every inbound HTTP request gets a correlation ID (generated or forwarded from
``X-Correlation-ID``). The middleware in :mod:`asciip_api.middleware` binds
the value here; downstream services, loggers, and exception payloads read it
via :func:`get_correlation_id`.
"""

from __future__ import annotations

import uuid
from contextvars import ContextVar, Token
from typing import Final

CORRELATION_ID_HEADER: Final[str] = "X-Correlation-ID"

_correlation_id: ContextVar[str] = ContextVar("asciip_correlation_id", default="")


def new_correlation_id() -> str:
    """Generate a new opaque correlation identifier (UUID4 hex, 32 chars)."""
    return uuid.uuid4().hex


def get_correlation_id() -> str:
    """Return the correlation ID bound to the current context.

    Returns an empty string when none is bound. Callers that require a value
    should call :func:`bind_correlation_id` first.
    """
    return _correlation_id.get()


def bind_correlation_id(value: str | None = None) -> Token[str]:
    """Bind ``value`` (or a fresh ID) and return the context token for reset.

    Example::

        token = bind_correlation_id()
        try:
            ...
        finally:
            reset_correlation_id(token)
    """
    return _correlation_id.set(value or new_correlation_id())


def reset_correlation_id(token: Token[str]) -> None:
    """Reset the context variable using a token previously returned by ``bind``."""
    _correlation_id.reset(token)
