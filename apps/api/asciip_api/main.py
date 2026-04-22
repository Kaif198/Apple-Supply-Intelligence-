"""ASCIIP FastAPI app factory — Phase 5 full surface.

Pipeline assembled here:

1. Logging + settings
2. Middleware chain  (correlation → access log → rate limit → CORS)
3. Error handlers    (RFC 7807 problem+json)
4. Routers           (meta, commodities, equity, suppliers, events,
                     scenarios, causal, alerts, exports, stream)
5. Lifecycle hooks   (feature-store migrate, optional APScheduler boot)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse, Response

from asciip_shared import (
    CORRELATION_ID_HEADER,
    configure_logging,
    get_logger,
    get_settings,
)

from asciip_data_pipeline.features import get_feature_store

from asciip_api.errors import install_error_handlers
from asciip_api.middleware import (
    install_access_log_middleware,
    install_correlation_middleware,
    install_rate_limit_middleware,
)
from asciip_api.routers import ALL_ROUTERS


_STARTED_AT = datetime.now(UTC)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    log = get_logger("asciip.api.lifecycle")
    settings = get_settings()

    # Ensure the DuckDB schema is migrated before any route touches it.
    try:
        get_feature_store().migrate()
        log.info("api.feature_store_migrated")
    except Exception as exc:  # pragma: no cover — surfaced via /api/health
        log.error("api.feature_store_migration_failed", error=str(exc))

    if settings.env == "production" and any(
        "localhost" in o for o in settings.cors_origin_list
    ):
        log.warning(
            "api.cors_localhost_in_production",
            hint="Set ASCIIP_CORS_ORIGINS to your production frontend URL",
        )

    scheduler = None
    if settings.enable_scheduler:
        try:
            from asciip_data_pipeline.schedule import build_scheduler

            scheduler = build_scheduler()
            scheduler.start()
            app.state.scheduler = scheduler
            log.info("api.scheduler_started")
        except Exception as exc:  # pragma: no cover — non-fatal
            log.warning("api.scheduler_start_failed", error=str(exc))

    try:
        yield
    finally:
        if scheduler is not None:
            try:
                scheduler.shutdown(wait=False)
            except Exception:  # pragma: no cover
                pass


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        pretty=settings.log_pretty,
        service_name=settings.service_name,
        version=settings.version,
    )

    app = FastAPI(
        title="ASCIIP API",
        version=settings.version,
        description=(
            "Apple Supply Chain Impact Intelligence Platform — full backend "
            "surface for commodity prices, supplier distress, event stream, "
            "scenarios, causal estimates, and exports."
        ),
        default_response_class=ORJSONResponse,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=_lifespan,
    )

    _MAX_BODY = 1_048_576  # 1 MB

    @app.middleware("http")
    async def _content_size_limit(request: Request, call_next: object) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY:
            return Response(status_code=413, content="Request body too large")
        return await call_next(request)  # type: ignore[operator]

    # Middleware order matters — outermost last, innermost first.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*", "If-None-Match"],
        expose_headers=[CORRELATION_ID_HEADER, "ETag", "X-Cache", "X-Response-Time-ms"],
    )
    install_rate_limit_middleware(app, capacity=settings.rate_limit_capacity, window_seconds=60.0)
    install_access_log_middleware(app)
    install_correlation_middleware(app)

    install_error_handlers(app)

    for router in ALL_ROUTERS:
        app.include_router(router)

    log = get_logger("asciip.api")
    log.info(
        "api.created",
        version=settings.version,
        env=settings.env,
        routers=[r.prefix or "/" for r in ALL_ROUTERS],
    )
    return app


app = create_app()
