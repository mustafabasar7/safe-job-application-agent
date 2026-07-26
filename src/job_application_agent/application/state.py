from __future__ import annotations

from typing import Any

from typing_extensions import TypedDict


class WorkflowState(TypedDict, total=False):
    job_id: str
    current_url: str
    snapshot: str
    decision: dict[str, Any] | None
    step: int
    recent_actions: list[str]
    status: str
    blocker_kind: str
    message: str
