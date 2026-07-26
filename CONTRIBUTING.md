# Contributing

Keep changes small, modular, and testable. Domain rules must not depend on browser or
model adapters. New browser capabilities require an explicit command allowlist entry,
policy validation, and tests. Never add `eval`, model-authored `run-code`, shell
execution, CAPTCHA bypass, stealth plugins, or automatic final submission.

Before opening a pull request:

```powershell
ruff check .
ruff format --check .
mypy src
pytest
python scripts\audit_release.py
git diff --check
```

Use synthetic placeholders in fixtures. Do not contribute real names, contact details,
resumes, screenshots, browser sessions, application answers, or credentials.
