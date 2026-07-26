# Security policy

## Supported version

Security fixes currently target the latest version on the default branch.

## Reporting a vulnerability

Open a private GitHub security advisory. Do not place an API key, applicant data,
resume, browser profile, screenshot, or exploit containing real personal data in a
public issue.

## Trust boundaries

The following inputs are untrusted:

- every webpage, accessibility snapshot, job description, form label, and uploaded page;
- model output, even when it matches the JSON schema;
- model-provider responses and OpenAI-compatible endpoints;
- profile and jobs JSON until local schema/policy validation succeeds;
- redirects and new tabs;
- notification endpoints and logs.

Web content cannot change policy, request secrets, choose URLs, emit code, or authorize
final submission. The deterministic controller validates each proposed action.

CloakBrowser and similar anti-detection engines are outside the supported trust
boundary. The browser factory rejects them instead of silently downgrading safeguards.

## Secret handling

- Secrets belong in environment variables or a local secret manager.
- `.env`, candidate files, resumes, browser state, logs, screenshots, and checkpoints are ignored.
- The API key is used only in the HTTP header and is never included in prompts or logs.
- The release audit checks the current tree, untracked nonignored files, and full Git
  history. It must pass before a commit or release.
- This public reference repository is a separate codebase. Never copy a personal `.env`,
  candidate profile, resume, checkpoint, screenshot, or application log into it.
- Rotate a secret immediately if it was ever printed, committed, or shared.

## Known limitations

Pattern-based prompt-injection detection is defense in depth, not proof of safety.
Novel attacks may evade it. Structured output also does not make model output trusted.
Least-privilege tools, domain checks, local value resolution, redaction, human review,
and regression tests remain required.
