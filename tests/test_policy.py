import pytest

from job_application_agent.domain.models import (
    BrowserAction,
    BrowserCommand,
    ValueOrigin,
)
from job_application_agent.security.policy import (
    JobPolicy,
    PolicyViolation,
    action_requires_final_approval,
    action_targets_sensitive_question,
    validate_action,
)


def action(**overrides: object) -> BrowserAction:
    values: dict[str, object] = {
        "command": BrowserCommand.FILL,
        "target_ref": "e12",
        "value_origin": ValueOrigin.PROFILE,
        "value_key": "identity.email",
        "literal_value": None,
        "is_final_submit": False,
    }
    values.update(overrides)
    return BrowserAction(**values)  # type: ignore[arg-type]


def test_official_domain_allows_subdomain() -> None:
    policy = JobPolicy(
        company_domain="example.com",
        application_url="https://careers.example.com/jobs/1",
    )
    policy.validate()
    assert policy.permits_url("https://apply.example.com/form")


def test_external_ats_is_rejected_under_strict_policy() -> None:
    policy = JobPolicy(
        company_domain="example.com",
        application_url="https://job-board.invalid/example/1",
    )
    with pytest.raises(PolicyViolation, match="official company domain"):
        policy.validate()


def test_snapshot_ref_is_required() -> None:
    with pytest.raises(PolicyViolation, match="snapshot ref"):
        validate_action(action(target_ref="email-field"))


def test_final_submit_is_always_rejected_by_base_policy() -> None:
    with pytest.raises(PolicyViolation, match="human approval"):
        validate_action(action(is_final_submit=True))


def test_shell_like_keypress_is_rejected() -> None:
    unsafe = action(
        command=BrowserCommand.PRESS,
        target_ref=None,
        value_origin=ValueOrigin.LITERAL,
        value_key=None,
        literal_value="Control+Alt+Delete",
    )
    with pytest.raises(PolicyViolation, match="allowlist"):
        validate_action(unsafe)


def test_file_origin_is_limited_to_upload() -> None:
    with pytest.raises(PolicyViolation, match="only valid for upload"):
        validate_action(action(value_origin=ValueOrigin.FILE))


def test_submit_button_requires_approval_even_if_model_marks_false() -> None:
    click = action(
        command=BrowserCommand.CLICK,
        value_origin=ValueOrigin.NONE,
        value_key=None,
        target_ref="e42",
    )
    snapshot = '- button "Submit application" [ref=e42]'
    assert action_requires_final_approval(click, snapshot)


def test_sensitive_question_is_detected_from_target_context() -> None:
    select = action(
        command=BrowserCommand.SELECT,
        target_ref="e9",
        value_origin=ValueOrigin.LITERAL,
        value_key=None,
        literal_value="Option",
    )
    snapshot = "\n".join(
        (
            '- text "What pronouns should we use?"',
            '- combobox "Pronouns" [ref=e9]',
        )
    )
    assert action_targets_sensitive_question(select, snapshot)
