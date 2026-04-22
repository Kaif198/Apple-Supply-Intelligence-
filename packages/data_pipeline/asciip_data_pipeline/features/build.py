"""Feature-store build entrypoint.

Runs:

1. Schema migrations (idempotent)
2. Raw + snapshot + unified ``src_*`` view refresh
3. Feature-view SQL in lexical order (idempotent ``CREATE OR REPLACE``)
4. Materialization of ``features_wide`` from every feature view that
   exposes the expected ``entity_id / as_of_ts / feature_*`` shape.

Called from ``make features`` and implicitly by the API on startup.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb

from asciip_shared import configure_logging, get_logger, get_settings

from asciip_data_pipeline.features.store import get_feature_store


@dataclass(frozen=True)
class WidePlan:
    """How to project a feature view into the long ``features_wide`` shape."""

    source_view: str
    entity_id_col: str
    entity_kind: str
    value_cols: tuple[str, ...]
    feature_prefix: str = ""


# Plans chosen so every scalar feature the models consume lands in features_wide.
PLANS: tuple[WidePlan, ...] = (
    WidePlan(
        source_view="commodity_price_daily",
        entity_id_col="entity_id",
        entity_kind="commodity",
        value_cols=("price",),
        feature_prefix="commodity_",
    ),
    WidePlan(
        source_view="commodity_vol_30d",
        entity_id_col="entity_id",
        entity_kind="commodity",
        value_cols=("vol_30d_annualized",),
        feature_prefix="commodity_",
    ),
    WidePlan(
        source_view="fx_daily",
        entity_id_col="entity_id",
        entity_kind="fx",
        value_cols=("rate",),
        feature_prefix="fx_",
    ),
    WidePlan(
        source_view="aapl_return_daily",
        entity_id_col="entity_id",
        entity_kind="equity",
        value_cols=("adj_close", "log_return"),
        feature_prefix="aapl_",
    ),
    WidePlan(
        source_view="apple_margin_target",
        entity_id_col="entity_id",
        entity_kind="equity",
        value_cols=("gross_margin",),
        feature_prefix="target_",
    ),
)


def _git_sha() -> str:
    if os.environ.get("ASCIIP_BUILD_SHA"):
        return os.environ["ASCIIP_BUILD_SHA"]
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:  # pragma: no cover — no git available
        return "unknown"


def _materialize_plan(con: duckdb.DuckDBPyConnection, plan: WidePlan, git_sha: str) -> int:
    inserted = 0
    for col in plan.value_cols:
        feature_name = f"{plan.feature_prefix}{col}"
        sql = (
            "INSERT OR REPLACE INTO features_wide "
            "(entity_id, entity_kind, as_of_ts, feature_name, feature_value, feature_text, git_sha) "
            f"SELECT {plan.entity_id_col}, '{plan.entity_kind}', as_of_ts, ?, "
            f"CAST({col} AS DOUBLE), NULL, ? "
            f"FROM {plan.source_view} "
            f"WHERE {col} IS NOT NULL"
        )
        result = con.execute(sql, [feature_name, git_sha])
        inserted += result.fetchall() and 0 or 0  # DuckDB does not return rowcount here
    return inserted


def build(refresh_only: bool = False) -> None:
    settings = get_settings()
    configure_logging(
        level=settings.log_level,
        pretty=settings.log_pretty,
        service_name="asciip-features-build",
        version=settings.version,
    )
    log = get_logger(__name__)

    store = get_feature_store()
    store.migrate()
    store.refresh_views()
    if refresh_only:
        log.info("features.refresh_only_complete")
        return

    store.rebuild_feature_views()

    git_sha = _git_sha()
    total = 0
    with store.connect() as con:
        for plan in PLANS:
            try:
                rows = _materialize_plan(con, plan, git_sha)
            except duckdb.CatalogException:
                # Feature view absent (e.g. snapshot missing); skip quietly.
                log.warning("features.plan_skipped", view=plan.source_view)
                continue
            total += rows
            log.info("features.plan_done", view=plan.source_view, inserted=rows)

        # Record lineage row per feature view (once per materialisation).
        materialised_at = datetime.now(UTC)
        for plan in PLANS:
            for col in plan.value_cols:
                feature_name = f"{plan.feature_prefix}{col}"
                con.execute(
                    "INSERT INTO feature_lineage "
                    "(feature_name, git_sha, source_tables, author, materialised_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    [
                        feature_name,
                        git_sha,
                        plan.source_view,
                        os.environ.get("USER") or os.environ.get("USERNAME") or "ci",
                        materialised_at,
                    ],
                )

    log.info("features.build_done", total_rows=total, git_sha=git_sha)


def main() -> int:
    parser = argparse.ArgumentParser(prog="asciip-features-build")
    parser.add_argument(
        "--refresh-only",
        action="store_true",
        help="Only refresh raw/src views; skip feature materialisation.",
    )
    args = parser.parse_args()
    build(refresh_only=args.refresh_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
