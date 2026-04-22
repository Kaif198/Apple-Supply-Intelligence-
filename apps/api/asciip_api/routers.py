"""All ASCIIP HTTP routes in one file.

Kept in a single module so the surface is easy to audit. Each router is
named after its resource group; ``main.py`` assembles them into the
FastAPI app.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator, Callable
from datetime import UTC, datetime
from typing import Any, Literal

from asciip_shared import get_settings
from fastapi import APIRouter, HTTPException, Path, Query, Request, Response, status
from sse_starlette.sse import EventSourceResponse

from asciip_api import services
from asciip_api.cache import current_watermark, get_cache, make_cache_key
from asciip_api.schemas import (
    AaplHistoryResponse,
    AckAlertRequest,
    AlertsResponse,
    CausalRequest,
    CausalResponse,
    CommoditiesResponse,
    CommodityForecastResponse,
    DcfRequest,
    DcfResponse,
    EventsResponse,
    ExportRequest,
    ExportResponse,
    FactorResponse,
    HealthComponent,
    HealthResponse,
    MonteCarloRequest,
    MonteCarloResponse,
    SensitivityRequest,
    SensitivityResponse,
    SupplierDistressResponse,
    SuppliersResponse,
    VersionResponse,
)

_STARTED_AT = datetime.now(UTC)


# ------------------------------------------------------------------ helpers


def _cached_json(
    request: Request,
    response: Response,
    *,
    key: str,
    ttl_seconds: float,
    producer: Callable[[], Any],
) -> Any:
    """Shared ETag + watermark cache wrapper."""
    watermark = current_watermark()
    cache = get_cache()
    entry = cache.get(key, watermark)
    if entry is not None:
        inm = request.headers.get("if-none-match")
        if inm and inm == entry.etag:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": entry.etag})
        response.headers["ETag"] = entry.etag
        response.headers["X-Cache"] = "HIT"
        return entry.value
    value = producer()
    etag = cache.put(key, value, watermark=watermark, ttl_seconds=ttl_seconds)
    response.headers["ETag"] = etag
    response.headers["X-Cache"] = "MISS"
    return value


# ======================================================================= meta


meta_router = APIRouter(prefix="/api", tags=["meta"])


@meta_router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    components: list[HealthComponent] = [
        HealthComponent(name="api", status="ok"),
    ]

    # Feature store component.
    try:
        wm = current_watermark()
        components.append(
            HealthComponent(name="feature_store", status="ok", detail=f"watermark={wm.isoformat()}")
        )
    except Exception as exc:  # pragma: no cover — surfaces degraded state
        components.append(HealthComponent(name="feature_store", status="degraded", detail=str(exc)))

    overall: Literal["ok", "degraded"] = (
        "ok" if all(c.status == "ok" for c in components) else "degraded"
    )
    return HealthResponse(
        status=overall,
        service=settings.service_name,
        version=settings.version,
        env=settings.env,
        started_at=_STARTED_AT,
        uptime_seconds=(datetime.now(UTC) - _STARTED_AT).total_seconds(),
        correlation_id=None,
        watermark=current_watermark(),
        components=components,
    )


@meta_router.get("/version", response_model=VersionResponse)
async def version() -> VersionResponse:
    settings = get_settings()
    return VersionResponse(version=settings.version, build_sha=settings.build_sha)


# ================================================================= commodities


commodities_router = APIRouter(prefix="/api/commodities", tags=["commodities"])


@commodities_router.get("/prices", response_model=CommoditiesResponse)
async def get_prices(
    request: Request,
    response: Response,
    lookback_days: int = Query(365, ge=5, le=1825),
) -> Any:
    key = make_cache_key("/api/commodities/prices", {"lookback_days": lookback_days})
    return _cached_json(
        request,
        response,
        key=key,
        ttl_seconds=60,
        producer=lambda: services.get_commodity_panel(lookback_days=lookback_days),
    )


@commodities_router.get("/forecast", response_model=CommodityForecastResponse)
async def get_forecast(
    request: Request,
    response: Response,
    entity_id: str = Query(
        ..., pattern=r"^(aluminum|copper|lithium_carbonate|rare_earth_ndpr|crude_oil_wti)$"
    ),
    horizon_days: int = Query(30, ge=7, le=180),
) -> Any:
    key = make_cache_key(
        "/api/commodities/forecast",
        {"entity_id": entity_id, "horizon_days": horizon_days},
    )
    return _cached_json(
        request,
        response,
        key=key,
        ttl_seconds=1800,
        producer=lambda: services.commodity_forecast(entity_id, horizon_days=horizon_days),
    )


# ====================================================================== equity


equity_router = APIRouter(prefix="/api/equity", tags=["equity"])


@equity_router.get("/aapl", response_model=AaplHistoryResponse)
async def get_aapl_history(
    request: Request,
    response: Response,
    lookback_days: int = Query(365, ge=30, le=1825),
) -> Any:
    key = make_cache_key("/api/equity/aapl", {"lookback_days": lookback_days})
    return _cached_json(
        request,
        response,
        key=key,
        ttl_seconds=60,
        producer=lambda: services.aapl_history(lookback_days=lookback_days),
    )


@equity_router.get("/factors", response_model=FactorResponse)
async def get_factors(request: Request, response: Response) -> Any:
    key = make_cache_key("/api/equity/factors")
    try:
        return _cached_json(
            request,
            response,
            key=key,
            ttl_seconds=900,
            producer=services.factor_report,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


# =================================================================== suppliers


suppliers_router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])


@suppliers_router.get("", response_model=SuppliersResponse)
async def get_suppliers(request: Request, response: Response) -> Any:
    return _cached_json(
        request,
        response,
        key="/api/suppliers",
        ttl_seconds=300,
        producer=services.list_suppliers,
    )


@suppliers_router.get("/{supplier_id}/distress", response_model=SupplierDistressResponse)
async def supplier_distress(supplier_id: str = Path(..., min_length=1, max_length=64)) -> Any:
    try:
        return services.supplier_distress(supplier_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


# ====================================================================== events


events_router = APIRouter(prefix="/api/events", tags=["events"])


@events_router.get("", response_model=EventsResponse)
async def list_events(
    request: Request,
    response: Response,
    severity: str | None = Query(None, pattern=r"^(low|medium|high|critical)$"),
    limit: int = Query(50, ge=1, le=500),
) -> Any:
    key = make_cache_key("/api/events", {"severity": severity, "limit": limit})
    return _cached_json(
        request,
        response,
        key=key,
        ttl_seconds=30,
        producer=lambda: services.list_events(severity=severity, limit=limit),
    )


@events_router.get("/{event_id}", response_model=None)
async def get_event(event_id: str = Path(..., min_length=1)) -> Any:
    evt = services.get_event(event_id)
    if evt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="event not found")
    return evt


# ================================================================== scenarios


scenarios_router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


@scenarios_router.post("/run", response_model=MonteCarloResponse)
async def run_scenarios(req: MonteCarloRequest) -> Any:
    return services.run_monte_carlo(req.model_dump())


@scenarios_router.post("/dcf", response_model=DcfResponse)
async def run_dcf_endpoint(req: DcfRequest) -> Any:
    return services.run_dcf_with_overrides(req.model_dump(exclude_none=True))


@scenarios_router.post("/sensitivity", response_model=SensitivityResponse)
async def sensitivity(req: SensitivityRequest) -> Any:
    return services.run_sensitivity(req.model_dump())


# ====================================================================== causal


causal_router = APIRouter(prefix="/api/causal", tags=["causal"])


@causal_router.post("/ate", response_model=CausalResponse)
async def ate(req: CausalRequest) -> Any:
    try:
        return services.estimate_commodity_ate(req.model_dump())
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc


# ====================================================================== alerts


alerts_router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@alerts_router.get("", response_model=AlertsResponse)
async def get_alerts(
    unacknowledged_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=1000),
) -> Any:
    return services.list_alerts(unacknowledged_only=unacknowledged_only, limit=limit)


@alerts_router.post("/{alert_id}/ack", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def ack_alert(
    alert_id: str = Path(..., min_length=1),
    _body: AckAlertRequest = AckAlertRequest(),
) -> Response:
    services.acknowledge_alert(alert_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ====================================================================== exports


exports_router = APIRouter(prefix="/api/exports", tags=["exports"])


@exports_router.post("", response_model=ExportResponse)
async def create_export(req: ExportRequest) -> Any:
    try:
        return services.export_dataset(req.model_dump())
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


# ====================================================================== stream


stream_router = APIRouter(prefix="/api/stream", tags=["stream"])


@stream_router.get("/events")
async def stream_events(
    request: Request,
    poll_interval_s: float = Query(5.0, ge=1.0, le=60.0),
    severity: str | None = Query(None, pattern=r"^(low|medium|high|critical)$"),
) -> EventSourceResponse:
    """Server-sent event feed for new disruption events.

    Emits a ``ping`` every ``poll_interval_s`` so HTTP/1.1 proxies don't
    drop idle connections, and an ``event`` payload whenever a new row
    appears in ``disruption_events``.
    """

    async def generator() -> AsyncGenerator[dict[str, str], None]:
        seen: set[str] = set()
        while True:
            if await request.is_disconnected():
                return
            payload = services.list_events(severity=severity, limit=50)
            for evt in payload["events"]:
                if evt["id"] in seen:
                    continue
                seen.add(evt["id"])
                yield {
                    "event": "disruption",
                    "data": json.dumps(evt, default=str),
                }
            yield {
                "event": "ping",
                "data": json.dumps({"ts": datetime.now(UTC).isoformat()}),
            }
            await asyncio.sleep(poll_interval_s)

    return EventSourceResponse(generator())


# -------------------------------------------------------------------- exports


ALL_ROUTERS: tuple[APIRouter, ...] = (
    meta_router,
    commodities_router,
    equity_router,
    suppliers_router,
    events_router,
    scenarios_router,
    causal_router,
    alerts_router,
    exports_router,
    stream_router,
)
