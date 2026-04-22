"""Monte Carlo simulator tests."""

from __future__ import annotations

import time

import numpy as np
import pytest

from asciip_ml_models.montecarlo import MonteCarloConfig, run_simulation
from asciip_ml_models.montecarlo.simulator import default_shocks
from asciip_ml_models.valuation import apple_base_case, run_dcf


pytestmark = [pytest.mark.unit, pytest.mark.req_14]


def _cfg(n: int = 10_000, **overrides) -> MonteCarloConfig:
    defaults = dict(
        n_trials=n,
        shocks=default_shocks(),
        supplier_stress_mean=0.15,
        supplier_stress_sd=0.05,
    )
    defaults.update(overrides)
    return MonteCarloConfig(**defaults)


def test_simulation_shapes() -> None:
    result = run_simulation(_cfg(n=1_000))
    assert result.implied_price_samples.shape == (1000,)
    assert result.margin_delta_bps_samples.shape == (1000,)
    assert result.revenue_delta_pct_samples.shape == (1000,)
    assert result.commodity_return_samples.shape == (1000, 5)


def test_deterministic_given_seed() -> None:
    a = run_simulation(_cfg(n=500, seed=42))
    b = run_simulation(_cfg(n=500, seed=42))
    np.testing.assert_array_equal(a.implied_price_samples, b.implied_price_samples)


def test_mean_price_near_dcf_baseline() -> None:
    """With zero-elasticity shocks and zero outage, MC collapses to the DCF."""
    no_shock = MonteCarloConfig(
        n_trials=2_000,
        shocks=(),
        supplier_stress_mean=0.0,
        supplier_stress_sd=0.0,
        outage_revenue_haircut_mean=1e-9,
        outage_revenue_haircut_sd=1e-9,
        seed=7,
    )
    result = run_simulation(no_shock)
    baseline = run_dcf(apple_base_case()).implied_price_usd
    assert abs(float(np.mean(result.implied_price_samples)) - baseline) < 0.01


def test_positive_commodity_moves_reduce_price_on_average() -> None:
    # Force all shocks to have strictly positive mean returns.
    stressed = MonteCarloConfig(
        n_trials=5_000,
        shocks=tuple(
            type(s)(
                name=s.name,
                mean_return=0.25,
                volatility=0.05,
                elasticity_bps_per_10pct=s.elasticity_bps_per_10pct,
            )
            for s in default_shocks()
        ),
        supplier_stress_mean=0.0,
        supplier_stress_sd=0.0,
        outage_revenue_haircut_mean=1e-9,
        outage_revenue_haircut_sd=1e-9,
        seed=9,
    )
    result = run_simulation(stressed)
    baseline = run_dcf(apple_base_case()).implied_price_usd
    assert float(np.mean(result.implied_price_samples)) < baseline


def test_var_cvar_monotonic() -> None:
    result = run_simulation(_cfg(n=5_000, seed=11))
    var_5, cvar_5 = result.var_cvar(5.0)
    var_25, cvar_25 = result.var_cvar(25.0)
    assert cvar_5 <= var_5
    assert var_5 <= var_25
    assert cvar_5 <= cvar_25


def test_10k_trials_under_one_second() -> None:
    t0 = time.perf_counter()
    result = run_simulation(_cfg(n=10_000, seed=20250101))
    elapsed = time.perf_counter() - t0
    assert result.implied_price_samples.shape == (10_000,)
    # Loose ceiling so CI hardware variance does not flake us.
    assert elapsed < 2.0, f"10k trials took {elapsed:.3f}s"


def test_summary_keys() -> None:
    result = run_simulation(_cfg(n=500, seed=3))
    summary = result.summary()
    assert {"n_trials", "mean_price", "std_price", "percentiles",
            "var_5pct", "cvar_5pct"} <= set(summary.keys())
    assert set(summary["percentiles"].keys()) == {"5", "25", "50", "75", "95"}
