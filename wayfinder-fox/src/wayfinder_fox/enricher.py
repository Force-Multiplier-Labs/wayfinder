"""
ProjectContextEnricher - enriches alerts with business context.

1. Extracts namespace/project from alert labels
2. Looks up ProjectContext (K8s CRD or .contextcore.yaml fallback)
3. Attaches business context: criticality, owner, SLOs
4. Emits fox.context.enrich span
5. Returns EnrichedAlert
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from opentelemetry import trace

from wayfinder_fox.kubernetes import ProjectContext, ProjectContextReader
from wayfinder_fox.telemetry import FoxTracer


@dataclass
class Alert:
    """Incoming alert from Alertmanager/Grafana."""

    name: str
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    status: str = "firing"
    source: str = "alertmanager"


@dataclass
class EnrichedAlert:
    """Alert enriched with ProjectContext business metadata."""

    alert: Alert
    project_id: str = ""
    criticality: str = "medium"
    business_owner: str = ""
    alert_channels: List[str] = field(default_factory=list)
    availability_slo: str = ""
    latency_p99: str = ""
    enriched: bool = False


class ProjectContextEnricher:
    """Enriches alerts with ProjectContext business metadata."""

    def __init__(
        self,
        reader: ProjectContextReader,
        tracer: FoxTracer,
    ):
        self._reader = reader
        self._tracer = tracer

    def enrich(self, alert: Alert) -> EnrichedAlert:
        """
        Enrich an alert with ProjectContext.

        Looks up project by namespace label, then project_id label,
        then falls back to YAML.
        """
        namespace = alert.labels.get("namespace")
        project_id = alert.labels.get("project_id", alert.labels.get("project", ""))

        ctx = self._reader.lookup(
            namespace=namespace,
            labels=alert.labels,
            project_id=project_id or None,
        )

        enriched = EnrichedAlert(alert=alert)

        if ctx is not None:
            enriched.project_id = ctx.project_id
            enriched.criticality = ctx.criticality
            enriched.business_owner = ctx.owner
            enriched.alert_channels = ctx.alert_channels
            enriched.availability_slo = ctx.availability_slo
            enriched.latency_p99 = ctx.latency_p99
            enriched.enriched = True
        else:
            enriched.project_id = project_id
            enriched.criticality = alert.labels.get("severity", "medium")

        span = self._tracer.context_enrich(
            alert_name=alert.name,
            project_id=enriched.project_id,
            criticality=enriched.criticality,
            business_owner=enriched.business_owner,
        )
        span.end()

        return enriched
