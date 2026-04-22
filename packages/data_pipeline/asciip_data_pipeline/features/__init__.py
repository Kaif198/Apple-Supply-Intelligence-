"""Feature store — DuckDB schema, views, materialization.

Layer 3 of ASCIIP. Every SQL fragment lives under
:mod:`asciip_data_pipeline.features.sql`; the Python surface here is kept
thin so callers (API routes, ML trainers) use a stable set of helpers.
"""

from asciip_data_pipeline.features.pit import (
    assert_no_leak,
    latest_feature,
    point_in_time_frame,
)
from asciip_data_pipeline.features.store import (
    FeatureStore,
    get_feature_store,
    watermark,
)

__all__ = [
    "FeatureStore",
    "assert_no_leak",
    "get_feature_store",
    "latest_feature",
    "point_in_time_frame",
    "watermark",
]
