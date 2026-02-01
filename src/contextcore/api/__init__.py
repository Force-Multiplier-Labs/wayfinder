"""
ContextCore Unified API Package.

Provides individual API access via factory functions and a combined
interface through ContextCoreAPI.

Example:
    # Individual API
    insights = create_insights_api("checkout", "claude")
    insights.emit(type="decision", summary="Chose X", confidence=0.9)

    # Unified API
    api = ContextCoreAPI(project_id="checkout", agent_id="claude")
    api.insights.emit(type="decision", summary="...", confidence=0.9)
    api.handoffs.create(to_agent="o11y", capability_id="investigate", task="...", inputs={})
    api.skills.query(trigger="format")
"""

from __future__ import annotations

from contextcore.api.insights import InsightsAPI
from contextcore.api.handoffs import HandoffsAPI
from contextcore.api.skills import SkillsAPI

__all__ = [
    "InsightsAPI",
    "HandoffsAPI",
    "SkillsAPI",
    "ContextCoreAPI",
    "create_insights_api",
    "create_handoffs_api",
    "create_skills_api",
]


def create_insights_api(project_id: str, agent_id: str, **kwargs) -> InsightsAPI:
    """Create configured InsightsAPI instance."""
    return InsightsAPI(project_id=project_id, agent_id=agent_id, **kwargs)


def create_handoffs_api(project_id: str, agent_id: str, **kwargs) -> HandoffsAPI:
    """Create configured HandoffsAPI instance."""
    return HandoffsAPI(project_id=project_id, agent_id=agent_id, **kwargs)


def create_skills_api(agent_id: str, **kwargs) -> SkillsAPI:
    """Create configured SkillsAPI instance."""
    return SkillsAPI(agent_id=agent_id, **kwargs)


class ContextCoreAPI:
    """Unified API for all ContextCore agent operations.

    Example:
        api = ContextCoreAPI(project_id="checkout", agent_id="claude")
        api.insights.emit(type="decision", summary="...", confidence=0.9)
        api.handoffs.create(to_agent="o11y", capability_id="investigate",
                           task="...", inputs={})
        api.skills.query(trigger="format")
    """

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        tempo_url: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        self.project_id = project_id
        self.agent_id = agent_id

        insights_kwargs: dict = {}
        if tempo_url:
            insights_kwargs["tempo_url"] = tempo_url
        self.insights = InsightsAPI(
            project_id=project_id, agent_id=agent_id, **insights_kwargs,
        )

        handoffs_kwargs: dict = {}
        if provider:
            handoffs_kwargs["provider"] = provider
        if model:
            handoffs_kwargs["model"] = model
        self.handoffs = HandoffsAPI(
            project_id=project_id, agent_id=agent_id, **handoffs_kwargs,
        )

        skills_kwargs: dict = {}
        if tempo_url:
            skills_kwargs["tempo_url"] = tempo_url
        self.skills = SkillsAPI(agent_id=agent_id, **skills_kwargs)
