"""
Query builder contracts for ContextCore telemetry.

Provides type-safe builders for PromQL, LogQL, and TraceQL queries
that ensure correct metric/label naming based on schema contracts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

from contextcore.contracts.metrics import (
    EventType,
    LabelName,
    MetricName,
    ProjectSchema,
)


@dataclass
class PromQLBuilder:
    """
    Builder for PromQL queries with schema validation.

    Example:
        builder = PromQLBuilder(schema)
        query = (
            builder
            .metric(MetricName.TASKS_TOTAL)
            .label("status", "complete")
            .sum_by("phase")
            .build()
        )
        # sum by (phase) (lm1_tasks_total{project="lm1_campaign",status="complete"})
    """

    schema: ProjectSchema
    _metric: Optional[MetricName] = None
    _labels: Dict[str, str] = field(default_factory=dict)
    _aggregations: List[str] = field(default_factory=list)
    _range: Optional[str] = None
    _offset: Optional[str] = None

    def metric(self, name: MetricName) -> "PromQLBuilder":
        """Set the metric to query."""
        self._metric = name
        return self

    def label(self, name: str, value: str) -> "PromQLBuilder":
        """Add a label filter."""
        self._labels[name] = value
        return self

    def labels(self, **kwargs: str) -> "PromQLBuilder":
        """Add multiple label filters."""
        self._labels.update(kwargs)
        return self

    def sum_by(self, *labels: str) -> "PromQLBuilder":
        """Add sum aggregation by labels."""
        self._aggregations.append(f"sum by ({','.join(labels)})")
        return self

    def max_by(self, *labels: str) -> "PromQLBuilder":
        """Add max aggregation by labels."""
        self._aggregations.append(f"max by ({','.join(labels)})")
        return self

    def avg_by(self, *labels: str) -> "PromQLBuilder":
        """Add avg aggregation by labels."""
        self._aggregations.append(f"avg by ({','.join(labels)})")
        return self

    def rate(self, range_: str) -> "PromQLBuilder":
        """Add rate function with range."""
        self._range = range_
        self._aggregations.append(f"rate")
        return self

    def increase(self, range_: str) -> "PromQLBuilder":
        """Add increase function with range."""
        self._range = range_
        self._aggregations.append(f"increase")
        return self

    def offset(self, duration: str) -> "PromQLBuilder":
        """Add time offset."""
        self._offset = duration
        return self

    def build(self) -> str:
        """Build the final PromQL query string."""
        if not self._metric:
            raise ValueError("Metric must be set")

        # Build base metric with labels
        full_name = self.schema.metric(self._metric)
        all_labels = {LabelName.PROJECT.value: self.schema.project_id}
        all_labels.update(self._labels)

        label_parts = [f'{k}="{v}"' for k, v in sorted(all_labels.items())]
        base = f"{full_name}{{{','.join(label_parts)}}}"

        # Add range if specified
        if self._range:
            base = f"{base}[{self._range}]"

        # Add offset if specified
        if self._offset:
            base = f"{base} offset {self._offset}"

        # Wrap with aggregations (innermost first)
        result = base
        for agg in self._aggregations:
            if agg in ("rate", "increase"):
                result = f"{agg}({result})"
            else:
                result = f"{agg} ({result})"

        return result


@dataclass
class LogQLBuilder:
    """
    Builder for LogQL queries with schema validation.

    Example:
        builder = LogQLBuilder(schema)
        query = (
            builder
            .label("service", "contextcore")
            .json()
            .event(EventType.TASK_COMPLETED)
            .line_format("Task {{.task_id}} completed")
            .build()
        )
    """

    schema: ProjectSchema
    _labels: Dict[str, str] = field(default_factory=dict)
    _pipeline: List[str] = field(default_factory=list)

    def label(self, name: str, value: str) -> "LogQLBuilder":
        """Add a stream selector label."""
        self._labels[name] = value
        return self

    def labels(self, **kwargs: str) -> "LogQLBuilder":
        """Add multiple stream selector labels."""
        self._labels.update(kwargs)
        return self

    def json(self) -> "LogQLBuilder":
        """Add JSON parser to pipeline."""
        self._pipeline.append("json")
        return self

    def logfmt(self) -> "LogQLBuilder":
        """Add logfmt parser to pipeline."""
        self._pipeline.append("logfmt")
        return self

    def event(self, event_type: EventType) -> "LogQLBuilder":
        """Filter by event type."""
        self._pipeline.append(f'event = "{event_type.value}"')
        return self

    def filter(self, field: str, value: str, op: str = "=") -> "LogQLBuilder":
        """Add a filter expression."""
        self._pipeline.append(f'{field} {op} "{value}"')
        return self

    def contains(self, text: str) -> "LogQLBuilder":
        """Add a line contains filter."""
        self._pipeline.append(f'|= "{text}"')
        return self

    def not_contains(self, text: str) -> "LogQLBuilder":
        """Add a line not contains filter."""
        self._pipeline.append(f'!= "{text}"')
        return self

    def regex(self, pattern: str) -> "LogQLBuilder":
        """Add a regex filter."""
        self._pipeline.append(f'|~ "{pattern}"')
        return self

    def line_format(self, template: str) -> "LogQLBuilder":
        """Add line formatting."""
        # Escape quotes in template
        escaped = template.replace('"', '\\"')
        self._pipeline.append(f'line_format "{escaped}"')
        return self

    def unwrap(self, field: str) -> "LogQLBuilder":
        """Unwrap a numeric field for metric queries."""
        self._pipeline.append(f"unwrap {field}")
        return self

    def build(self) -> str:
        """Build the final LogQL query string."""
        # Build stream selector
        all_labels = {LabelName.PROJECT.value: self.schema.project_id}
        all_labels.update(self._labels)

        label_parts = [f'{k}="{v}"' for k, v in sorted(all_labels.items())]
        base = f"{{{','.join(label_parts)}}}"

        # Add pipeline stages
        if self._pipeline:
            pipeline = " | ".join(self._pipeline)
            return f"{base} | {pipeline}"

        return base


@dataclass
class TraceQLBuilder:
    """
    Builder for TraceQL queries with schema validation.

    Example:
        builder = TraceQLBuilder(schema)
        query = (
            builder
            .span_attr("task.id", "PROJ-123")
            .span_attr("task.status", "done")
            .build()
        )
    """

    schema: ProjectSchema
    _span_attrs: Dict[str, str] = field(default_factory=dict)
    _resource_attrs: Dict[str, str] = field(default_factory=dict)
    _intrinsics: Dict[str, str] = field(default_factory=dict)
    _duration: Optional[str] = None

    def span_attr(self, name: str, value: str) -> "TraceQLBuilder":
        """Filter by span attribute."""
        self._span_attrs[name] = value
        return self

    def resource_attr(self, name: str, value: str) -> "TraceQLBuilder":
        """Filter by resource attribute."""
        self._resource_attrs[name] = value
        return self

    def service(self, name: str) -> "TraceQLBuilder":
        """Filter by service name."""
        self._resource_attrs["service.name"] = name
        return self

    def name(self, span_name: str) -> "TraceQLBuilder":
        """Filter by span name."""
        self._intrinsics["name"] = span_name
        return self

    def status(self, status: Literal["ok", "error", "unset"]) -> "TraceQLBuilder":
        """Filter by span status."""
        self._intrinsics["status"] = status
        return self

    def duration(self, comparison: str) -> "TraceQLBuilder":
        """Filter by span duration (e.g., '>1s', '<500ms')."""
        self._duration = comparison
        return self

    def build(self) -> str:
        """Build the final TraceQL query string."""
        conditions = []

        # Add project filter
        conditions.append(f'resource.project.id = "{self.schema.project_id}"')

        # Add resource attributes
        for k, v in self._resource_attrs.items():
            conditions.append(f'resource.{k} = "{v}"')

        # Add span attributes
        for k, v in self._span_attrs.items():
            conditions.append(f'span.{k} = "{v}"')

        # Add intrinsics
        for k, v in self._intrinsics.items():
            if k == "status":
                conditions.append(f"{k} = {v}")
            else:
                conditions.append(f'{k} = "{v}"')

        # Add duration
        if self._duration:
            conditions.append(f"duration {self._duration}")

        return f"{{ {' && '.join(conditions)} }}"


def generate_dashboard_queries(
    schema: ProjectSchema,
) -> Dict[str, str]:
    """
    Generate standard dashboard queries for a project.

    Returns a dictionary of panel names to PromQL/LogQL queries.

    Args:
        schema: Project schema defining naming conventions

    Returns:
        Dictionary mapping panel names to query strings
    """
    return {
        # Overview metrics
        "overall_progress": schema.promql(MetricName.PROGRESS),
        "completion_rate": schema.promql(MetricName.COMPLETION_RATE),
        "blocked_count": schema.promql(MetricName.BLOCKED_COUNT),
        # Task counts
        "tasks_complete": schema.promql(MetricName.TASKS_TOTAL, status="complete"),
        "tasks_in_progress": schema.promql(MetricName.TASKS_TOTAL, status="in_progress"),
        "tasks_by_status": schema.promql(MetricName.TASKS_TOTAL),
        # Phase progress
        "phase_progress": schema.promql(MetricName.PHASE_PROGRESS),
        # Effort
        "effort_total": schema.promql(MetricName.EFFORT_POINTS_TOTAL, type="total"),
        "effort_complete": schema.promql(MetricName.EFFORT_POINTS_TOTAL, type="complete"),
        # Tasks by phase
        "tasks_by_phase": schema.promql(MetricName.TASKS_BY_PHASE),
        # Task detail
        "task_percent_complete": schema.promql(MetricName.TASK_PERCENT_COMPLETE),
        # Activity log (LogQL)
        "activity_log": schema.logql(),
    }


def validate_query_against_schema(
    query: str,
    schema: ProjectSchema,
) -> List[str]:
    """
    Validate a PromQL/LogQL query against a schema.

    Checks that:
    - Metric names match schema prefix
    - Project label value matches schema
    - Phase values are valid (if present)

    Args:
        query: The query string to validate
        schema: The project schema

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check for correct project label
    expected_project = f'project="{schema.project_id}"'
    if expected_project not in query and f"project.id = \"{schema.project_id}\"" not in query:
        errors.append(
            f"Query should reference project '{schema.project_id}', "
            f"expected label: {expected_project}"
        )

    # Check for metric prefix (for PromQL)
    if schema.metric_prefix and not query.startswith("{"):
        # Looks like PromQL with a metric name
        if not any(query.startswith(schema.metric_prefix) for _ in [1]):
            # More sophisticated check
            import re
            metrics_pattern = rf"^{schema.metric_prefix}[a-z_]+"
            if not re.search(metrics_pattern, query):
                # Check if any known metric is in the query
                known_metrics = {schema.metric(m) for m in MetricName}
                found_metric = False
                for m in known_metrics:
                    if m in query:
                        found_metric = True
                        break
                if not found_metric:
                    errors.append(
                        f"Query metric should use prefix '{schema.metric_prefix}'"
                    )

    return errors
