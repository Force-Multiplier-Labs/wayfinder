"""
CriticalityRouter - routes enriched alerts to actions based on criticality.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from wayfinder_fox.config import FoxConfig
from wayfinder_fox.enricher import EnrichedAlert
from wayfinder_fox.telemetry import FoxTracer


class CriticalityRouter:
    """Routes enriched alerts to action lists based on business criticality."""

    def __init__(
        self,
        tracer: FoxTracer,
        config: Optional[FoxConfig] = None,
    ):
        self._tracer = tracer
        self._config = config or FoxConfig()

    def route(self, enriched: EnrichedAlert) -> List[str]:
        """
        Determine which actions to execute based on criticality.

        Returns list of action names to dispatch.
        """
        criticality = enriched.criticality.lower()
        return list(self._config.routing_table.get(criticality, ["log"]))

    def dispatch(self, enriched: EnrichedAlert) -> List[str]:
        """Route and emit action spans for each dispatched action."""
        actions = self.route(enriched)

        for action_name in actions:
            span = self._tracer.action(
                action_name=action_name,
                alert_name=enriched.alert.name,
                project_id=enriched.project_id,
            )
            span.end()

        return actions
