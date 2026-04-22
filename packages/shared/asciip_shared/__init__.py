"""Shared utilities for all ASCIIP services.

Every package in the monorepo imports from here. The surface is intentionally
small so that breaking changes ripple predictably.
"""

from asciip_shared.config import Settings, get_settings
from asciip_shared.constants import (
    COMMODITY_CODES,
    COMMODITY_ORDER,
    SEVERITY_CLASSES,
    SEVERITY_THRESHOLDS_USD,
    SeverityClass,
)
from asciip_shared.correlation import (
    CORRELATION_ID_HEADER,
    bind_correlation_id,
    get_correlation_id,
    new_correlation_id,
)
from asciip_shared.exceptions import (
    ASCIIPError,
    ConfigurationError,
    DataSourceError,
    FeatureStoreError,
    ModelError,
    NotFoundError,
    ProblemDetail,
    ValidationError,
)
from asciip_shared.logging import configure_logging, get_logger
from asciip_shared.provenance import (
    ProvenanceEntry,
    ProvenanceKind,
    SourceMetadata,
)

__all__ = [
    "CORRELATION_ID_HEADER",
    "COMMODITY_CODES",
    "COMMODITY_ORDER",
    "SEVERITY_CLASSES",
    "SEVERITY_THRESHOLDS_USD",
    "ASCIIPError",
    "ConfigurationError",
    "DataSourceError",
    "FeatureStoreError",
    "ModelError",
    "NotFoundError",
    "ProblemDetail",
    "ProvenanceEntry",
    "ProvenanceKind",
    "SeverityClass",
    "Settings",
    "SourceMetadata",
    "ValidationError",
    "bind_correlation_id",
    "configure_logging",
    "get_correlation_id",
    "get_logger",
    "get_settings",
    "new_correlation_id",
]

__version__ = "0.1.0"
