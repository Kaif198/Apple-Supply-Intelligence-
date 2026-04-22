"""AAPL factor regression — excess returns vs supply-stress + macro factors."""

from asciip_ml_models.factor.regression import (
    FactorModel,
    FactorTrainingResult,
    train_factor_regression,
)

__all__ = ["FactorModel", "FactorTrainingResult", "train_factor_regression"]
