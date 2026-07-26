from pathlib import Path

import pytest

from job_application_agent.application.services import _load_jobs


def write_jobs(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "jobs-config.json"
    path.write_text(body, encoding="utf-8")
    return path


def test_job_must_be_explicitly_remote(tmp_path: Path) -> None:
    path = write_jobs(
        tmp_path,
        """{
          "jobs": [{
            "id": "one",
            "company": "Example",
            "role": "Engineer",
            "company_domain": "careers.example.com",
            "discovery_url": "https://careers.example.com/jobs/one",
            "application_url": "https://careers.example.com/jobs/one",
            "remote": false,
            "remote_regions": ["Global"],
            "resume_key": "documents.resume"
          }]
        }""",
    )
    with pytest.raises(ValueError, match="explicitly verified as remote"):
        _load_jobs(path)


def test_discovery_url_must_be_official(tmp_path: Path) -> None:
    path = write_jobs(
        tmp_path,
        """{
          "jobs": [{
            "id": "one",
            "company": "Example",
            "role": "Engineer",
            "company_domain": "careers.example.com",
            "discovery_url": "https://job-board.invalid/jobs/one",
            "application_url": "https://careers.example.com/jobs/one",
            "remote": true,
            "remote_regions": ["Global"],
            "resume_key": "documents.resume"
          }]
        }""",
    )
    with pytest.raises(ValueError, match="Discovery URL"):
        _load_jobs(path)
