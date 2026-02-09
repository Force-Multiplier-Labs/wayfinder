"""Tests for contextcore_coyote.models — pure data model logic."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from contextcore_coyote.models import (
    Incident,
    IncidentSeverity,
    Lesson,
    StageResult,
    StageStatus,
)


# --- StageStatus enum ---


class TestStageStatus:
    """Test StageStatus enum values."""

    def test_all_values_exist(self):
        assert StageStatus.PENDING == "pending"
        assert StageStatus.RUNNING == "running"
        assert StageStatus.AWAITING_APPROVAL == "awaiting_approval"
        assert StageStatus.COMPLETED == "completed"
        assert StageStatus.FAILED == "failed"
        assert StageStatus.SKIPPED == "skipped"

    def test_has_six_members(self):
        assert len(StageStatus) == 6

    def test_is_str_enum(self):
        assert isinstance(StageStatus.PENDING, str)


# --- IncidentSeverity enum ---


class TestIncidentSeverity:
    """Test IncidentSeverity enum values."""

    def test_all_values_exist(self):
        assert IncidentSeverity.CRITICAL == "critical"
        assert IncidentSeverity.HIGH == "high"
        assert IncidentSeverity.MEDIUM == "medium"
        assert IncidentSeverity.LOW == "low"
        assert IncidentSeverity.INFO == "info"

    def test_has_five_members(self):
        assert len(IncidentSeverity) == 5


# --- Incident ---


class TestIncident:
    """Test Incident dataclass."""

    def test_from_error_basic(self):
        inc = Incident.from_error("Something broke")
        assert inc.title == "Something broke"
        assert inc.description == "Something broke"
        assert inc.error_message == "Something broke"
        assert inc.severity == IncidentSeverity.MEDIUM
        assert inc.source == "log"
        assert inc.id.startswith("INC-")
        assert inc.detected_at is not None

    def test_from_error_multiline(self):
        msg = "First line error\nSecond line detail\nThird line"
        inc = Incident.from_error(msg)
        assert inc.title == "First line error"
        assert inc.description == msg

    def test_from_error_long_title_truncated(self):
        long_msg = "A" * 200
        inc = Incident.from_error(long_msg)
        assert len(inc.title) <= 100

    def test_from_error_empty_string(self):
        inc = Incident.from_error("")
        assert inc.title == ""
        assert inc.description == ""

    def test_from_error_custom_severity(self):
        inc = Incident.from_error("crash", severity=IncidentSeverity.CRITICAL)
        assert inc.severity == IncidentSeverity.CRITICAL

    def test_from_error_custom_source(self):
        inc = Incident.from_error("alert fired", source="alert")
        assert inc.source == "alert"

    def test_from_error_with_stack_trace(self):
        inc = Incident.from_error("error", stack_trace="at line 42")
        assert inc.stack_trace == "at line 42"

    def test_from_error_id_contains_timestamp(self):
        inc = Incident.from_error("test")
        # ID format: INC-YYYYMMDDHHMMSS
        assert len(inc.id) == 18  # "INC-" + 14 digits

    def test_from_github_issue(self):
        issue_data = {
            "title": "Bug in auth",
            "body": "Login fails for SSO users",
            "labels": [{"name": "bug"}, {"name": "auth"}],
        }
        inc = Incident.from_github_issue(123, issue_data)
        assert inc.id == "GH-123"
        assert inc.title == "Bug in auth"
        assert inc.source == "github"
        assert inc.labels == {"bug": "true", "auth": "true"}

    def test_from_github_issue_missing_fields(self):
        inc = Incident.from_github_issue(1, {})
        assert inc.title == "Unknown"
        assert inc.description == ""
        assert inc.labels == {}

    def test_to_dict(self, sample_incident):
        d = sample_incident.to_dict()
        assert d["id"] == "INC-20260209120000"
        assert d["severity"] == "high"
        assert d["source"] == "log"
        assert isinstance(d["created_at"], str)
        assert isinstance(d["detected_at"], str)

    def test_to_dict_none_detected_at(self):
        inc = Incident(id="test", title="t", description="d")
        d = inc.to_dict()
        assert d["detected_at"] is None

    def test_default_field_factories(self):
        inc = Incident(id="test", title="t", description="d")
        assert inc.labels == {}
        assert inc.annotations == {}
        assert inc.affected_files == []
        assert inc.related_prs == []
        assert inc.raw_payload == {}


# --- StageResult ---


class TestStageResult:
    """Test StageResult dataclass."""

    def test_duration_seconds_completed(self, completed_stage_result):
        assert completed_stage_result.duration_seconds == pytest.approx(15.0)

    def test_duration_seconds_incomplete(self, incomplete_stage_result):
        assert incomplete_stage_result.duration_seconds is None

    def test_to_dict(self, completed_stage_result):
        d = completed_stage_result.to_dict()
        assert d["stage_name"] == "investigate"
        assert d["status"] == "completed"
        assert d["duration_seconds"] == pytest.approx(15.0)
        assert isinstance(d["started_at"], str)
        assert isinstance(d["completed_at"], str)

    def test_to_dict_incomplete(self, incomplete_stage_result):
        d = incomplete_stage_result.to_dict()
        assert d["completed_at"] is None
        assert d["duration_seconds"] is None

    def test_default_field_factories(self):
        r = StageResult(
            stage_name="test",
            status=StageStatus.PENDING,
            started_at=datetime.now(),
        )
        assert r.output == {}
        assert r.affected_code == []
        assert r.tradeoffs == []
        assert r.alternatives == []
        assert r.code_changes == {}
        assert r.lessons == []
        assert r.prevention_steps == []


# --- Lesson ---


class TestLesson:
    """Test Lesson dataclass."""

    def test_construction(self, sample_lesson):
        assert sample_lesson.id == "INC-001-L1"
        assert sample_lesson.incident_id == "INC-001"
        assert sample_lesson.category == "null-reference"
        assert sample_lesson.confidence == 0.9

    def test_to_dict(self, sample_lesson):
        d = sample_lesson.to_dict()
        assert d["id"] == "INC-001-L1"
        assert d["incident_id"] == "INC-001"
        assert d["category"] == "null-reference"
        assert d["confidence"] == 0.9
        assert isinstance(d["created_at"], str)
        assert d["related_files"] == ["UserService.java"]
        assert "null-check" in d["tags"]

    def test_default_values(self):
        lesson = Lesson(
            id="L1",
            incident_id="INC-1",
            category="test",
            lesson="test lesson",
            prevention="test prevention",
        )
        assert lesson.related_files == []
        assert lesson.tags == []
        assert lesson.confidence == 0.8
