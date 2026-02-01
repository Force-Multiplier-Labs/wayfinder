"""
Tests for schema contracts - ensuring naming consistency.
"""

import pytest

from contextcore.contracts import (
    MetricName,
    LabelName,
    EventType,
    ProjectSchema,
    validate_labels,
    validate_metric_name,
)
from contextcore.contracts.queries import (
    PromQLBuilder,
    LogQLBuilder,
    TraceQLBuilder,
    generate_dashboard_queries,
    validate_query_against_schema,
)


@pytest.fixture
def lm1_schema():
    """Create LM1 project schema."""
    return ProjectSchema(
        project_id="lm1_campaign",
        metric_prefix="lm1_",
        phases=["foundation", "authority", "launch", "scale"],
    )


@pytest.fixture
def contextcore_schema():
    """Create ContextCore project schema."""
    return ProjectSchema(
        project_id="contextcore",
        metric_prefix="cc_",
        phases=["core", "agent", "integrations"],
    )


class TestMetricName:
    """Tests for MetricName enum."""

    def test_metric_values_lowercase(self):
        """All metric names should be lowercase."""
        for metric in MetricName:
            assert metric.value == metric.value.lower()

    def test_metric_values_underscore(self):
        """Multi-word metrics should use underscores."""
        assert MetricName.COMPLETION_RATE.value == "completion_rate"
        assert MetricName.BLOCKED_COUNT.value == "blocked_count"


class TestLabelName:
    """Tests for LabelName enum."""

    def test_project_label(self):
        """Project label should be 'project'."""
        assert LabelName.PROJECT.value == "project"

    def test_label_values_lowercase(self):
        """All label names should be lowercase."""
        for label in LabelName:
            assert label.value == label.value.lower()


class TestEventType:
    """Tests for EventType enum."""

    def test_event_format(self):
        """Events should be namespace.action format."""
        for event in EventType:
            assert "." in event.value

    def test_task_events(self):
        """Task events should start with 'task.'."""
        task_events = [
            EventType.TASK_CREATED,
            EventType.TASK_STATUS_CHANGED,
            EventType.TASK_BLOCKED,
            EventType.TASK_UNBLOCKED,
            EventType.TASK_COMPLETED,
            EventType.TASK_CANCELLED,
            EventType.TASK_PROGRESS_UPDATED,
        ]
        for event in task_events:
            assert event.value.startswith("task.")


class TestProjectSchema:
    """Tests for ProjectSchema."""

    def test_metric_prefix_normalized(self):
        """Prefix should end with underscore."""
        schema = ProjectSchema(
            project_id="test",
            metric_prefix="test",  # No underscore
        )
        assert schema.metric_prefix == "test_"

    def test_metric_prefix_lowercase_required(self):
        """Prefix must be lowercase."""
        with pytest.raises(ValueError):
            ProjectSchema(
                project_id="test",
                metric_prefix="TEST_",
            )

    def test_metric_returns_full_name(self, lm1_schema):
        """metric() should return prefix + metric name."""
        assert lm1_schema.metric(MetricName.PROGRESS) == "lm1_progress"
        assert lm1_schema.metric(MetricName.TASKS_TOTAL) == "lm1_tasks_total"

    def test_promql_with_project_label(self, lm1_schema):
        """promql() should include project label."""
        query = lm1_schema.promql(MetricName.PROGRESS)
        assert 'project="lm1_campaign"' in query
        assert query.startswith("lm1_progress{")

    def test_promql_with_extra_labels(self, lm1_schema):
        """promql() should include extra labels."""
        query = lm1_schema.promql(MetricName.TASKS_TOTAL, status="done")
        assert 'status="done"' in query
        assert 'project="lm1_campaign"' in query

    def test_logql_basic(self, lm1_schema):
        """logql() should create stream selector."""
        query = lm1_schema.logql()
        assert query == '{project="lm1_campaign"}'

    def test_logql_with_event(self, lm1_schema):
        """logql() with event should add filter."""
        query = lm1_schema.logql(event_type=EventType.TASK_COMPLETED)
        assert 'json' in query
        assert 'event = "task.completed"' in query

    def test_validate_phase(self, lm1_schema):
        """validate_phase() should check against defined phases."""
        assert lm1_schema.validate_phase("foundation") is True
        assert lm1_schema.validate_phase("invalid") is False

    def test_validate_status(self, lm1_schema):
        """validate_status() should check against default statuses."""
        assert lm1_schema.validate_status("done") is True
        assert lm1_schema.validate_status("in_progress") is True
        assert lm1_schema.validate_status("invalid") is False


class TestValidateLabels:
    """Tests for validate_labels function."""

    def test_valid_labels(self):
        """Valid labels should return empty error list."""
        labels = {"project": "test", "status": "done"}
        errors = validate_labels(labels)
        assert errors == []

    def test_missing_required_label(self):
        """Missing required label should return error."""
        labels = {"status": "done"}  # Missing project
        errors = validate_labels(labels)
        assert len(errors) == 1
        assert "project" in errors[0]

    def test_empty_value(self):
        """Empty label value should return error."""
        labels = {"project": "", "status": "done"}
        errors = validate_labels(labels)
        assert len(errors) == 1
        assert "Empty" in errors[0]

    def test_custom_required_labels(self):
        """Should check custom required labels."""
        labels = {"project": "test"}
        errors = validate_labels(labels, required={"project", "phase", "status"})
        assert len(errors) == 1
        assert "phase" in errors[0] or "status" in errors[0]


class TestValidateMetricName:
    """Tests for validate_metric_name function."""

    def test_valid_metric(self):
        """Valid metric should return empty error list."""
        errors = validate_metric_name("lm1_progress", prefix="lm1_")
        assert errors == []

    def test_wrong_prefix(self):
        """Wrong prefix should return error."""
        errors = validate_metric_name("wrong_progress", prefix="lm1_")
        assert len(errors) >= 1
        assert "prefix" in errors[0].lower()

    def test_uppercase_invalid(self):
        """Uppercase metric should return error."""
        errors = validate_metric_name("LM1_PROGRESS")
        assert len(errors) >= 1
        assert "lowercase" in errors[0].lower()


class TestPromQLBuilder:
    """Tests for PromQLBuilder."""

    def test_basic_query(self, lm1_schema):
        """Basic query should include metric and project."""
        builder = PromQLBuilder(schema=lm1_schema)
        query = builder.metric(MetricName.PROGRESS).build()
        assert query == 'lm1_progress{project="lm1_campaign"}'

    def test_with_labels(self, lm1_schema):
        """Query with labels should include them."""
        builder = PromQLBuilder(schema=lm1_schema)
        query = (
            builder
            .metric(MetricName.TASKS_TOTAL)
            .label("status", "done")
            .build()
        )
        assert 'status="done"' in query

    def test_sum_by(self, lm1_schema):
        """sum_by should wrap query."""
        builder = PromQLBuilder(schema=lm1_schema)
        query = (
            builder
            .metric(MetricName.TASKS_TOTAL)
            .sum_by("phase")
            .build()
        )
        assert query.startswith("sum by (phase)")

    def test_rate(self, lm1_schema):
        """rate should add range and wrap."""
        builder = PromQLBuilder(schema=lm1_schema)
        query = (
            builder
            .metric(MetricName.TASKS_TOTAL)
            .rate("5m")
            .build()
        )
        assert "[5m]" in query
        assert "rate(" in query

    def test_missing_metric_raises(self, lm1_schema):
        """Building without metric should raise."""
        builder = PromQLBuilder(schema=lm1_schema)
        with pytest.raises(ValueError):
            builder.build()


class TestLogQLBuilder:
    """Tests for LogQLBuilder."""

    def test_basic_query(self, lm1_schema):
        """Basic query should create stream selector."""
        builder = LogQLBuilder(schema=lm1_schema)
        query = builder.build()
        assert query == '{project="lm1_campaign"}'

    def test_with_json_parser(self, lm1_schema):
        """Should add json parser."""
        builder = LogQLBuilder(schema=lm1_schema)
        query = builder.json().build()
        assert "| json" in query

    def test_with_event_filter(self, lm1_schema):
        """Should filter by event type."""
        builder = LogQLBuilder(schema=lm1_schema)
        query = builder.json().event(EventType.TASK_COMPLETED).build()
        assert 'event = "task.completed"' in query

    def test_line_format(self, lm1_schema):
        """Should add line formatting."""
        builder = LogQLBuilder(schema=lm1_schema)
        query = (
            builder
            .json()
            .line_format("Task {{.task_id}} completed")
            .build()
        )
        assert "line_format" in query
        assert "{{.task_id}}" in query


class TestTraceQLBuilder:
    """Tests for TraceQLBuilder."""

    def test_basic_query(self, lm1_schema):
        """Basic query should include project."""
        builder = TraceQLBuilder(schema=lm1_schema)
        query = builder.build()
        assert 'resource.project.id = "lm1_campaign"' in query

    def test_with_span_attr(self, lm1_schema):
        """Should filter by span attribute."""
        builder = TraceQLBuilder(schema=lm1_schema)
        query = builder.span_attr("task.id", "TASK-123").build()
        assert 'span.task.id = "TASK-123"' in query

    def test_with_service(self, lm1_schema):
        """Should filter by service name."""
        builder = TraceQLBuilder(schema=lm1_schema)
        query = builder.service("contextcore").build()
        assert 'resource.service.name = "contextcore"' in query


class TestGenerateDashboardQueries:
    """Tests for dashboard query generation."""

    def test_generates_all_panels(self, lm1_schema):
        """Should generate queries for all standard panels."""
        queries = generate_dashboard_queries(lm1_schema)

        expected_panels = [
            "overall_progress",
            "completion_rate",
            "blocked_count",
            "tasks_complete",
            "tasks_in_progress",
            "tasks_by_status",
            "phase_progress",
            "task_percent_complete",
            "activity_log",
        ]

        for panel in expected_panels:
            assert panel in queries

    def test_queries_use_correct_schema(self, lm1_schema):
        """All queries should use schema's metric prefix."""
        queries = generate_dashboard_queries(lm1_schema)

        for name, query in queries.items():
            if name != "activity_log":  # LogQL doesn't have metric prefix
                assert 'lm1_' in query or query.startswith("{")


class TestValidateQueryAgainstSchema:
    """Tests for query validation."""

    def test_valid_query(self, lm1_schema):
        """Valid query should return no errors."""
        query = 'lm1_progress{project="lm1_campaign"}'
        errors = validate_query_against_schema(query, lm1_schema)
        assert errors == []

    def test_wrong_project_label(self, lm1_schema):
        """Wrong project should return error."""
        query = 'lm1_progress{project="wrong_project"}'
        errors = validate_query_against_schema(query, lm1_schema)
        assert len(errors) >= 1
        assert "lm1_campaign" in errors[0]
