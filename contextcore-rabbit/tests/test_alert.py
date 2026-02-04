"""
Tests for the Alert model and its parsing classmethods.

Covers:
- AlertSeverity and AlertStatus enums
- Alert dataclass defaults and to_dict serialization
- Alert.from_grafana parsing (firing, resolved, severity mapping, missing fields)
- Alert.from_alertmanager parsing (firing, severity mapping, missing fields)
- Alert.from_manual_trigger parsing
"""

import pytest

from contextcore_rabbit.alert import Alert, AlertSeverity, AlertStatus


# ---------------------------------------------------------------------------
# Enum values
# ---------------------------------------------------------------------------

class TestAlertSeverity:
    def test_severity_values(self):
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.HIGH.value == "high"
        assert AlertSeverity.MEDIUM.value == "medium"
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.INFO.value == "info"

    def test_severity_member_count(self):
        assert len(AlertSeverity) == 5


class TestAlertStatus:
    def test_status_values(self):
        assert AlertStatus.FIRING.value == "firing"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.PENDING.value == "pending"

    def test_status_member_count(self):
        assert len(AlertStatus) == 3


# ---------------------------------------------------------------------------
# Alert dataclass basics
# ---------------------------------------------------------------------------

class TestAlertDataclass:
    def test_minimal_construction(self):
        alert = Alert(id="a1", name="TestAlert")
        assert alert.id == "a1"
        assert alert.name == "TestAlert"
        assert alert.severity == AlertSeverity.MEDIUM
        assert alert.status == AlertStatus.FIRING
        assert alert.source == "unknown"
        assert alert.message == ""
        assert alert.labels == {}
        assert alert.annotations == {}
        assert alert.starts_at is None
        assert alert.ends_at is None
        assert alert.generator_url is None
        assert alert.fingerprint is None
        assert alert.raw_payload == {}

    def test_full_construction(self):
        alert = Alert(
            id="a2",
            name="FullAlert",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.RESOLVED,
            source="prometheus",
            message="CPU on fire",
            labels={"env": "prod"},
            annotations={"runbook": "http://wiki/cpu"},
            starts_at="2026-01-01T00:00:00Z",
            ends_at="2026-01-01T01:00:00Z",
            generator_url="http://prom/graph",
            fingerprint="fp-123",
            raw_payload={"original": True},
        )
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.status == AlertStatus.RESOLVED
        assert alert.labels["env"] == "prod"

    def test_to_dict_contains_all_keys(self):
        alert = Alert(id="a3", name="DictAlert", fingerprint="fp-dict")
        d = alert.to_dict()
        expected_keys = {
            "id", "name", "severity", "status", "source",
            "message", "labels", "annotations",
            "starts_at", "ends_at", "generator_url", "fingerprint",
        }
        assert set(d.keys()) == expected_keys

    def test_to_dict_serializes_enums_as_strings(self):
        alert = Alert(
            id="a4", name="EnumAlert",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.RESOLVED,
        )
        d = alert.to_dict()
        assert d["severity"] == "high"
        assert d["status"] == "resolved"

    def test_to_dict_does_not_include_raw_payload(self):
        """raw_payload is intentionally excluded from to_dict output."""
        alert = Alert(id="a5", name="RawTest", raw_payload={"key": "val"})
        d = alert.to_dict()
        assert "raw_payload" not in d


# ---------------------------------------------------------------------------
# Alert.from_grafana
# ---------------------------------------------------------------------------

class TestAlertFromGrafana:
    def test_parses_firing_alert(self, grafana_firing_payload):
        alert = Alert.from_grafana(grafana_firing_payload)

        assert alert.name == "HighLatency"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.status == AlertStatus.FIRING
        assert alert.source == "grafana"
        assert alert.message == "P99 latency is 2.3s (SLO: 500ms)"
        assert alert.fingerprint == "fp-grafana-001"
        assert alert.starts_at == "2026-01-15T10:00:00Z"
        assert alert.generator_url == "http://grafana:3000/alerting/rule/abc"

    def test_parses_resolved_alert(self, grafana_resolved_payload):
        alert = Alert.from_grafana(grafana_resolved_payload)

        assert alert.status == AlertStatus.RESOLVED
        assert alert.ends_at == "2026-01-15T10:05:00Z"

    def test_severity_mapping_warning_to_medium(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "Warn", "severity": "warning"},
                "annotations": {},
            }]
        }
        alert = Alert.from_grafana(payload)
        assert alert.severity == AlertSeverity.MEDIUM

    def test_severity_mapping_info(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "Info", "severity": "info"},
                "annotations": {},
            }]
        }
        alert = Alert.from_grafana(payload)
        assert alert.severity == AlertSeverity.INFO

    def test_severity_mapping_high(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "High", "severity": "high"},
                "annotations": {},
            }]
        }
        alert = Alert.from_grafana(payload)
        assert alert.severity == AlertSeverity.HIGH

    def test_unknown_severity_defaults_to_medium(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "X", "severity": "catastrophic"},
                "annotations": {},
            }]
        }
        alert = Alert.from_grafana(payload)
        assert alert.severity == AlertSeverity.MEDIUM

    def test_missing_severity_defaults_to_medium(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "NoSev"},
                "annotations": {},
            }]
        }
        alert = Alert.from_grafana(payload)
        assert alert.severity == AlertSeverity.MEDIUM

    def test_uses_fingerprint_as_id(self, grafana_firing_payload):
        alert = Alert.from_grafana(grafana_firing_payload)
        assert alert.id == "fp-grafana-001"

    def test_generates_id_when_no_fingerprint(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "NoFP"},
                "annotations": {},
            }]
        }
        alert = Alert.from_grafana(payload)
        # Should have some non-empty id even without fingerprint
        assert alert.id
        assert isinstance(alert.id, str)

    def test_preserves_labels(self, grafana_firing_payload):
        alert = Alert.from_grafana(grafana_firing_payload)
        assert alert.labels["service"] == "checkout"
        assert alert.labels["rabbit_action"] == "log"

    def test_preserves_raw_payload(self, grafana_firing_payload):
        alert = Alert.from_grafana(grafana_firing_payload)
        assert alert.raw_payload == grafana_firing_payload

    def test_message_falls_back_to_summary(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "FallbackMsg"},
                "annotations": {"summary": "Only summary here"},
            }]
        }
        alert = Alert.from_grafana(payload)
        assert alert.message == "Only summary here"

    def test_empty_alerts_list_falls_back_to_top_level(self):
        payload = {
            "title": "TopLevelTitle",
            "alerts": [],
            "status": "firing",
        }
        alert = Alert.from_grafana(payload)
        assert alert.name == "TopLevelTitle"

    def test_no_alerts_key_uses_payload_itself(self):
        payload = {
            "title": "NoAlerts",
            "status": "firing",
            "labels": {"alertname": "DirectPayload", "severity": "high"},
            "annotations": {"description": "Direct description"},
            "fingerprint": "fp-direct",
        }
        alert = Alert.from_grafana(payload)
        assert alert.name == "DirectPayload"
        assert alert.severity == AlertSeverity.HIGH
        assert alert.message == "Direct description"
        assert alert.fingerprint == "fp-direct"


# ---------------------------------------------------------------------------
# Alert.from_alertmanager
# ---------------------------------------------------------------------------

class TestAlertFromAlertmanager:
    def test_parses_firing_alert(self, alertmanager_payload):
        alert = Alert.from_alertmanager(alertmanager_payload)

        assert alert.name == "HighErrorRate"
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.status == AlertStatus.FIRING
        assert alert.source == "alertmanager"
        assert "12%" in alert.message
        assert alert.fingerprint == "fp-am-001"

    def test_resolved_status(self):
        payload = {
            "alerts": [{
                "status": "resolved",
                "labels": {"alertname": "Resolved", "severity": "warning"},
                "annotations": {},
                "fingerprint": "fp-resolved",
            }]
        }
        alert = Alert.from_alertmanager(payload)
        assert alert.status == AlertStatus.RESOLVED

    def test_severity_mapping_warning_to_medium(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "Warn", "severity": "warning"},
                "annotations": {},
            }]
        }
        alert = Alert.from_alertmanager(payload)
        assert alert.severity == AlertSeverity.MEDIUM

    def test_severity_mapping_info(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "Info", "severity": "info"},
                "annotations": {},
            }]
        }
        alert = Alert.from_alertmanager(payload)
        assert alert.severity == AlertSeverity.INFO

    def test_default_severity_for_missing_label(self):
        """Alertmanager defaults to 'warning' which maps to MEDIUM."""
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "NoSev"},
                "annotations": {},
            }]
        }
        alert = Alert.from_alertmanager(payload)
        assert alert.severity == AlertSeverity.MEDIUM

    def test_unknown_severity_defaults_to_medium(self):
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {"alertname": "X", "severity": "mega"},
                "annotations": {},
            }]
        }
        alert = Alert.from_alertmanager(payload)
        assert alert.severity == AlertSeverity.MEDIUM

    def test_empty_alerts_list_falls_back_to_top_level(self):
        payload = {
            "alerts": [],
            "labels": {"alertname": "TopLevel"},
            "annotations": {},
            "status": "firing",
        }
        alert = Alert.from_alertmanager(payload)
        assert alert.name == "TopLevel"

    def test_preserves_annotations(self, alertmanager_payload):
        alert = Alert.from_alertmanager(alertmanager_payload)
        assert "Error rate" in alert.annotations.get("description", "")

    def test_preserves_raw_payload(self, alertmanager_payload):
        alert = Alert.from_alertmanager(alertmanager_payload)
        assert alert.raw_payload == alertmanager_payload


# ---------------------------------------------------------------------------
# Alert.from_manual_trigger
# ---------------------------------------------------------------------------

class TestAlertFromManualTrigger:
    def test_basic_parsing(self, manual_trigger_payload):
        alert = Alert.from_manual_trigger(manual_trigger_payload)

        assert alert.id == "manual-001"
        assert alert.name == "run_diagnostic"
        assert alert.severity == AlertSeverity.INFO
        assert alert.status == AlertStatus.FIRING
        assert alert.source == "manual"
        assert "clicked" in alert.message
        assert alert.labels["environment"] == "staging"
        assert alert.annotations["dashboard"] == "checkout-health"

    def test_defaults_for_empty_payload(self):
        alert = Alert.from_manual_trigger({})

        assert alert.id  # auto-generated
        assert alert.name == "manual_trigger"
        assert alert.message == "Manual trigger from dashboard"
        assert alert.labels == {}
        assert alert.annotations == {}

    def test_preserves_raw_payload(self, manual_trigger_payload):
        alert = Alert.from_manual_trigger(manual_trigger_payload)
        assert alert.raw_payload == manual_trigger_payload
