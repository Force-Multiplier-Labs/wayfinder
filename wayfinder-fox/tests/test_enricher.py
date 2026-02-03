"""Tests for ProjectContextEnricher."""

from __future__ import annotations

from tests.conftest import CollectingExporter, MockProjectContextReader
from wayfinder_fox.enricher import Alert, ProjectContextEnricher
from wayfinder_fox.kubernetes import ProjectContext
from wayfinder_fox.telemetry import FoxTracer


def test_enrich_with_context(
    fox_tracer: FoxTracer,
    collecting_exporter: CollectingExporter,
    sample_alert: Alert,
    sample_context: ProjectContext,
):
    """Enrichment attaches business context from ProjectContext."""
    reader = MockProjectContextReader(
        contexts={"checkout-service": sample_context}
    )
    enricher = ProjectContextEnricher(reader=reader, tracer=fox_tracer)

    result, span = enricher.enrich(sample_alert)
    span.end()

    assert result.enriched is True
    assert result.project_id == "checkout-service"
    assert result.criticality == "critical"
    assert result.business_owner == "commerce-team"
    assert result.alert_channels == ["commerce-oncall"]
    assert result.availability_slo == "99.95"

    # Verify fox.context.enrich span was emitted
    fox_tracer.shutdown()
    enrich_spans = [s for s in collecting_exporter.spans if s.name == "fox.context.enrich"]
    assert len(enrich_spans) == 1
    attrs = dict(enrich_spans[0].attributes)
    assert attrs["project.id"] == "checkout-service"
    assert attrs["business.owner"] == "commerce-team"


def test_enrich_without_context(
    fox_tracer: FoxTracer,
    collecting_exporter: CollectingExporter,
    sample_alert: Alert,
):
    """Enrichment falls back to alert labels when no ProjectContext found."""
    reader = MockProjectContextReader(contexts={})
    enricher = ProjectContextEnricher(reader=reader, tracer=fox_tracer)

    result, span = enricher.enrich(sample_alert)
    span.end()

    assert result.enriched is False
    assert result.project_id == "checkout-service"  # from alert labels
    assert result.criticality == "critical"  # from alert severity label
    assert result.business_owner == ""


def test_enrich_emits_span_even_without_context(
    fox_tracer: FoxTracer,
    collecting_exporter: CollectingExporter,
):
    """A span is always emitted even when enrichment has no ProjectContext."""
    alert = Alert(name="Unknown", labels={}, source="test")
    reader = MockProjectContextReader(contexts={})
    enricher = ProjectContextEnricher(reader=reader, tracer=fox_tracer)

    _, span = enricher.enrich(alert)
    span.end()
    fox_tracer.shutdown()

    assert len(collecting_exporter.spans) == 1
    assert collecting_exporter.spans[0].name == "fox.context.enrich"
