"""Unit tests for :mod:`asciip_shared.config`."""

from __future__ import annotations

import pytest

from asciip_shared.config import Settings, get_settings, reset_settings_cache
from asciip_shared.exceptions import ConfigurationError


pytestmark = pytest.mark.unit


def test_defaults_load_without_any_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Ensure nothing from a developer's real .env bleeds in.
    for key in list(monkeypatch._setitem.keys() if hasattr(monkeypatch, "_setitem") else []):
        monkeypatch.delenv(key, raising=False)
    for key in (
        "ASCIIP_ENV",
        "ASCIIP_LOG_LEVEL",
        "ASCIIP_DCF_WACC",
        "FRED_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    reset_settings_cache()
    s = Settings()  # type: ignore[call-arg]
    assert s.env == "development"
    assert s.log_level == "INFO"
    assert 0 < s.dcf_wacc < 1
    assert s.dcf_horizon_years == 5
    assert s.mc_iterations == 10_000
    assert s.cors_origin_list == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]


def test_production_rejects_wildcard_cors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASCIIP_ENV", "production")
    monkeypatch.setenv("ASCIIP_CORS_ORIGINS", "*")
    reset_settings_cache()
    with pytest.raises(ConfigurationError):
        get_settings()


def test_invalid_dcf_wacc_fails_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ASCIIP_DCF_WACC", "1.5")
    reset_settings_cache()
    with pytest.raises(ConfigurationError):
        get_settings()


def test_source_enabled_reflects_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", "abc")
    monkeypatch.delenv("MARKETAUX_API_KEY", raising=False)
    reset_settings_cache()
    s = get_settings()
    assert s.source_enabled("fred") is True
    assert s.source_enabled("marketaux") is False
    assert s.source_enabled("unknown") is False
