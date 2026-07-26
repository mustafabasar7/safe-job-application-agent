from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    workspace: Path
    model_provider: str
    model_api_key: str
    model_name: str
    model_base_url: str
    daily_request_limit: int
    candidate_profile_path: Path
    jobs_config_path: Path
    browser_provider: str
    playwright_cli: str
    playwright_session: str
    headed: bool
    max_steps: int

    @classmethod
    def from_environment(cls, workspace: Path | None = None) -> Settings:
        root = (workspace or Path.cwd()).resolve()
        load_dotenv(root / ".env", override=False)
        provider = os.getenv("MODEL_PROVIDER", "gemini").strip().casefold()
        default_model = (
            "gemini-3.6-flash" if provider == "gemini" else "deepseek-v4-flash"
        )
        provider_key = (
            os.getenv("GEMINI_API_KEY", "")
            if provider == "gemini"
            else os.getenv("OPENAI_COMPATIBLE_API_KEY", "")
        )
        configured_name = os.getenv("MODEL_NAME", "").strip()
        if not configured_name and provider == "gemini":
            configured_name = os.getenv("GEMINI_MODEL", "").strip()
        limit = _bounded_integer("MODEL_DAILY_REQUEST_LIMIT", 900, 1, 999)
        max_steps = _bounded_integer("JOB_AGENT_MAX_STEPS", 30, 1, 100)
        return cls(
            workspace=root,
            model_provider=provider,
            model_api_key=os.getenv("MODEL_API_KEY", "").strip()
            or provider_key.strip(),
            model_name=configured_name or default_model,
            model_base_url=os.getenv(
                "MODEL_BASE_URL", "https://api.deepseek.com"
            ).strip(),
            daily_request_limit=limit,
            candidate_profile_path=_required_path("CANDIDATE_PROFILE_PATH"),
            jobs_config_path=_required_path("JOBS_CONFIG_PATH"),
            browser_provider=os.getenv("BROWSER_PROVIDER", "playwright_cli")
            .strip()
            .casefold(),
            playwright_cli=os.getenv("PLAYWRIGHT_CLI", "playwright-cli").strip(),
            playwright_session=os.getenv("PLAYWRIGHT_SESSION", "job-agent").strip(),
            headed=os.getenv("PLAYWRIGHT_HEADLESS", "false").lower()
            not in {"1", "true", "yes"},
            max_steps=max_steps,
        )

    def validate_runtime(self) -> None:
        if self.model_provider not in {"gemini", "openai_compatible"}:
            raise ConfigurationError("Unsupported model provider")
        if not self.model_api_key:
            raise ConfigurationError("Model API key is missing")
        if not self.model_name:
            raise ConfigurationError("Model name is missing")
        if self.browser_provider != "playwright_cli":
            raise ConfigurationError(
                "Only the policy-compliant playwright_cli browser is supported"
            )
        for label, path in (
            ("candidate profile", self.candidate_profile_path),
            ("jobs config", self.jobs_config_path),
        ):
            if not path.is_file():
                raise ConfigurationError(f"{label} file does not exist")


def load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Cannot read JSON object at {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"Expected a JSON object at {path}")
    return value


def _required_path(name: str) -> Path:
    raw = os.getenv(name, "").strip()
    if not raw:
        return Path("__NOT_CONFIGURED__")
    return Path(raw).expanduser().resolve()


def _bounded_integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise ConfigurationError(f"{name} must be between {minimum} and {maximum}")
    return value
