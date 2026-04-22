"""Phase 1 smoke tests for the FastAPI scaffold."""

from __future__ import annotations

import pytest
from asciip_api.main import app
from asciip_shared import CORRELATION_ID_HEADER
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["components"]["api"] == "ok"
    assert body["version"]
    assert body["uptime_seconds"] >= 0


def test_health_echoes_correlation_id(client: TestClient) -> None:
    r = client.get("/api/health", headers={CORRELATION_ID_HEADER: "cid-abc-123"})
    assert r.status_code == 200
    assert r.headers[CORRELATION_ID_HEADER] == "cid-abc-123"
    assert r.json()["correlation_id"] == "cid-abc-123"


def test_health_generates_correlation_when_missing(client: TestClient) -> None:
    r = client.get("/api/health")
    cid = r.headers[CORRELATION_ID_HEADER]
    assert cid
    assert len(cid) == 32
    int(cid, 16)  # valid hex


def test_openapi_served(client: TestClient) -> None:
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    spec = r.json()
    assert spec["info"]["title"] == "ASCIIP API"
    assert "/api/health" in spec["paths"]


def test_version_endpoint(client: TestClient) -> None:
    r = client.get("/api/version")
    assert r.status_code == 200
    assert r.json()["version"]
