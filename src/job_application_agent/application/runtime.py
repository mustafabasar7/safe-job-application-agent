from __future__ import annotations

from functools import lru_cache

from job_application_agent.application.services import Services
from job_application_agent.config.settings import Settings


@lru_cache(maxsize=1)
def services() -> Services:
    return Services(Settings.from_environment())
