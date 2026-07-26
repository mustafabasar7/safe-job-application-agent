from __future__ import annotations

from typing import Protocol

from job_application_agent.domain.models import BrowserAction, PageSnapshot


class BrowserProvider(Protocol):
    def available(self) -> bool: ...

    def open(self, url: str) -> PageSnapshot: ...

    def snapshot(self) -> PageSnapshot: ...

    def execute(
        self, action: BrowserAction, resolved_value: str | None
    ) -> PageSnapshot: ...
