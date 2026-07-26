from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch

from job_application_agent.browser.factory import (
    UnsupportedBrowserProvider,
    create_browser_provider,
)
from job_application_agent.browser.playwright_cli import PlaywrightCliBrowser
from job_application_agent.model.base import ModelError
from job_application_agent.model.factory import create_decision_provider
from job_application_agent.model.gemini import GeminiDecisionProvider
from job_application_agent.model.openai_compatible import (
    OpenAICompatibleDecisionProvider,
)
from job_application_agent.storage.quota import RollingQuota


def quota(tmp_path: Path) -> RollingQuota:
    return RollingQuota(tmp_path / "quota.json", 10)


def test_model_factory_supports_two_independent_adapters(tmp_path: Path) -> None:
    gemini = create_decision_provider(
        provider="gemini",
        api_key="",
        model="synthetic-gemini-model",
        base_url="",
        quota=quota(tmp_path),
    )
    compatible = create_decision_provider(
        provider="openai_compatible",
        api_key="",
        model="synthetic-compatible-model",
        base_url="https://api.example.com",
        quota=quota(tmp_path),
    )
    assert isinstance(gemini, GeminiDecisionProvider)
    assert isinstance(compatible, OpenAICompatibleDecisionProvider)


def test_remote_compatible_endpoint_requires_https(tmp_path: Path) -> None:
    with pytest.raises(ModelError, match="HTTPS"):
        create_decision_provider(
            provider="openai_compatible",
            api_key="",
            model="synthetic-model",
            base_url="http://api.example.com",
            quota=quota(tmp_path),
        )


def test_local_compatible_endpoint_may_use_http(tmp_path: Path) -> None:
    provider = create_decision_provider(
        provider="openai_compatible",
        api_key="",
        model="synthetic-model",
        base_url="http://127.0.0.1:8000/v1",
        quota=quota(tmp_path),
    )
    assert isinstance(provider, OpenAICompatibleDecisionProvider)


def test_browser_factory_uses_official_playwright_cli(tmp_path: Path) -> None:
    provider = create_browser_provider(
        provider="playwright_cli",
        executable="playwright-cli",
        session="test",
        workspace=tmp_path,
        headed=True,
    )
    assert isinstance(provider, PlaywrightCliBrowser)


def test_cloakbrowser_is_explicitly_rejected(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedBrowserProvider, match="anti-detection"):
        create_browser_provider(
            provider="cloakbrowser",
            executable="cloakbrowser",
            session="test",
            workspace=tmp_path,
            headed=True,
        )


class FakeHttpResponse:
    def __enter__(self) -> FakeHttpResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        decision = {
            "status": "needs_user",
            "reason": "A fact is unavailable",
            "message": "Ask the applicant",
            "blocker_kind": "unknown_answer",
            "action": None,
        }
        body = {"choices": [{"message": {"content": json.dumps(decision)}}]}
        return json.dumps(body).encode()


def test_compatible_provider_has_finite_json_request(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: urllib.request.Request, timeout: int) -> FakeHttpResponse:
        captured["payload"] = json.loads(request.data or b"{}")
        captured["timeout"] = timeout
        return FakeHttpResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = OpenAICompatibleDecisionProvider(
        api_key="runtime-key",
        model="synthetic-model",
        base_url="https://api.example.com",
        quota=quota(tmp_path),
    )
    decision = provider.decide(
        page_url="https://careers.example.com/job/1",
        safe_snapshot='textbox "Name" [ref=e1]',
        profile_keys=["identity.first_name"],
        model_context={},
        recent_actions=[],
    )
    payload = captured["payload"]
    assert payload["response_format"] == {"type": "json_object"}
    assert payload["max_tokens"] == 1600
    assert payload["stream"] is False
    assert captured["timeout"] == 120
    assert decision.blocker_kind.value == "unknown_answer"
