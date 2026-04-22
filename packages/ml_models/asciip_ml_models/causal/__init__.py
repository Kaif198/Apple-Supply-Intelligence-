"""Causal engine — ATE estimation for commodity-shock treatments.

Primary path uses DoWhy's 4-step workflow (model → identify → estimate →
refute). A deterministic Double-ML (partial-out OLS) fallback is always
available so the rest of the stack keeps compiling when DoWhy is
temporarily unavailable.
"""

from asciip_ml_models.causal.engine import (
    CausalConfig,
    CausalEstimate,
    estimate_ate,
    run_refutations,
)

__all__ = ["CausalConfig", "CausalEstimate", "estimate_ate", "run_refutations"]
