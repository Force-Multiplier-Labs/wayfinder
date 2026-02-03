"""
FoxEnrichAction - Rabbit action that dispatches to Fox enrichment pipeline.

When an alert arrives at Rabbit with rabbit_action: "fox_enrich" label,
Rabbit dispatches to this action. Flow:

1. Rabbit receives alert -> dispatches to FoxEnrichAction.execute()
2. Fox emits fox.alert.received span
3. Fox enriches with ProjectContext -> fox.context.enrich span
4. Fox routes by criticality
5. Fox dispatches sub-actions -> fox.action.* spans for each
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from contextcore_rabbit.action import (
    Action,
    ActionResult,
    ActionStatus,
    action_registry,
)

from wayfinder_fox.config import FoxConfig
from wayfinder_fox.enricher import Alert, EnrichedAlert, ProjectContextEnricher
from wayfinder_fox.kubernetes import ProjectContextReader
from wayfinder_fox.router import CriticalityRouter
from wayfinder_fox.telemetry import FoxTracer

logger = logging.getLogger(__name__)


@action_registry.register("fox_enrich")
class FoxEnrichAction(Action):
    """Rabbit action that runs Fox context enrichment pipeline."""

    name = "fox_enrich"
    description = "Enrich alert with ProjectContext and route by criticality"

    def __init__(self):
        config = FoxConfig()
        self._tracer = FoxTracer()
        self._reader = ProjectContextReader(
            yaml_path=config.contextcore_yaml_path,
            use_kubernetes=config.use_kubernetes,
        )
        self._enricher = ProjectContextEnricher(
            reader=self._reader,
            tracer=self._tracer,
        )
        self._router = CriticalityRouter(
            tracer=self._tracer,
            config=config,
        )

    def validate(self, payload: Dict[str, Any]) -> Optional[str]:
        """Validate alert payload has required fields."""
        if not payload:
            return "Empty payload"

        # Alertmanager webhook format has "alerts" array
        alerts = payload.get("alerts")
        if alerts is not None:
            if not isinstance(alerts, list) or len(alerts) == 0:
                return "Alertmanager payload must have non-empty 'alerts' array"
            return None

        # Direct trigger format needs at least an alert name
        if not payload.get("alert_name") and not payload.get("alertname"):
            return "Payload must have 'alert_name' or 'alertname'"

        return None

    def execute(
        self, payload: Dict[str, Any], context: Dict[str, Any]
    ) -> ActionResult:
        """
        Execute Fox enrichment pipeline for incoming alert(s).

        Handles both Alertmanager webhook format (alerts array) and
        direct trigger format (single alert).
        """
        alerts = payload.get("alerts")

        if alerts is not None:
            # Alertmanager webhook: process each alert
            results = []
            for alert_data in alerts:
                result = self._process_alert(alert_data, context)
                results.append(result)

            return ActionResult(
                status=ActionStatus.SUCCESS,
                action_name=self.name,
                message=f"Processed {len(results)} alerts",
                data={"alerts_processed": len(results), "results": results},
            )
        else:
            # Direct trigger: single alert
            result = self._process_alert(payload, context)
            return ActionResult(
                status=ActionStatus.SUCCESS,
                action_name=self.name,
                message=f"Enriched alert: {result.get('alert_name', 'unknown')}",
                data=result,
            )

    def _process_alert(
        self, alert_data: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single alert through the Fox pipeline."""
        labels = alert_data.get("labels", {})
        annotations = alert_data.get("annotations", {})
        alert_name = (
            labels.get("alertname")
            or alert_data.get("alert_name")
            or alert_data.get("alertname", "unknown")
        )
        source = context.get("source", alert_data.get("source", "alertmanager"))
        status = alert_data.get("status", "firing")

        alert = Alert(
            name=alert_name,
            labels=labels,
            annotations=annotations,
            status=status,
            source=source,
        )

        # 1. fox.alert.received
        received_span = self._tracer.alert_received(
            alert_name=alert.name,
            criticality=labels.get("severity", "medium"),
            source=source,
        )
        received_span.end()

        # 2. fox.context.enrich
        enriched = self._enricher.enrich(alert)

        # 3. Route and dispatch sub-actions
        dispatched_actions = self._router.dispatch(enriched)

        return {
            "alert_name": alert.name,
            "project_id": enriched.project_id,
            "criticality": enriched.criticality,
            "enriched": enriched.enriched,
            "actions_dispatched": dispatched_actions,
        }
