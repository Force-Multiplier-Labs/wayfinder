"""
Shared fixtures for contextcore-rabbit tests.
"""

import pytest

from contextcore_rabbit.action import Action, ActionRegistry, ActionResult, ActionStatus
from contextcore_rabbit.alert import Alert, AlertSeverity, AlertStatus as AlertAlertStatus


# ---------------------------------------------------------------------------
# Reusable alert payloads
# ---------------------------------------------------------------------------

@pytest.fixture
def grafana_firing_payload():
    """A Grafana alert webhook payload with a single firing alert."""
    return {
        "status": "firing",
        "title": "High Latency Detected",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighLatency",
                    "severity": "critical",
                    "service": "checkout",
                    "rabbit_action": "log",
                },
                "annotations": {
                    "summary": "Latency above SLO",
                    "description": "P99 latency is 2.3s (SLO: 500ms)",
                },
                "startsAt": "2026-01-15T10:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://grafana:3000/alerting/rule/abc",
                "fingerprint": "fp-grafana-001",
            }
        ],
    }


@pytest.fixture
def grafana_resolved_payload():
    """A Grafana alert webhook payload with a resolved alert."""
    return {
        "status": "resolved",
        "alerts": [
            {
                "status": "resolved",
                "labels": {
                    "alertname": "HighLatency",
                    "severity": "warning",
                },
                "annotations": {
                    "summary": "Latency recovered",
                },
                "startsAt": "2026-01-15T10:00:00Z",
                "endsAt": "2026-01-15T10:05:00Z",
                "fingerprint": "fp-grafana-002",
            }
        ],
    }


@pytest.fixture
def alertmanager_payload():
    """An Alertmanager webhook payload."""
    return {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "HighErrorRate",
                    "severity": "critical",
                    "namespace": "production",
                },
                "annotations": {
                    "description": "Error rate is 12% (threshold: 5%)",
                },
                "startsAt": "2026-01-15T12:00:00Z",
                "endsAt": "0001-01-01T00:00:00Z",
                "generatorURL": "http://alertmanager:9093/graph",
                "fingerprint": "fp-am-001",
            }
        ],
    }


@pytest.fixture
def manual_trigger_payload():
    """A manual trigger payload from a dashboard button."""
    return {
        "action_name": "run_diagnostic",
        "trigger_id": "manual-001",
        "message": "User clicked diagnostic button",
        "labels": {"environment": "staging"},
        "context": {"dashboard": "checkout-health"},
    }


# ---------------------------------------------------------------------------
# Action helpers
# ---------------------------------------------------------------------------

class SuccessAction(Action):
    """An action that always succeeds."""

    name = "test_success"
    description = "Always succeeds"

    def execute(self, payload, context):
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.name,
            message="ok",
            data={"received_keys": list(payload.keys())},
        )


class FailingAction(Action):
    """An action that always raises an exception."""

    name = "test_failing"
    description = "Always raises"

    def execute(self, payload, context):
        raise RuntimeError("intentional failure")


class ValidatingAction(Action):
    """An action that validates the payload requires a 'required_field'."""

    name = "test_validating"
    description = "Requires 'required_field'"

    def validate(self, payload):
        if "required_field" not in payload:
            return "missing required_field"
        return None

    def execute(self, payload, context):
        return ActionResult(
            status=ActionStatus.SUCCESS,
            action_name=self.name,
            message="validated and executed",
        )


@pytest.fixture
def fresh_registry():
    """An isolated ActionRegistry with no pre-registered actions."""
    return ActionRegistry()


@pytest.fixture
def populated_registry():
    """An ActionRegistry with test actions registered."""
    reg = ActionRegistry()
    reg.register_class("success", SuccessAction)
    reg.register_class("failing", FailingAction)
    reg.register_class("validating", ValidatingAction)
    return reg
