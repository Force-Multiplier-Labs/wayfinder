"""
Query builders for observability backends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class MetricsQuery:
    """Builder for Prometheus queries."""

    base_metric: str
    labels: dict = field(default_factory=dict)
    rate_window: Optional[str] = None
    aggregation: Optional[str] = None

    def build(self) -> str:
        """Build the PromQL query."""
        # Build label selector
        label_parts = [f'{k}="{v}"' for k, v in self.labels.items()]
        label_selector = "{" + ", ".join(label_parts) + "}" if label_parts else ""

        query = f"{self.base_metric}{label_selector}"

        # Add rate if specified
        if self.rate_window:
            query = f"rate({query}[{self.rate_window}])"

        # Add aggregation if specified
        if self.aggregation:
            query = f"{self.aggregation}({query})"

        return query

    def with_label(self, key: str, value: str) -> "MetricsQuery":
        """Add a label filter."""
        self.labels[key] = value
        return self

    def with_rate(self, window: str = "5m") -> "MetricsQuery":
        """Apply rate function."""
        self.rate_window = window
        return self

    def sum(self) -> "MetricsQuery":
        """Apply sum aggregation."""
        self.aggregation = "sum"
        return self

    def avg(self) -> "MetricsQuery":
        """Apply avg aggregation."""
        self.aggregation = "avg"
        return self


@dataclass
class LogQuery:
    """Builder for Loki queries."""

    stream_selector: dict = field(default_factory=dict)
    line_filters: List[str] = field(default_factory=list)
    label_filters: List[str] = field(default_factory=list)
    parsers: List[str] = field(default_factory=list)

    def build(self) -> str:
        """Build the LogQL query."""
        # Build stream selector
        parts = [f'{k}="{v}"' for k, v in self.stream_selector.items()]
        query = "{" + ", ".join(parts) + "}"

        # Add line filters
        for filter_text in self.line_filters:
            query += f' |= "{filter_text}"'

        # Add label filters
        for label_filter in self.label_filters:
            query += f" | {label_filter}"

        # Add parsers
        for parser in self.parsers:
            query += f" | {parser}"

        return query

    def job(self, job_name: str) -> "LogQuery":
        """Filter by job."""
        self.stream_selector["job"] = job_name
        return self

    def contains(self, text: str) -> "LogQuery":
        """Add a line contains filter."""
        self.line_filters.append(text)
        return self

    def json(self) -> "LogQuery":
        """Parse as JSON."""
        self.parsers.append("json")
        return self

    def logfmt(self) -> "LogQuery":
        """Parse as logfmt."""
        self.parsers.append("logfmt")
        return self


@dataclass
class TraceQuery:
    """Builder for Tempo TraceQL queries."""

    conditions: List[str] = field(default_factory=list)

    def build(self) -> str:
        """Build the TraceQL query."""
        if not self.conditions:
            return "{}"
        return "{ " + " && ".join(self.conditions) + " }"

    def status(self, status: str) -> "TraceQuery":
        """Filter by status."""
        self.conditions.append(f'status = {status}')
        return self

    def service(self, service_name: str) -> "TraceQuery":
        """Filter by service name."""
        self.conditions.append(f'resource.service.name = "{service_name}"')
        return self

    def operation(self, operation_name: str) -> "TraceQuery":
        """Filter by operation name."""
        self.conditions.append(f'name = "{operation_name}"')
        return self

    def duration(self, op: str, value: str) -> "TraceQuery":
        """Filter by duration."""
        self.conditions.append(f"duration {op} {value}")
        return self

    def attribute(self, key: str, value: str) -> "TraceQuery":
        """Filter by span attribute."""
        self.conditions.append(f'span.{key} = "{value}"')
        return self


# Common query templates
class QueryTemplates:
    """Pre-built query templates for common investigation patterns."""

    @staticmethod
    def error_rate(service: str = "", window: str = "5m") -> str:
        """Query for error rate."""
        labels = f'job="{service}"' if service else ""
        return f'sum(rate(http_requests_total{{status=~"5..",{labels}}}[{window}])) / sum(rate(http_requests_total{{{labels}}}[{window}]))'

    @staticmethod
    def latency_p99(service: str = "", window: str = "5m") -> str:
        """Query for P99 latency."""
        labels = f'job="{service}"' if service else ""
        return f"histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{{{labels}}}[{window}])) by (le))"

    @staticmethod
    def error_logs(service: str = "", error_text: str = "error") -> str:
        """Query for error logs."""
        job_filter = f'job="{service}"' if service else 'job=~".+"'
        return f'{{{job_filter}}} |= "{error_text}" | logfmt | level = "error"'

    @staticmethod
    def failed_traces(service: str = "") -> str:
        """Query for failed traces."""
        if service:
            return f'{{ status = error && resource.service.name = "{service}" }}'
        return "{ status = error }"

    @staticmethod
    def slow_traces(threshold: str = "1s", service: str = "") -> str:
        """Query for slow traces."""
        if service:
            return f'{{ duration > {threshold} && resource.service.name = "{service}" }}'
        return f"{{ duration > {threshold} }}"
