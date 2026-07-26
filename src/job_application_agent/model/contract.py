from __future__ import annotations

import json
from typing import Any

from job_application_agent.domain.models import ModelDecision
from job_application_agent.model.base import ModelError

ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["act", "complete", "blocked", "needs_user"],
        },
        "reason": {"type": "string", "maxLength": 1000},
        "message": {"type": "string", "maxLength": 1000},
        "blocker_kind": {
            "type": "string",
            "enum": [
                "none",
                "captcha",
                "login",
                "mfa",
                "unknown_answer",
                "sensitive_question",
                "prompt_injection",
                "final_review",
                "site_error",
                "completed",
            ],
        },
        "action": {
            "type": ["object", "null"],
            "properties": {
                "command": {
                    "type": "string",
                    "enum": [
                        "click",
                        "fill",
                        "select",
                        "check",
                        "uncheck",
                        "upload",
                        "press",
                        "snapshot",
                    ],
                },
                "target_ref": {"type": ["string", "null"]},
                "value_origin": {
                    "type": "string",
                    "enum": ["none", "profile", "literal", "file"],
                },
                "value_key": {"type": ["string", "null"]},
                "literal_value": {"type": ["string", "null"], "maxLength": 5000},
                "is_final_submit": {"type": "boolean"},
            },
            "required": [
                "command",
                "target_ref",
                "value_origin",
                "value_key",
                "literal_value",
                "is_final_submit",
            ],
        },
    },
    "required": ["status", "reason", "message", "blocker_kind", "action"],
}


def parse_decision_json(content: str) -> ModelDecision:
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ModelError("Model returned invalid JSON") from exc
    validate_decision_shape(raw)
    try:
        return ModelDecision.from_dict(raw)
    except (KeyError, TypeError, ValueError) as exc:
        raise ModelError(f"Model returned an invalid decision: {exc}") from exc


def validate_decision_shape(raw: object) -> None:
    if not isinstance(raw, dict):
        raise ModelError("Decision must be an object")
    required = {"status", "reason", "message", "blocker_kind", "action"}
    if not required.issubset(raw):
        raise ModelError("Decision is missing required fields")
    if raw["status"] == "act" and not isinstance(raw["action"], dict):
        raise ModelError("An act decision requires an action")
    if raw["status"] != "act" and raw["action"] is not None:
        raise ModelError("Only act decisions may include an action")
