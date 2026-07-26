from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from job_application_agent.domain.models import ModelDecision
from job_application_agent.model.base import ModelError
from job_application_agent.model.contract import ACTION_SCHEMA, parse_decision_json
from job_application_agent.model.prompt import build_decision_prompt
from job_application_agent.storage.quota import RollingQuota


class GeminiDecisionProvider:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        quota: RollingQuota,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._quota = quota

    def quota_status(self) -> tuple[int, int]:
        return self._quota.status()

    def decide(
        self,
        *,
        page_url: str,
        safe_snapshot: str,
        profile_keys: list[str],
        model_context: dict[str, Any],
        recent_actions: list[str],
    ) -> ModelDecision:
        if not self._api_key:
            raise ModelError("Model API key is missing")
        self._quota.reserve()
        payload = {
            "model": self._model,
            "store": False,
            "input": build_decision_prompt(
                page_url=page_url,
                safe_snapshot=safe_snapshot,
                profile_keys=profile_keys,
                model_context=model_context,
                recent_actions=recent_actions,
            ),
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": ACTION_SCHEMA,
            },
        }
        request = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/interactions",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self._api_key,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                raw = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            exc.read()
            raise ModelError(f"Gemini request failed with status {exc.code}") from exc
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ModelError(f"Gemini request failed: {type(exc).__name__}") from exc
        return parse_decision_json(_extract_text(raw))


def _extract_text(response: dict[str, Any]) -> str:
    parts: list[str] = []
    for step in response.get("steps", []):
        if step.get("type") != "model_output":
            continue
        for block in step.get("content", []):
            if block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
    if not parts:
        raise ModelError("Gemini response contains no model output")
    return "\n".join(parts)
