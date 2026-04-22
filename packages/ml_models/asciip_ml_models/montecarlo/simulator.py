"""Vectorised Monte Carlo simulator for supply-chain shocks.

Design
------
Each trial draws a vector of *commodity return shocks* from a multivariate
normal with the caller-supplied correlation matrix. The shocks are mapped
into:

1. **Margin delta (bps)** via elasticities measured by the margin Ridge
   (or caller-provided fallback coefficients).
2. **Revenue delta (%)** via a supplier-disruption Bernoulli term — if the
   trial's supplier-stress composite exceeds a threshold, revenue is
   haircut by a log-normal amount representing production outage depth.
3. **Implied share price** by re-running the DCF with the perturbed
   margin + revenue growth inputs.

Everything is numpy-vectorised — ``run_simulation(n_trials=10_000)`` runs
in well under one second on commodity hardware. The implementation keeps
to the public scipy/numpy surface so that the Web Worker (future hermetic
JS port) can mirror it without compile-time surprises.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

import numpy as np

from asciip_ml_models.valuation.base_case import (
    DCFAssumptions,
    apple_base_case,
)


@dataclass(frozen=True)
class ShockSpec:
    """Per-commodity shock parameters.

    The shock is modelled as a pass-through on the COGS line; a positive
    ``elasticity_bps_per_10pct`` means a +10% commodity-price move *reduces*
    gross margin by that many basis points.
    """

    name: str
    mean_return: float  # annualised expected log return
    volatility: float  # annualised standard deviation (log returns)
    elasticity_bps_per_10pct: float  # margin sensitivity per 10% commodity move


@dataclass(frozen=True)
class MonteCarloConfig:
    n_trials: int = 10_000
    horizon_years: float = 1.0
    shocks: tuple[ShockSpec, ...] = ()
    correlation: tuple[tuple[float, ...], ...] | None = None  # optional
    supplier_stress_mean: float = 0.15  # baseline P(supplier outage)
    supplier_stress_sd: float = 0.05
    outage_revenue_haircut_mean: float = 0.03
    outage_revenue_haircut_sd: float = 0.01
    seed: int = 20250101
    assumptions: DCFAssumptions = field(default_factory=apple_base_case)


@dataclass(frozen=True)
class MonteCarloResult:
    config: MonteCarloConfig
    implied_price_samples: np.ndarray  # shape (n_trials,)
    margin_delta_bps_samples: np.ndarray  # shape (n_trials,)
    revenue_delta_pct_samples: np.ndarray  # shape (n_trials,)
    commodity_return_samples: np.ndarray  # shape (n_trials, k)

    @property
    def n_trials(self) -> int:
        return int(self.implied_price_samples.shape[0])

    def percentiles(self, qs: Sequence[float] = (5, 25, 50, 75, 95)) -> dict[float, float]:
        return {float(q): float(np.nanpercentile(self.implied_price_samples, q)) for q in qs}

    def var_cvar(self, q: float = 5.0) -> tuple[float, float]:
        price = self.implied_price_samples
        var = float(np.nanpercentile(price, q))
        cvar = float(np.nanmean(price[price <= var])) if np.any(price <= var) else var
        return var, cvar

    def summary(self) -> dict[str, object]:
        pct = self.percentiles()
        var5, cvar5 = self.var_cvar(5.0)
        return {
            "n_trials": self.n_trials,
            "mean_price": float(np.nanmean(self.implied_price_samples)),
            "std_price": float(np.nanstd(self.implied_price_samples)),
            "percentiles": {str(int(k)): v for k, v in pct.items()},
            "var_5pct": var5,
            "cvar_5pct": cvar5,
            "mean_margin_delta_bps": float(np.nanmean(self.margin_delta_bps_samples)),
            "mean_revenue_delta_pct": float(np.nanmean(self.revenue_delta_pct_samples)),
        }


# --------------------------------------------------------------------------- core


def _build_correlation(n: int, user_corr: tuple[tuple[float, ...], ...] | None) -> np.ndarray:
    if user_corr is None:
        # Mild positive correlation across industrial commodities.
        default = np.full((n, n), 0.35, dtype=np.float64)
        np.fill_diagonal(default, 1.0)
        return default
    arr = np.asarray(user_corr, dtype=np.float64)
    if arr.shape != (n, n):
        raise ValueError(f"correlation must be {n}x{n}, got {arr.shape}")
    if not np.allclose(arr, arr.T, atol=1e-9):
        raise ValueError("correlation must be symmetric")
    return arr


def _draw_correlated_returns(cfg: MonteCarloConfig, rng: np.random.Generator) -> np.ndarray:
    if not cfg.shocks:
        return np.zeros((cfg.n_trials, 0), dtype=np.float64)
    k = len(cfg.shocks)
    means = np.array([s.mean_return for s in cfg.shocks], dtype=np.float64)
    vols = np.array([s.volatility for s in cfg.shocks], dtype=np.float64)
    corr = _build_correlation(k, cfg.correlation)

    # Build covariance on a horizon-scaled basis.
    np.sqrt(cfg.horizon_years)
    cov = corr * np.outer(vols, vols) * (cfg.horizon_years)

    # Cholesky factor + standard-normal draw; robust to mildly singular matrices
    # via jitter fallback.
    try:
        chol = np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        chol = np.linalg.cholesky(cov + np.eye(k) * 1e-8)

    z = rng.standard_normal(size=(cfg.n_trials, k))
    drift = means * cfg.horizon_years
    log_returns = drift + z @ chol.T
    # Convert log returns to simple returns for margin pass-through math.
    return np.expm1(log_returns)


def _margin_delta_bps(simple_returns: np.ndarray, elasticities_per_10pct: np.ndarray) -> np.ndarray:
    """Sum per-commodity elasticity contributions.

    Elasticities are stated per 10% move, so divide by 0.10.
    """
    if simple_returns.size == 0:
        return np.zeros(simple_returns.shape[0])
    return -simple_returns @ (elasticities_per_10pct / 0.10)


def _revenue_delta_pct(cfg: MonteCarloConfig, rng: np.random.Generator) -> np.ndarray:
    # Supplier-stress composite as a clipped normal draw on [0, 1].
    stress = rng.normal(
        loc=cfg.supplier_stress_mean,
        scale=cfg.supplier_stress_sd,
        size=cfg.n_trials,
    )
    stress = np.clip(stress, 0.0, 1.0)
    outage = rng.binomial(1, stress, size=cfg.n_trials).astype(np.float64)

    haircut = rng.lognormal(
        mean=np.log(max(cfg.outage_revenue_haircut_mean, 1e-6)),
        sigma=max(cfg.outage_revenue_haircut_sd, 1e-6),
        size=cfg.n_trials,
    )
    return -outage * haircut


def _price_from_perturbations(
    cfg: MonteCarloConfig,
    margin_delta_bps: np.ndarray,
    revenue_delta_pct: np.ndarray,
) -> np.ndarray:
    """Re-run DCF per trial using perturbed fcf_margin and revenue_cagr.

    The perturbations are small so a first-order Taylor expansion around
    the base case is numerically equivalent to running the closed-form DCF
    per trial, but we keep the loop-free matrix form below so the output
    is identical to the analytic formula.
    """
    a = cfg.assumptions
    years = np.arange(1, a.horizon_years + 1, dtype=np.float64)

    # Vectorise over trials: shape (n_trials, horizon_years).
    perturbed_margin = np.clip(
        a.fcf_margin + margin_delta_bps[:, None] / 10_000.0,
        0.01,
        0.99,
    )
    perturbed_cagr = a.revenue_cagr_5y + revenue_delta_pct[:, None] / a.horizon_years

    revenue = a.revenue_ttm_bn * np.power(1.0 + perturbed_cagr, years[None, :])
    fcf = revenue * perturbed_margin
    discount = np.power(1.0 + a.wacc, years)
    pv_explicit = np.sum(fcf / discount, axis=1)

    terminal = fcf[:, -1] * (1.0 + a.terminal_growth) / (a.wacc - a.terminal_growth)
    pv_terminal = terminal / discount[-1]

    enterprise = pv_explicit + pv_terminal
    equity = enterprise + a.net_cash_bn
    return equity / a.shares_diluted_bn


def run_simulation(config: MonteCarloConfig) -> MonteCarloResult:
    """Execute the full vectorised trial batch."""
    if config.n_trials <= 0:
        raise ValueError("n_trials must be positive")

    rng = np.random.default_rng(config.seed)

    returns = _draw_correlated_returns(config, rng)
    elasticities = np.array([s.elasticity_bps_per_10pct for s in config.shocks], dtype=np.float64)
    margin_delta = _margin_delta_bps(returns, elasticities)
    revenue_delta = _revenue_delta_pct(config, rng)
    prices = _price_from_perturbations(config, margin_delta, revenue_delta)

    return MonteCarloResult(
        config=config,
        implied_price_samples=prices,
        margin_delta_bps_samples=margin_delta,
        revenue_delta_pct_samples=revenue_delta,
        commodity_return_samples=returns,
    )


# ------------------------------------------------------------------ calibration


def default_shocks() -> tuple[ShockSpec, ...]:
    """Default shock set used by the Control Tower demo card.

    Elasticities are expressed per 10% commodity move and calibrated so a
    -20 bps total margin hit at the 95th percentile corresponds to a
    joint +10%/+10% aluminum/copper move — consistent with Apple's 10-K
    commodity-sensitivity commentary.
    """
    return (
        ShockSpec("aluminum", mean_return=0.02, volatility=0.18, elasticity_bps_per_10pct=8.0),
        ShockSpec("copper", mean_return=0.02, volatility=0.22, elasticity_bps_per_10pct=9.0),
        ShockSpec("lithium", mean_return=0.00, volatility=0.45, elasticity_bps_per_10pct=4.0),
        ShockSpec("cobalt", mean_return=-0.01, volatility=0.35, elasticity_bps_per_10pct=3.0),
        ShockSpec("brent", mean_return=0.01, volatility=0.28, elasticity_bps_per_10pct=5.0),
    )
