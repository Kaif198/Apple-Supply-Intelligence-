"""Tests for the exception hierarchy and Problem Detail payloads."""

from __future__ import annotations

import pytest

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


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("cls", "expected_status"),
    [
        (ASCIIPError, 500),
        (ValidationError, 400),
        (NotFoundError, 404),
        (DataSourceError, 503),
        (FeatureStoreError, 500),
        (ModelError, 500),
        (ConfigurationError, 500),
    ],
)
def test_status_codes(cls: type[ASCIIPError], expected_status: int) -> None:
    err = cls("boom")
    assert err.status_code == expected_status
    assert err.title
    assert err.slug


def test_to_problem_roundtrip() -> None:
    err = ValidationError(
        "lithium_delta_pct out of range",
        detail={"field": "lithium_delta_pct", "value": 9001},
        correlation_id="abc",
    )
    pd = err.to_problem(instance="/api/scenarios")
    assert isinstance(pd, ProblemDetail)
    payload = pd.to_dict()
    assert payload["status"] == 400
    assert payload["title"] == "Validation error"
    assert payload["detail"] == "lithium_delta_pct out of range"
    assert payload["field"] == "lithium_delta_pct"
    assert payload["value"] == 9001
    assert payload["correlation_id"] == "abc"
    assert payload["instance"] == "/api/scenarios"
    assert payload["type"].endswith("/validation-error")


def test_problem_detail_strips_none() -> None:
    pd = ProblemDetail(type="about:blank", title="x", status=500)
    out = pd.to_dict()
    assert "instance" not in out
    assert "correlation_id" not in out
    assert out["status"] == 500
