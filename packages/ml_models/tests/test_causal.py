"""Causal engine tests — uses synthetic DGP so ground truth is known."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from asciip_ml_models.causal import CausalConfig, estimate_ate
from asciip_ml_models.causal.engine import _double_ml_ate


pytestmark = [pytest.mark.unit, pytest.mark.req_11]


def _make_synthetic(n: int = 800, true_effect: float = 1.5, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    w1 = rng.normal(size=n)
    w2 = rng.normal(size=n)
    # Treatment depends on confounders + noise.
    t = 0.5 * w1 - 0.3 * w2 + rng.normal(scale=0.5, size=n)
    # Outcome = true_effect * t + confounder influence + noise.
    y = true_effect * t + 0.8 * w1 + 0.4 * w2 + rng.normal(scale=0.3, size=n)
    return pd.DataFrame({"T": t, "Y": y, "W1": w1, "W2": w2})


def test_dml_recovers_true_ate_within_10pct() -> None:
    data = _make_synthetic(true_effect=1.5)
    cfg = CausalConfig(
        treatment="T", outcome="Y", confounders=("W1", "W2"), data=data
    )
    est = _double_ml_ate(cfg)
    assert est.method == "double_ml"
    assert abs(est.ate - 1.5) / 1.5 < 0.10
    assert est.ci_low < 1.5 < est.ci_high
    assert est.std_error > 0


def test_estimate_ate_public_api() -> None:
    """Public estimator falls back to DML when DoWhy isn't importable."""
    data = _make_synthetic(true_effect=0.8, n=400)
    est = estimate_ate(
        CausalConfig(
            treatment="T",
            outcome="Y",
            confounders=("W1", "W2"),
            data=data,
        )
    )
    assert est.method in {"double_ml", "dowhy_backdoor_linear"}
    assert 0.6 < est.ate < 1.0
    assert est.n_obs == 400


def test_zero_effect_confidence_interval_covers_zero() -> None:
    data = _make_synthetic(true_effect=0.0, n=600)
    est = _double_ml_ate(
        CausalConfig(
            treatment="T",
            outcome="Y",
            confounders=("W1", "W2"),
            data=data,
        )
    )
    assert est.ci_low < 0.0 < est.ci_high


def test_raises_on_tiny_sample() -> None:
    data = _make_synthetic(n=10)
    with pytest.raises(ValueError):
        _double_ml_ate(
            CausalConfig(
                treatment="T",
                outcome="Y",
                confounders=("W1", "W2"),
                data=data,
            )
        )
