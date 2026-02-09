"""
Observability integration for incident investigation.

Query Prometheus, Loki, Tempo, and Pyroscope for correlated signals.
"""

from contextcore_coyote.o11y.client import O11yClient
from contextcore_coyote.o11y.queries import (
    MetricsQuery,
    LogQuery,
    TraceQuery,
    QueryResult,
)

__all__ = [
    "O11yClient",
    "MetricsQuery",
    "LogQuery",
    "TraceQuery",
    "QueryResult",
]
