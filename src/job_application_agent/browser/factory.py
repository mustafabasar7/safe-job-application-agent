from __future__ import annotations

from pathlib import Path

from job_application_agent.browser.base import BrowserProvider
from job_application_agent.browser.playwright_cli import PlaywrightCliBrowser


class UnsupportedBrowserProvider(ValueError):
    pass


def create_browser_provider(
    *,
    provider: str,
    executable: str,
    session: str,
    workspace: Path,
    headed: bool,
) -> BrowserProvider:
    normalized = provider.strip().casefold()
    if normalized == "playwright_cli":
        return PlaywrightCliBrowser(
            executable=executable,
            session=session,
            workspace=workspace,
            headed=headed,
        )
    if normalized == "cloakbrowser":
        raise UnsupportedBrowserProvider(
            "CloakBrowser is an anti-detection browser and is intentionally unsupported"
        )
    raise UnsupportedBrowserProvider(f"Unsupported browser provider: {provider}")
