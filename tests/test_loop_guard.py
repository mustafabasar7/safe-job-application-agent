import pytest

from job_application_agent.security.loop_guard import (
    repeated_action_block_reason,
    step_budget_block_reason,
)


def test_third_logical_action_is_blocked() -> None:
    reason = repeated_action_block_reason("same", ["same", "other", "same"])
    assert reason == "The same logical action repeated three times"


def test_different_actions_do_not_trigger_repeat_guard() -> None:
    assert repeated_action_block_reason("new", ["one", "two", "three"]) is None


def test_step_budget_stops_before_another_model_loop() -> None:
    assert step_budget_block_reason(29, 30) is None
    assert step_budget_block_reason(30, 30) is not None


def test_invalid_loop_limits_fail_closed() -> None:
    with pytest.raises(ValueError):
        repeated_action_block_reason("same", [], maximum_previous_occurrences=0)
    with pytest.raises(ValueError):
        step_budget_block_reason(0, 0)
