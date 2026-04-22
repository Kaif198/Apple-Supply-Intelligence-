"""Margin-sensitivity Ridge regression.

Regresses AAPL's quarterly gross margin (``target_gross_margin``) on the
quarter-end snapshot of commodity prices, commodity vols, and FX rates
from ``features_wide``. The resulting coefficients are the elasticities
consumed by :mod:`asciip_ml_models.montecarlo.simulator` and by the
Margin card on the Executive Summary page.
"""

from asciip_ml_models.margin.ridge import (
    MarginModel,
    MarginTrainingResult,
    build_training_frame,
    train_margin_ridge,
)

__all__ = [
    "MarginModel",
    "MarginTrainingResult",
    "build_training_frame",
    "train_margin_ridge",
]
