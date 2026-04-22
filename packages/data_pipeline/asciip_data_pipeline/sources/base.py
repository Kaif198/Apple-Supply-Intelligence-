"""Base class + registry for every external data source adapter.

Design notes
------------
* Every adapter returns a Polars DataFrame and a :class:`SourceMetadata`
  instance so downstream callers can compute provenance and lineage
  without introspecting adapter internals.
* Retries are implemented once, here, via :mod:`tenacity`; adapters
  declare only the operation-specific HTTP call.
* Snapshot fallback is also centralized: on exhausted retries, we read
  the matching Parquet snapshot under ``data/snapshots/{source}.parquet``
  and flag ``fallback=True`` on the returned metadata.
"""

from __future__ import annotations

import abc
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, ClassVar

import polars as pl
from asciip_shared import (
    DataSourceError,
    SourceMetadata,
    get_logger,
    get_settings,
)
from tenacity import (
    RetryError,
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


@dataclass(slots=True)
class SourceResult:
    """Output of a single source fetch."""

    data: pl.DataFrame
    metadata: SourceMetadata


class Source(abc.ABC):
    """Abstract base for every external adapter.

    Subclasses must declare :attr:`name` and :attr:`source_url` and implement
    :meth:`_fetch` — a single, blocking HTTP call that returns a DataFrame.
    Everything else (retries, caching, audit, snapshot fallback) is handled
    by :meth:`fetch`.
    """

    name: ClassVar[str] = ""
    source_url: ClassVar[str] = ""
    snapshot_filename: ClassVar[str] = ""

    #: Exceptions that should trigger a retry (HTTP errors, transient I/O).
    retry_exceptions: ClassVar[tuple[type[BaseException], ...]] = (
        ConnectionError,
        TimeoutError,
        OSError,
    )

    retry_attempts: ClassVar[int] = 3
    retry_initial_wait_s: ClassVar[float] = 1.0
    retry_max_wait_s: ClassVar[float] = 8.0

    def __init__(self) -> None:
        if not self.name:
            raise TypeError(f"{type(self).__name__} must set class attribute `name`")
        self.settings = get_settings()
        self.log = get_logger(f"asciip.sources.{self.name}")

    # ------------------------------------------------------------------ hooks

    @abc.abstractmethod
    def _fetch(self) -> pl.DataFrame:
        """Execute the adapter's primary HTTPS call and return a DataFrame."""

    def is_configured(self) -> bool:  # pragma: no cover - overridden by most adapters
        """Return True if the adapter has the credentials it needs.

        Adapters that require no key should leave this as ``True`` (default).
        """
        return True

    # ------------------------------------------------------------------ public

    def fetch(self) -> SourceResult:
        """Run the adapter with retries, audit metadata, and snapshot fallback."""
        started = datetime.now(UTC)
        if not self.is_configured():
            self.log.warning(
                "source.unconfigured",
                source=self.name,
                note="missing credentials; using snapshot fallback",
            )
            return self._fallback(reason="unconfigured")

        try:
            for attempt in Retrying(
                stop=stop_after_attempt(self.retry_attempts),
                wait=wait_exponential(
                    multiplier=self.retry_initial_wait_s, max=self.retry_max_wait_s
                ),
                retry=retry_if_exception_type(self.retry_exceptions),
                reraise=True,
            ):
                with attempt:
                    df = self._fetch()
        except RetryError as exc:  # pragma: no cover — defensive
            self.log.error("source.retry_exhausted", source=self.name, error=str(exc))
            return self._fallback(reason="retry_exhausted")
        except self.retry_exceptions as exc:
            self.log.error(
                "source.fetch_failed",
                source=self.name,
                error=str(exc),
                type=type(exc).__name__,
            )
            return self._fallback(reason=str(exc))
        except Exception as exc:  # pragma: no cover — unexpected
            self.log.exception("source.unexpected_error", source=self.name)
            raise DataSourceError(f"{self.name}: {exc}", detail={"source": self.name}) from exc

        payload = df.write_ipc(None, compression="uncompressed").getvalue()  # type: ignore[union-attr]
        meta = SourceMetadata(
            source_name=self.name,
            source_url=self.source_url,
            fetched_at=started,
            row_count=df.height,
            checksum_sha256=hashlib.sha256(payload).hexdigest(),
        )
        self.log.info(
            "source.fetch_ok",
            source=self.name,
            rows=df.height,
            duration_ms=int((datetime.now(UTC) - started).total_seconds() * 1000),
        )
        return SourceResult(data=df, metadata=meta)

    # ------------------------------------------------------------------ snapshot

    def snapshot_path(self) -> Path:
        return self.settings.snapshots_dir / (self.snapshot_filename or f"{self.name}.parquet")

    def _fallback(self, *, reason: str) -> SourceResult:
        path = self.snapshot_path()
        if not path.exists():
            raise DataSourceError(
                f"{self.name}: no snapshot available at {path}",
                detail={"source": self.name, "reason": reason},
            )
        df = pl.read_parquet(path)
        meta = SourceMetadata.for_path(
            source_name=self.name,
            source_url=self.source_url,
            path=path,
            row_count=df.height,
            fallback=True,
            fallback_snapshot_ts=datetime.fromtimestamp(path.stat().st_mtime, tz=UTC),
            notes=f"fallback: {reason}",
        )
        self.log.warning(
            "source.fallback",
            source=self.name,
            reason=reason,
            snapshot=str(path),
            rows=df.height,
        )
        return SourceResult(data=df, metadata=meta)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class SourceRegistry:
    """Ordered collection of source adapters keyed by :attr:`Source.name`."""

    def __init__(self) -> None:
        self._sources: dict[str, type[Source]] = {}

    def register(self, cls: type[Source]) -> type[Source]:
        if not cls.name:
            raise ValueError(f"{cls.__name__} cannot register without a name")
        if cls.name in self._sources:
            raise ValueError(f"duplicate source name: {cls.name}")
        self._sources[cls.name] = cls
        return cls

    def instantiate_all(self) -> list[Source]:
        return [cls() for cls in self._sources.values()]

    def get(self, name: str) -> type[Source]:
        return self._sources[name]

    def names(self) -> list[str]:
        return list(self._sources)

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._sources

    def __len__(self) -> int:
        return len(self._sources)


default_registry = SourceRegistry()


def register_source(cls: type[Source]) -> type[Source]:
    """Class decorator registering ``cls`` with the default registry."""
    return default_registry.register(cls)


# Convenience: make Any explicitly available in ``__all__`` expansions.
_ = Any
