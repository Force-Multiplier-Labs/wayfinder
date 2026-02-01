"""
Health checking for ContextCore observability stack.

Provides health status for:
- Grafana
- Tempo
- Mimir
- Loki
- OTLP endpoints
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import httpx


class HealthStatus(str, Enum):
    """Health status of a component."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component."""

    name: str
    status: HealthStatus
    message: str
    url: Optional[str] = None
    response_time_ms: Optional[float] = None
    details: Optional[dict] = None


@dataclass
class HealthCheckResult:
    """Aggregated health check results."""

    components: list[ComponentHealth] = field(default_factory=list)

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.components if c.status == HealthStatus.HEALTHY)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.components if c.status == HealthStatus.UNHEALTHY)

    @property
    def all_healthy(self) -> bool:
        return all(c.status == HealthStatus.HEALTHY for c in self.components)

    def add(self, component: ComponentHealth):
        self.components.append(component)


# Default component endpoints
DEFAULT_COMPONENTS = {
    "Grafana": {
        "url": "http://localhost:3000/api/health",
        "method": "GET",
    },
    "Tempo": {
        "url": "http://localhost:3200/ready",
        "method": "GET",
    },
    "Mimir": {
        "url": "http://localhost:9009/ready",
        "method": "GET",
    },
    "Loki": {
        "url": "http://localhost:3100/ready",
        "method": "GET",
    },
}


def check_component_health(
    name: str,
    url: str,
    method: str = "GET",
    timeout: float = 5.0,
    expected_status: int = 200,
) -> ComponentHealth:
    """
    Check health of a single component via HTTP.

    Args:
        name: Component name
        url: Health check URL
        method: HTTP method
        timeout: Request timeout in seconds
        expected_status: Expected HTTP status code

    Returns:
        ComponentHealth with status and details
    """
    try:
        with httpx.Client(timeout=timeout) as client:
            import time

            start = time.time()
            response = client.request(method, url)
            elapsed_ms = (time.time() - start) * 1000

            if response.status_code == expected_status:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    message="Ready",
                    url=url,
                    response_time_ms=elapsed_ms,
                )
            else:
                return ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"HTTP {response.status_code}",
                    url=url,
                    response_time_ms=elapsed_ms,
                )
    except httpx.ConnectError:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message="Connection refused",
            url=url,
        )
    except httpx.TimeoutException:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message="Timeout",
            url=url,
        )
    except Exception as e:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNKNOWN,
            message=str(e),
            url=url,
        )


def check_port_listening(name: str, port: int, host: str = "localhost") -> ComponentHealth:
    """
    Check if a port is listening.

    Args:
        name: Component/service name
        port: Port number
        host: Host to check

    Returns:
        ComponentHealth with status
    """
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex((host, port))
        if result == 0:
            return ComponentHealth(
                name=name,
                status=HealthStatus.HEALTHY,
                message=f"Listening on port {port}",
            )
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=f"Not listening on port {port}",
        )
    except socket.error as e:
        return ComponentHealth(
            name=name,
            status=HealthStatus.UNHEALTHY,
            message=f"Socket error: {e}",
        )
    finally:
        sock.close()


def health_check(
    components: Optional[dict] = None,
    include_otlp: bool = True,
) -> HealthCheckResult:
    """
    Check health of all components.

    Args:
        components: Dict of component configs (name -> {url, method})
        include_otlp: Include OTLP endpoint checks

    Returns:
        HealthCheckResult with all component statuses
    """
    if components is None:
        components = DEFAULT_COMPONENTS

    result = HealthCheckResult()

    # Check HTTP endpoints
    for name, config in components.items():
        health = check_component_health(
            name=name,
            url=config["url"],
            method=config.get("method", "GET"),
        )
        result.add(health)

    # Check OTLP endpoints
    if include_otlp:
        result.add(check_port_listening("OTLP gRPC", 4317))
        result.add(check_port_listening("OTLP HTTP", 4318))

    return result
