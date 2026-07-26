from __future__ import annotations

from pathlib import Path
from typing import Any

from job_application_agent.config.settings import ConfigurationError


class Profile:
    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @property
    def model_context(self) -> dict[str, Any]:
        value = self._raw.get("model_context", {})
        if not isinstance(value, dict):
            raise ConfigurationError("model_context must be an object")
        return value

    def keys(self) -> list[str]:
        return sorted(_flatten_keys(self._raw, excluded={"model_context"}))

    def sensitive_values(self) -> list[str]:
        return [
            value for value in _flatten_strings(self._raw) if len(value.strip()) >= 3
        ]

    def resolve(self, key: str) -> str:
        current: object = self._raw
        for part in key.split("."):
            if not isinstance(current, dict) or part not in current:
                raise ConfigurationError(f"Unknown profile key: {key}")
            current = current[part]
        if not isinstance(current, str | int | float | bool):
            raise ConfigurationError(f"Profile key is not a scalar value: {key}")
        return str(current)

    def resolve_file(self, key: str) -> str:
        path = Path(self.resolve(key)).expanduser().resolve()
        if not path.is_file():
            raise ConfigurationError(f"Profile file does not exist: {key}")
        return str(path)


def _flatten_keys(
    value: dict[str, Any], *, excluded: set[str], prefix: str = ""
) -> list[str]:
    result: list[str] = []
    for key, child in value.items():
        if key in excluded:
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            result.extend(_flatten_keys(child, excluded=excluded, prefix=path))
        elif isinstance(child, str | int | float | bool):
            result.append(path)
    return result


def _flatten_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for child in value.values():
            result.extend(_flatten_strings(child))
        return result
    if isinstance(value, list):
        result = []
        for child in value:
            result.extend(_flatten_strings(child))
        return result
    return []
