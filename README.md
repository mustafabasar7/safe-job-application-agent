# Safe Job Application Agent

A security-gated, open-source reference agent for navigating remote-job application
forms on official company domains. It uses pure LangGraph for resumable state,
Gemini for constrained decisions, and the official Playwright CLI for browser actions.

This repository contains no applicant profile, resume, API key, browser state,
checkpoint, screenshot, or machine-specific path. Runtime data is deliberately kept
in ignored local files.

## Safety model

- Official-domain allowlist: the browser may remain only on the configured company domain.
- Untrusted-page boundary: web text is data, never agent instructions.
- Prompt-injection gate: suspicious instruction or secret-exfiltration text pauses before a model call.
- Narrow browser adapter: no model-authored JavaScript, shell command, URL, or CLI flag can execute.
- Local value resolution: the model chooses profile keys; the controller inserts actual values locally.
- PII redaction: known profile values are removed from later page snapshots before model calls.
- Human checkpoints: CAPTCHA, MFA, unknown/sensitive answers, and final submission pause.
- Exact final approval: only `EVET` allows the prepared final submit action.
- Rolling budget: Gemini calls stop at the configured 24-hour cap (maximum 999).
- Release audit: committed files are scanned for secrets, PII, runtime artifacts, and local paths.

The project does not bypass CAPTCHA, fingerprinting, access controls, rate limits, or
site terms. It intentionally uses a normal headed browser by default.

## Quick start

Requirements: Python 3.11+, Node.js, Chrome, and the official `playwright-cli` binary.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
playwright-cli install
Copy-Item .env.example .env
Copy-Item config\candidate.example.json candidate.json
Copy-Item config\jobs.example.json jobs.json
```

Fill only the ignored local files, then set their absolute paths in `.env`:

```text
CANDIDATE_PROFILE_PATH=...
JOBS_CONFIG_PATH=...
```

Validate without opening an application:

```powershell
job-agent doctor
python scripts\audit_release.py
langgraph dev
```

Start a graph thread with `{"job_id": "company-role-001"}`. The LangGraph
Studio/server UI shows interrupts and state. See [the Turkish project guide](docs/PROJE_REHBERI_TR.md)
for the architecture, security model, setup, testing, and extension points.

## Project layout

```text
src/job_application_agent/
  application/   orchestration and profile resolution
  browser/       official Playwright CLI adapter
  config/        environment and JSON validation
  domain/        dependency-free decision types
  model/         Gemini structured-output adapter
  security/      domain, action, redaction, and injection policies
  storage/       rolling quota ledger
tests/           policy and regression tests
skills/          reusable Codex workflow skill
docs/            user-facing educational material
```

## Maturity

This is a safety-first `0.1.0` reference implementation. Career sites differ widely;
expect human intervention for custom widgets and ambiguous questions. Never run it
unattended until you have tested the target domain and reviewed its terms.
