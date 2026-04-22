"""Post-deploy smoke check — hits /api/health and prints the result.

Used by ``make smoke``, Docker healthchecks, and CI's ``smoke.yml`` workflow.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import httpx
from asciip_shared import configure_logging, get_logger, get_settings


def _fetch(url: str, *, timeout: float) -> dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        response = client.get(url)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="asciip-smoke")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/api/health",
        help="Health endpoint to probe.",
    )
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument(
        "--once",
        action="store_true",
        help="Single probe, exit non-zero on failure (used as Docker HEALTHCHECK).",
    )
    args = parser.parse_args(argv)

    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        pretty=settings.log_pretty,
        service_name="asciip-smoke",
        version=settings.version,
    )
    log = get_logger(__name__)

    try:
        payload = _fetch(args.url, timeout=args.timeout)
    except Exception as exc:  # — smoke intentionally catches everything
        log.error("smoke.failed", url=args.url, error=str(exc))
        return 1

    if payload.get("status") != "ok":
        log.error("smoke.bad_status", payload=payload)
        return 1

    log.info(
        "smoke.ok",
        version=payload.get("version"),
        uptime=payload.get("uptime_seconds"),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
