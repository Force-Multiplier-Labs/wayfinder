"""Tests for CriticalityRouter."""

from __future__ import annotations

from tests.conftest import CollectingExporter
from wayfinder_fox.config import FoxConfig
from wayfinder_fox.enricher import Alert, EnrichedAlert
from wayfinder_fox.router import CriticalityRouter
from wayfinder_fox.telemetry import FoxTracer


def _make_enriched(criticality: str = "critical") -> EnrichedAlert:
    return EnrichedAlert(
        alert=Alert(name="TestAlert", source="test"),
        project_id="test-project",
        criticality=criticality,
        business_owner="test-team",
        enriched=True,
    )


def test_route_critical(fox_tracer: FoxTracer):
    """Critical alerts route to claude_analysis and context_notify."""
    router = CriticalityRouter(tracer=fox_tracer)
    actions = router.route(_make_enriched("critical"))
    assert actions == ["claude_analysis", "context_notify"]


def test_route_high(fox_tracer: FoxTracer):
    """High alerts route to context_notify only."""
    router = CriticalityRouter(tracer=fox_tracer)
    actions = router.route(_make_enriched("high"))
    assert actions == ["context_notify"]


def test_route_medium(fox_tracer: FoxTracer):
    """Medium alerts route to log."""
    router = CriticalityRouter(tracer=fox_tracer)
    actions = router.route(_make_enriched("medium"))
    assert actions == ["log"]


def test_route_low(fox_tracer: FoxTracer):
    """Low alerts route to log."""
    router = CriticalityRouter(tracer=fox_tracer)
    actions = router.route(_make_enriched("low"))
    assert actions == ["log"]


def test_route_unknown_defaults_to_log(fox_tracer: FoxTracer):
    """Unknown criticality defaults to log."""
    router = CriticalityRouter(tracer=fox_tracer)
    actions = router.route(_make_enriched("unknown"))
    assert actions == ["log"]


def test_dispatch_emits_action_spans(
    fox_tracer: FoxTracer,
    collecting_exporter: CollectingExporter,
):
    """Dispatch emits a fox.action.* span for each action."""
    router = CriticalityRouter(tracer=fox_tracer)
    actions = router.dispatch(_make_enriched("critical"))
    fox_tracer.shutdown()

    assert actions == ["claude_analysis", "context_notify"]
    action_spans = [s for s in collecting_exporter.spans if s.name.startswith("fox.action.")]
    assert len(action_spans) == 2
    span_names = {s.name for s in action_spans}
    assert "fox.action.claude_analysis" in span_names
    assert "fox.action.context_notify" in span_names


def test_custom_routing_table(fox_tracer: FoxTracer):
    """Custom routing table overrides default routing."""
    config = FoxConfig(routing_table={
        "critical": ["escalate"],
        "high": ["escalate"],
        "medium": ["notify"],
        "low": ["ignore"],
    })
    router = CriticalityRouter(tracer=fox_tracer, config=config)

    assert router.route(_make_enriched("critical")) == ["escalate"]
    assert router.route(_make_enriched("medium")) == ["notify"]
