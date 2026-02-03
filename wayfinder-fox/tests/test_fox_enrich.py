"""Tests for FoxEnrichAction Rabbit integration."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from wayfinder_fox.actions.fox_enrich import FoxEnrichAction
from wayfinder_fox.config import FoxConfig
from wayfinder_fox.enricher import Alert
from wayfinder_fox.kubernetes import ProjectContext
from wayfinder_fox.telemetry import FoxTracer

from conftest import CollectingExporter, MockProjectContextReader


class TestFoxEnrichActionValidation:
    """Test payload validation."""

    def _make_action(self):
        """Create a FoxEnrichAction with mocked dependencies."""
        exporter = CollectingExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = FoxTracer(tracer_provider=provider)
        reader = MockProjectContextReader()

        action = FoxEnrichAction.__new__(FoxEnrichAction)
        action._tracer = tracer
        action._reader = reader
        from wayfinder_fox.enricher import ProjectContextEnricher
        from wayfinder_fox.router import CriticalityRouter
        action._enricher = ProjectContextEnricher(reader=reader, tracer=tracer)
        action._router = CriticalityRouter(tracer=tracer)
        return action, exporter

    def test_rejects_empty_payload(self):
        action, _ = self._make_action()
        assert action.validate({}) is not None

    def test_rejects_empty_alerts_array(self):
        action, _ = self._make_action()
        assert action.validate({"alerts": []}) is not None

    def test_accepts_alertmanager_payload(self):
        action, _ = self._make_action()
        payload = {
            "alerts": [
                {"labels": {"alertname": "TestAlert"}, "status": "firing"}
            ]
        }
        assert action.validate(payload) is None

    def test_accepts_direct_trigger_payload(self):
        action, _ = self._make_action()
        payload = {"alert_name": "TestAlert", "labels": {}}
        assert action.validate(payload) is None

    def test_rejects_missing_alert_name(self):
        action, _ = self._make_action()
        payload = {"labels": {"foo": "bar"}}
        assert action.validate(payload) is not None


class TestFoxEnrichActionExecution:
    """Test the full enrichment pipeline via Rabbit action interface."""

    def _make_action(self, contexts=None):
        """Create a FoxEnrichAction with mocked dependencies."""
        exporter = CollectingExporter()
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(exporter))
        tracer = FoxTracer(tracer_provider=provider)
        reader = MockProjectContextReader(contexts=contexts)

        action = FoxEnrichAction.__new__(FoxEnrichAction)
        action.name = "fox_enrich"
        action._tracer = tracer
        action._reader = reader
        from wayfinder_fox.enricher import ProjectContextEnricher
        from wayfinder_fox.router import CriticalityRouter
        action._enricher = ProjectContextEnricher(reader=reader, tracer=tracer)
        action._router = CriticalityRouter(tracer=tracer)
        return action, exporter

    def test_direct_trigger_enrichment(self):
        ctx = ProjectContext(
            project_id="checkout-service",
            criticality="critical",
            owner="commerce-team",
            alert_channels=["commerce-oncall"],
        )
        action, exporter = self._make_action(
            contexts={"checkout-service": ctx}
        )

        payload = {
            "alert_name": "ContextCoreTaskStalled",
            "labels": {
                "project_id": "checkout-service",
                "severity": "critical",
            },
            "annotations": {"summary": "Task stalled"},
        }

        result = action.execute(payload, {"source": "grafana"})

        assert result.status.value == "success"
        assert result.data["alert_name"] == "ContextCoreTaskStalled"
        assert result.data["project_id"] == "checkout-service"
        assert result.data["criticality"] == "critical"
        assert result.data["enriched"] is True
        assert "claude_analysis" in result.data["actions_dispatched"]

    def test_alertmanager_webhook_format(self):
        action, exporter = self._make_action()

        payload = {
            "alerts": [
                {
                    "labels": {
                        "alertname": "ContextCoreExporterFailure",
                        "severity": "critical",
                    },
                    "annotations": {"summary": "OTLP export failed"},
                    "status": "firing",
                },
                {
                    "labels": {
                        "alertname": "ContextCoreInsightLatencyHigh",
                        "severity": "warning",
                    },
                    "annotations": {"summary": "P99 > 500ms"},
                    "status": "firing",
                },
            ]
        }

        result = action.execute(payload, {})

        assert result.status.value == "success"
        assert result.data["alerts_processed"] == 2

    def test_unenriched_alert_uses_severity_fallback(self):
        action, exporter = self._make_action()

        payload = {
            "alert_name": "UnknownAlert",
            "labels": {"severity": "warning"},
        }

        result = action.execute(payload, {})

        assert result.status.value == "success"
        assert result.data["enriched"] is False
        assert result.data["criticality"] == "warning"

    def test_emits_expected_spans(self):
        ctx = ProjectContext(
            project_id="test-project",
            criticality="high",
            owner="test-team",
        )
        action, exporter = self._make_action(
            contexts={"test-project": ctx}
        )

        payload = {
            "alert_name": "TestAlert",
            "labels": {
                "project_id": "test-project",
                "severity": "high",
            },
        }

        action.execute(payload, {})

        span_names = [s.name for s in exporter.spans]
        assert "fox.alert.received" in span_names
        assert "fox.context.enrich" in span_names
        # High criticality routes to context_notify
        assert "fox.action.context_notify" in span_names
