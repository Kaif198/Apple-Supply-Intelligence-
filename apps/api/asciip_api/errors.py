"""RFC 7807 problem-details error handlers.

Every exception surfaces as a JSON body conforming to
``application/problem+json`` with stable keys:

* ``type``     — stable URN identifying the error class
* ``title``    — human-readable summary
* ``status``   — mirrored HTTP status code
* ``detail``   — variable message (never sensitive)
* ``instance`` — correlation id so users can attach it to a support ticket
* ``errors``   — optional structured field-level details
"""

from __future__ import annotations

from typing import Any

from asciip_shared import (
    CORRELATION_ID_HEADER,
    ASCIIPError,
    DataSourceError,
    FeatureStoreError,
    get_correlation_id,
    get_logger,
)
from asciip_shared import (
    ValidationError as AsciipValidationError,
)
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_PROBLEM_CONTENT_TYPE = "application/problem+json"


def _problem_response(
    *,
    status_code: int,
    title: str,
    type_: str,
    detail: str,
    errors: Any = None,
) -> ORJSONResponse:
    body: dict[str, Any] = {
        "type": type_,
        "title": title,
        "status": status_code,
        "detail": detail,
        "instance": get_correlation_id() or "no-correlation",
    }
    if errors is not None:
        body["errors"] = errors
    headers = {"Content-Type": _PROBLEM_CONTENT_TYPE}
    cid = get_correlation_id()
    if cid:
        headers[CORRELATION_ID_HEADER] = cid
    return ORJSONResponse(body, status_code=status_code, headers=headers)


def install_error_handlers(app: FastAPI) -> None:
    """Register handlers for every ASCIIP + FastAPI exception type."""
    log = get_logger("asciip.api.errors")

    @app.exception_handler(AsciipValidationError)
    async def _handle_validation(_: Request, exc: AsciipValidationError) -> ORJSONResponse:
        log.info("api.validation_error", detail=str(exc), errors=exc.detail)
        return _problem_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Validation failed",
            type_="urn:asciip:error:validation",
            detail=str(exc),
            errors=exc.detail,
        )

    @app.exception_handler(DataSourceError)
    async def _handle_source(_: Request, exc: DataSourceError) -> ORJSONResponse:
        log.warning("api.source_error", detail=str(exc))
        return _problem_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            title="Upstream data source unavailable",
            type_="urn:asciip:error:data-source",
            detail=str(exc),
            errors=exc.detail,
        )

    @app.exception_handler(FeatureStoreError)
    async def _handle_store(_: Request, exc: FeatureStoreError) -> ORJSONResponse:
        log.error("api.feature_store_error", detail=str(exc))
        return _problem_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Feature store failure",
            type_="urn:asciip:error:feature-store",
            detail=str(exc),
            errors=exc.detail,
        )

    @app.exception_handler(ASCIIPError)
    async def _handle_generic(_: Request, exc: ASCIIPError) -> ORJSONResponse:
        log.error("api.asciip_error", detail=str(exc))
        return _problem_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="ASCIIP platform error",
            type_="urn:asciip:error:platform",
            detail=str(exc),
            errors=getattr(exc, "detail", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_fastapi_validation(_: Request, exc: RequestValidationError) -> ORJSONResponse:
        return _problem_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            title="Request validation failed",
            type_="urn:asciip:error:request-shape",
            detail="One or more request fields failed validation.",
            errors=exc.errors(),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http(_: Request, exc: StarletteHTTPException) -> ORJSONResponse:
        return _problem_response(
            status_code=exc.status_code,
            title=exc.detail if isinstance(exc.detail, str) else "HTTP error",
            type_=f"urn:asciip:error:http-{exc.status_code}",
            detail=str(exc.detail) if exc.detail else "",
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(_: Request, exc: Exception) -> ORJSONResponse:
        log.exception("api.unhandled_exception", error=str(exc))
        return _problem_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            title="Unexpected server error",
            type_="urn:asciip:error:unexpected",
            detail="An unexpected error occurred. Correlation id attached.",
        )
