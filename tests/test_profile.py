from pathlib import Path

import pytest

from job_application_agent.application.profile import Profile
from job_application_agent.config.settings import ConfigurationError


def test_profile_exposes_keys_but_excludes_model_context() -> None:
    profile = Profile(
        {
            "identity": {"email": "private-value"},
            "model_context": {"summary": "approved context"},
        }
    )
    assert profile.keys() == ["identity.email"]
    assert profile.model_context == {"summary": "approved context"}


def test_profile_resolves_nested_scalar() -> None:
    profile = Profile({"work": {"notice_days": 14}})
    assert profile.resolve("work.notice_days") == "14"


def test_unknown_profile_key_fails_closed() -> None:
    profile = Profile({"identity": {"email": "private-value"}})
    with pytest.raises(ConfigurationError, match="Unknown profile key"):
        profile.resolve("identity.phone")


def test_file_resolution_requires_existing_file(tmp_path: Path) -> None:
    profile = Profile({"documents": {"resume": str(tmp_path / "missing.pdf")}})
    with pytest.raises(ConfigurationError, match="does not exist"):
        profile.resolve_file("documents.resume")
