"""Tests for Fox telemetry span emission."""

from __future__ import annotations

from tests.conftest import CollectingExporter
from wayfinder_fox.telemetry import FoxTracer


def test_alert_received_span(fox_tracer: FoxTracer, collecting_exporter: CollectingExporter):
    """fox.alert.received emits correct span name and attributes."""
    span = fox_tracer.alert_received(
        alert_name="KubePodCrashLooping",
        criticality="critical",
        source="alertmanager",
    )
    span.end()
    fox_tracer.shutdown()

    assert len(collecting_exporter.spans) == 1
    s = collecting_exporter.spans[0]
    assert s.name == "fox.alert.received"
    attrs = dict(s.attributes)
    assert attrs["alert.name"] == "KubePodCrashLooping"
    assert attrs["alert.criticality"] == "critical"
    assert attrs["alert.source"] == "alertmanager"


def test_context_enrich_span(fox_tracer: FoxTracer, collecting_exporter: CollectingExporter):
    """fox.context.enrich emits correct span name and attributes."""
    span = fox_tracer.context_enrich(
        alert_name="HighErrorRate",
        project_id="checkout-service",
        criticality="critical",
        business_owner="commerce-team",
    )
    span.end()
    fox_tracer.shutdown()

    assert len(collecting_exporter.spans) == 1
    s = collecting_exporter.spans[0]
    assert s.name == "fox.context.enrich"
    attrs = dict(s.attributes)
    assert attrs["alert.name"] == "HighErrorRate"
    assert attrs["project.id"] == "checkout-service"
    assert attrs["alert.criticality"] == "critical"
    assert attrs["business.owner"] == "commerce-team"


def test_action_span(fox_tracer: FoxTracer, collecting_exporter: CollectingExporter):
    """fox.action.<name> emits correct span name and attributes."""
    span = fox_tracer.action(
        action_name="claude",
        alert_name="KubePodCrashLooping",
        project_id="checkout-service",
    )
    span.end()
    fox_tracer.shutdown()

    assert len(collecting_exporter.spans) == 1
    s = collecting_exporter.spans[0]
    assert s.name == "fox.action.claude"
    attrs = dict(s.attributes)
    assert attrs["action.name"] == "claude"
    assert attrs["alert.name"] == "KubePodCrashLooping"
    assert attrs["project.id"] == "checkout-service"


def test_extra_attrs(fox_tracer: FoxTracer, collecting_exporter: CollectingExporter):
    """Extra attributes are included in spans."""
    span = fox_tracer.alert_received(
        alert_name="Test",
        criticality="low",
        source="test",
        extra_attrs={"custom.key": "custom_value"},
    )
    span.end()
    fox_tracer.shutdown()

    attrs = dict(collecting_exporter.spans[0].attributes)
    assert attrs["custom.key"] == "custom_value"
