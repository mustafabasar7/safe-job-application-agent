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


def test_release_audit_detects_openai_compatible_and_unquoted_keys(
    tmp_path: Path,
) -> None:
    sample = tmp_path / "bad.env.txt"
    sample.write_text(
        "MODEL_API_KEY=" + "sk-" + ("z" * 32) + "\nSERVICE_SECRET=abcdefghijklmnop",
        encoding="utf-8",
    )
    rules = {finding.rule for finding in audit(tmp_path)}
    assert "openai-compatible-api-key" in rules
    assert "generic-secret-assignment" in rules


def test_release_audit_rejects_nonstandard_candidate_profile_name(
    tmp_path: Path,
) -> None:
    (tmp_path / "candidate.private.json").write_text("{}", encoding="utf-8")
    rules = {finding.rule for finding in audit(tmp_path)}
    assert "runtime-file" in rules


def test_release_audit_detects_secret_removed_from_git_history(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "audit@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Release Audit"],
        cwd=tmp_path,
        check=True,
    )
    sample = tmp_path / "leaked.txt"
    sample.write_text("MODEL_API_KEY=" + "sk-" + ("q" * 32), encoding="utf-8")
    subprocess.run(["git", "add", "leaked.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "temporary"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    sample.write_text("clean", encoding="utf-8")
    subprocess.run(["git", "add", "leaked.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "remove secret"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )

    rules = {finding.rule for finding in audit(tmp_path, include_history=True)}
    assert "historical-openai-compatible-api-key" in rules
