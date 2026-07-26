from __future__ import annotations

from job_application_agent.application.state import WorkflowState
from job_application_agent.domain.models import DecisionStatus


def route_after_inspection(state: WorkflowState) -> str:
    return "pause" if state.get("status") == "blocked" else "decide"


def route_after_decision(state: WorkflowState) -> str:
    decision = state.get("decision") or {}
    status = decision.get("status")
    if status == DecisionStatus.ACT.value:
        return "execute"
    if status in {DecisionStatus.BLOCKED.value, DecisionStatus.NEEDS_USER.value}:
        return "pause"
    return "end"


def route_after_budget(state: WorkflowState) -> str:
    return "pause" if state.get("status") == "blocked" else "inspect"


def route_after_pause(state: WorkflowState) -> str:
    return "end" if state.get("status") == "stopped" else "inspect"
