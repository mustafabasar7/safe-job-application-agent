from __future__ import annotations

from typing import Any, Protocol

from job_application_agent.domain.models import ModelDecision


class DecisionProvider(Protocol):
    def decide(
        self,
        *,
        page_url: str,
        safe_snapshot: str,
        profile_keys: list[str],
        model_context: dict[str, Any],
        recent_actions: list[str],
    ) -> ModelDecision: ...

    def quota_status(self) -> tuple[int, int]: ...


class ModelError(RuntimeError):
    pass
