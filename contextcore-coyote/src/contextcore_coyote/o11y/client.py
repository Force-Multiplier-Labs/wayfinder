"""
Observability client for querying backends.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from contextcore_coyote.config import get_config

logger = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Result from an observability query."""

    query: str
    source: str  # prometheus, loki, tempo
    success: bool
    data: Any = None
    error: Optional[str] = None


class O11yClient:
    """
    Client for querying observability backends.

    Supports Prometheus (metrics), Loki (logs), Tempo (traces),
    and Pyroscope (profiles).
    """

    def __init__(
        self,
        prometheus_url: Optional[str] = None,
        loki_url: Optional[str] = None,
        tempo_url: Optional[str] = None,
        pyroscope_url: Optional[str] = None,
        timeout: float = 30.0,
    ) -> None:
        """
        Initialize the O11y client.

        Args:
            prometheus_url: Prometheus endpoint
            loki_url: Loki endpoint
            tempo_url: Tempo endpoint
            pyroscope_url: Pyroscope endpoint
            timeout: Request timeout in seconds
        """
        config = get_config()

        self.prometheus_url = prometheus_url or config.prometheus_url
        self.loki_url = loki_url or config.loki_url
        self.tempo_url = tempo_url or config.tempo_url
        self.pyroscope_url = pyroscope_url or config.pyroscope_url

        self.client = httpx.Client(timeout=timeout)

    def query_metrics(
        self,
        query: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        step: str = "1m",
    ) -> QueryResult:
        """
        Query Prometheus metrics.

        Args:
            query: PromQL query
            start: Start time (default: 1 hour ago)
            end: End time (default: now)
            step: Step interval

        Returns:
            QueryResult with metric data
        """
        if not self.prometheus_url:
            return QueryResult(
                query=query,
                source="prometheus",
                success=False,
                error="Prometheus URL not configured",
            )

        end = end or datetime.now()
        start = start or (end - timedelta(hours=1))

        try:
            response = self.client.get(
                f"{self.prometheus_url}/api/v1/query_range",
                params={
                    "query": query,
                    "start": start.timestamp(),
                    "end": end.timestamp(),
                    "step": step,
                },
            )
            response.raise_for_status()
            data = response.json()

            return QueryResult(
                query=query,
                source="prometheus",
                success=data.get("status") == "success",
                data=data.get("data", {}).get("result", []),
            )

        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            return QueryResult(
                query=query,
                source="prometheus",
                success=False,
                error=str(e),
            )

    def query_logs(
        self,
        query: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> QueryResult:
        """
        Query Loki logs.

        Args:
            query: LogQL query
            start: Start time (default: 1 hour ago)
            end: End time (default: now)
            limit: Maximum number of log lines

        Returns:
            QueryResult with log data
        """
        if not self.loki_url:
            return QueryResult(
                query=query,
                source="loki",
                success=False,
                error="Loki URL not configured",
            )

        end = end or datetime.now()
        start = start or (end - timedelta(hours=1))

        try:
            response = self.client.get(
                f"{self.loki_url}/loki/api/v1/query_range",
                params={
                    "query": query,
                    "start": int(start.timestamp() * 1e9),  # Loki uses nanoseconds
                    "end": int(end.timestamp() * 1e9),
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()

            return QueryResult(
                query=query,
                source="loki",
                success=data.get("status") == "success",
                data=data.get("data", {}).get("result", []),
            )

        except Exception as e:
            logger.error(f"Loki query failed: {e}")
            return QueryResult(
                query=query,
                source="loki",
                success=False,
                error=str(e),
            )

    def query_traces(
        self,
        query: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 20,
    ) -> QueryResult:
        """
        Query Tempo traces.

        Args:
            query: TraceQL query
            start: Start time (default: 1 hour ago)
            end: End time (default: now)
            limit: Maximum number of traces

        Returns:
            QueryResult with trace data
        """
        if not self.tempo_url:
            return QueryResult(
                query=query,
                source="tempo",
                success=False,
                error="Tempo URL not configured",
            )

        end = end or datetime.now()
        start = start or (end - timedelta(hours=1))

        try:
            response = self.client.get(
                f"{self.tempo_url}/api/search",
                params={
                    "q": query,
                    "start": int(start.timestamp()),
                    "end": int(end.timestamp()),
                    "limit": limit,
                },
            )
            response.raise_for_status()
            data = response.json()

            return QueryResult(
                query=query,
                source="tempo",
                success=True,
                data=data.get("traces", []),
            )

        except Exception as e:
            logger.error(f"Tempo query failed: {e}")
            return QueryResult(
                query=query,
                source="tempo",
                success=False,
                error=str(e),
            )

    def get_trace(self, trace_id: str) -> QueryResult:
        """
        Get a specific trace by ID.

        Args:
            trace_id: Trace ID

        Returns:
            QueryResult with trace data
        """
        if not self.tempo_url:
            return QueryResult(
                query=trace_id,
                source="tempo",
                success=False,
                error="Tempo URL not configured",
            )

        try:
            response = self.client.get(f"{self.tempo_url}/api/traces/{trace_id}")
            response.raise_for_status()

            return QueryResult(
                query=trace_id,
                source="tempo",
                success=True,
                data=response.json(),
            )

        except Exception as e:
            logger.error(f"Tempo trace fetch failed: {e}")
            return QueryResult(
                query=trace_id,
                source="tempo",
                success=False,
                error=str(e),
            )

    def investigate_error(
        self,
        error_message: str,
        timestamp: datetime,
        window: timedelta = timedelta(minutes=5),
    ) -> Dict[str, QueryResult]:
        """
        Investigate an error by querying multiple backends.

        Args:
            error_message: Error message to search for
            timestamp: When the error occurred
            window: Time window around the error

        Returns:
            Dict of QueryResults from each backend
        """
        start = timestamp - window
        end = timestamp + window
        results = {}

        # Query logs for the error
        if self.loki_url:
            log_query = f'{{job=~".+"}} |= "{error_message[:50]}"'
            results["logs"] = self.query_logs(log_query, start, end)

        # Query for error rate metrics
        if self.prometheus_url:
            metric_query = 'rate(http_requests_total{status=~"5.."}[5m])'
            results["metrics"] = self.query_metrics(metric_query, start, end)

        # Query for error traces
        if self.tempo_url:
            trace_query = "{ status = error }"
            results["traces"] = self.query_traces(trace_query, start, end)

        return results

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self) -> "O11yClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()
