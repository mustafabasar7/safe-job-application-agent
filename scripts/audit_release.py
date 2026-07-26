from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    path: Path
    rule: str


TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
FORBIDDEN_NAMES = {
    ".env",
    "candidate.json",
    "jobs.json",
}
ALLOWED_TEMPLATE_NAMES = {
    ".env.example",
    "candidate.example.json",
    "jobs.example.json",
}
FORBIDDEN_SUFFIXES = {
    ".db",
    ".doc",
    ".docx",
    ".jpeg",
    ".jpg",
    ".log",
    ".pdf",
    ".png",
    ".sqlite",
    ".sqlite3",
    ".webp",
}
CONTENT_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("google-api-key", re.compile(r"AIza[0-9A-Za-z_-]{30,}")),
    ("openai-compatible-api-key", re.compile(r"\bsk-[0-9A-Za-z_-]{20,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"gh[opusr]_[0-9A-Za-z]{20,}")),
    ("gitlab-token", re.compile(r"glpat-[0-9A-Za-z_-]{20,}")),
    ("slack-token", re.compile(r"xox[baprs]-[0-9A-Za-z-]{20,}")),
    (
        "generic-secret-assignment",
        re.compile(
            r"(?im)^(?:"
            r"[ \t]*(?:export[ \t]+)?[A-Z][A-Z0-9_.-]*"
            r"(?:API[_-]?KEY|TOKEN|PASSWORD|SECRET)[A-Z0-9_.-]*"
            r"[ \t]*[=:][ \t]*['\"]?[0-9A-Za-z_./+=-]{16,}"
            r"|[ \t]*['\"](?:api[_-]?key|token|password|secret)"
            r"[0-9A-Za-z_.-]*['\"][ \t]*:[ \t]*['\"][^'\"\s]{12,}"
            r")"
        ),
    ),
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    (
        "email-address",
        re.compile(
            r"\b[A-Z0-9._%+-]+@(?!example\.com\b)[A-Z0-9.-]+\.[A-Z]{2,}\b",
            re.IGNORECASE,
        ),
    ),
    ("phone-number", re.compile(r"(?<!\w)\+\d{9,15}(?!\w)")),
    ("windows-user-path", re.compile(r"[A-Za-z]:\\Users\\[^\\\r\n]+")),
    ("unix-user-path", re.compile(r"/(?:home|Users)/[^/\r\n]+")),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    root = args.root.resolve()
    findings = audit(root, include_history=True)
    if findings:
        for finding in findings:
            print(f"BLOCKED {finding.rule}: {finding.path}")
        return 1
    print("Release audit: clean")
    return 0


def audit(root: Path, *, include_history: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    for path in _candidate_files(root):
        relative = path.relative_to(root)
        if _forbidden_runtime_name(path.name):
            findings.append(Finding(relative, "runtime-file"))
            continue
        if path.suffix.casefold() in FORBIDDEN_SUFFIXES:
            findings.append(Finding(relative, "personal-or-runtime-artifact"))
            continue
        if path.suffix.casefold() not in TEXT_SUFFIXES and path.name not in {"LICENSE"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            findings.append(Finding(relative, "unreadable-text-file"))
            continue
        for name, pattern in CONTENT_RULES:
            if pattern.search(content):
                findings.append(Finding(relative, name))
    if include_history:
        findings.extend(_audit_git_history(root))
    return findings


def _forbidden_runtime_name(name: str) -> bool:
    lowered = name.casefold()
    if lowered in ALLOWED_TEMPLATE_NAMES:
        return False
    return (
        lowered in FORBIDDEN_NAMES
        or (lowered.startswith(".env.") and lowered != ".env.example")
        or (lowered.startswith("candidate") and lowered.endswith(".json"))
        or (lowered.startswith("profile") and lowered.endswith(".json"))
    )


def _audit_git_history(root: Path) -> list[Finding]:
    objects = subprocess.run(
        ["git", "rev-list", "--objects", "--all"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if objects.returncode != 0:
        return []

    findings: list[Finding] = []
    seen: set[str] = set()
    for line in objects.stdout.splitlines():
        object_id, separator, raw_path = line.partition(" ")
        if not separator or object_id in seen:
            continue
        seen.add(object_id)
        relative = Path(raw_path)
        if _forbidden_runtime_name(relative.name):
            findings.append(Finding(relative, "historical-runtime-file"))
            continue
        if relative.suffix.casefold() in FORBIDDEN_SUFFIXES:
            findings.append(Finding(relative, "historical-personal-artifact"))
            continue
        if relative.suffix.casefold() not in TEXT_SUFFIXES and relative.name not in {
            "LICENSE"
        }:
            continue
        blob = subprocess.run(
            ["git", "cat-file", "blob", object_id],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if blob.returncode != 0:
            continue
        try:
            content = blob.stdout.decode("utf-8")
        except UnicodeDecodeError:
            findings.append(Finding(relative, "historical-unreadable-text-file"))
            continue
        for name, pattern in CONTENT_RULES:
            if pattern.search(content):
                findings.append(Finding(relative, f"historical-{name}"))
    return findings


def _candidate_files(root: Path) -> list[Path]:
    tracked = _git_files(root)
    if tracked is not None:
        return [root / item for item in tracked if (root / item).is_file()]
    ignored_parts = {
        ".data",
        ".git",
        ".mypy_cache",
        ".playwright",
        ".pytest_cache",
        ".ruff_cache",
        ".venv",
        "__pycache__",
    }
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not ignored_parts.intersection(path.relative_to(root).parts)
    ]


def _git_files(root: Path) -> list[Path] | None:
    completed = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return [
        Path(item.decode("utf-8")) for item in completed.stdout.split(b"\0") if item
    ]


if __name__ == "__main__":
    raise SystemExit(main())
