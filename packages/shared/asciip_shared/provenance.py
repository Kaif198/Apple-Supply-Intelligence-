"""Data provenance and source-attribution primitives (Requirement 17).

Every value displayed in the UI is backed by a ``ProvenanceEntry``. Adapters
return a ``SourceMetadata`` object alongside the fetched DataFrame; the
orchestrator persists it to the ``ingestion_audit`` table; the API layer
assembles per-field ``ProvenanceEntry`` lists and attaches them to responses.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class ProvenanceKind(StrEnum):
    """How a value was obtained."""

    LIVE = "live"  # fetched from an external source just now
    CACHE = "cache"  # served from the API cache layer
    SNAPSHOT = "snapshot"  # fallback Parquet snapshot
    SYNTHETIC_CALIBRATION = "synthetic_calibration"  # deterministic offline calibration
    DERIVED = "derived"  # computed from one or more upstream provenances


@dataclass(slots=True)
class SourceMetadata:
    """Returned by every source adapter alongside its DataFrame.

    Stored to ``ingestion_audit`` and referenced by every downstream
    ``ProvenanceEntry``.
    """

    source_name: str
    source_url: str
    fetched_at: datetime
    row_count: int
    checksum_sha256: str
    fallback: bool = False
    fallback_snapshot_ts: datetime | None = None
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at.astimezone(UTC).isoformat(),
            "row_count": self.row_count,
            "checksum_sha256": self.checksum_sha256,
            "fallback": self.fallback,
            "fallback_snapshot_ts": (
                self.fallback_snapshot_ts.astimezone(UTC).isoformat()
                if self.fallback_snapshot_ts
                else None
            ),
            "notes": self.notes,
        }

    @classmethod
    def for_bytes(
        cls,
        source_name: str,
        source_url: str,
        payload: bytes,
        row_count: int,
        *,
        fallback: bool = False,
        fallback_snapshot_ts: datetime | None = None,
        notes: str = "",
    ) -> SourceMetadata:
        return cls(
            source_name=source_name,
            source_url=source_url,
            fetched_at=datetime.now(UTC),
            row_count=row_count,
            checksum_sha256=hashlib.sha256(payload).hexdigest(),
            fallback=fallback,
            fallback_snapshot_ts=fallback_snapshot_ts,
            notes=notes,
        )

    @classmethod
    def for_path(
        cls,
        source_name: str,
        source_url: str,
        path: Path,
        row_count: int,
        *,
        fallback: bool = False,
        fallback_snapshot_ts: datetime | None = None,
        notes: str = "",
    ) -> SourceMetadata:
        payload = path.read_bytes()
        return cls.for_bytes(
            source_name=source_name,
            source_url=source_url,
            payload=payload,
            row_count=row_count,
            fallback=fallback,
            fallback_snapshot_ts=fallback_snapshot_ts,
            notes=notes,
        )


@dataclass(slots=True)
class ProvenanceEntry:
    """Per-field attribution attached to API responses (Requirement 17.1)."""

    source_name: str
    source_url: str
    fetched_at: datetime
    kind: ProvenanceKind = ProvenanceKind.LIVE
    field_path: str = ""  # dotted path within the response payload
    notes: str = ""

    @classmethod
    def from_metadata(
        cls,
        meta: SourceMetadata,
        *,
        field_path: str = "",
        kind: ProvenanceKind | None = None,
    ) -> ProvenanceEntry:
        resolved_kind = kind or (ProvenanceKind.SNAPSHOT if meta.fallback else ProvenanceKind.LIVE)
        return cls(
            source_name=meta.source_name,
            source_url=meta.source_url,
            fetched_at=meta.fetched_at,
            kind=resolved_kind,
            field_path=field_path,
            notes=meta.notes,
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "source_url": self.source_url,
            "fetched_at": self.fetched_at.astimezone(UTC).isoformat(),
            "kind": self.kind.value,
            "field_path": self.field_path,
            "notes": self.notes,
        }


@dataclass(slots=True)
class ProvenanceBundle:
    """Collection of provenance entries used as a response envelope field."""

    entries: list[ProvenanceEntry] = field(default_factory=list)

    def add(self, entry: ProvenanceEntry) -> None:
        self.entries.append(entry)

    def extend(self, entries: list[ProvenanceEntry]) -> None:
        self.entries.extend(entries)

    @property
    def has_synthetic(self) -> bool:
        return any(e.kind is ProvenanceKind.SYNTHETIC_CALIBRATION for e in self.entries)

    @property
    def has_snapshot_fallback(self) -> bool:
        return any(e.kind is ProvenanceKind.SNAPSHOT for e in self.entries)

    def as_list(self) -> list[dict[str, Any]]:
        return [e.as_dict() for e in self.entries]
