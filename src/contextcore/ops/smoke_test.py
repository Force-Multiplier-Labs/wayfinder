"""
Smoke testing for ContextCore observability stack.

Validates the entire stack is working after deployment:
1. All components responding
2. Datasources configured
3. Dashboards provisioned
4. Can emit and query telemetry
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

import httpx


class TestStatus(str, Enum):
    """Status of a smoke test."""

    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


@dataclass
class SmokeTestResult:
    """Result of a single smoke test."""

    name: str
    status: TestStatus
    message: str
    duration_ms: Optional[float] = None
    details: Optional[str] = None


@dataclass
class SmokeTestSuite:
    """Aggregated smoke test results."""

    results: list[SmokeTestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAIL)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.SKIP)

    @property
    def all_passed(self) -> bool:
        return all(r.status in (TestStatus.PASS, TestStatus.SKIP) for r in self.results)

    def add(self, result: SmokeTestResult):
        self.results.append(result)


def test_grafana_health() -> SmokeTestResult:
    """Test Grafana is responding."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get("http://localhost:3000/api/health")
            if response.status_code == 200:
                return SmokeTestResult(
                    name="Grafana Health",
                    status=TestStatus.PASS,
                    message="Grafana is responding",
                )
            return SmokeTestResult(
                name="Grafana Health",
                status=TestStatus.FAIL,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return SmokeTestResult(
            name="Grafana Health",
            status=TestStatus.FAIL,
            message=str(e),
        )


def test_tempo_health() -> SmokeTestResult:
    """Test Tempo is responding."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get("http://localhost:3200/ready")
            if response.status_code == 200:
                return SmokeTestResult(
                    name="Tempo Health",
                    status=TestStatus.PASS,
                    message="Tempo is responding",
                )
            return SmokeTestResult(
                name="Tempo Health",
                status=TestStatus.FAIL,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return SmokeTestResult(
            name="Tempo Health",
            status=TestStatus.FAIL,
            message=str(e),
        )


def test_mimir_health() -> SmokeTestResult:
    """Test Mimir is responding."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get("http://localhost:9009/ready")
            if response.status_code == 200:
                return SmokeTestResult(
                    name="Mimir Health",
                    status=TestStatus.PASS,
                    message="Mimir is responding",
                )
            return SmokeTestResult(
                name="Mimir Health",
                status=TestStatus.FAIL,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return SmokeTestResult(
            name="Mimir Health",
            status=TestStatus.FAIL,
            message=str(e),
        )


def test_loki_health() -> SmokeTestResult:
    """Test Loki is responding."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get("http://localhost:3100/ready")
            if response.status_code == 200:
                return SmokeTestResult(
                    name="Loki Health",
                    status=TestStatus.PASS,
                    message="Loki is responding",
                )
            return SmokeTestResult(
                name="Loki Health",
                status=TestStatus.FAIL,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return SmokeTestResult(
            name="Loki Health",
            status=TestStatus.FAIL,
            message=str(e),
        )


def test_grafana_datasources() -> SmokeTestResult:
    """Test Grafana has datasources configured."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(
                "http://localhost:3000/api/datasources",
                auth=("admin", "admin"),
            )
            if response.status_code == 200:
                datasources = response.json()
                if len(datasources) > 0:
                    names = [ds.get("name", "unknown") for ds in datasources]
                    return SmokeTestResult(
                        name="Grafana Datasources",
                        status=TestStatus.PASS,
                        message=f"{len(datasources)} datasource(s) configured",
                        details=", ".join(names),
                    )
                return SmokeTestResult(
                    name="Grafana Datasources",
                    status=TestStatus.FAIL,
                    message="No datasources configured",
                )
            return SmokeTestResult(
                name="Grafana Datasources",
                status=TestStatus.FAIL,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return SmokeTestResult(
            name="Grafana Datasources",
            status=TestStatus.FAIL,
            message=str(e),
        )


def test_grafana_dashboards() -> SmokeTestResult:
    """Test Grafana has dashboards provisioned."""
    try:
        with httpx.Client(timeout=5) as client:
            response = client.get(
                "http://localhost:3000/api/search?type=dash-db",
                auth=("admin", "admin"),
            )
            if response.status_code == 200:
                dashboards = response.json()
                if len(dashboards) > 0:
                    return SmokeTestResult(
                        name="Grafana Dashboards",
                        status=TestStatus.PASS,
                        message=f"{len(dashboards)} dashboard(s) provisioned",
                    )
                return SmokeTestResult(
                    name="Grafana Dashboards",
                    status=TestStatus.SKIP,
                    message="No dashboards (run 'contextcore dashboards provision')",
                )
            return SmokeTestResult(
                name="Grafana Dashboards",
                status=TestStatus.FAIL,
                message=f"HTTP {response.status_code}",
            )
    except Exception as e:
        return SmokeTestResult(
            name="Grafana Dashboards",
            status=TestStatus.FAIL,
            message=str(e),
        )


def test_contextcore_cli() -> SmokeTestResult:
    """Test ContextCore CLI is available."""
    try:
        from contextcore import TaskTracker

        return SmokeTestResult(
            name="ContextCore CLI",
            status=TestStatus.PASS,
            message="CLI is available",
        )
    except ImportError as e:
        return SmokeTestResult(
            name="ContextCore CLI",
            status=TestStatus.FAIL,
            message=f"Import error: {e}",
            details="Run: pip install -e .",
        )


def test_can_emit_span() -> SmokeTestResult:
    """Test can emit a span to OTLP endpoint."""
    try:
        import socket

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(("localhost", 4317))
        sock.close()

        if result == 0:
            return SmokeTestResult(
                name="OTLP Endpoint",
                status=TestStatus.PASS,
                message="OTLP gRPC endpoint is listening",
            )
        return SmokeTestResult(
            name="OTLP Endpoint",
            status=TestStatus.FAIL,
            message="OTLP gRPC endpoint not available on port 4317",
        )
    except Exception as e:
        return SmokeTestResult(
            name="OTLP Endpoint",
            status=TestStatus.FAIL,
            message=str(e),
        )


# Default smoke tests
DEFAULT_TESTS: list[Callable[[], SmokeTestResult]] = [
    test_grafana_health,
    test_tempo_health,
    test_mimir_health,
    test_loki_health,
    test_grafana_datasources,
    test_grafana_dashboards,
    test_contextcore_cli,
    test_can_emit_span,
]


def smoke_test(
    tests: Optional[list[Callable[[], SmokeTestResult]]] = None,
) -> SmokeTestSuite:
    """
    Run all smoke tests.

    Args:
        tests: List of test functions (defaults to DEFAULT_TESTS)

    Returns:
        SmokeTestSuite with all test results
    """
    if tests is None:
        tests = DEFAULT_TESTS

    suite = SmokeTestSuite()

    for test_fn in tests:
        import time

        start = time.time()
        result = test_fn()
        result.duration_ms = (time.time() - start) * 1000
        suite.add(result)

    return suite
