"""
Contract validation utilities.

Provides tools to validate telemetry emissions against ContextCore contracts,
ensuring metric names, label names, and values conform to the schema.

Usage:
    from contextcore.contracts.validate import ContractValidator

    validator = ContractValidator(project_schema=LM1_SCHEMA)

    # Validate a metric emission
    errors = validator.validate_metric(
        name="lm1_progress",
        labels={"project": "lm1_campaign", "phase": "foundation"},
    )

    # Validate a log event
    errors = validator.validate_log_event(
        event_type="task.status_changed",
        attributes={"task.id": "TASK-1", "from": "todo", "to": "in_progress"},
    )
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from contextcore.contracts.metrics import (
    EventType,
    LabelName,
    MetricName,
    ProjectSchema,
    REQUIRED_LABELS,
    TASK_LABELS,
    validate_labels,
    validate_metric_name,
)
from contextcore.contracts.types import (
    TASK_STATUS_VALUES,
    PRIORITY_VALUES,
    TASK_TYPE_VALUES,
    INSIGHT_TYPE_VALUES,
    HANDOFF_STATUS_VALUES,
)


class ValidationResult:
    """Result of a validation check."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []

    @property
    def is_valid(self) -> bool:
        """Return True if no errors."""
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

    def __repr__(self) -> str:
        if self.is_valid and not self.warnings:
            return "ValidationResult(valid=True)"
        return f"ValidationResult(errors={self.errors}, warnings={self.warnings})"


class ContractValidator:
    """
    Validates telemetry emissions against ContextCore contracts.

    Args:
        project_schema: Optional ProjectSchema to validate against
        strict: If True, warnings become errors
    """

    def __init__(
        self,
        project_schema: Optional[ProjectSchema] = None,
        strict: bool = False,
    ):
        self.schema = project_schema
        self.strict = strict

        # Build valid value sets
        self._valid_statuses = set(TASK_STATUS_VALUES)
        self._valid_priorities = set(PRIORITY_VALUES)
        self._valid_task_types = set(TASK_TYPE_VALUES)
        self._valid_insight_types = set(INSIGHT_TYPE_VALUES)
        self._valid_handoff_statuses = set(HANDOFF_STATUS_VALUES)
        self._valid_event_types = {e.value for e in EventType}
        self._valid_metric_names = {m.value for m in MetricName}
        self._valid_label_names = {l.value for l in LabelName}

    def validate_metric(
        self,
        name: str,
        labels: Dict[str, Any],
        value: Optional[Any] = None,
    ) -> ValidationResult:
        """
        Validate a metric emission.

        Args:
            name: Metric name
            labels: Label key-value pairs
            value: Optional metric value

        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult()

        # Validate metric name
        prefix = self.schema.metric_prefix if self.schema else ""
        name_errors = validate_metric_name(name, prefix)
        for err in name_errors:
            result.add_error(err)

        # Check if metric name is known
        suffix = name[len(prefix):] if prefix else name
        if suffix not in self._valid_metric_names:
            result.add_warning(f"Unknown metric suffix '{suffix}'")

        # Validate labels
        label_errors = validate_labels(labels, context=f"Metric '{name}': ")
        for err in label_errors:
            result.add_error(err)

        # Validate label names
        for label_name in labels.keys():
            if label_name not in self._valid_label_names:
                result.add_warning(f"Unknown label name '{label_name}'")

        # Validate project label matches schema
        if self.schema and labels.get("project"):
            if labels["project"] != self.schema.project_id:
                result.add_warning(
                    f"Project label '{labels['project']}' doesn't match schema "
                    f"project_id '{self.schema.project_id}'"
                )

        # Validate specific label values
        self._validate_label_values(labels, result)

        # Convert warnings to errors in strict mode
        if self.strict:
            result.errors.extend(result.warnings)
            result.warnings = []

        return result

    def validate_log_event(
        self,
        event_type: str,
        attributes: Dict[str, Any],
    ) -> ValidationResult:
        """
        Validate a structured log event.

        Args:
            event_type: Event type (e.g., "task.status_changed")
            attributes: Event attributes

        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult()

        # Validate event type
        if event_type not in self._valid_event_types:
            result.add_warning(f"Unknown event type '{event_type}'")

        # Validate project label
        if "project" not in attributes and "project.id" not in attributes:
            result.add_error("Missing required 'project' or 'project.id' attribute")

        # Validate specific attributes based on event type
        if event_type == "task.status_changed":
            if "from" not in attributes or "to" not in attributes:
                result.add_error("task.status_changed requires 'from' and 'to' attributes")
            else:
                if attributes.get("from") not in self._valid_statuses:
                    result.add_error(f"Invalid 'from' status: {attributes.get('from')}")
                if attributes.get("to") not in self._valid_statuses:
                    result.add_error(f"Invalid 'to' status: {attributes.get('to')}")

        elif event_type in ("task.created", "task.completed", "task.cancelled"):
            if "task.id" not in attributes:
                result.add_error(f"{event_type} requires 'task.id' attribute")

        # Validate attribute values
        self._validate_label_values(attributes, result)

        if self.strict:
            result.errors.extend(result.warnings)
            result.warnings = []

        return result

    def validate_span_attributes(
        self,
        attributes: Dict[str, Any],
        span_type: str = "task",
    ) -> ValidationResult:
        """
        Validate span attributes.

        Args:
            attributes: Span attribute key-value pairs
            span_type: Type of span ("task", "session", "handoff")

        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult()

        # Check required attributes based on span type
        if span_type == "task":
            required = {"task.id", "task.title", "task.type"}
            for attr in required:
                if attr not in attributes:
                    result.add_error(f"Missing required task attribute: {attr}")

        elif span_type == "session":
            required = {"agent.id", "agent.type"}
            for attr in required:
                if attr not in attributes:
                    result.add_error(f"Missing required session attribute: {attr}")

        elif span_type == "handoff":
            required = {"handoff.id", "handoff.from_agent", "handoff.to_agent"}
            for attr in required:
                if attr not in attributes:
                    result.add_error(f"Missing required handoff attribute: {attr}")

        # Validate attribute values
        self._validate_label_values(attributes, result)

        if self.strict:
            result.errors.extend(result.warnings)
            result.warnings = []

        return result

    def _validate_label_values(
        self,
        labels: Dict[str, Any],
        result: ValidationResult,
    ) -> None:
        """Validate specific label values against known enums."""
        # Status validation
        status_keys = ["status", "task.status", "from", "to"]
        for key in status_keys:
            if key in labels and labels[key] not in self._valid_statuses:
                result.add_error(
                    f"Invalid status value '{labels[key]}' for '{key}'. "
                    f"Valid values: {sorted(self._valid_statuses)}"
                )

        # Priority validation
        priority_keys = ["priority", "task.priority"]
        for key in priority_keys:
            if key in labels and labels[key] not in self._valid_priorities:
                result.add_error(
                    f"Invalid priority value '{labels[key]}' for '{key}'. "
                    f"Valid values: {sorted(self._valid_priorities)}"
                )

        # Task type validation
        type_keys = ["task.type"]
        for key in type_keys:
            if key in labels and labels[key] not in self._valid_task_types:
                result.add_error(
                    f"Invalid task type '{labels[key]}' for '{key}'. "
                    f"Valid values: {sorted(self._valid_task_types)}"
                )

        # Insight type validation
        if "insight_type" in labels:
            if labels["insight_type"] not in self._valid_insight_types:
                result.add_error(
                    f"Invalid insight type '{labels['insight_type']}'. "
                    f"Valid values: {sorted(self._valid_insight_types)}"
                )

        # Handoff status validation
        if "handoff.status" in labels:
            if labels["handoff.status"] not in self._valid_handoff_statuses:
                result.add_error(
                    f"Invalid handoff status '{labels['handoff.status']}'. "
                    f"Valid values: {sorted(self._valid_handoff_statuses)}"
                )

        # Phase validation (if schema provides phases)
        if self.schema and self.schema.phases and "phase" in labels:
            if labels["phase"] not in self.schema.phases:
                result.add_warning(
                    f"Phase '{labels['phase']}' not in schema phases: "
                    f"{self.schema.phases}"
                )


def validate_all(
    metrics: Optional[List[Dict[str, Any]]] = None,
    events: Optional[List[Dict[str, Any]]] = None,
    spans: Optional[List[Dict[str, Any]]] = None,
    schema: Optional[ProjectSchema] = None,
    strict: bool = False,
) -> ValidationResult:
    """
    Validate multiple telemetry items at once.

    Args:
        metrics: List of {"name": str, "labels": dict} items
        events: List of {"event_type": str, "attributes": dict} items
        spans: List of {"attributes": dict, "span_type": str} items
        schema: Optional ProjectSchema
        strict: If True, warnings become errors

    Returns:
        Merged ValidationResult
    """
    validator = ContractValidator(project_schema=schema, strict=strict)
    result = ValidationResult()

    if metrics:
        for m in metrics:
            r = validator.validate_metric(m["name"], m.get("labels", {}))
            result.merge(r)

    if events:
        for e in events:
            r = validator.validate_log_event(e["event_type"], e.get("attributes", {}))
            result.merge(r)

    if spans:
        for s in spans:
            r = validator.validate_span_attributes(
                s.get("attributes", {}),
                s.get("span_type", "task"),
            )
            result.merge(r)

    return result
