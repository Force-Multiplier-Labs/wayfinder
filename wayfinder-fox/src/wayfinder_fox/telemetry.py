"""
Fox OTel span emission.

Emits spans matching the Fox Alert Automation dashboard contract:
    - fox.alert.received   attrs: alert.name, alert.criticality, alert.source
    - fox.context.enrich   attrs: alert.name, project.id, alert.criticality, business.owner
    - fox.action.*         attrs: alert.name, project.id, action.name
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource


class FoxTracer:
    """Manages Fox span emission with correct attribute contracts."""

    SERVICE_NAME = "wayfinder-fox"

    def __init__(
        self,
        tracer_provider: Optional[TracerProvider] = None,
        span_exporter: Optional[Any] = None,
    ):
        if tracer_provider is not None:
            self._provider = tracer_provider
        else:
            resource = Resource.create({"service.name": self.SERVICE_NAME})
            self._provider = TracerProvider(resource=resource)
            if span_exporter is not None:
                self._provider.add_span_processor(
                    BatchSpanProcessor(span_exporter)
                )
        self._tracer = self._provider.get_tracer("wayfinder-fox")

    @property
    def tracer(self) -> trace.Tracer:
        return self._tracer

    def alert_received(
        self,
        alert_name: str,
        criticality: str,
        source: str,
        extra_attrs: Optional[Dict[str, str]] = None,
    ) -> trace.Span:
        """Start a fox.alert.received span."""
        attrs: Dict[str, str] = {
            "alert.name": alert_name,
            "alert.criticality": criticality,
            "alert.source": source,
        }
        if extra_attrs:
            attrs.update(extra_attrs)
        return self._tracer.start_span("fox.alert.received", attributes=attrs)

    def context_enrich(
        self,
        alert_name: str,
        project_id: str,
        criticality: str,
        business_owner: str,
        extra_attrs: Optional[Dict[str, str]] = None,
    ) -> trace.Span:
        """Start a fox.context.enrich span."""
        attrs: Dict[str, str] = {
            "alert.name": alert_name,
            "project.id": project_id,
            "alert.criticality": criticality,
            "business.owner": business_owner,
        }
        if extra_attrs:
            attrs.update(extra_attrs)
        return self._tracer.start_span("fox.context.enrich", attributes=attrs)

    def action(
        self,
        action_name: str,
        alert_name: str,
        project_id: str,
        extra_attrs: Optional[Dict[str, str]] = None,
    ) -> trace.Span:
        """Start a fox.action.<name> span."""
        attrs: Dict[str, str] = {
            "alert.name": alert_name,
            "project.id": project_id,
            "action.name": action_name,
        }
        if extra_attrs:
            attrs.update(extra_attrs)
        return self._tracer.start_span(
            f"fox.action.{action_name}", attributes=attrs
        )

    def shutdown(self) -> None:
        """Flush and shut down the tracer provider."""
        self._provider.shutdown()
