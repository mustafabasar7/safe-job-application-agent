from pathlib import Path

from pytest import MonkeyPatch

from job_application_agent.config.settings import Settings


def test_provider_specific_key_is_backward_compatible(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("MODEL_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-key")
    monkeypatch.setenv("MODEL_NAME", "synthetic-model")
    settings = Settings.from_environment(tmp_path)
    assert settings.model_api_key == "synthetic-key"
    assert settings.model_provider == "gemini"


def test_openai_compatible_defaults_to_deepseek_model(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "openai_compatible")
    monkeypatch.delenv("MODEL_NAME", raising=False)
    settings = Settings.from_environment(tmp_path)
    assert settings.model_name == "deepseek-v4-flash"
