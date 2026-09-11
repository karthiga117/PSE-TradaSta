"""Configuration tests."""

import pytest

from app.core.config import Settings


def test_default_configuration() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "TradaSta AI"
    assert settings.app_version == "0.1.0"
    assert settings.api_v1_prefix == "/api/v1"


def test_environment_variables_override_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "Test Service")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test Service"
    assert settings.debug is True
    assert settings.log_level == "DEBUG"
