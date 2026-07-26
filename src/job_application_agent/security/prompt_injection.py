from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class InjectionFinding:
    rule: str
    excerpt: str


_INJECTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|forget)\b.{0,60}\b(previous|prior|system|developer)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "secret_exfiltration",
        re.compile(
            r"\b(reveal|print|paste|send|upload|exfiltrate)\b.{0,80}"
            r"\b(api[-_ ]?key|secret|token|password|environment variable|\.env)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "tool_hijack",
        re.compile(
            r"\b(run|execute|open|call)\b.{0,60}"
            r"\b(shell|powershell|terminal|command|external api|webhook)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "prompt_disclosure",
        re.compile(
            r"\b(show|reveal|repeat|print)\b.{0,60}"
            r"\b(system prompt|hidden prompt|instructions)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)


def find_prompt_injection(page_text: str) -> list[InjectionFinding]:
    findings: list[InjectionFinding] = []
    for name, pattern in _INJECTION_RULES:
        match = pattern.search(page_text)
        if match:
            excerpt = " ".join(match.group(0).split())[:160]
            findings.append(InjectionFinding(rule=name, excerpt=excerpt))
    return findings


def wrap_untrusted_content(page_text: str, *, maximum_chars: int = 50_000) -> str:
    bounded = page_text[:maximum_chars]
    digest = hashlib.sha256(bounded.encode("utf-8", errors="replace")).hexdigest()[:16]
    return (
        f'<UNTRUSTED_WEB_CONTENT sha256="{digest}">\n'
        f"{bounded}\n"
        "</UNTRUSTED_WEB_CONTENT>"
    )


def redact_known_values(page_text: str, sensitive_values: list[str]) -> str:
    redacted = page_text
    for value in sorted(set(sensitive_values), key=len, reverse=True):
        clean = value.strip()
        if len(clean) >= 3:
            redacted = re.sub(
                re.escape(clean), "[REDACTED_PROFILE_VALUE]", redacted, flags=re.I
            )
    return redacted
