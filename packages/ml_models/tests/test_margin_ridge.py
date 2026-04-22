"""End-to-end test for the margin-sensitivity Ridge.

Uses the synthetic feature store so it runs offline. The tiny training
sample (≤19 quarters) means we can only check structural invariants, not
predictive strength — the goal is to prove the full build → train →
register → predict pipeline works.
"""

from __future__ import annotations

import math

import pytest
from asciip_ml_models.margin import MarginModel, train_margin_ridge
from asciip_ml_models.margin.ridge import FEATURE_NAMES, load_production
from asciip_ml_models.registry import get_registry

pytestmark = [pytest.mark.integration, pytest.mark.req_10]


def test_training_pipeline_end_to_end(seeded_feature_store) -> None:
    result = train_margin_ridge(version="test-v1", register=True, promote=True)
    assert result.n_samples >= 10
    assert result.alpha_selected in {0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0}
    assert result.residual_std >= 0.0
    assert -1.0 <= result.train_r2 <= 1.0
    assert result.registry_id, "model was not persisted in the registry"


def test_promoted_model_loads_from_registry(seeded_feature_store) -> None:
    train_margin_ridge(version="prod-v1", register=True, promote=True)
    model = load_production()
    assert isinstance(model, MarginModel)
    assert model.feature_names == FEATURE_NAMES
    # Elasticity vector has one entry per feature.
    elasticities = model.elasticities_bps_per_10pct()
    assert set(elasticities.keys()) == set(FEATURE_NAMES)
    assert all(math.isfinite(v) for v in elasticities.values())


def test_predict_returns_plausible_margin(seeded_feature_store) -> None:
    train_margin_ridge(version="pred-v1", register=True, promote=True)
    model = load_production()
    assert model is not None
    features = {name: 0.0 for name in FEATURE_NAMES}  # all missing → standardised 0.
    pred = model.predict(features)
    # Apple gross margin in [0.30, 0.55] for any reasonable scenario.
    assert 0.30 < pred < 0.55


def test_registry_promote_exclusivity(seeded_feature_store) -> None:
    train_margin_ridge(version="a", register=True, promote=True)
    train_margin_ridge(version="b", register=True, promote=True)
    prod = get_registry().get_production("margin_sensitivity_ridge")
    assert prod is not None
    assert prod.version == "b"
