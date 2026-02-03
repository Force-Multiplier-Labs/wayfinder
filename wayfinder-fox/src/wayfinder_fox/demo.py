"""
Fox demo data generator.

Produces historical Fox spans so the Fox Alert Automation dashboard
shows data immediately after deployment.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from wayfinder_fox.telemetry import FoxTracer


DEMO_ALERTS = [
    {"name": "KubePodCrashLooping", "source": "alertmanager", "criticality": "critical"},
    {"name": "KubePodNotReady", "source": "alertmanager", "criticality": "high"},
    {"name": "TargetDown", "source": "alertmanager", "criticality": "warning"},
    {"name": "HighErrorRate", "source": "grafana", "criticality": "critical"},
    {"name": "DiskSpaceRunningLow", "source": "alertmanager", "criticality": "warning"},
    {"name": "HighLatencyP99", "source": "grafana", "criticality": "high"},
    {"name": "ContextCoreExporterFailure", "source": "alertmanager", "criticality": "critical"},
    {"name": "ContextCoreTaskStalled", "source": "alertmanager", "criticality": "warning"},
]

DEMO_PROJECTS = [
    {"id": "contextcore", "owner": "observability-team", "criticality": "critical"},
    {"id": "checkout-service", "owner": "commerce-team", "criticality": "critical"},
    {"id": "commerce-platform", "owner": "platform-team", "criticality": "high"},
]

ACTIONS_BY_CRITICALITY = {
    "critical": ["claude", "context_notify"],
    "high": ["context_notify"],
    "warning": ["log"],
}


def generate_demo_data(
    span_exporter: Optional[object] = None,
    count: int = 50,
    hours_back: int = 24,
) -> int:
    """
    Generate demo Fox spans.

    Args:
        span_exporter: OTel span exporter (e.g., OTLPSpanExporter)
        count: Number of alert flows to generate
        hours_back: How far back in time to generate data

    Returns:
        Number of spans generated
    """
    tracer = FoxTracer(span_exporter=span_exporter)
    spans_created = 0
    now = datetime.now(timezone.utc)

    for i in range(count):
        alert_def = random.choice(DEMO_ALERTS)
        project_def = random.choice(DEMO_PROJECTS)

        # Compute a random historical timestamp within the hours_back window
        alert_time = now - timedelta(
            hours=random.uniform(0, hours_back),
            minutes=random.uniform(0, 60),
        )
        start_ns = int(alert_time.timestamp() * 1e9)

        # fox.alert.received — 0.5-5ms duration
        span = tracer.alert_received(
            alert_name=alert_def["name"],
            criticality=alert_def["criticality"],
            source=alert_def["source"],
            start_time=start_ns,
        )
        span.end(end_time=start_ns + random.randint(500_000, 5_000_000))
        spans_created += 1

        # fox.context.enrich — starts 1-50ms after alert, 1-100ms duration
        enrich_ns = start_ns + random.randint(1_000_000, 50_000_000)
        span = tracer.context_enrich(
            alert_name=alert_def["name"],
            project_id=project_def["id"],
            criticality=project_def["criticality"],
            business_owner=project_def["owner"],
            start_time=enrich_ns,
        )
        span.end(end_time=enrich_ns + random.randint(1_000_000, 100_000_000))
        spans_created += 1

        # fox.action.* based on criticality — 5-500ms per action
        actions = ACTIONS_BY_CRITICALITY.get(
            project_def["criticality"], ["log"]
        )
        action_start = enrich_ns + random.randint(1_000_000, 10_000_000)
        for action_name in actions:
            span = tracer.action(
                action_name=action_name,
                alert_name=alert_def["name"],
                project_id=project_def["id"],
                start_time=action_start,
            )
            span.end(end_time=action_start + random.randint(5_000_000, 500_000_000))
            spans_created += 1
            action_start += random.randint(1_000_000, 10_000_000)

    tracer.shutdown()
    return spans_created
