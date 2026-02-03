"""Shared test fixtures for wayfinder-fox."""

from __future__ import annotations

from typing import List

import pytest
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult

from wayfinder_fox.config import FoxConfig
from wayfinder_fox.enricher import Alert
from wayfinder_fox.kubernetes import ProjectContext, ProjectContextReader
from wayfinder_fox.telemetry import FoxTracer


class CollectingExporter(SpanExporter):
    """Test exporter that collects spans in memory."""

    def __init__(self) -> None:
        self.spans: List[ReadableSpan] = []

    def export(self, spans: List[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


class MockProjectContextReader(ProjectContextReader):
    """ProjectContextReader that returns pre-configured contexts."""

    def __init__(self, contexts: dict[str, ProjectContext] | None = None):
        super().__init__()
        self._contexts = contexts or {}

    def lookup(self, namespace=None, labels=None, project_id=None):
        key = project_id or namespace or ""
        return self._contexts.get(key)


@pytest.fixture
def collecting_exporter() -> CollectingExporter:
    return CollectingExporter()


@pytest.fixture
def fox_tracer(collecting_exporter: CollectingExporter) -> FoxTracer:
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(collecting_exporter))
    return FoxTracer(tracer_provider=provider)


@pytest.fixture
def sample_alert() -> Alert:
    return Alert(
        name="KubePodCrashLooping",
        labels={
            "namespace": "commerce",
            "project_id": "checkout-service",
            "severity": "critical",
            "pod": "checkout-api-abc123",
        },
        annotations={
            "summary": "Pod is crash-looping",
        },
        source="alertmanager",
    )


@pytest.fixture
def sample_context() -> ProjectContext:
    return ProjectContext(
        project_id="checkout-service",
        criticality="critical",
        owner="commerce-team",
        alert_channels=["commerce-oncall"],
        availability_slo="99.95",
        latency_p99="200ms",
    )


@pytest.fixture
def fox_config() -> FoxConfig:
    return FoxConfig()


def make_fox_enrich_action(contexts=None):
    """Create a FoxEnrichAction with mocked dependencies for testing."""
    from wayfinder_fox.actions.fox_enrich import FoxEnrichAction
    from wayfinder_fox.enricher import ProjectContextEnricher
    from wayfinder_fox.router import CriticalityRouter

    exporter = CollectingExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = FoxTracer(tracer_provider=provider)
    reader = MockProjectContextReader(contexts=contexts)

    action = FoxEnrichAction.__new__(FoxEnrichAction)
    action.name = "fox_enrich"
    action._tracer = tracer
    action._reader = reader
    action._enricher = ProjectContextEnricher(reader=reader, tracer=tracer)
    action._router = CriticalityRouter(tracer=tracer)
    return action, exporter
