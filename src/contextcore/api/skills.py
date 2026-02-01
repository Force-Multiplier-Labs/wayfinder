"""
A2A-style API facade for agent skills.

Provides a resource.action naming pattern while delegating to the existing
SkillCapabilityEmitter and SkillCapabilityQuerier classes.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from contextcore.skill import (
    SkillCapability,
    SkillManifest,
)

logger = logging.getLogger(__name__)

__all__ = ["SkillsAPI", "CapabilitiesAPI"]


class SkillsAPI:
    """A2A-style API for agent skills.

    Example:
        api = SkillsAPI(agent_id="claude-code")
        api.emit(manifest=my_manifest, capabilities=[cap1, cap2])
        matching = api.query(trigger="format code", budget_tokens=1000)
        api.capabilities.invoke("skill-1", "format", inputs={"code": "..."})
    """

    def __init__(self, agent_id: str, tempo_url: str | None = None) -> None:
        if not agent_id:
            raise ValueError("agent_id cannot be empty")
        self.agent_id = agent_id
        self._tempo_url = tempo_url
        # Lazy-init emitter/querier to avoid import overhead
        self._emitter = None
        self._querier = None
        self._capabilities_api = None

    def _get_emitter(self):
        if self._emitter is None:
            from contextcore.skill.emitter import SkillCapabilityEmitter
            self._emitter = SkillCapabilityEmitter(agent_id=self.agent_id)
        return self._emitter

    def _get_querier(self):
        if self._querier is None:
            from contextcore.skill.querier import SkillCapabilityQuerier
            kwargs = {}
            if self._tempo_url:
                kwargs["tempo_url"] = self._tempo_url
            self._querier = SkillCapabilityQuerier(**kwargs)
        return self._querier

    def emit(self, manifest: SkillManifest, capabilities: list[SkillCapability]) -> None:
        """Register a skill with its capabilities."""
        self._get_emitter().emit_skill_with_capabilities(manifest, capabilities)

    def query(
        self,
        trigger: str,
        category: str | None = None,
        budget_tokens: int | None = None,
    ) -> list[dict[str, Any]]:
        """Query skills based on trigger and optional filters."""
        return self._get_querier().query(
            trigger,
            category=category,
            budget_tokens=budget_tokens,
        )

    def get(self, skill_id: str) -> SkillManifest | None:
        """Retrieve a specific skill by ID."""
        try:
            return self._get_querier().get(skill_id)
        except Exception:
            return None

    def list(self) -> list[SkillManifest]:
        """List all registered skills."""
        return self._get_querier().list()

    @property
    def capabilities(self) -> CapabilitiesAPI:
        """Access capability-specific operations."""
        if self._capabilities_api is None:
            self._capabilities_api = CapabilitiesAPI(self._get_emitter())
        return self._capabilities_api


class CapabilitiesAPI:
    """Nested API for capability-specific operations."""

    def __init__(self, emitter: Any) -> None:
        self._emitter = emitter

    def emit(self, skill_id: str, capability: SkillCapability) -> None:
        """Emit a capability for a skill."""
        self._emitter.emit_capability(skill_id=skill_id, capability=capability)

    def invoke(self, skill_id: str, capability_id: str, inputs: dict[str, Any]) -> None:
        """Invoke a capability."""
        self._emitter.emit_invoked(skill_id, capability_id, inputs)

    def complete(self, skill_id: str, capability_id: str, outputs: dict[str, Any]) -> None:
        """Mark a capability invocation as succeeded."""
        self._emitter.emit_succeeded(skill_id, capability_id, outputs)

    def fail(self, skill_id: str, capability_id: str, error: str) -> None:
        """Mark a capability invocation as failed."""
        self._emitter.emit_failed(skill_id, capability_id, error)
