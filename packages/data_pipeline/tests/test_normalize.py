"""Tests for supplier name normalization."""

from __future__ import annotations

import pytest
from asciip_data_pipeline.supplier_extract.normalize import normalize_supplier_name

pytestmark = [pytest.mark.unit, pytest.mark.req_24]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Hon Hai Precision Industry Co., Ltd.", "Hon Hai Precision (Foxconn)"),
        ("Foxconn", "Hon Hai Precision (Foxconn)"),
        ("Foxconn Technology Group", "Hon Hai Precision (Foxconn)"),
        ("Taiwan Semiconductor Manufacturing Company", "TSMC"),
        ("TSMC", "TSMC"),
        ("Samsung Electronics Co., Ltd.", "Samsung Electronics"),
        ("LG Display Co., Ltd.", "LG Display"),
        ("Luxshare Precision Industry Co., Ltd.", "Luxshare Precision"),
        ("Pegatron Corporation", "Pegatron"),
        ("AAC Technologies Holdings Inc.", "AAC Technologies"),
        ("Amperex Technology Limited", "ATL (Amperex)"),
    ],
)
def test_known_aliases_collapse(raw: str, expected: str) -> None:
    assert normalize_supplier_name(raw) == expected


def test_idempotent() -> None:
    once = normalize_supplier_name("Foxconn Technology Group")
    twice = normalize_supplier_name(once)
    assert once == twice == "Hon Hai Precision (Foxconn)"


def test_preserves_unknown_capitalization() -> None:
    assert normalize_supplier_name("TDK Corporation") == "TDK"
    assert normalize_supplier_name("Acme Widgets Co., Ltd.") == "Acme Widgets"


def test_empty_input() -> None:
    assert normalize_supplier_name("") == ""
    assert normalize_supplier_name("   ") == ""
