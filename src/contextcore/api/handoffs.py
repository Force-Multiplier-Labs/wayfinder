"""
A2A-style API facade for agent handoffs.

Provides a resource.action naming pattern while delegating to the existing
HandoffManager and HandoffReceiver classes.
"""

from __future__ import annotations

from typing import Any, Generator, Optional

from contextcore.agent.handoff import (
    ExpectedOutput,
    Handoff,
    HandoffManager,
    HandoffPriority,
    HandoffReceiver,
    HandoffResult,
    HandoffStatus,
)
from contextcore.contracts.timeouts import HANDOFF_DEFAULT_TIMEOUT_MS

__all__ = ["HandoffsAPI"]


class HandoffsAPI:
    """A2A-style API for agent handoffs.

    Wraps HandoffManager and HandoffReceiver with resource.action naming.

    Example:
        api = HandoffsAPI(project_id="checkout", agent_id="claude")
        handoff_id = api.create(
            to_agent="o11y",
            capability_id="investigate",
            task="Find root cause of latency spike",
            inputs={"trace_id": "abc123"},
        )
        result = api.await_(handoff_id, timeout_ms=30000)
    """

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        namespace: str = "default",
        storage_type: str | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> None:
        self._project_id = project_id
        self._agent_id = agent_id
        self._manager = HandoffManager(
            project_id=project_id,
            agent_id=agent_id,
            namespace=namespace,
            storage_type=storage_type,
            provider=provider,
            model=model,
        )

    # --- Client-side methods ---

    def create(
        self,
        to_agent: str,
        capability_id: str,
        task: str,
        inputs: dict[str, Any],
        expected_output: ExpectedOutput | None = None,
        priority: str = "normal",
        timeout_ms: int = HANDOFF_DEFAULT_TIMEOUT_MS,
    ) -> str:
        """Create a handoff to another agent.

        Returns:
            Handoff ID for tracking.
        """
        if expected_output is None:
            expected_output = ExpectedOutput(type="generic", fields=[])
        return self._manager.create_handoff(
            to_agent=to_agent,
            capability_id=capability_id,
            task=task,
            inputs=inputs,
            expected_output=expected_output,
            priority=HandoffPriority(priority),
            timeout_ms=timeout_ms,
        )

    def get(self, handoff_id: str) -> HandoffResult:
        """Get current status of a handoff."""
        return self._manager.get_handoff_status(handoff_id)

    def await_(self, handoff_id: str, timeout_ms: int = HANDOFF_DEFAULT_TIMEOUT_MS) -> HandoffResult:
        """Wait for a handoff to complete.

        Note: Uses ``await_`` to avoid Python keyword conflict.
        """
        return self._manager.await_result(handoff_id, timeout_ms=timeout_ms)

    def send(
        self,
        to_agent: str,
        capability_id: str,
        task: str,
        inputs: dict[str, Any],
        expected_output: ExpectedOutput | None = None,
        timeout_ms: int = HANDOFF_DEFAULT_TIMEOUT_MS,
    ) -> HandoffResult:
        """Create and immediately await a handoff (convenience method)."""
        if expected_output is None:
            expected_output = ExpectedOutput(type="generic", fields=[])
        return self._manager.create_and_await(
            to_agent=to_agent,
            capability_id=capability_id,
            task=task,
            inputs=inputs,
            expected_output=expected_output,
            timeout_ms=timeout_ms,
        )

    # --- Server-side methods (require a receiver) ---

    def _get_receiver(self, capabilities: list[str] | None = None) -> HandoffReceiver:
        """Get or create a HandoffReceiver."""
        return HandoffReceiver(
            agent_id=self._agent_id,
            capabilities=capabilities or [],
            namespace=self._manager.namespace,
        )

    def accept(self, handoff_id: str) -> None:
        """Accept an incoming handoff."""
        receiver = self._get_receiver()
        receiver.accept(handoff_id, project_id=self._project_id)

    def complete(self, handoff_id: str, result_trace_id: str) -> None:
        """Complete a handoff with result."""
        receiver = self._get_receiver()
        receiver.complete(handoff_id, project_id=self._project_id, result_trace_id=result_trace_id)

    def fail(self, handoff_id: str, reason: str) -> None:
        """Fail a handoff with error reason."""
        receiver = self._get_receiver()
        receiver.fail(handoff_id, project_id=self._project_id, reason=reason)

    def subscribe(
        self,
        capabilities: list[str],
        project_id: str | None = None,
        poll_interval_s: float = 2.0,
    ) -> Generator[Handoff, None, None]:
        """Subscribe to incoming handoffs as a generator.

        Args:
            capabilities: Capabilities this agent handles
            project_id: Project to poll (defaults to instance project_id)
            poll_interval_s: Seconds between polls
        """
        receiver = self._get_receiver(capabilities)
        yield from receiver.poll_handoffs(
            project_id=project_id or self._project_id,
            poll_interval_s=poll_interval_s,
        )
