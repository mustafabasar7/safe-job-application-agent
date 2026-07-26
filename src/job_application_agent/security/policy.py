from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

from job_application_agent.domain.models import (
    BrowserAction,
    BrowserCommand,
    ValueOrigin,
)


class PolicyViolation(ValueError):
    pass


@dataclass(frozen=True)
class JobPolicy:
    company_domain: str
    application_url: str

    def validate(self) -> None:
        requested_host = _host(self.application_url)
        company_host = self.company_domain.casefold().strip(".")
        if not requested_host or not company_host:
            raise PolicyViolation("Company domain and application URL are required")
        if not _same_site(requested_host, company_host):
            raise PolicyViolation(
                "Application URL is not on the configured official company domain"
            )

    def permits_url(self, url: str) -> bool:
        return _same_site(_host(url), self.company_domain.casefold().strip("."))


_REF_PATTERN = re.compile(r"^e\d+$")
_SAFE_KEYS = {
    "Enter",
    "Tab",
    "Escape",
    "ArrowDown",
    "ArrowUp",
    "Space",
}


def validate_action(action: BrowserAction) -> None:
    commands_requiring_target = {
        BrowserCommand.CLICK,
        BrowserCommand.FILL,
        BrowserCommand.SELECT,
        BrowserCommand.CHECK,
        BrowserCommand.UNCHECK,
    }
    if action.command in commands_requiring_target and (
        not action.target_ref or not _REF_PATTERN.fullmatch(action.target_ref)
    ):
        raise PolicyViolation("Action target must be a current Playwright snapshot ref")
    if action.is_final_submit:
        raise PolicyViolation(
            "Final submit requires an explicit human approval interrupt"
        )
    if (
        action.command is BrowserCommand.PRESS
        and action.literal_value not in _SAFE_KEYS
    ):
        raise PolicyViolation("Keyboard key is not on the allowlist")
    if (
        action.value_origin is ValueOrigin.FILE
        and action.command is not BrowserCommand.UPLOAD
    ):
        raise PolicyViolation("File values are only valid for upload actions")
    if (
        action.command is BrowserCommand.UPLOAD
        and action.value_origin is not ValueOrigin.FILE
    ):
        raise PolicyViolation("Upload actions must use a configured file key")
    if action.command in {BrowserCommand.FILL, BrowserCommand.SELECT} and (
        action.value_origin not in {ValueOrigin.PROFILE, ValueOrigin.LITERAL}
    ):
        raise PolicyViolation("Fill and select require a profile or literal value")


_FINAL_WORDS = re.compile(
    r"\b(submit|send application|apply now|complete application|finish application)\b",
    re.IGNORECASE,
)
_SENSITIVE_WORDS = re.compile(
    r"\b(gender|pronouns?|race|ethnicity|disability|disabled|veteran|"
    r"sexual orientation|religion|marital status|date of birth|age)\b",
    re.IGNORECASE,
)


def action_requires_final_approval(action: BrowserAction, snapshot: str) -> bool:
    if action.command is BrowserCommand.PRESS and action.literal_value == "Enter":
        return bool(_FINAL_WORDS.search(snapshot))
    if action.command is not BrowserCommand.CLICK or not action.target_ref:
        return False
    return bool(_FINAL_WORDS.search(_target_context(snapshot, action.target_ref)))


def action_targets_sensitive_question(action: BrowserAction, snapshot: str) -> bool:
    if action.command not in {
        BrowserCommand.FILL,
        BrowserCommand.SELECT,
        BrowserCommand.CHECK,
        BrowserCommand.UNCHECK,
    }:
        return False
    if not action.target_ref:
        return False
    return bool(_SENSITIVE_WORDS.search(_target_context(snapshot, action.target_ref)))


def _target_context(snapshot: str, target_ref: str) -> str:
    lines = snapshot.splitlines()
    for index, line in enumerate(lines):
        if f"ref={target_ref}" in line:
            start = max(0, index - 2)
            end = min(len(lines), index + 3)
            return "\n".join(lines[start:end])
    return ""


def _host(url: str) -> str:
    return (urlparse(url).hostname or "").casefold().strip(".")


def _same_site(host: str, expected: str) -> bool:
    return host == expected or host.endswith("." + expected)
