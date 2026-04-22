"""Tests for provenance dataclasses."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from asciip_shared.provenance import (
    ProvenanceBundle,
    ProvenanceEntry,
    ProvenanceKind,
    SourceMetadata,
)

pytestmark = pytest.mark.unit


def test_source_metadata_checksum_stable() -> None:
    payload = b"hello world"
    m1 = SourceMetadata.for_bytes("demo", "https://example.test", payload, row_count=1)
    m2 = SourceMetadata.for_bytes("demo", "https://example.test", payload, row_count=1)
    assert m1.checksum_sha256 == m2.checksum_sha256
    assert len(m1.checksum_sha256) == 64  # sha256 hex


def test_source_metadata_as_dict_serializes_timestamps() -> None:
    m = SourceMetadata(
        source_name="fred",
        source_url="https://api.stlouisfed.org",
        fetched_at=datetime(2026, 4, 19, 12, 0, tzinfo=UTC),
        row_count=42,
        checksum_sha256="0" * 64,
    )
    d = m.as_dict()
    assert d["fetched_at"].endswith("+00:00")
    assert d["fallback"] is False
    assert d["row_count"] == 42


def test_entry_from_metadata_infers_snapshot_kind() -> None:
    fallback = SourceMetadata(
        source_name="fred",
        source_url="https://api.stlouisfed.org",
        fetched_at=datetime.now(UTC),
        row_count=0,
        checksum_sha256="0" * 64,
        fallback=True,
    )
    entry = ProvenanceEntry.from_metadata(fallback, field_path="commodity.copper")
    assert entry.kind is ProvenanceKind.SNAPSHOT


def test_bundle_tracks_synthetic_and_snapshot() -> None:
    now = datetime.now(UTC)
    bundle = ProvenanceBundle()
    bundle.add(ProvenanceEntry("a", "https://a", now, ProvenanceKind.LIVE))
    assert bundle.has_synthetic is False
    assert bundle.has_snapshot_fallback is False
    bundle.add(ProvenanceEntry("b", "https://b", now, ProvenanceKind.SYNTHETIC_CALIBRATION))
    bundle.add(ProvenanceEntry("c", "https://c", now, ProvenanceKind.SNAPSHOT))
    assert bundle.has_synthetic is True
    assert bundle.has_snapshot_fallback is True
    assert len(bundle.as_list()) == 3


@pytest.mark.parametrize(
    "bad_bytes",
    [b"", b"x", b"hello world" + b"\0" * 100],
)
def test_for_bytes_accepts_any_payload(bad_bytes: bytes) -> None:
    m = SourceMetadata.for_bytes("x", "https://x", bad_bytes, row_count=0)
    assert len(m.checksum_sha256) == 64
