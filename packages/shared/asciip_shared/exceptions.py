"""Typed exception hierarchy and RFC 7807 problem-detail payloads.

Every error raised inside ASCIIP should be a subclass of :class:`ASCIIPError`.
The API layer maps these to ``application/problem+json`` responses in a single
exception handler (see :mod:`asciip_api.errors`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class ASCIIPError(Exception):
    """Base class for all domain errors raised by ASCIIP services."""

    #: HTTP status this error maps to in the API layer.
    status_code: int = 500
    #: Short, stable slug used for the ``type`` URI on the problem detail.
    slug: str = "internal-error"
    #: Short human-readable title.
    title: str = "Internal server error"

    def __init__(
        self,
        message: str,
        *,
        detail: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.detail: dict[str, Any] = detail or {}
        self.correlation_id = correlation_id

    def to_problem(self, instance: str | None = None) -> ProblemDetail:
        return ProblemDetail(
            type=f"about:blank/asciip/{self.slug}",
            title=self.title,
            status=self.status_code,
            detail=self.message,
            instance=instance,
            correlation_id=self.correlation_id,
            extensions=self.detail,
        )


class ConfigurationError(ASCIIPError):
    status_code = 500
    slug = "configuration-error"
    title = "Configuration error"


class ValidationError(ASCIIPError):
    status_code = 400
    slug = "validation-error"
    title = "Validation error"


class NotFoundError(ASCIIPError):
    status_code = 404
    slug = "not-found"
    title = "Resource not found"


class DataSourceError(ASCIIPError):
    """Raised when an external adapter fails past the retry budget."""

    status_code = 503
    slug = "data-source-unavailable"
    title = "Data source unavailable"


class FeatureStoreError(ASCIIPError):
    status_code = 500
    slug = "feature-store-error"
    title = "Feature store error"


class ModelError(ASCIIPError):
    status_code = 500
    slug = "model-error"
    title = "Model inference error"


class RateLimitedError(ASCIIPError):
    status_code = 429
    slug = "rate-limited"
    title = "Too many requests"


class UnauthorizedError(ASCIIPError):
    status_code = 401
    slug = "unauthorized"
    title = "Unauthorized"


class ForbiddenError(ASCIIPError):
    status_code = 403
    slug = "forbidden"
    title = "Forbidden"


# ---------------------------------------------------------------------------
# Problem detail payload (RFC 7807)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class ProblemDetail:
    """RFC 7807 ``application/problem+json`` body.

    Kept as a plain dataclass (not Pydantic) so this module has no runtime
    dependency on the schema libraries used by the API layer. The API layer
    converts this to its Pydantic model when serialising.
    """

    type: str
    title: str
    status: int
    detail: str | None = None
    instance: str | None = None
    correlation_id: str | None = None
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        ext = data.pop("extensions", {})
        # Problem Details allow arbitrary members alongside the standard ones.
        if isinstance(ext, dict):
            data.update(ext)
        return {k: v for k, v in data.items() if v is not None}
