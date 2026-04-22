"""Watermark-aware in-memory TTL cache.

A single process-wide cache keyed by ``(route, params, feature-store
watermark)``. Responses are evicted automatically when either (a) the TTL
expires or (b) the feature-store watermark advances — whichever happens
first. Upstream routes attach the watermark via the ``etag_for`` helper so
clients can send ``If-None-Match`` and get a ``304 Not Modified``.

The implementation is intentionally dependency-free (no Redis) so a single
container boot is self-contained.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass
class _Entry:
    value: Any
    etag: str
    expires_at: float
    watermark: datetime


class WatermarkedCache:
    def __init__(self, default_ttl_seconds: float = 60.0, max_entries: int = 2048) -> None:
        self._store: dict[str, _Entry] = {}
        self._lock = threading.RLock()
        self._ttl = default_ttl_seconds
        self._max = max_entries

    def _now(self) -> float:
        return time.monotonic()

    def _evict_if_needed(self) -> None:
        if len(self._store) <= self._max:
            return
        # Drop the ~25% oldest entries (by expires_at).
        cutoff = sorted(self._store.items(), key=lambda kv: kv[1].expires_at)[
            : max(1, len(self._store) // 4)
        ]
        for key, _ in cutoff:
            self._store.pop(key, None)

    def get(self, key: str, watermark: datetime) -> _Entry | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at < self._now() or entry.watermark != watermark:
                self._store.pop(key, None)
                return None
            return entry

    def put(
        self,
        key: str,
        value: Any,
        *,
        watermark: datetime,
        ttl_seconds: float | None = None,
    ) -> str:
        etag = _compute_etag(key, watermark, value)
        with self._lock:
            self._store[key] = _Entry(
                value=value,
                etag=etag,
                expires_at=self._now() + (ttl_seconds or self._ttl),
                watermark=watermark,
            )
            self._evict_if_needed()
        return etag

    def invalidate_prefix(self, prefix: str) -> int:
        removed = 0
        with self._lock:
            for key in list(self._store):
                if key.startswith(prefix):
                    self._store.pop(key, None)
                    removed += 1
        return removed

    def clear(self) -> None:
        with self._lock:
            self._store.clear()


def _compute_etag(key: str, watermark: datetime, value: Any) -> str:
    payload = json.dumps(
        {"k": key, "w": watermark.isoformat(), "v": _canonicalise(value)},
        sort_keys=True,
        default=str,
    ).encode("utf-8")
    return '"' + hashlib.sha256(payload).hexdigest()[:24] + '"'


def _canonicalise(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _canonicalise(obj[k]) for k in sorted(obj)}
    if isinstance(obj, (list, tuple)):
        return [_canonicalise(v) for v in obj]
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return obj


# ---------------------------------------------------------------- module singleton

_cache = WatermarkedCache()


def get_cache() -> WatermarkedCache:
    return _cache


def make_cache_key(path: str, params: dict[str, Any] | None = None) -> str:
    items = sorted((params or {}).items())
    suffix = "&".join(f"{k}={v}" for k, v in items if v is not None)
    return f"{path}?{suffix}" if suffix else path


def current_watermark() -> datetime:
    """Return the latest ``as_of_ts`` visible in ``features_wide``."""
    from asciip_data_pipeline.features import watermark

    return watermark() or datetime(1970, 1, 1, tzinfo=UTC)
