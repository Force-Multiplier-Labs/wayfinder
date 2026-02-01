"""
A2A-style API facade for agent insights.

Provides a resource.action naming pattern while delegating to the existing
InsightEmitter and InsightQuerier classes.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from contextcore.agent.insights import (
    Evidence,
    Insight,
    InsightAudience,
    InsightEmitter,
    InsightQuerier,
    InsightType,
)

__all__ = ["InsightsAPI"]


class InsightsAPI:
    """A2A-style API for agent insights.

    Wraps InsightEmitter and InsightQuerier with resource.action naming.

    Example:
        api = InsightsAPI(project_id="checkout", agent_id="claude")
        insight = api.emit(
            type="decision",
            summary="Chose event-driven architecture",
            confidence=0.92,
        )
        decisions = api.query(type="decision", time_range="7d")
    """

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        session_id: str | None = None,
        tempo_url: str | None = None,
        local_storage_path: str | None = None,
        agent_name: str | None = None,
        agent_description: str | None = None,
    ) -> None:
        self._project_id = project_id
        self._agent_id = agent_id
        self._emitter = InsightEmitter(
            project_id=project_id,
            agent_id=agent_id,
            session_id=session_id,
            local_storage_path=local_storage_path,
            agent_name=agent_name,
            agent_description=agent_description,
        )
        querier_kwargs: dict[str, Any] = {}
        if tempo_url is not None:
            querier_kwargs["tempo_url"] = tempo_url
        if local_storage_path is not None:
            querier_kwargs["local_storage_path"] = local_storage_path
        self._querier = InsightQuerier(**querier_kwargs)

    # --- Emit methods ---

    def emit(
        self,
        type: str,
        summary: str,
        confidence: float,
        audience: str = "both",
        rationale: str | None = None,
        evidence: list[Evidence] | None = None,
        applies_to: list[str] | None = None,
        category: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        **kwargs: Any,
    ) -> Insight:
        """Emit an insight.

        Args:
            type: Insight type (decision, recommendation, lesson, etc.)
            summary: Brief description
            confidence: Confidence score 0.0-1.0
            audience: Target audience (agent, human, both)
            rationale: Reasoning behind insight
            evidence: Supporting evidence references
            applies_to: File paths this insight applies to
            category: Category for grouping
            provider: LLM provider name
            model: LLM model name
            input_tokens: Prompt token count
            output_tokens: Completion token count

        Returns:
            Emitted Insight with trace_id populated.
        """
        return self._emitter.emit(
            insight_type=InsightType(type),
            summary=summary,
            confidence=confidence,
            audience=InsightAudience(audience),
            rationale=rationale,
            evidence=evidence,
            applies_to=applies_to,
            category=category,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            **kwargs,
        )

    def emit_decision(self, summary: str, confidence: float, **kwargs: Any) -> Insight:
        """Emit a decision insight."""
        return self._emitter.emit_decision(summary, confidence, **kwargs)

    def emit_lesson(
        self,
        summary: str,
        category: str,
        confidence: float = 0.9,
        applies_to: list[str] | None = None,
        **kwargs: Any,
    ) -> Insight:
        """Emit a lesson learned."""
        return self._emitter.emit_lesson(summary, category, confidence, applies_to, **kwargs)

    # --- Query methods ---

    def query(
        self,
        project_id: str | None = None,
        type: str | None = None,
        agent_id: str | None = None,
        min_confidence: float | None = None,
        time_range: str = "24h",
        limit: int = 100,
        applies_to: str | None = None,
        category: str | None = None,
    ) -> list[Insight]:
        """Query insights with optional filters."""
        return self._querier.query(
            project_id=project_id or self._project_id,
            insight_type=InsightType(type) if type else None,
            agent_id=agent_id,
            min_confidence=min_confidence,
            time_range=time_range,
            limit=limit,
            applies_to=applies_to,
            category=category,
        )

    def get(self, insight_id: str) -> Insight | None:
        """Retrieve a specific insight by ID.

        Queries recent insights and filters by ID.
        """
        results = self._querier.query(project_id=self._project_id, time_range="30d", limit=500)
        for insight in results:
            if insight.id == insight_id:
                return insight
        return None

    def list(self, project_id: str | None = None, limit: int = 100) -> list[Insight]:
        """List insights for a project (alias for query with minimal filters)."""
        return self.query(project_id=project_id, limit=limit)
