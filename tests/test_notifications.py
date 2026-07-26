import json
from pathlib import Path

from job_application_agent.application.notifications import LocalNotifier


def test_notifier_removes_path_query_and_fragment(tmp_path: Path) -> None:
    notifier = LocalNotifier(tmp_path)
    notifier.notify(
        kind="captcha",
        message="Human verification detected",
        url="https://careers.example.com/private/path?candidate=value#section",
    )
    lines = (tmp_path / "alerts.ndjson").read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    assert record["origin"] == "https://careers.example.com"
    assert "candidate" not in lines[0]


def test_notifier_deduplicates_identical_alert(tmp_path: Path) -> None:
    notifier = LocalNotifier(tmp_path)
    for _ in range(2):
        notifier.notify(
            kind="site_error",
            message="Page is stuck",
            url="https://careers.example.com/job/1",
        )
    lines = (tmp_path / "alerts.ndjson").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
