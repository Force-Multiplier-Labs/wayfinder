"""
Query builder contracts for ContextCore telemetry.

Provides type-safe builders for PromQL, LogQL, and TraceQL queries
that ensure correct metric/label naming based on schema contracts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set, Tuple

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


# ---------------------------------------------------------------------------
# Rule file metric extraction and validation
# ---------------------------------------------------------------------------

# Recording rule name pattern: "aggregation:base_metric:function"
_RECORDING_RULE_RE = re.compile(r"\w+:\w+:\w+")


def extract_source_metrics_from_expr(expr: str, prefix: str) -> Set[str]:
    """
    Extract source (raw) metric names from a PromQL expression.

    Distinguishes between:
    - Source metrics: ``startd8_requests_total`` (need to exist in code)
    - Recording rule references: ``service:startd8_availability:rate5m`` (derived)

    The key insight: source metrics appear as bare identifiers, while recording
    rule references use ``aggregation:metric:function`` colon syntax.  A naive
    ``prefix_\\w+`` regex matches substrings of recording rule names, producing
    false positives.

    Algorithm:
    1. Find all ``aggregation:metric:function`` tokens and mask them out.
    2. Match ``prefix_\\w+`` on the remaining text — these are source metrics.

    Args:
        expr: PromQL or LogQL expression string.
        prefix: Metric prefix to search for (e.g., ``"startd8"``).

    Returns:
        Set of source metric names found in the expression.

    Example:
        >>> expr = "service:startd8_availability:rate5m < 0.999"
        >>> extract_source_metrics_from_expr(expr, "startd8")
        set()
        >>> expr = "sum(rate(startd8_requests_total{status=\\"success\\"}[5m]))"
        >>> extract_source_metrics_from_expr(expr, "startd8")
        {'startd8_requests_total'}
    """
    # Step 1: Mask recording rule references so they can't produce false matches
    masked = _RECORDING_RULE_RE.sub(" ", expr)

    # Step 2: Match bare metric names in the cleaned text
    pattern = re.compile(rf"(?<![:\w]){re.escape(prefix)}_[a-z_0-9]+(?![:\w])")
    return set(pattern.findall(masked))


def extract_metrics_from_rule_file(
    rule_data: Dict[str, Any],
    prefix: str,
) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Parse a Prometheus/Loki rule file and classify all metric references.

    Returns three disjoint sets:
    - **source_metrics**: Raw metrics referenced in ``expr:`` fields that must
      exist in application source code.
    - **recording_rules_defined**: Recording rule names declared in ``record:``
      fields (these are created by the rules, not pre-existing).
    - **recording_rules_referenced**: Recording rule names used inside ``expr:``
      fields (must match a ``record:`` definition, either in this file or another).

    Args:
        rule_data: Parsed YAML dict with Prometheus rule group structure.
        prefix: Metric prefix (e.g., ``"startd8"``).

    Returns:
        Tuple of (source_metrics, recording_rules_defined, recording_rules_referenced).

    Example:
        >>> import yaml
        >>> data = yaml.safe_load(open("rules/mimir/startd8-recording-rules.yaml"))
        >>> src, defined, referenced = extract_metrics_from_rule_file(data, "startd8")
        >>> "startd8_requests_total" in src
        True
        >>> "service:startd8_availability:rate5m" in defined
        True
    """
    source_metrics: Set[str] = set()
    recording_rules_defined: Set[str] = set()
    recording_rules_referenced: Set[str] = set()

    prefix_pattern = re.compile(
        rf"\w+:{re.escape(prefix)}_\w+:\w+"
    )

    for group in rule_data.get("groups", []):
        for rule in group.get("rules", []):
            # Collect recording rule definitions
            if "record" in rule:
                recording_rules_defined.add(rule["record"])

            # Analyse expr
            expr = rule.get("expr", "")
            if not expr:
                continue

            # Find recording rule references in the expression
            for match in prefix_pattern.finditer(expr):
                recording_rules_referenced.add(match.group())

            # Extract source metrics (with recording rule names masked out)
            source_metrics.update(
                extract_source_metrics_from_expr(expr, prefix)
            )

    return source_metrics, recording_rules_defined, recording_rules_referenced


def validate_rule_file_metrics(
    rule_data: Dict[str, Any],
    known_source_metrics: Set[str],
    prefix: str,
    recording_rules_from_other_files: Optional[Set[str]] = None,
) -> List[str]:
    """
    Validate that all metric references in a Prometheus/Loki rule file resolve.

    Checks:
    1. Every source metric in ``expr:`` exists in *known_source_metrics*.
    2. Every recording rule referenced in ``expr:`` is either defined in this
       file or in *recording_rules_from_other_files*.

    Args:
        rule_data: Parsed YAML dict with Prometheus rule group structure.
        known_source_metrics: Set of metric names that exist in application code.
        prefix: Metric prefix (e.g., ``"startd8"``).
        recording_rules_from_other_files: Optional set of recording rule names
            defined in companion rule files.

    Returns:
        List of error strings (empty if all references resolve).

    Example:
        >>> errors = validate_rule_file_metrics(
        ...     rule_data=yaml.safe_load(open("startd8-alerts.yaml")),
        ...     known_source_metrics={"startd8_requests_total", "startd8_response_time_ms"},
        ...     prefix="startd8",
        ...     recording_rules_from_other_files={"service:startd8_availability:rate5m"},
        ... )
        >>> errors
        []
    """
    errors: List[str] = []

    src, defined, referenced = extract_metrics_from_rule_file(
        rule_data, prefix
    )

    # Check source metrics exist
    for metric in sorted(src):
        # Strip _bucket suffix — Prometheus histograms auto-generate it
        base = metric.removesuffix("_bucket")
        if metric not in known_source_metrics and base not in known_source_metrics:
            errors.append(f"Unknown source metric: {metric}")

    # Check recording rule references resolve
    all_defined = defined | (recording_rules_from_other_files or set())
    for ref in sorted(referenced):
        if ref not in all_defined:
            errors.append(f"Unresolved recording rule reference: {ref}")

    return errors
