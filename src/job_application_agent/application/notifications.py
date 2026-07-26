from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class LocalNotifier:
    """Emit a deduplicated local alert without sending applicant data externally."""

    data_directory: Path

    def notify(self, *, kind: str, message: str, url: str) -> None:
        safe_url = _origin(url)
        fingerprint = hashlib.sha256(
            f"{kind}|{message}|{safe_url}".encode()
        ).hexdigest()
        self.data_directory.mkdir(parents=True, exist_ok=True)
        marker = self.data_directory / "last-alert.txt"
        try:
            if marker.read_text(encoding="utf-8") == fingerprint:
                return
        except OSError:
            pass
        marker.write_text(fingerprint, encoding="utf-8")
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "kind": kind,
            "message": message,
            "origin": safe_url,
        }
        with (self.data_directory / "alerts.ndjson").open(
            "a", encoding="utf-8"
        ) as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"\a[JOB_AGENT:{kind.upper()}] {message} ({safe_url})", flush=True)
        if os.name == "nt":
            try:
                import winsound

                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except (ImportError, RuntimeError):
                pass


def _origin(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "unknown-origin"
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme}://{parsed.hostname}{port}"
