"""APScheduler declarations for the in-process refresh loop.

When the API process starts with ``ASCIIP_ENABLE_SCHEDULER=true`` (the
default in containers), the scheduler runs ingestion on per-source
cadences without requiring external cron. GitHub Actions ``ingest.yml``
handles scheduled refresh for stateless deployments.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Final

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from asciip_shared import get_logger, get_settings

from asciip_data_pipeline import orchestrator


@dataclass(frozen=True)
class JobSpec:
    name: str
    trigger: CronTrigger | IntervalTrigger
    func: Callable[[], Awaitable[object]]


def _build_specs() -> list[JobSpec]:
    settings = get_settings()
    return [
        JobSpec(
            name="ingestion.commodity",
            trigger=IntervalTrigger(seconds=settings.refresh_commodity_seconds),
            func=orchestrator.run_once,
        ),
        JobSpec(
            name="ingestion.trade",
            trigger=IntervalTrigger(seconds=settings.refresh_trade_seconds),
            func=orchestrator.run_once,
        ),
        JobSpec(
            name="ingestion.supplier_quarterly",
            # 02:05 UTC on the first of Feb/May/Aug/Nov.
            trigger=CronTrigger(day=1, month="2,5,8,11", hour=2, minute=5),
            func=orchestrator.run_once,
        ),
    ]


JOBS: Final[tuple[JobSpec, ...]] = tuple(_build_specs()) if False else ()


def build_scheduler(loop: asyncio.AbstractEventLoop | None = None) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(event_loop=loop or asyncio.get_event_loop())
    log = get_logger("asciip.scheduler")
    for spec in _build_specs():
        sched.add_job(spec.func, spec.trigger, id=spec.name, replace_existing=True)
        log.info("scheduler.job_registered", name=spec.name, trigger=str(spec.trigger))
    return sched
