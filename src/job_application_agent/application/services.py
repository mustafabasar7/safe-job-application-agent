from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from job_application_agent.application.notifications import LocalNotifier
from job_application_agent.application.profile import Profile
from job_application_agent.browser.playwright_cli import PlaywrightCliBrowser
from job_application_agent.config.settings import Settings, load_json_object
from job_application_agent.model.gemini import GeminiDecisionProvider
from job_application_agent.security.policy import JobPolicy
from job_application_agent.storage.quota import RollingQuota


@dataclass(frozen=True)
class JobRecord:
    job_id: str
    company: str
    role: str
    discovery_url: str
    remote_regions: tuple[str, ...]
    resume_key: str
    policy: JobPolicy


class Services:
    def __init__(self, settings: Settings) -> None:
        settings.validate_runtime()
        self.settings = settings
        self.profile = Profile(load_json_object(settings.candidate_profile_path))
        self.notifier = LocalNotifier(settings.workspace / ".data")
        self.browser = PlaywrightCliBrowser(
            executable=settings.playwright_cli,
            session=settings.playwright_session,
            workspace=settings.workspace,
            headed=settings.headed,
        )
        quota = RollingQuota(
            settings.workspace / ".data" / "gemini-quota.json",
            settings.daily_request_limit,
        )
        self.model = GeminiDecisionProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            quota=quota,
        )
        self._jobs = _load_jobs(settings.jobs_config_path)

    def job(self, job_id: str) -> JobRecord:
        try:
            record = self._jobs[job_id]
        except KeyError as exc:
            raise ValueError(f"Unknown job id: {job_id}") from exc
        self.profile.resolve_file(record.resume_key)
        return record


def _load_jobs(path: Path) -> dict[str, JobRecord]:
    raw = load_json_object(path)
    rows = raw.get("jobs")
    if not isinstance(rows, list):
        raise ValueError("jobs config must contain a jobs array")
    result: dict[str, JobRecord] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Each job must be an object")
        record = _parse_job(row)
        record.policy.validate()
        if record.job_id in result:
            raise ValueError(f"Duplicate job id: {record.job_id}")
        result[record.job_id] = record
    return result


def _parse_job(row: dict[str, Any]) -> JobRecord:
    required = (
        "id",
        "company",
        "role",
        "company_domain",
        "discovery_url",
        "application_url",
        "resume_key",
    )
    missing = [
        key for key in required if not isinstance(row.get(key), str) or not row[key]
    ]
    if missing:
        raise ValueError(f"Job record is missing string fields: {', '.join(missing)}")
    if row.get("remote") is not True:
        raise ValueError("Job record must be explicitly verified as remote")
    remote_regions = row.get("remote_regions")
    if (
        not isinstance(remote_regions, list)
        or not remote_regions
        or not all(
            isinstance(region, str) and region.strip() for region in remote_regions
        )
    ):
        raise ValueError("Job record must contain verified remote_regions")
    policy = JobPolicy(
        company_domain=row["company_domain"],
        application_url=row["application_url"],
    )
    if not policy.permits_url(row["discovery_url"]):
        raise ValueError("Discovery URL is not on the official company domain")
    return JobRecord(
        job_id=row["id"],
        company=row["company"],
        role=row["role"],
        discovery_url=row["discovery_url"],
        remote_regions=tuple(remote_regions),
        resume_key=row["resume_key"],
        policy=policy,
    )
