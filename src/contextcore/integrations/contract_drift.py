"""
Contract drift detection for ContextCore.

Compares an OpenAPI specification against live service responses to detect
contract drift — missing endpoints, schema mismatches, and unexpected properties.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from contextcore.integrations.openapi_parser import EndpointSpec, parse_openapi

__all__ = ["DriftIssue", "DriftReport", "ContractDriftDetector"]


class DriftSeverity(str, Enum):
    """Severity levels for drift issues."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class DriftIssue:
    """A single contract drift issue detected between spec and live service."""

    endpoint: str
    method: str
    severity: DriftSeverity
    description: str
    expected: Optional[str] = None
    actual: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "endpoint": self.endpoint,
            "method": self.method,
            "severity": self.severity.value,
            "description": self.description,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass
class DriftReport:
    """Aggregated results of a contract drift detection run."""

    project_id: str
    contract_url: str
    service_url: str
    endpoints_checked: int = 0
    endpoints_passed: int = 0
    issues: List[DriftIssue] = field(default_factory=list)

    @property
    def has_drift(self) -> bool:
        """True if any issues were detected."""
        return len(self.issues) > 0

    @property
    def critical_issues(self) -> List[DriftIssue]:
        """Return only critical-severity issues."""
        return [i for i in self.issues if i.severity == DriftSeverity.CRITICAL]

    def to_markdown(self) -> str:
        """Render the report as markdown."""
        lines = [
            f"# Contract Drift Report: {self.project_id}",
            "",
            f"- **Contract**: {self.contract_url}",
            f"- **Service**: {self.service_url}",
            f"- **Endpoints checked**: {self.endpoints_checked}",
            f"- **Endpoints passed**: {self.endpoints_passed}",
            f"- **Issues found**: {len(self.issues)}",
            "",
        ]

        if not self.issues:
            lines.append("No drift detected.")
            return "\n".join(lines)

        lines.append("## Issues")
        lines.append("")
        for issue in self.issues:
            icon = {"critical": "🔴", "warning": "🟡", "info": "🔵"}.get(
                issue.severity.value, "⚪"
            )
            lines.append(f"### {icon} [{issue.severity.value.upper()}] {issue.method} {issue.endpoint}")
            lines.append("")
            lines.append(issue.description)
            if issue.expected:
                lines.append(f"- **Expected**: {issue.expected}")
            if issue.actual:
                lines.append(f"- **Actual**: {issue.actual}")
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "project_id": self.project_id,
            "contract_url": self.contract_url,
            "service_url": self.service_url,
            "endpoints_checked": self.endpoints_checked,
            "endpoints_passed": self.endpoints_passed,
            "has_drift": self.has_drift,
            "issues": [i.to_dict() for i in self.issues],
        }


class ContractDriftDetector:
    """Detects contract drift between an OpenAPI spec and a live service.

    Parses the OpenAPI specification, probes each endpoint on the live
    service, and compares status codes, content types, and response
    schemas to detect drift.
    """

    def __init__(self, timeout: int = 10) -> None:
        """Initialize the detector.

        Args:
            timeout: HTTP request timeout in seconds for probing endpoints.
        """
        self.timeout = timeout

    def detect(
        self,
        project_id: str,
        contract_url: str,
        service_url: str,
    ) -> DriftReport:
        """Run drift detection.

        Args:
            project_id: Project identifier for the report.
            contract_url: URL or file path to the OpenAPI specification.
            service_url: Base URL of the live service to probe.

        Returns:
            DriftReport with all detected issues.
        """
        report = DriftReport(
            project_id=project_id,
            contract_url=contract_url,
            service_url=service_url.rstrip("/"),
        )

        # Parse the contract
        try:
            endpoints = parse_openapi(contract_url)
        except Exception as e:
            report.issues.append(
                DriftIssue(
                    endpoint="*",
                    method="*",
                    severity=DriftSeverity.CRITICAL,
                    description=f"Failed to parse OpenAPI spec: {e}",
                )
            )
            return report

        # Check each endpoint
        for endpoint in endpoints:
            report.endpoints_checked += 1
            issues = self._check_endpoint(endpoint, report.service_url)
            if issues:
                report.issues.extend(issues)
            else:
                report.endpoints_passed += 1

        return report

    def _check_endpoint(
        self, endpoint: EndpointSpec, service_url: str
    ) -> List[DriftIssue]:
        """Check a single endpoint for drift.

        Args:
            endpoint: The endpoint spec from the contract.
            service_url: Base URL of the live service.

        Returns:
            List of drift issues found (empty if endpoint matches spec).
        """
        issues: List[DriftIssue] = []
        url = f"{service_url}{endpoint.path}"

        try:
            req = urllib.request.Request(url, method=endpoint.method)
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                issues.append(
                    DriftIssue(
                        endpoint=endpoint.path,
                        method=endpoint.method,
                        severity=DriftSeverity.CRITICAL,
                        description="Endpoint not found on live service",
                        expected="2xx response",
                        actual=f"HTTP {e.code}",
                    )
                )
            elif e.code >= 500:
                issues.append(
                    DriftIssue(
                        endpoint=endpoint.path,
                        method=endpoint.method,
                        severity=DriftSeverity.CRITICAL,
                        description="Server error when probing endpoint",
                        expected="2xx response",
                        actual=f"HTTP {e.code}",
                    )
                )
            return issues
        except (urllib.error.URLError, OSError) as e:
            issues.append(
                DriftIssue(
                    endpoint=endpoint.path,
                    method=endpoint.method,
                    severity=DriftSeverity.CRITICAL,
                    description=f"Cannot reach endpoint: {e}",
                )
            )
            return issues

        # Check content type
        if endpoint.response_content_type:
            if endpoint.response_content_type not in content_type:
                issues.append(
                    DriftIssue(
                        endpoint=endpoint.path,
                        method=endpoint.method,
                        severity=DriftSeverity.WARNING,
                        description="Response content type mismatch",
                        expected=endpoint.response_content_type,
                        actual=content_type,
                    )
                )

        # Check response schema
        if endpoint.response_schema and "application/json" in content_type:
            try:
                response_data = json.loads(body)
                schema_issues = self._check_schema(
                    endpoint, endpoint.response_schema, response_data
                )
                issues.extend(schema_issues)
            except json.JSONDecodeError:
                issues.append(
                    DriftIssue(
                        endpoint=endpoint.path,
                        method=endpoint.method,
                        severity=DriftSeverity.WARNING,
                        description="Response is not valid JSON despite JSON content type",
                    )
                )

        return issues

    def _check_schema(
        self,
        endpoint: EndpointSpec,
        schema: Dict[str, Any],
        data: Any,
    ) -> List[DriftIssue]:
        """Check response data against expected schema.

        Args:
            endpoint: The endpoint being checked.
            schema: Expected JSON schema from the OpenAPI spec.
            data: Actual response data.

        Returns:
            List of schema-related drift issues.
        """
        issues: List[DriftIssue] = []

        # Check required properties
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        if isinstance(data, dict):
            for prop in required:
                if prop not in data:
                    issues.append(
                        DriftIssue(
                            endpoint=endpoint.path,
                            method=endpoint.method,
                            severity=DriftSeverity.WARNING,
                            description=f"Missing required property: {prop}",
                            expected=f"Property '{prop}' present",
                            actual="Property missing",
                        )
                    )

            # Check for unexpected properties
            if properties:
                for key in data:
                    if key not in properties:
                        issues.append(
                            DriftIssue(
                                endpoint=endpoint.path,
                                method=endpoint.method,
                                severity=DriftSeverity.INFO,
                                description=f"Unexpected property in response: {key}",
                            )
                        )

        return issues
