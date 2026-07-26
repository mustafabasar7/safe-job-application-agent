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
    gemini_api_key: str
    gemini_model: str
    daily_request_limit: int
    candidate_profile_path: Path
    jobs_config_path: Path
    playwright_cli: str
    playwright_session: str
    headed: bool
    max_steps: int

    @classmethod
    def from_environment(cls, workspace: Path | None = None) -> Settings:
        root = (workspace or Path.cwd()).resolve()
        load_dotenv(root / ".env", override=False)
        limit = _bounded_integer("GEMINI_DAILY_REQUEST_LIMIT", 900, 1, 999)
        max_steps = _bounded_integer("JOB_AGENT_MAX_STEPS", 30, 1, 100)
        return cls(
            workspace=root,
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip(),
            daily_request_limit=limit,
            candidate_profile_path=_required_path("CANDIDATE_PROFILE_PATH"),
            jobs_config_path=_required_path("JOBS_CONFIG_PATH"),
            playwright_cli=os.getenv("PLAYWRIGHT_CLI", "playwright-cli").strip(),
            playwright_session=os.getenv("PLAYWRIGHT_SESSION", "job-agent").strip(),
            headed=os.getenv("PLAYWRIGHT_HEADLESS", "false").lower()
            not in {"1", "true", "yes"},
            max_steps=max_steps,
        )

    def validate_runtime(self) -> None:
        if not self.gemini_api_key:
            raise ConfigurationError("GEMINI_API_KEY is missing")
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
