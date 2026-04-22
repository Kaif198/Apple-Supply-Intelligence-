"""External data source adapters.

Every adapter subclasses :class:`asciip_data_pipeline.sources.base.Source` and
is registered via :func:`register_source` so the orchestrator can enumerate
them. Import the module for the side-effect registration.
"""

from __future__ import annotations

from asciip_data_pipeline.sources.base import (
    Source,
    SourceRegistry,
    SourceResult,
    default_registry,
    register_source,
)

__all__ = [
    "Source",
    "SourceRegistry",
    "SourceResult",
    "default_registry",
    "register_source",
]
