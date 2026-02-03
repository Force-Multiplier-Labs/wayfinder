"""
Context-enriched notification action.

Dispatched for critical and high severity alerts. Sends enriched
alert context to configured notification channels.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from wayfinder_fox.enricher import EnrichedAlert
from wayfinder_fox.telemetry import FoxTracer

logger = logging.getLogger(__name__)


class ContextNotifyAction:
    """Sends context-enriched notification."""

    ACTION_NAME = "context_notify"

    def __init__(self, tracer: FoxTracer):
        self._tracer = tracer

    def execute(self, enriched: EnrichedAlert) -> Dict[str, Any]:
        """
        Send a context-enriched notification.

        In production this would dispatch to Slack/PagerDuty/email
        with business context attached.
        """
        span = self._tracer.action(
            action_name="context_notify",
            alert_name=enriched.alert.name,
            project_id=enriched.project_id,
            extra_attrs={
                "alert.criticality": enriched.criticality,
                "business.owner": enriched.business_owner,
            },
        )

        try:
            result = {
                "action": self.ACTION_NAME,
                "alert": enriched.alert.name,
                "project": enriched.project_id,
                "channels": enriched.alert_channels,
                "owner": enriched.business_owner,
                "notified": True,
            }
            logger.info(
                "Notification sent for %s (project=%s, owner=%s)",
                enriched.alert.name,
                enriched.project_id,
                enriched.business_owner,
            )
            return result
        finally:
            span.end()
