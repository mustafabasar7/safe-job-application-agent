from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DecisionStatus(StrEnum):
    ACT = "act"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    NEEDS_USER = "needs_user"


class BlockerKind(StrEnum):
    NONE = "none"
    CAPTCHA = "captcha"
    LOGIN = "login"
    MFA = "mfa"
    UNKNOWN_ANSWER = "unknown_answer"
    SENSITIVE_QUESTION = "sensitive_question"
    PROMPT_INJECTION = "prompt_injection"
    FINAL_REVIEW = "final_review"
    SITE_ERROR = "site_error"
    COMPLETED = "completed"


class BrowserCommand(StrEnum):
    CLICK = "click"
    FILL = "fill"
    SELECT = "select"
    CHECK = "check"
    UNCHECK = "uncheck"
    UPLOAD = "upload"
    PRESS = "press"
    SNAPSHOT = "snapshot"


class ValueOrigin(StrEnum):
    NONE = "none"
    PROFILE = "profile"
    LITERAL = "literal"
    FILE = "file"


@dataclass(frozen=True)
class BrowserAction:
    command: BrowserCommand
    target_ref: str | None
    value_origin: ValueOrigin
    value_key: str | None
    literal_value: str | None
    is_final_submit: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> BrowserAction:
        return cls(
            command=BrowserCommand(raw["command"]),
            target_ref=_optional_string(raw.get("target_ref")),
            value_origin=ValueOrigin(raw.get("value_origin", "none")),
            value_key=_optional_string(raw.get("value_key")),
            literal_value=_optional_string(raw.get("literal_value")),
            is_final_submit=bool(raw.get("is_final_submit", False)),
        )


@dataclass(frozen=True)
class ModelDecision:
    status: DecisionStatus
    reason: str
    message: str
    blocker_kind: BlockerKind
    action: BrowserAction | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ModelDecision:
        action_raw = raw.get("action")
        return cls(
            status=DecisionStatus(raw["status"]),
            reason=str(raw["reason"]),
            message=str(raw["message"]),
            blocker_kind=BlockerKind(raw["blocker_kind"]),
            action=BrowserAction.from_dict(action_raw)
            if isinstance(action_raw, dict)
            else None,
        )


@dataclass(frozen=True)
class PageSnapshot:
    url: str
    content: str


def _optional_string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None
