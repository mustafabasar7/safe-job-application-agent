from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path


class QuotaExceeded(RuntimeError):
    pass


class RollingQuota:
    def __init__(self, path: Path, limit: int) -> None:
        self._path = path
        self._limit = limit

    def reserve(self) -> tuple[int, int]:
        events = self._recent_events()
        if len(events) >= self._limit:
            raise QuotaExceeded(
                f"Rolling 24-hour request limit reached: {len(events)}/{self._limit}"
            )
        events.append(datetime.now(UTC))
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(
                {"request_timestamps": [event.isoformat() for event in events]},
                indent=2,
            ),
            encoding="utf-8",
        )
        temporary.replace(self._path)
        return len(events), self._limit

    def status(self) -> tuple[int, int]:
        return len(self._recent_events()), self._limit

    def _recent_events(self) -> list[datetime]:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        result: list[datetime] = []
        for value in raw.get("request_timestamps", []):
            if not isinstance(value, str):
                continue
            try:
                parsed = datetime.fromisoformat(value)
            except ValueError:
                continue
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            normalized = parsed.astimezone(UTC)
            if normalized >= cutoff:
                result.append(normalized)
        return sorted(result)
