from __future__ import annotations

from job_application_agent.model.base import DecisionProvider, ModelError
from job_application_agent.model.gemini import GeminiDecisionProvider
from job_application_agent.model.openai_compatible import (
    OpenAICompatibleDecisionProvider,
)
from job_application_agent.storage.quota import RollingQuota


def create_decision_provider(
    *,
    provider: str,
    api_key: str,
    model: str,
    base_url: str,
    quota: RollingQuota,
) -> DecisionProvider:
    normalized = provider.strip().casefold()
    if normalized == "gemini":
        return GeminiDecisionProvider(api_key=api_key, model=model, quota=quota)
    if normalized == "openai_compatible":
        return OpenAICompatibleDecisionProvider(
            api_key=api_key,
            model=model,
            base_url=base_url,
            quota=quota,
        )
    raise ModelError(f"Unsupported model provider: {provider}")
