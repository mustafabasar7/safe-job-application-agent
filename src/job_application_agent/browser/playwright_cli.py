from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from job_application_agent.domain.models import (
    BrowserAction,
    BrowserCommand,
    PageSnapshot,
)


class BrowserError(RuntimeError):
    pass


class PlaywrightCliBrowser:
    """Narrow adapter: the model cannot emit JavaScript, shell, URLs, or CLI flags."""

    def __init__(
        self,
        *,
        executable: str,
        session: str,
        workspace: Path,
        headed: bool,
    ) -> None:
        self._executable = _resolve_executable(executable)
        self._session = session
        self._workspace = workspace
        self._headed = headed

    def available(self) -> bool:
        return bool(shutil.which(self._executable) or Path(self._executable).is_file())

    def open(self, url: str) -> PageSnapshot:
        profile = self._workspace / ".data" / "browser-profile"
        args = ["open", url, "--browser=chrome", f"--profile={profile}"]
        if self._headed:
            args.append("--headed")
        return self._page_state(self._run(args, timeout=120))

    def snapshot(self) -> PageSnapshot:
        return self._page_state(self._run(["snapshot"], timeout=45))

    def execute(
        self, action: BrowserAction, resolved_value: str | None
    ) -> PageSnapshot:
        command = action.command
        target = action.target_ref
        if command in {
            BrowserCommand.CLICK,
            BrowserCommand.CHECK,
            BrowserCommand.UNCHECK,
        }:
            output = self._run([command.value, _required(target)], timeout=60)
        elif command in {BrowserCommand.FILL, BrowserCommand.SELECT}:
            output = self._run(
                [command.value, _required(target), _required(resolved_value)],
                timeout=60,
            )
        elif command is BrowserCommand.PRESS:
            output = self._run(["press", _required(resolved_value)], timeout=60)
        elif command is BrowserCommand.UPLOAD:
            path = Path(_required(resolved_value)).resolve()
            if not path.is_file():
                raise BrowserError("Upload file does not exist")
            if target:
                self._run(["click", target], timeout=60)
            output = self._run(["upload", str(path)], timeout=60)
        elif command is BrowserCommand.SNAPSHOT:
            output = self._run(["snapshot"], timeout=45)
        else:
            raise BrowserError(f"Unsupported browser action: {command}")
        return self._page_state(output)

    def _run(self, args: list[str], *, timeout: int) -> str:
        command = [self._executable, f"-s={self._session}", *args]
        try:
            completed = subprocess.run(
                command,
                cwd=self._workspace,
                text=True,
                encoding="utf-8",
                errors="replace",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BrowserError(f"Playwright CLI failed: {exc}") from exc
        output = completed.stdout or ""
        if completed.returncode != 0 or re.search(r"(?m)^### Error\s*$", output):
            raise BrowserError(
                f"Playwright CLI action failed with exit code {completed.returncode}"
            )
        return output

    def _page_state(self, output: str) -> PageSnapshot:
        url = _last_match(output, (r"- Page URL:\s*(\S+)", r"Page URL:\s*(\S+)"))
        snapshot = _inline_snapshot(output)
        if not snapshot:
            paths = re.findall(r"\[Snapshot\]\(([^)]+)\)", output)
            for raw_path in reversed(paths):
                candidate = Path(raw_path.strip().strip('"'))
                if not candidate.is_absolute():
                    candidate = self._workspace / candidate
                if candidate.is_file():
                    snapshot = candidate.read_text(encoding="utf-8", errors="replace")
                    break
        if not snapshot:
            raise BrowserError("Playwright CLI did not produce a readable snapshot")
        return PageSnapshot(url=url, content=snapshot)


def _resolve_executable(value: str) -> str:
    if os.name == "nt" and not Path(value).suffix:
        return shutil.which(value + ".cmd") or shutil.which(value) or value
    return shutil.which(value) or value


def _required(value: str | None) -> str:
    if not value:
        raise BrowserError("Browser action is missing a required value")
    return value


def _last_match(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            return str(matches[-1]).strip()
    return ""


def _inline_snapshot(output: str) -> str:
    matches = re.findall(
        r"### Snapshot\s*```(?:ya?ml)?\s*\r?\n(.*?)\r?\n```",
        output,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return matches[-1].strip() if matches else ""
