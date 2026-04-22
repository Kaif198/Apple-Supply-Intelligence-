"""Point-in-time helpers.

Every consumer of ``features_wide`` reads through :func:`point_in_time_frame`
so no model trains on data that was not observable at the target timestamp.
This is the guardrail behind Requirement 3.5; the property test in
``tests/test_point_in_time.py`` enforces the invariant across 500 random
historical timestamps.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

import duckdb

from asciip_data_pipeline.features.store import get_feature_store


def point_in_time_frame(
    *,
    feature_names: Iterable[str] | None = None,
    as_of: datetime | None = None,
    entity_ids: Iterable[str] | None = None,
    entity_kind: str | None = None,
) -> list[dict[str, object]]:
    """Return rows from ``features_wide`` observable at or before ``as_of``.

    The returned list is a plain list of dicts so callers can avoid pulling
    polars/pandas when they only need a handful of rows.
    """
    cutoff = (as_of or datetime.now(UTC)).astimezone(UTC)
    predicates: list[str] = ["as_of_ts <= ?"]
    params: list[object] = [cutoff]

    if feature_names is not None:
        names = list(feature_names)
        if not names:
            return []
        placeholders = ",".join("?" for _ in names)
        predicates.append(f"feature_name IN ({placeholders})")
        params.extend(names)

    if entity_ids is not None:
        ids = list(entity_ids)
        if not ids:
            return []
        placeholders = ",".join("?" for _ in ids)
        predicates.append(f"entity_id IN ({placeholders})")
        params.extend(ids)

    if entity_kind is not None:
        predicates.append("entity_kind = ?")
        params.append(entity_kind)

    store = get_feature_store()
    with store.connect() as con:
        rows = con.execute(
            "SELECT entity_id, entity_kind, as_of_ts, feature_name, feature_value "
            "FROM features_wide "
            f"WHERE {' AND '.join(predicates)} "
            "ORDER BY as_of_ts, entity_id, feature_name",
            params,
        ).fetchall()
        columns = [d[0] for d in con.description]

    return [dict(zip(columns, row, strict=True)) for row in rows]


def latest_feature(
    feature_name: str, *, entity_id: str | None = None, as_of: datetime | None = None
) -> float | None:
    cutoff = (as_of or datetime.now(UTC)).astimezone(UTC)
    store = get_feature_store()
    with store.connect() as con:
        if entity_id is not None:
            sql = (
                "SELECT feature_value FROM features_wide "
                "WHERE feature_name = ? AND entity_id = ? AND as_of_ts <= ? "
                "ORDER BY as_of_ts DESC LIMIT 1"
            )
            row = con.execute(sql, [feature_name, entity_id, cutoff]).fetchone()
        else:
            sql = (
                "SELECT feature_value FROM features_wide "
                "WHERE feature_name = ? AND as_of_ts <= ? "
                "ORDER BY as_of_ts DESC LIMIT 1"
            )
            row = con.execute(sql, [feature_name, cutoff]).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def assert_no_leak(con: duckdb.DuckDBPyConnection, cutoff: datetime) -> int:
    """Return the count of rows that violate PIT at ``cutoff``.

    Used by :mod:`tests.test_point_in_time` to drive the property check.
    """
    result = con.execute(
        "SELECT COUNT(*) FROM features_wide WHERE as_of_ts > ?",
        [cutoff],
    ).fetchone()
    return int(result[0]) if result else 0
