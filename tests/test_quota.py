import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from job_application_agent.storage.quota import QuotaExceeded, RollingQuota


def test_quota_uses_rolling_24_hour_window(tmp_path: Path) -> None:
    path = tmp_path / "quota.json"
    old = datetime.now(UTC) - timedelta(hours=25)
    path.write_text(
        json.dumps({"request_timestamps": [old.isoformat()]}), encoding="utf-8"
    )
    quota = RollingQuota(path, limit=1)
    assert quota.status() == (0, 1)
    assert quota.reserve() == (1, 1)
    with pytest.raises(QuotaExceeded):
        quota.reserve()
