"""Supplier extraction utilities (Requirement 24).

Parses Apple's public Supplier List PDF, normalizes supplier names, and
geocodes facility addresses via OpenStreetMap Nominatim. The snapshot
generated here seeds both the feature store and the supplier-network
visualization on the frontend.
"""

from asciip_data_pipeline.supplier_extract.geocode import (
    GeocodeResult,
    NominatimGeocoder,
    geocode_suppliers,
)
from asciip_data_pipeline.supplier_extract.normalize import normalize_supplier_name

__all__ = [
    "GeocodeResult",
    "NominatimGeocoder",
    "geocode_suppliers",
    "normalize_supplier_name",
]
