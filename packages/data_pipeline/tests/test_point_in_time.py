"""Property test: no future leak into point-in-time queries.

For 500 random historical timestamps, we assert that
``point_in_time_frame(as_of=t)`` returns zero rows with ``as_of_ts > t``.
This is the Requirement 3.5 guarantee enforced in CI.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
from asciip_data_pipeline import synthetic
from asciip_data_pipeline.features import (
    assert_no_leak,
    get_feature_store,
    point_in_time_frame,
)
from asciip_data_pipeline.features.build import build as build_features
from asciip_shared.config import reset_settings_cache
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

pytestmark = [pytest.mark.property, pytest.mark.req_3]


@pytest.fixture(scope="module")
def built_store(tmp_path_factory: pytest.TempPathFactory):  # type: ignore[no-untyped-def]
    tmp = tmp_path_factory.mktemp("pit_data")
    import os

    for sub in ("raw", "features", "models", "exports", "snapshots"):
        (tmp / sub).mkdir(parents=True, exist_ok=True)
    os.environ["ASCIIP_DATA_DIR"] = str(tmp)
    os.environ["ASCIIP_DUCKDB_PATH"] = str(tmp / "features" / "asciip.duckdb")
    os.environ["ASCIIP_SNAPSHOTS_DIR"] = str(tmp / "snapshots")
    os.environ["ASCIIP_MODELS_DIR"] = str(tmp / "models")
    os.environ["ASCIIP_EXPORTS_DIR"] = str(tmp / "exports")
    os.environ["ASCIIP_RAW_DIR"] = str(tmp / "raw")
    reset_settings_cache()

    # Reset module-level singletons that cached the previous path.
    from asciip_data_pipeline.features import store as store_mod

    store_mod._default_store = None  # type: ignore[attr-defined]

    synthetic.write_snapshots(tmp / "snapshots")
    build_features()
    return get_feature_store()


_EARLIEST = date(2022, 1, 1)
_LATEST = date(2026, 1, 1)


@given(days=st.integers(min_value=0, max_value=(_LATEST - _EARLIEST).days))
@settings(
    max_examples=500, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_no_future_leak_at_random_cutoffs(built_store, days: int) -> None:  # type: ignore[no-untyped-def]
    cutoff = datetime.combine(_EARLIEST + timedelta(days=days), datetime.min.time(), tzinfo=UTC)
    rows = point_in_time_frame(as_of=cutoff)
    assert all(
        r["as_of_ts"] <= cutoff for r in rows
    ), f"point_in_time_frame leaked rows after {cutoff}"


def test_assert_no_leak_helper(built_store) -> None:  # type: ignore[no-untyped-def]
    cutoff = datetime(2023, 1, 1, tzinfo=UTC)
    store = get_feature_store()
    with store.connect() as con:
        before = con.execute(
            "SELECT COUNT(*) FROM features_wide WHERE as_of_ts <= ?", [cutoff]
        ).fetchone()
        after = assert_no_leak(con, datetime(3000, 1, 1, tzinfo=UTC))
    assert before
    assert before[0] > 0
    assert after == 0
