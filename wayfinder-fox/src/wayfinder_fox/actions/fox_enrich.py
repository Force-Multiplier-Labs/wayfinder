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

from opentelemetry import trace

try:
    from contextcore_rabbit.action import (
        Action,
        ActionResult,
        ActionStatus,
        action_registry,
    )
except ImportError:
    raise ImportError(
        "contextcore-rabbit is required for Rabbit integration. "
        "Install with: pip install wayfinder-fox[rabbit]"
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
            # Alertmanager webhook: process each alert, tolerating per-alert failures
            results = []
            failures = 0
            for alert_data in alerts:
                try:
                    result = self._process_alert(alert_data, context)
                    results.append(result)
                except Exception as e:
                    logger.exception(
                        "Failed to process alert: %s",
                        alert_data.get("labels", {}).get("alertname", "unknown"),
                    )
                    failures += 1
                    results.append({
                        "error": str(e),
                        "alert_name": alert_data.get("labels", {}).get(
                            "alertname", "unknown"
                        ),
                    })

            status = ActionStatus.SUCCESS if failures == 0 else ActionStatus.FAILED
            return ActionResult(
                status=status,
                action_name=self.name,
                message=f"Processed {len(results)} alerts ({failures} failures)",
                data={
                    "alerts_processed": len(results),
                    "failures": failures,
                    "results": results,
                },
            )
        else:
            # Direct trigger: single alert
            try:
                result = self._process_alert(payload, context)
                return ActionResult(
                    status=ActionStatus.SUCCESS,
                    action_name=self.name,
                    message=f"Enriched alert: {result.get('alert_name', 'unknown')}",
                    data=result,
                )
            except Exception as e:
                logger.exception("Failed to process alert")
                return ActionResult(
                    status=ActionStatus.FAILED,
                    action_name=self.name,
                    message=f"Failed to enrich alert: {e}",
                    data={"error": str(e)},
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

        # 1. fox.alert.received — root span for the entire pipeline
        received_span = self._tracer.alert_received(
            alert_name=alert.name,
            criticality=labels.get("severity", "medium"),
            source=source,
        )
        with trace.use_span(received_span, end_on_exit=True):
            # 2. fox.context.enrich — child of received
            enriched, enrich_span = self._enricher.enrich(alert)

            with trace.use_span(enrich_span, end_on_exit=True):
                # 3. Route and dispatch sub-actions — grandchildren of enrich
                dispatched_actions = self._router.dispatch(enriched)

        return {
            "alert_name": alert.name,
            "project_id": enriched.project_id,
            "criticality": enriched.criticality,
            "enriched": enriched.enriched,
            "actions_dispatched": dispatched_actions,
        }
