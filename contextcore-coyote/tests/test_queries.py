"""Tests for contextcore_coyote.o11y.queries — query builders."""

from __future__ import annotations

import pytest

from contextcore_coyote.o11y.queries import (
    LogQuery,
    MetricsQuery,
    QueryTemplates,
    TraceQuery,
)


# --- MetricsQuery ---


class TestMetricsQuery:
    """Test PromQL query builder."""

    def test_basic_metric(self):
        q = MetricsQuery(base_metric="http_requests_total")
        assert q.build() == "http_requests_total"

    def test_with_labels(self):
        q = MetricsQuery(base_metric="http_requests_total", labels={"job": "api"})
        assert q.build() == 'http_requests_total{job="api"}'

    def test_multiple_labels(self):
        q = MetricsQuery(
            base_metric="http_requests_total",
            labels={"job": "api", "status": "200"},
        )
        result = q.build()
        assert "http_requests_total{" in result
        assert 'job="api"' in result
        assert 'status="200"' in result

    def test_with_rate(self):
        q = MetricsQuery(base_metric="http_requests_total", rate_window="5m")
        assert q.build() == "rate(http_requests_total[5m])"

    def test_with_rate_and_labels(self):
        q = MetricsQuery(
            base_metric="http_requests_total",
            labels={"job": "api"},
            rate_window="5m",
        )
        assert q.build() == 'rate(http_requests_total{job="api"}[5m])'

    def test_with_aggregation(self):
        q = MetricsQuery(base_metric="http_requests_total", aggregation="sum")
        assert q.build() == "sum(http_requests_total)"

    def test_with_rate_and_aggregation(self):
        q = MetricsQuery(
            base_metric="http_requests_total",
            rate_window="5m",
            aggregation="sum",
        )
        assert q.build() == "sum(rate(http_requests_total[5m]))"

    def test_fluent_api_with_label(self):
        q = MetricsQuery(base_metric="up").with_label("job", "api")
        assert q.build() == 'up{job="api"}'

    def test_fluent_api_with_rate(self):
        q = MetricsQuery(base_metric="http_requests_total").with_rate("1m")
        assert q.build() == "rate(http_requests_total[1m])"

    def test_fluent_api_sum(self):
        q = MetricsQuery(base_metric="http_requests_total").sum()
        assert q.build() == "sum(http_requests_total)"

    def test_fluent_api_avg(self):
        q = MetricsQuery(base_metric="http_requests_total").avg()
        assert q.build() == "avg(http_requests_total)"

    def test_empty_labels(self):
        q = MetricsQuery(base_metric="up", labels={})
        assert q.build() == "up"

    def test_full_chain(self):
        q = (
            MetricsQuery(base_metric="http_requests_total")
            .with_label("job", "api")
            .with_rate("5m")
            .sum()
        )
        assert q.build() == 'sum(rate(http_requests_total{job="api"}[5m]))'


# --- LogQuery ---


class TestLogQuery:
    """Test LogQL query builder."""

    def test_basic_stream_selector(self):
        q = LogQuery(stream_selector={"job": "api"})
        assert q.build() == '{job="api"}'

    def test_multiple_selectors(self):
        q = LogQuery(stream_selector={"job": "api", "env": "prod"})
        result = q.build()
        assert 'job="api"' in result
        assert 'env="prod"' in result

    def test_with_line_filter(self):
        q = LogQuery(stream_selector={"job": "api"}, line_filters=["error"])
        assert q.build() == '{job="api"} |= "error"'

    def test_multiple_line_filters(self):
        q = LogQuery(
            stream_selector={"job": "api"},
            line_filters=["error", "timeout"],
        )
        result = q.build()
        assert '|= "error"' in result
        assert '|= "timeout"' in result

    def test_with_json_parser(self):
        q = LogQuery(stream_selector={"job": "api"}, parsers=["json"])
        assert q.build() == '{job="api"} | json'

    def test_with_logfmt_parser(self):
        q = LogQuery(stream_selector={"job": "api"}, parsers=["logfmt"])
        assert q.build() == '{job="api"} | logfmt'

    def test_fluent_api_job(self):
        q = LogQuery().job("api")
        assert q.build() == '{job="api"}'

    def test_fluent_api_contains(self):
        q = LogQuery().job("api").contains("error")
        assert q.build() == '{job="api"} |= "error"'

    def test_fluent_api_json(self):
        q = LogQuery().job("api").json()
        assert q.build() == '{job="api"} | json'

    def test_fluent_api_logfmt(self):
        q = LogQuery().job("api").logfmt()
        assert q.build() == '{job="api"} | logfmt'

    def test_full_chain(self):
        q = LogQuery().job("api").contains("error").json()
        assert q.build() == '{job="api"} |= "error" | json'

    def test_label_filters(self):
        q = LogQuery(
            stream_selector={"job": "api"},
            label_filters=['level = "error"'],
        )
        assert q.build() == '{job="api"} | level = "error"'

    def test_empty_stream_selector(self):
        q = LogQuery(stream_selector={})
        assert q.build() == "{}"


# --- TraceQuery ---


class TestTraceQuery:
    """Test TraceQL query builder."""

    def test_empty_query(self):
        q = TraceQuery()
        assert q.build() == "{}"

    def test_status_filter(self):
        q = TraceQuery().status("error")
        assert q.build() == "{ status = error }"

    def test_service_filter(self):
        q = TraceQuery().service("api")
        assert q.build() == '{ resource.service.name = "api" }'

    def test_operation_filter(self):
        q = TraceQuery().operation("GET /users")
        assert q.build() == '{ name = "GET /users" }'

    def test_duration_filter(self):
        q = TraceQuery().duration(">", "1s")
        assert q.build() == "{ duration > 1s }"

    def test_attribute_filter(self):
        q = TraceQuery().attribute("http.status_code", "500")
        assert q.build() == '{ span.http.status_code = "500" }'

    def test_multiple_conditions(self):
        q = TraceQuery().status("error").service("api")
        result = q.build()
        assert "status = error" in result
        assert 'resource.service.name = "api"' in result
        assert "&&" in result

    def test_full_chain(self):
        q = TraceQuery().service("api").status("error").duration(">", "500ms")
        result = q.build()
        assert "&&" in result
        assert "status = error" in result
        assert "duration > 500ms" in result


# --- QueryTemplates ---


class TestQueryTemplates:
    """Test pre-built query templates."""

    def test_error_rate_with_service(self):
        q = QueryTemplates.error_rate(service="api")
        assert "rate(" in q
        assert 'job="api"' in q
        assert "5.." in q

    def test_error_rate_default(self):
        q = QueryTemplates.error_rate()
        assert "rate(" in q
        assert "5.." in q

    def test_error_rate_custom_window(self):
        q = QueryTemplates.error_rate(window="15m")
        assert "[15m]" in q

    def test_latency_p99_with_service(self):
        q = QueryTemplates.latency_p99(service="api")
        assert "histogram_quantile(0.99" in q
        assert 'job="api"' in q

    def test_latency_p99_default(self):
        q = QueryTemplates.latency_p99()
        assert "histogram_quantile(0.99" in q

    def test_error_logs_with_service(self):
        q = QueryTemplates.error_logs(service="api")
        assert 'job="api"' in q
        assert "error" in q

    def test_error_logs_default(self):
        q = QueryTemplates.error_logs()
        assert 'job=~".+"' in q

    def test_error_logs_custom_text(self):
        q = QueryTemplates.error_logs(error_text="timeout")
        assert "timeout" in q

    def test_failed_traces_with_service(self):
        q = QueryTemplates.failed_traces(service="api")
        assert "status = error" in q
        assert 'resource.service.name = "api"' in q

    def test_failed_traces_default(self):
        q = QueryTemplates.failed_traces()
        assert q == "{ status = error }"

    def test_slow_traces_with_threshold(self):
        q = QueryTemplates.slow_traces(threshold="2s")
        assert "duration > 2s" in q

    def test_slow_traces_with_service(self):
        q = QueryTemplates.slow_traces(service="api")
        assert "duration > 1s" in q
        assert 'resource.service.name = "api"' in q

    def test_slow_traces_default(self):
        q = QueryTemplates.slow_traces()
        assert q == "{ duration > 1s }"
