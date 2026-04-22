"""Supplier distress classifier end-to-end tests."""

from __future__ import annotations

import pytest
from asciip_ml_models.distress import train_distress_classifier
from asciip_ml_models.distress.classifier import load_production

pytestmark = [pytest.mark.integration, pytest.mark.req_9]


def test_training_pipeline(seeded_feature_store) -> None:
    result = train_distress_classifier(version="test-v1", register=True, promote=True)
    assert result.n_samples > 50
    assert 0.0 <= result.brier <= 0.25
    assert 0.0 <= result.roc_auc <= 1.0
    # Synthetic suppliers have enough signal that AUC > 0.65.
    assert result.roc_auc > 0.65
    assert result.registry_id


def test_production_model_predicts_probabilities(seeded_feature_store) -> None:
    train_distress_classifier(version="prod-v1", register=True, promote=True)
    model = load_production()
    assert model is not None
    # A supplier in full distress (low OTD, high DPO, high concentration).
    proba_high = model.predict_proba(
        [
            {
                "annual_spend_billions": 2.0,
                "otd_rate_90d": 0.70,
                "dpo_days": 130.0,
                "revenue_concentration_top3": 0.9,
                "tier": 1,
                "category": "assembly",
                "country": "CN",
            }
        ]
    )[0]
    # A healthy supplier.
    proba_low = model.predict_proba(
        [
            {
                "annual_spend_billions": 0.5,
                "otd_rate_90d": 0.99,
                "dpo_days": 60.0,
                "revenue_concentration_top3": 0.2,
                "tier": 2,
                "category": "components",
                "country": "US",
            }
        ]
    )[0]
    assert 0.0 <= proba_low <= 1.0
    assert 0.0 <= proba_high <= 1.0
    assert proba_high > proba_low
