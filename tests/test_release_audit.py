import subprocess
from pathlib import Path

from scripts.audit_release import audit


def test_release_audit_detects_local_user_path(tmp_path: Path) -> None:
    sample = tmp_path / "bad.txt"
    sample.write_text("C:\\Users\\someone\\resume.pdf", encoding="utf-8")
    findings = audit(tmp_path)
    assert any(finding.rule == "windows-user-path" for finding in findings)


def test_release_audit_accepts_placeholders(tmp_path: Path) -> None:
    sample = tmp_path / "safe.json"
    sample.write_text('{"email": "YOUR_EMAIL", "api_key": ""}', encoding="utf-8")
    assert audit(tmp_path) == []


def test_release_audit_detects_email_and_phone(tmp_path: Path) -> None:
    sample = tmp_path / "bad.txt"
    email = "person" + "@" + "invalid.test"
    phone = "+" + "11234567890"
    sample.write_text(f"{email} {phone}", encoding="utf-8")
    rules = {finding.rule for finding in audit(tmp_path)}
    assert rules == {"email-address", "phone-number"}


def test_release_audit_scans_untracked_nonignored_files(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    safe = tmp_path / "safe.txt"
    safe.write_text("safe", encoding="utf-8")
    subprocess.run(["git", "add", "safe.txt"], cwd=tmp_path, check=True)
    secret = "AIza" + ("x" * 32)
    (tmp_path / "untracked.txt").write_text(secret, encoding="utf-8")
    rules = {finding.rule for finding in audit(tmp_path)}
    assert "google-api-key" in rules
