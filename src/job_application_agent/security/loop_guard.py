from __future__ import annotations


def repeated_action_block_reason(
    signature: str,
    recent_signatures: list[str],
    *,
    maximum_previous_occurrences: int = 2,
) -> str | None:
    if maximum_previous_occurrences < 1:
        raise ValueError("maximum_previous_occurrences must be positive")
    if recent_signatures.count(signature) >= maximum_previous_occurrences:
        return "The same logical action repeated three times"
    return None


def step_budget_block_reason(step: int, maximum_steps: int) -> str | None:
    if maximum_steps < 1:
        raise ValueError("maximum_steps must be positive")
    if step >= maximum_steps:
        return (
            "Step budget reached. Inspect the browser, then reply DEVAM to grant "
            "another tranche."
        )
    return None
