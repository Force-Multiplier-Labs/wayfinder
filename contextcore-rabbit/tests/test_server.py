"""
Tests for the WebhookServer Flask application.

Covers all HTTP endpoints:
- GET  /health
- GET  /actions
- POST /trigger
- POST /workflow/run
- GET  /workflow/status/<run_id>
- GET  /workflow/history
- POST /webhook/grafana
- POST /webhook/alertmanager
- POST /webhook/manual
"""

import json
import threading
import time

import pytest

from contextcore_rabbit.action import action_registry, ActionStatus
from contextcore_rabbit.server import WebhookServer
from contextcore_rabbit.actions.beaver_workflow import _workflow_runs

# Ensure built-in actions are registered before server tests
import contextcore_rabbit.actions  # noqa: F401


def _wait_for_threads():
    """Give background workflow threads a moment to finish or fail."""
    time.sleep(0.15)
    for t in threading.enumerate():
        if t.name != "MainThread" and t.is_alive():
            t.join(timeout=0.3)


@pytest.fixture
def app():
    """Create a test Flask app from WebhookServer."""
    server = WebhookServer(port=0)
    server.app.config["TESTING"] = True
    return server.app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture(autouse=True)
def clear_workflow_runs():
    """Reset workflow state between tests."""
    _workflow_runs.clear()
    yield
    _wait_for_threads()
    _workflow_runs.clear()


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_returns_healthy_status(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert data["status"] == "healthy"
        assert data["service"] == "contextcore-rabbit"

    def test_includes_timestamp(self, client):
        resp = client.get("/health")
        data = resp.get_json()
        assert "timestamp" in data


# ---------------------------------------------------------------------------
# GET /actions
# ---------------------------------------------------------------------------

class TestActionsEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/actions")
        assert resp.status_code == 200

    def test_returns_list_of_actions(self, client):
        resp = client.get("/actions")
        data = resp.get_json()
        assert "actions" in data
        assert isinstance(data["actions"], list)

    def test_includes_log_action(self, client):
        resp = client.get("/actions")
        data = resp.get_json()
        names = [a["name"] for a in data["actions"]]
        assert "log" in names

    def test_includes_beaver_workflow_action(self, client):
        resp = client.get("/actions")
        data = resp.get_json()
        names = [a["name"] for a in data["actions"]]
        assert "beaver_workflow" in names


# ---------------------------------------------------------------------------
# POST /trigger
# ---------------------------------------------------------------------------

class TestTriggerEndpoint:
    def test_missing_action_field_returns_400(self, client):
        resp = client.post(
            "/trigger",
            data=json.dumps({"payload": {}}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_trigger_log_action(self, client):
        resp = client.post(
            "/trigger",
            data=json.dumps({
                "action": "log",
                "payload": {"alert": "test"},
                "context": {"env": "ci"},
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["action_name"] == "log"

    def test_trigger_unknown_action_returns_500(self, client):
        resp = client.post(
            "/trigger",
            data=json.dumps({"action": "nonexistent"}),
            content_type="application/json",
        )
        assert resp.status_code == 500
        data = resp.get_json()
        assert data["status"] == "failed"

    def test_trigger_empty_body_returns_400(self, client):
        resp = client.post(
            "/trigger",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# POST /workflow/run
# ---------------------------------------------------------------------------

class TestWorkflowRunEndpoint:
    def test_missing_project_id_returns_400(self, client):
        resp = client.post(
            "/workflow/run",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "project_id" in data["error"].lower()

    def test_successful_run_returns_started(self, client):
        resp = client.post(
            "/workflow/run",
            data=json.dumps({"project_id": "my-proj"}),
            content_type="application/json",
        )
        # The action will try to import PrimeContractorWorkflow, which will fail
        # in tests, so this should return a 500. But we test the request handling.
        data = resp.get_json()
        # The beaver_workflow action succeeds (it fires off a thread), but the
        # thread itself will fail when it tries to import PrimeContractorWorkflow.
        # The action itself returns SUCCESS immediately (fire-and-forget).
        assert resp.status_code == 200
        assert data["status"] == "started"
        assert data["project_id"] == "my-proj"
        assert "run_id" in data

    def test_dry_run_mode(self, client):
        resp = client.post(
            "/workflow/run",
            data=json.dumps({"project_id": "p", "dry_run": True}),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["mode"] == "dry_run"

    def test_execute_mode_is_default(self, client):
        resp = client.post(
            "/workflow/run",
            data=json.dumps({"project_id": "p"}),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["mode"] == "execute"


# ---------------------------------------------------------------------------
# GET /workflow/status/<run_id>
# ---------------------------------------------------------------------------

class TestWorkflowStatusEndpoint:
    def test_unknown_run_returns_404(self, client):
        resp = client.get("/workflow/status/unknown-id")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["status"] == "error"

    def test_known_run_returns_data(self, client):
        _workflow_runs["known-id"] = {
            "run_id": "known-id",
            "project_id": "proj",
            "status": "running",
            "dry_run": False,
            "started_at": "2026-01-15T10:00:00",
            "completed_at": None,
            "steps_total": 10,
            "steps_completed": 3,
            "error": None,
        }

        resp = client.get("/workflow/status/known-id")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["run_id"] == "known-id"
        assert data["status"] == "running"
        assert data["steps_total"] == 10
        assert data["steps_completed"] == 3

    def test_includes_progress_percent(self, client):
        _workflow_runs["prog-id"] = {
            "run_id": "prog-id",
            "project_id": "p",
            "status": "running",
            "dry_run": False,
            "started_at": "2026-01-15T10:00:00",
            "completed_at": None,
            "steps_total": 4,
            "steps_completed": 2,
            "error": None,
        }

        resp = client.get("/workflow/status/prog-id")
        data = resp.get_json()
        assert data["progress_percent"] == 50.0

    def test_progress_percent_zero_when_no_steps(self, client):
        _workflow_runs["zero-id"] = {
            "run_id": "zero-id",
            "project_id": "p",
            "status": "starting",
            "dry_run": False,
            "started_at": None,
            "completed_at": None,
            "steps_total": 0,
            "steps_completed": 0,
            "error": None,
        }

        resp = client.get("/workflow/status/zero-id")
        data = resp.get_json()
        assert data["progress_percent"] == 0


# ---------------------------------------------------------------------------
# GET /workflow/history
# ---------------------------------------------------------------------------

class TestWorkflowHistoryEndpoint:
    def test_empty_history(self, client):
        resp = client.get("/workflow/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["runs"] == []
        assert data["total"] == 0

    def test_returns_runs(self, client):
        _workflow_runs["h1"] = {
            "run_id": "h1", "project_id": "p1",
            "started_at": "2026-01-15T10:00:00",
        }
        _workflow_runs["h2"] = {
            "run_id": "h2", "project_id": "p2",
            "started_at": "2026-01-15T11:00:00",
        }

        resp = client.get("/workflow/history")
        data = resp.get_json()
        assert len(data["runs"]) == 2

    def test_filter_by_project_id(self, client):
        _workflow_runs["h1"] = {
            "run_id": "h1", "project_id": "alpha",
            "started_at": "2026-01-15T10:00:00",
        }
        _workflow_runs["h2"] = {
            "run_id": "h2", "project_id": "beta",
            "started_at": "2026-01-15T11:00:00",
        }

        resp = client.get("/workflow/history?project_id=alpha")
        data = resp.get_json()
        assert len(data["runs"]) == 1
        assert data["runs"][0]["project_id"] == "alpha"

    def test_limit_parameter(self, client):
        for i in range(5):
            _workflow_runs[f"h{i}"] = {
                "run_id": f"h{i}", "project_id": "p",
                "started_at": f"2026-01-15T{10 + i}:00:00",
            }

        resp = client.get("/workflow/history?limit=2")
        data = resp.get_json()
        assert len(data["runs"]) == 2


# ---------------------------------------------------------------------------
# POST /webhook/grafana
# ---------------------------------------------------------------------------

class TestGrafanaWebhookEndpoint:
    def test_valid_grafana_alert(self, client, grafana_firing_payload):
        resp = client.post(
            "/webhook/grafana",
            data=json.dumps(grafana_firing_payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert data["action_name"] == "log"

    def test_uses_rabbit_action_label(self, client):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "Test", "rabbit_action": "log"},
                "annotations": {},
            }]
        }
        resp = client.post(
            "/webhook/grafana",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["action_name"] == "log"

    def test_defaults_to_log_action(self, client):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "NoAction"},
                "annotations": {},
            }]
        }
        resp = client.post(
            "/webhook/grafana",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["action_name"] == "log"

    def test_empty_body_still_processes(self, client):
        resp = client.post(
            "/webhook/grafana",
            data=json.dumps({}),
            content_type="application/json",
        )
        # Empty payload should still parse (with defaults)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST /webhook/alertmanager
# ---------------------------------------------------------------------------

class TestAlertmanagerWebhookEndpoint:
    def test_valid_alertmanager_payload(self, client, alertmanager_payload):
        resp = client.post(
            "/webhook/alertmanager",
            data=json.dumps(alertmanager_payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"

    def test_defaults_to_log_action(self, client):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "Test"},
                "annotations": {},
            }]
        }
        resp = client.post(
            "/webhook/alertmanager",
            data=json.dumps(payload),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["action_name"] == "log"


# ---------------------------------------------------------------------------
# POST /webhook/manual
# ---------------------------------------------------------------------------

class TestManualWebhookEndpoint:
    def test_manual_trigger_defaults(self, client):
        resp = client.post(
            "/webhook/manual",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        # Default action is beaver_workflow which starts a thread
        assert data["action_name"] == "beaver_workflow"
        assert data["status"] == "success"

    def test_manual_trigger_with_action(self, client):
        resp = client.post(
            "/webhook/manual",
            data=json.dumps({
                "action": "log",
                "project_id": "manual-proj",
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["action_name"] == "log"
        assert data["status"] == "success"

    def test_manual_trigger_adds_context(self, client):
        resp = client.post(
            "/webhook/manual",
            data=json.dumps({
                "action": "log",
                "project_id": "p",
                "context": {"extra": "info"},
            }),
            content_type="application/json",
        )
        assert resp.status_code == 200

    def test_manual_trigger_dry_run(self, client):
        resp = client.post(
            "/webhook/manual",
            data=json.dumps({
                "action": "beaver_workflow",
                "project_id": "p",
                "dry_run": True,
            }),
            content_type="application/json",
        )
        data = resp.get_json()
        assert data["status"] == "success"
