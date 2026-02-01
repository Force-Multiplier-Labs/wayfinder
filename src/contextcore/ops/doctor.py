"""
Preflight checks for ContextCore deployment.

Validates system readiness before deployment:
- Required tools (docker, python)
- Docker daemon running
- Port availability
- Disk space
- Data directories
"""

from __future__ import annotations

import shutil
import socket
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class CheckStatus(str, Enum):
    """Status of a preflight check."""

    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


@dataclass
class CheckResult:
    """Result of a single preflight check."""

    name: str
    status: CheckStatus
    message: str
    details: Optional[str] = None


@dataclass
class DoctorResult:
    """Aggregated results of all preflight checks."""

    checks: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.PASS)

    @property
    def warnings(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.WARN)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status == CheckStatus.FAIL)

    @property
    def ready(self) -> bool:
        """System is ready if no failures (warnings are acceptable)."""
        return self.failed == 0

    def add(self, check: CheckResult):
        self.checks.append(check)


# Default ports for observability stack
REQUIRED_PORTS = {
    3000: "Grafana",
    3100: "Loki",
    3200: "Tempo",
    9009: "Mimir",
    4317: "OTLP gRPC",
    4318: "OTLP HTTP",
}

# Required tools
REQUIRED_TOOLS = ["docker", "python3"]

# Optional tools
OPTIONAL_TOOLS = ["docker-compose", "kubectl", "kind"]

# Data directories (relative to project root)
DATA_DIRS = ["data/tempo", "data/mimir", "data/loki", "data/grafana"]


def check_tool(name: str) -> CheckResult:
    """Check if a tool is available in PATH."""
    path = shutil.which(name)
    if path:
        return CheckResult(
            name=f"tool:{name}",
            status=CheckStatus.PASS,
            message=f"{name} found",
            details=path,
        )
    return CheckResult(
        name=f"tool:{name}",
        status=CheckStatus.FAIL,
        message=f"{name} not found",
        details="Install with: brew install {name}" if name != "python3" else None,
    )


def check_docker_running() -> CheckResult:
    """Check if Docker daemon is running."""
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            return CheckResult(
                name="docker:daemon",
                status=CheckStatus.PASS,
                message="Docker is running",
            )
        return CheckResult(
            name="docker:daemon",
            status=CheckStatus.FAIL,
            message="Docker is not running",
            details="Start Docker Desktop or run: sudo systemctl start docker",
        )
    except subprocess.TimeoutExpired:
        return CheckResult(
            name="docker:daemon",
            status=CheckStatus.FAIL,
            message="Docker daemon timed out",
        )
    except FileNotFoundError:
        return CheckResult(
            name="docker:daemon",
            status=CheckStatus.FAIL,
            message="Docker not installed",
        )


def check_port_available(port: int, service: str) -> CheckResult:
    """Check if a port is available for binding."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        result = sock.connect_ex(("127.0.0.1", port))
        if result == 0:
            # Port is in use
            return CheckResult(
                name=f"port:{port}",
                status=CheckStatus.FAIL,
                message=f"Port {port} ({service}) is in use",
                details=f"Free the port or change {service} port",
            )
        # Port is available
        return CheckResult(
            name=f"port:{port}",
            status=CheckStatus.PASS,
            message=f"Port {port} ({service}) is available",
        )
    except socket.error:
        # Assume available if we can't connect
        return CheckResult(
            name=f"port:{port}",
            status=CheckStatus.PASS,
            message=f"Port {port} ({service}) is available",
        )
    finally:
        sock.close()


def check_disk_space(min_gb: int = 10) -> CheckResult:
    """Check if sufficient disk space is available."""
    try:
        stat = os.statvfs(".")
        free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        if free_gb >= min_gb:
            return CheckResult(
                name="disk:space",
                status=CheckStatus.PASS,
                message=f"Disk space: {free_gb:.1f}GB available",
            )
        return CheckResult(
            name="disk:space",
            status=CheckStatus.WARN,
            message=f"Low disk space: {free_gb:.1f}GB (recommended: {min_gb}GB)",
        )
    except Exception as e:
        return CheckResult(
            name="disk:space",
            status=CheckStatus.WARN,
            message=f"Could not check disk space: {e}",
        )


def check_data_directory(path: str, base_path: Optional[Path] = None) -> CheckResult:
    """Check if a data directory exists."""
    if base_path:
        full_path = base_path / path
    else:
        full_path = Path(path)

    if full_path.exists():
        return CheckResult(
            name=f"dir:{path}",
            status=CheckStatus.PASS,
            message=f"{path} exists",
        )
    return CheckResult(
        name=f"dir:{path}",
        status=CheckStatus.WARN,
        message=f"{path} will be created",
        details=f"Directory will be created on 'make up'",
    )


def doctor(
    check_ports: bool = True,
    check_tools: bool = True,
    check_docker: bool = True,
    check_disk: bool = True,
    check_dirs: bool = True,
    base_path: Optional[Path] = None,
) -> DoctorResult:
    """
    Run all preflight checks.

    Args:
        check_ports: Check if required ports are available
        check_tools: Check if required tools are installed
        check_docker: Check if Docker daemon is running
        check_disk: Check disk space
        check_dirs: Check if data directories exist
        base_path: Base path for data directories

    Returns:
        DoctorResult with all check results
    """
    result = DoctorResult()

    # Check required tools
    if check_tools:
        for tool in REQUIRED_TOOLS:
            result.add(check_tool(tool))

    # Check Docker daemon
    if check_docker:
        result.add(check_docker_running())

    # Check ports
    if check_ports:
        for port, service in REQUIRED_PORTS.items():
            result.add(check_port_available(port, service))

    # Check disk space
    if check_disk:
        result.add(check_disk_space())

    # Check data directories
    if check_dirs:
        for dir_path in DATA_DIRS:
            result.add(check_data_directory(dir_path, base_path))

    return result
