from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from job_application_agent.application.services import Services
from job_application_agent.config.settings import ConfigurationError, Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="job-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "doctor", help="validate local configuration without applying"
    )
    args = parser.parse_args(argv)
    if args.command == "doctor":
        return _doctor()
    return 2


def _doctor() -> int:
    try:
        settings = Settings.from_environment(Path.cwd())
        services = Services(settings)
    except (ConfigurationError, OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    executable = shutil.which(settings.playwright_cli) or shutil.which(
        settings.playwright_cli + ".cmd"
    )
    if not executable or not services.browser.available():
        print("ERROR: playwright-cli is not available", file=sys.stderr)
        return 1
    used, limit = services.model.quota_status()
    print("Configuration: OK")
    print(f"Playwright CLI: {executable}")
    print(f"Model provider: {settings.model_provider}")
    print(f"Model rolling quota: {used}/{limit}")
    print("Candidate values: loaded locally and not printed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
