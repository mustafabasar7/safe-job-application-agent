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
    ("github-token", re.compile(r"gh[opusr]_[0-9A-Za-z]{20,}")),
    (
        "generic-secret-assignment",
        re.compile(r"(?i)(api[_-]?key|token|password)\s*[=:]\s*['\"][^'\"\s]{12,}"),
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
    findings = audit(root)
    if findings:
        for finding in findings:
            print(f"BLOCKED {finding.rule}: {finding.path}")
        return 1
    print("Release audit: clean")
    return 0


def audit(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in _candidate_files(root):
        relative = path.relative_to(root)
        if path.name in FORBIDDEN_NAMES:
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
