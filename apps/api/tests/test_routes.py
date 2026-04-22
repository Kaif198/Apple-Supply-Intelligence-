"""Happy-path integration tests for every Phase-5 HTTP surface."""

from __future__ import annotations

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.req_15, pytest.mark.req_16]


# -------------------------------------------------------------------- meta


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["service"] == "asciip-api"
    assert body["status"] in {"ok", "degraded"}
    assert any(c["name"] == "feature_store" for c in body["components"])


def test_version(client):
    r = client.get("/api/version")
    assert r.status_code == 200
    assert r.json()["schema_version"] == "v1"


# -------------------------------------------------------------------- commodities


def test_commodity_prices_etag_and_cache(client):
    r1 = client.get("/api/commodities/prices?lookback_days=365")
    assert r1.status_code == 200
    etag = r1.headers["etag"]
    assert etag
    assert r1.headers["x-cache"] == "MISS"
    assert {"commodities", "as_of"} <= set(r1.json().keys())
    assert len(r1.json()["commodities"]) == 5

    r2 = client.get("/api/commodities/prices?lookback_days=365")
    assert r2.status_code == 200
    assert r2.headers["x-cache"] == "HIT"
    assert r2.headers["etag"] == etag

    r3 = client.get(
        "/api/commodities/prices?lookback_days=365",
        headers={"If-None-Match": etag},
    )
    assert r3.status_code == 304


def test_commodity_prices_validation(client):
    r = client.get("/api/commodities/prices?lookback_days=4")
    assert r.status_code == 422
    assert r.headers["content-type"] == "application/problem+json"


# -------------------------------------------------------------------- equity


def test_aapl_history(client):
    r = client.get("/api/equity/aapl?lookback_days=180")
    assert r.status_code == 200
    body = r.json()
    assert "series" in body
    assert len(body["series"]) > 0
    sample = body["series"][-1]
    assert {"as_of_ts", "adj_close"} <= set(sample)


def test_factor_report_graceful_when_untrained(client):
    r = client.get("/api/equity/factors")
    # If not trained yet the service returns 503 via problem+json.
    assert r.status_code in {200, 503}


# -------------------------------------------------------------------- suppliers


def test_list_suppliers(client):
    r = client.get("/api/suppliers")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 0
    assert len(body["suppliers"]) == body["count"]


def test_supplier_distress_not_found(client):
    r = client.get("/api/suppliers/does-not-exist/distress")
    assert r.status_code == 404
    assert r.headers["content-type"] == "application/problem+json"


def test_supplier_distress_happy_path(client):
    suppliers = client.get("/api/suppliers").json()["suppliers"]
    sup_id = suppliers[0]["id"]
    r = client.get(f"/api/suppliers/{sup_id}/distress")
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["distress_probability"] <= 1.0


# -------------------------------------------------------------------- events


def test_events_list(client):
    r = client.get("/api/events?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert "events" in body
    assert body["count"] == len(body["events"])


# -------------------------------------------------------------------- scenarios


def test_dcf_default_assumptions_match_anchor(client):
    r = client.post("/api/scenarios/dcf", json={})
    assert r.status_code == 200
    body = r.json()
    assert 167.0 <= body["implied_price_usd"] <= 185.0
    assert len(body["projected_revenue_bn"]) == body["assumptions"]["horizon_years"]


def test_dcf_overrides_applied(client):
    r = client.post("/api/scenarios/dcf", json={"wacc": 0.12})
    assert r.status_code == 200
    assert r.json()["assumptions"]["wacc"] == pytest.approx(0.12)
    # Higher WACC depresses implied price.
    assert r.json()["implied_price_usd"] < 150.0


def test_sensitivity_grid(client):
    r = client.post(
        "/api/scenarios/sensitivity",
        json={
            "row_field": "wacc",
            "row_values": [0.07, 0.08, 0.09, 0.10],
            "col_field": "terminal_growth",
            "col_values": [0.02, 0.025, 0.03],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["implied_prices"]) == 4
    assert all(len(row) == 3 for row in body["implied_prices"])


def test_monte_carlo(client):
    r = client.post(
        "/api/scenarios/run",
        json={
            "n_trials": 500,
            "horizon_years": 1.0,
            "shocks": [
                {
                    "name": "aluminum",
                    "mean_return": 0.02,
                    "volatility": 0.18,
                    "elasticity_bps_per_10pct": 8.0,
                },
                {
                    "name": "copper",
                    "mean_return": 0.02,
                    "volatility": 0.22,
                    "elasticity_bps_per_10pct": 9.0,
                },
            ],
            "supplier_stress_mean": 0.1,
            "supplier_stress_sd": 0.02,
            "outage_revenue_haircut_mean": 0.03,
            "outage_revenue_haircut_sd": 0.01,
            "seed": 7,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["n_trials"] == 500
    assert "percentiles" in body
    assert set(body["percentiles"].keys()) == {"5", "25", "50", "75", "95"}
    assert len(body["implied_price_samples"]) > 0


def test_monte_carlo_validation_caps_n_trials(client):
    r = client.post(
        "/api/scenarios/run",
        json={
            "n_trials": 1_000_000,
            "horizon_years": 1.0,
            "shocks": [],
            "seed": 1,
        },
    )
    assert r.status_code == 422


# -------------------------------------------------------------------- exports


def test_export_json(client):
    r = client.post(
        "/api/exports",
        json={"format": "json", "dataset": "suppliers"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["format"] == "json"
    assert body["size_bytes"] > 0
    assert len(body["sha256"]) == 64


def test_export_unknown_dataset(client):
    r = client.post(
        "/api/exports",
        json={"format": "json", "dataset": "nope"},
    )
    assert r.status_code == 422
