"""
Claude analysis action for critical alerts.

Dispatched when criticality is 'critical'. Sends alert context
to an LLM for root cause analysis suggestions.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from wayfinder_fox.enricher import EnrichedAlert
from wayfinder_fox.telemetry import FoxTracer

logger = logging.getLogger(__name__)


class ClaudeAnalysisAction:
    """Sends enriched alert to Claude for analysis."""

    ACTION_NAME = "claude_analysis"

    def __init__(self, tracer: FoxTracer):
        self._tracer = tracer

    def execute(self, enriched: EnrichedAlert) -> Dict[str, Any]:
        """
        Execute Claude analysis for an enriched alert.

        In production this would call contextcore-beaver for LLM analysis.
        Currently emits a span and returns a placeholder result.
        """
        span = self._tracer.action(
            action_name="claude",
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
                "analysis": "LLM analysis pending - connect contextcore-beaver",
            }
            return result
        finally:
            span.end()
