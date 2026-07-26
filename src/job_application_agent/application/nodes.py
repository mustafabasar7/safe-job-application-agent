from __future__ import annotations

import hashlib
import re
from dataclasses import replace

from langgraph.types import interrupt

from job_application_agent.application.runtime import services
from job_application_agent.application.services import Services
from job_application_agent.application.state import WorkflowState
from job_application_agent.domain.models import BrowserAction, ValueOrigin
from job_application_agent.security.policy import (
    PolicyViolation,
    action_requires_final_approval,
    action_targets_sensitive_question,
    validate_action,
)
from job_application_agent.security.prompt_injection import (
    find_prompt_injection,
    redact_known_values,
)


def open_application(state: WorkflowState) -> WorkflowState:
    runtime = services()
    job = runtime.job(state["job_id"])
    page = runtime.browser.open(job.policy.application_url)
    return {
        "current_url": page.url or job.policy.application_url,
        "snapshot": page.content,
        "step": 0,
        "recent_actions": [],
        "status": "running",
        "blocker_kind": "none",
        "message": "Application page opened",
    }


def inspect_page(state: WorkflowState) -> WorkflowState:
    runtime = services()
    job = runtime.job(state["job_id"])
    if not job.policy.permits_url(state["current_url"]):
        return _blocked(
            "site_error", "Browser left the configured official company domain"
        )
    snapshot = state["snapshot"]
    findings = find_prompt_injection(snapshot)
    if findings:
        rules = ", ".join(finding.rule for finding in findings)
        return _blocked(
            "prompt_injection", f"Potential prompt injection detected: {rules}"
        )
    if re.search(
        r"\b(captcha|recaptcha|hcaptcha|verify you are human)\b", snapshot, re.I
    ):
        return _blocked("captcha", "CAPTCHA or human verification detected")
    if re.search(
        r"\b(two-factor|2fa|multi-factor|verification code)\b", snapshot, re.I
    ):
        return _blocked("mfa", "MFA or verification code detected")
    return {"status": "running", "blocker_kind": "none"}


def decide_next_action(state: WorkflowState) -> WorkflowState:
    runtime = services()
    safe_snapshot = redact_known_values(
        state["snapshot"], runtime.profile.sensitive_values()
    )
    decision = runtime.model.decide(
        page_url=state["current_url"],
        safe_snapshot=safe_snapshot,
        profile_keys=runtime.profile.keys(),
        model_context=runtime.profile.model_context,
        recent_actions=state.get("recent_actions", []),
    )
    action = None
    if decision.action:
        action = {
            "command": decision.action.command.value,
            "target_ref": decision.action.target_ref,
            "value_origin": decision.action.value_origin.value,
            "value_key": decision.action.value_key,
            "literal_value": decision.action.literal_value,
            "is_final_submit": decision.action.is_final_submit,
        }
    return {
        "decision": {
            "status": decision.status.value,
            "reason": decision.reason,
            "message": decision.message,
            "blocker_kind": decision.blocker_kind.value,
            "action": action,
        },
        "status": decision.status.value,
        "blocker_kind": decision.blocker_kind.value,
        "message": decision.message,
    }


def execute_action(state: WorkflowState) -> WorkflowState:
    runtime = services()
    decision = state.get("decision")
    raw = decision.get("action") if decision else None
    if not isinstance(raw, dict):
        return _blocked("site_error", "Model act decision did not contain an action")
    action = BrowserAction.from_dict(raw)
    sensitive_result = _handle_sensitive_action(action, state, runtime)
    if sensitive_result is not None:
        return sensitive_result
    approved_action = _approve_final_action(action, state, runtime)
    if approved_action is None:
        return {
            "status": "stopped",
            "blocker_kind": "final_review",
            "message": "Final submission was not approved",
        }
    return _execute_validated_action(approved_action, state, runtime)


def pause_for_user(state: WorkflowState) -> WorkflowState:
    runtime = services()
    runtime.notifier.notify(
        kind=state.get("blocker_kind", "unknown_answer"),
        message=state.get("message", "Human input is required"),
        url=state.get("current_url", ""),
    )
    answer = interrupt(
        {
            "kind": state.get("blocker_kind", "unknown_answer"),
            "message": state.get("message", "Human input is required"),
        }
    )
    if answer != "DEVAM":
        return {"status": "stopped", "message": "Stopped without an exact DEVAM"}
    page = runtime.browser.snapshot()
    return {
        "current_url": page.url or state["current_url"],
        "snapshot": page.content,
        "status": "running",
        "blocker_kind": "none",
        "message": "Resumed after human intervention",
    }


def enforce_step_budget(state: WorkflowState) -> WorkflowState:
    if state.get("step", 0) < services().settings.max_steps:
        return state
    return _blocked(
        "site_error",
        (
            "Step budget reached. Inspect the browser, then reply DEVAM to grant "
            "another tranche."
        ),
    )


def _handle_sensitive_action(
    action: BrowserAction, state: WorkflowState, runtime: Services
) -> WorkflowState | None:
    if not action_targets_sensitive_question(action, state["snapshot"]):
        return None
    runtime.notifier.notify(
        kind="sensitive_question",
        message="A sensitive question requires a human choice",
        url=state["current_url"],
    )
    answer = interrupt(
        {
            "kind": "sensitive_question",
            "message": (
                "A sensitive question requires a human choice. Fill it in the "
                "browser, then reply exactly DEVAM."
            ),
        }
    )
    if answer != "DEVAM":
        return {
            "status": "stopped",
            "blocker_kind": "sensitive_question",
            "message": "Stopped without an exact DEVAM",
        }
    page = runtime.browser.snapshot()
    return {
        "current_url": page.url or state["current_url"],
        "snapshot": page.content,
        "status": "running",
        "blocker_kind": "none",
        "message": "Sensitive answer handled by the user",
    }


def _approve_final_action(
    action: BrowserAction, state: WorkflowState, runtime: Services
) -> BrowserAction | None:
    if not (
        action.is_final_submit
        or action_requires_final_approval(action, state["snapshot"])
    ):
        return action
    runtime.notifier.notify(
        kind="final_review",
        message="The prepared application is waiting for final review",
        url=state["current_url"],
    )
    answer = interrupt(
        {
            "kind": "final_review",
            "message": "Review the visible application. Reply exactly EVET to submit.",
        }
    )
    return replace(action, is_final_submit=False) if answer == "EVET" else None


def _execute_validated_action(
    action: BrowserAction, state: WorkflowState, runtime: Services
) -> WorkflowState:
    try:
        validate_action(action)
        resolved = _resolve_action_value(action, runtime)
        signature = _action_signature(action)
        recent = state.get("recent_actions", [])
        if recent.count(signature) >= 2:
            return _blocked(
                "site_error", "The same logical action repeated three times"
            )
        page = runtime.browser.execute(action, resolved)
        job = runtime.job(state["job_id"])
        current_url = page.url or state["current_url"]
        if not job.policy.permits_url(current_url):
            raise PolicyViolation(
                "Browser action navigated outside the official domain"
            )
    except (PolicyViolation, ValueError) as exc:
        return _blocked("site_error", str(exc))
    return {
        "current_url": current_url,
        "snapshot": page.content,
        "step": state.get("step", 0) + 1,
        "recent_actions": [*recent[-7:], signature],
        "status": "running",
        "blocker_kind": "none",
        "message": "Browser action completed",
    }


def _resolve_action_value(action: BrowserAction, runtime: Services) -> str | None:
    if action.value_origin in {ValueOrigin.NONE, ValueOrigin.LITERAL}:
        return action.literal_value
    if not action.value_key:
        raise PolicyViolation("Action value key is missing")
    if action.value_origin is ValueOrigin.PROFILE:
        return runtime.profile.resolve(action.value_key)
    if action.value_origin is ValueOrigin.FILE:
        return runtime.profile.resolve_file(action.value_key)
    raise PolicyViolation("Unsupported value origin")


def _action_signature(action: BrowserAction) -> str:
    logical = "|".join(
        (
            action.command.value,
            action.target_ref or "",
            action.value_origin.value,
            action.value_key or "",
        )
    )
    return hashlib.sha256(logical.encode()).hexdigest()[:16]


def _blocked(kind: str, message: str) -> WorkflowState:
    return {"status": "blocked", "blocker_kind": kind, "message": message}
