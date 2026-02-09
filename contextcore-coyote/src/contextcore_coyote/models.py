"""
Core data models for ContextCore Coyote.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class StageStatus(str, Enum):
    """Status of a pipeline stage."""

    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class IncidentSeverity(str, Enum):
    """Severity level of an incident."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class Incident:
    """
    Represents an incident to be investigated and resolved.

    An incident is typically triggered by an error in production logs,
    an alert from monitoring, or a bug report.
    """

    id: str
    title: str
    description: str
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    source: str = "manual"  # manual, log, alert, github

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    detected_at: Optional[datetime] = None

    # Context
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)
    affected_files: List[str] = field(default_factory=list)
    related_prs: List[str] = field(default_factory=list)

    # O11y context
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    log_query: Optional[str] = None

    # Raw data
    raw_payload: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_error(
        cls,
        error_message: str,
        stack_trace: Optional[str] = None,
        source: str = "log",
        severity: IncidentSeverity = IncidentSeverity.MEDIUM,
        **kwargs,
    ) -> "Incident":
        """
        Create an incident from an error message.

        Args:
            error_message: The error message
            stack_trace: Optional stack trace
            source: Where the error was detected
            severity: Incident severity
            **kwargs: Additional incident fields

        Returns:
            New Incident instance
        """
        # Generate ID from timestamp
        incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Extract title from error message
        title = error_message.split("\n")[0][:100]

        return cls(
            id=incident_id,
            title=title,
            description=error_message,
            error_message=error_message,
            stack_trace=stack_trace,
            source=source,
            severity=severity,
            detected_at=datetime.now(),
            **kwargs,
        )

    @classmethod
    def from_github_issue(cls, issue_number: int, issue_data: Dict[str, Any]) -> "Incident":
        """
        Create an incident from a GitHub issue.

        Args:
            issue_number: GitHub issue number
            issue_data: Issue data from GitHub API

        Returns:
            New Incident instance
        """
        return cls(
            id=f"GH-{issue_number}",
            title=issue_data.get("title", "Unknown"),
            description=issue_data.get("body", ""),
            source="github",
            labels={label["name"]: "true" for label in issue_data.get("labels", [])},
            raw_payload=issue_data,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "error_message": self.error_message,
            "stack_trace": self.stack_trace,
            "severity": self.severity.value,
            "source": self.source,
            "created_at": self.created_at.isoformat(),
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "labels": self.labels,
            "affected_files": self.affected_files,
            "related_prs": self.related_prs,
        }


@dataclass
class StageResult:
    """Result of a pipeline stage execution."""

    stage_name: str
    status: StageStatus
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Output
    summary: str = ""
    details: str = ""
    output: Dict[str, Any] = field(default_factory=dict)

    # For investigation stage
    root_cause: Optional[str] = None
    affected_code: List[str] = field(default_factory=list)
    originating_pr: Optional[str] = None

    # For design stage
    fix_specification: Optional[str] = None
    tradeoffs: List[str] = field(default_factory=list)
    alternatives: List[str] = field(default_factory=list)

    # For implementation stage
    code_changes: Dict[str, str] = field(default_factory=dict)  # file -> diff
    pr_url: Optional[str] = None

    # For test stage
    tests_passed: Optional[bool] = None
    test_output: Optional[str] = None
    regression_risk: Optional[str] = None

    # For learn stage
    lessons: List[str] = field(default_factory=list)
    prevention_steps: List[str] = field(default_factory=list)

    # Error handling
    error: Optional[str] = None
    retries: int = 0

    @property
    def duration_seconds(self) -> Optional[float]:
        """Get stage duration in seconds."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage_name": self.stage_name,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary,
            "error": self.error,
        }


@dataclass
class Lesson:
    """A lesson learned from an incident."""

    id: str
    incident_id: str
    category: str
    lesson: str
    prevention: str
    created_at: datetime = field(default_factory=datetime.now)
    related_files: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "incident_id": self.incident_id,
            "category": self.category,
            "lesson": self.lesson,
            "prevention": self.prevention,
            "created_at": self.created_at.isoformat(),
            "related_files": self.related_files,
            "tags": self.tags,
            "confidence": self.confidence,
        }
