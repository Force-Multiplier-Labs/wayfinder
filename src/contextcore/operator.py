"""
Kubernetes operator for ProjectContext CRD using kopf framework.

This operator watches ProjectContext resources and generates observability
artifacts (ServiceMonitor, PrometheusRules, Grafana dashboards) based on
the project context metadata.

Prime Contractor Pattern: Components drafted by Haiku, assembled by Opus.
"""

from __future__ import annotations

import functools
import json
import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypeVar

import kopf
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

# Schema compatibility helpers for v1/v1alpha1
from contextcore.crd_helpers import (
    get_criticality,
    get_metrics_config,
    get_owner,
    get_project_id,
    get_service_name,
)

T = TypeVar("T")


# =============================================================================
# JSON Structured Logging for Loki
# =============================================================================


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging optimized for Loki ingestion.

    Outputs JSON objects with standard fields and support for contextual extras.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON for Loki ingestion."""
        entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Add exception info if present
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from logging call
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs", "message",
                "pathname", "process", "processName", "relativeCreated",
                "thread", "threadName", "exc_info", "exc_text", "stack_info",
            ):
                if not key.startswith("_"):
                    entry[key] = value

        return json.dumps(entry, default=str)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure root logger with JSON formatter for Loki ingestion."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create stdout handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    root_logger.addHandler(handler)

    return root_logger


logger = logging.getLogger("contextcore.operator")


# =============================================================================
# OpenTelemetry Tracing
# =============================================================================


class OperatorTracer:
    """OpenTelemetry tracing integration for Kubernetes operators."""

    def __init__(
        self,
        service_name: Optional[str] = None,
        endpoint: Optional[str] = None,
    ):
        """Initialize operator tracer with OTLP exporter."""
        self.service_name = service_name or os.environ.get(
            "OTEL_SERVICE_NAME", "contextcore-operator"
        )
        self.endpoint = endpoint or os.environ.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
        )

        # Initialize resource with service metadata
        resource = Resource.create({
            "service.name": self.service_name,
            "service.namespace": "contextcore",
        })

        # Create tracer provider
        self._provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(self._provider)

        # Add OTLP exporter
        self._setup_exporter()

        # Get tracer instance
        self._tracer = trace.get_tracer(__name__)

    def _setup_exporter(self) -> None:
        """Configure OTLP exporter."""
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )

            exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
            self._provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(
                "OTLP exporter configured",
                extra={
                    "service_name": self.service_name,
                    "endpoint": self.endpoint,
                },
            )
        except ImportError:
            logger.warning(
                "OTLP exporter not installed; spans will not be exported",
                extra={"install_cmd": "pip install opentelemetry-exporter-otlp"},
            )

    @contextmanager
    def trace_action(
        self,
        action: str,
        project_id: str,
        resource_name: str,
        resource_namespace: str,
        **extra_attributes: Any,
    ):
        """Context manager for tracing operator actions."""
        attributes: Dict[str, Any] = {
            "project.id": project_id,
            "k8s.resource.name": resource_name,
            "k8s.resource.namespace": resource_namespace,
            "operator.action": action,
        }
        attributes.update(extra_attributes)

        span = self._tracer.start_span(
            name=f"operator.{action}",
            kind=SpanKind.INTERNAL,
            attributes=attributes,
        )

        try:
            yield span
            span.set_status(Status(StatusCode.OK))
            span.add_event("action_completed", attributes={"action": action})
        except Exception as exc:
            span.record_exception(exc)
            span.set_status(Status(StatusCode.ERROR, f"{action} failed: {exc}"))
            raise
        finally:
            span.end()

    def shutdown(self) -> None:
        """Flush and shutdown the tracer provider."""
        self._provider.force_flush()
        self._provider.shutdown()


# Global tracer instance
_tracer: Optional[OperatorTracer] = None


def get_tracer() -> OperatorTracer:
    """Get or create the global operator tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = OperatorTracer()
    return _tracer


# =============================================================================
# Artifact Generators
# =============================================================================


def generate_cost_labels(spec: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate labels for cost attribution from business context.

    These labels enable cloud cost tracking by business unit when applied
    to generated resources (ServiceMonitor, PrometheusRule, Dashboard ConfigMap).

    Extracts:
    - cost-center from business.costCenter
    - owner from business.owner
    - business-value from business.value
    - criticality from business.criticality
    - project-id from project.id or project (string)
    """
    labels: Dict[str, str] = {}

    business = spec.get("business", {})

    if business.get("costCenter"):
        labels["cost-center"] = _sanitize_label_value(business["costCenter"])

    if business.get("owner"):
        labels["owner"] = _sanitize_label_value(business["owner"])

    if business.get("value"):
        labels["business-value"] = _sanitize_label_value(business["value"])

    if business.get("criticality"):
        labels["criticality"] = _sanitize_label_value(business["criticality"])

    # Add project reference
    project = spec.get("project", {})
    if isinstance(project, dict) and project.get("id"):
        labels["project-id"] = _sanitize_label_value(project["id"])
    elif isinstance(project, str):
        labels["project-id"] = _sanitize_label_value(project)

    return labels


def _sanitize_label_value(value: str) -> str:
    """
    Sanitize a string to be a valid Kubernetes label value.

    Label values must:
    - Be 63 characters or less
    - Begin and end with alphanumeric characters
    - Contain only alphanumerics, '-', '_', or '.'
    """
    import re

    # Replace invalid characters with hyphens
    sanitized = re.sub(r"[^a-zA-Z0-9\-_.]", "-", str(value))
    # Remove leading/trailing non-alphanumeric characters
    sanitized = re.sub(r"^[^a-zA-Z0-9]+", "", sanitized)
    sanitized = re.sub(r"[^a-zA-Z0-9]+$", "", sanitized)
    # Truncate to 63 characters
    return sanitized[:63]


def generate_service_monitor(
    name: str,
    namespace: str,
    spec: Dict[str, Any],
    labels: Dict[str, str],
) -> Dict[str, Any]:
    """
    Generate a Kubernetes ServiceMonitor CR from a ProjectContext spec.

    Supports both v1 (nested) and v1alpha1 (flat) schemas.

    Scrape interval is derived from criticality:
    - critical: 10s
    - high: 30s
    - medium: 60s
    - low: 120s

    Includes cost attribution labels from business context.
    """
    project_id = get_project_id(spec, name)
    service = get_service_name(spec, name)
    criticality = (get_criticality(spec) or "medium").lower()

    scrape_interval = {
        "critical": "10s",
        "high": "30s",
        "medium": "60s",
        "low": "120s",
    }.get(criticality, "60s")

    metadata_labels = {
        "contextcore.io/project": project_id,
        "contextcore.io/service": service,
        "contextcore.io/criticality": criticality,
        "contextcore.io/managed-by": "contextcore-operator",
    }
    # Add cost attribution labels
    cost_labels = generate_cost_labels(spec)
    metadata_labels.update(cost_labels)
    metadata_labels.update(labels)

    return {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "ServiceMonitor",
        "metadata": {
            "name": f"{name}-monitor",
            "namespace": namespace,
            "labels": metadata_labels,
            "ownerReferences": [],  # Filled by caller
        },
        "spec": {
            "selector": {
                "matchLabels": {"app": service},
            },
            "endpoints": [
                {
                    "port": "metrics",
                    "interval": scrape_interval,
                    "path": "/metrics",
                },
            ],
        },
    }


def generate_prometheus_rules(
    name: str,
    namespace: str,
    spec: Dict[str, Any],
    labels: Dict[str, str],
) -> Dict[str, Any]:
    """
    Generate a PrometheusRule CR with recording and alerting rules.

    Supports both v1 (nested) and v1alpha1 (flat) schemas.
    Uses configurable metric names from spec.observability.metrics.

    Alert severity and detection windows are derived from criticality:
    - critical: P1 alerts, 1m detection
    - high: P2 alerts, 5m detection
    - medium: P3 alerts, 15m detection
    - low: P4 alerts, 30m detection

    Alert annotations are enriched with contextual information from ProjectContext:
    - architecture_decision from design.adr
    - runbook_url from observability.runbook
    - owner and business_criticality from business.*
    - known_risks summary from risks[]
    """
    project_id = get_project_id(spec, name)
    service = get_service_name(spec, name)
    criticality = (get_criticality(spec) or "medium").lower()
    metrics = get_metrics_config(spec)
    requests_metric = metrics["requestsTotal"]
    duration_metric = metrics["durationBucket"]

    config_map = {
        "critical": {"severity": "P1", "window": "1m", "threshold": 99.95},
        "high": {"severity": "P2", "window": "5m", "threshold": 99.9},
        "medium": {"severity": "P3", "window": "15m", "threshold": 99.5},
        "low": {"severity": "P4", "window": "30m", "threshold": 99.0},
    }
    cfg = config_map.get(criticality, config_map["medium"])

    metadata_labels = {
        "contextcore.io/project": project_id,
        "contextcore.io/service": service,
        "contextcore.io/criticality": criticality,
        "contextcore.io/managed-by": "contextcore-operator",
    }
    # Add cost attribution labels
    cost_labels = generate_cost_labels(spec)
    metadata_labels.update(cost_labels)
    metadata_labels.update(labels)

    # Build enriched annotations from ProjectContext metadata
    base_annotations = _build_enriched_annotations(spec, project_id, service, cfg)

    # Create availability alert annotations
    availability_annotations = base_annotations.copy()
    availability_annotations["summary"] = f"{service} availability below {cfg['threshold']}%"
    availability_annotations["description"] = (
        f"Service {service} (project {project_id}) availability SLO violation"
    )

    # Create latency alert annotations
    latency_annotations = base_annotations.copy()
    latency_annotations["summary"] = f"{service} P99 latency elevated"
    latency_annotations["description"] = (
        f"Service {service} (project {project_id}) P99 latency exceeds 500ms"
    )

    return {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "PrometheusRule",
        "metadata": {
            "name": f"{name}-rules",
            "namespace": namespace,
            "labels": metadata_labels,
            "ownerReferences": [],
        },
        "spec": {
            "groups": [
                {
                    "name": f"{service}.recording.rules",
                    "interval": "30s",
                    "rules": [
                        {
                            "record": f"{service}:availability:rate5m",
                            "expr": f'(sum(rate({requests_metric}{{service="{service}",status=~"2.."}}[5m])) / sum(rate({requests_metric}{{service="{service}"}}[5m]))) * 100',
                            "labels": {"service": service, "sli_type": "availability"},
                        },
                        {
                            "record": f"{service}:latency_p99:rate5m",
                            "expr": f'histogram_quantile(0.99, sum(rate({duration_metric}{{service="{service}"}}[5m])) by (le))',
                            "labels": {"service": service, "sli_type": "latency_p99"},
                        },
                    ],
                },
                {
                    "name": f"{service}.alerting.rules",
                    "interval": "30s",
                    "rules": [
                        {
                            "alert": f"{service.title()}AvailabilityLow",
                            "expr": f'{service}:availability:rate5m < {cfg["threshold"]}',
                            "for": cfg["window"],
                            "labels": {
                                "severity": cfg["severity"],
                                "service": service,
                                "project": project_id,
                                "contextcore_managed": "true",
                            },
                            "annotations": availability_annotations,
                        },
                        {
                            "alert": f"{service.title()}LatencyHigh",
                            "expr": f'{service}:latency_p99:rate5m > 0.5',
                            "for": cfg["window"],
                            "labels": {
                                "severity": cfg["severity"],
                                "service": service,
                                "project": project_id,
                                "contextcore_managed": "true",
                            },
                            "annotations": latency_annotations,
                        },
                    ],
                },
            ],
        },
    }


def _build_enriched_annotations(
    spec: Dict[str, Any],
    project_id: str,
    service: str,
    cfg: Dict[str, Any],
) -> Dict[str, str]:
    """
    Build enriched alert annotations from ProjectContext metadata.

    Extracts contextual information from:
    - design.adr -> architecture_decision
    - observability.runbook -> runbook_url
    - business.owner -> owner
    - business.criticality -> business_criticality
    - risks[] -> known_risks (summary of top 3)
    """
    annotations: Dict[str, str] = {}

    # Add ADR reference if available
    design = spec.get("design", {})
    if design.get("adr"):
        annotations["architecture_decision"] = design["adr"]

    # Add runbook URL if available
    observability = spec.get("observability", {})
    if observability.get("runbook"):
        annotations["runbook_url"] = observability["runbook"]

    # Add business context
    business = spec.get("business", {})
    if business.get("owner"):
        annotations["owner"] = business["owner"]
    if business.get("criticality"):
        annotations["business_criticality"] = business["criticality"]

    # Add relevant risks as annotation (top 3, summarized)
    risks = spec.get("risks", [])
    if risks:
        risk_summary = "; ".join([
            f"{r.get('type', 'unknown')}: {r.get('description', 'N/A')[:50]}"
            for r in risks[:3]
        ])
        annotations["known_risks"] = risk_summary
        # Add mitigation hint for first risk type
        first_risk_type = risks[0].get("type", "") if risks else ""
        if first_risk_type:
            annotations["mitigation_hint"] = _get_mitigation_for_risk_type(first_risk_type)

    return annotations


def _get_mitigation_for_risk_type(risk_type: str) -> str:
    """Get default mitigation hint for risk type."""
    mitigations = {
        "availability": "Check pod health, recent deployments, upstream dependencies",
        "security": "Review access logs, check for unauthorized access patterns",
        "data-integrity": "Verify database consistency, check replication lag",
        "compliance": "Escalate to compliance team, preserve audit logs",
        "performance": "Check resource utilization, review recent changes, scale if needed",
        "capacity": "Monitor resource usage trends, consider horizontal scaling",
    }
    return mitigations.get(risk_type, "Review runbook for specific guidance")


def generate_grafana_dashboard(
    name: str,
    namespace: str,
    spec: Dict[str, Any],
    labels: Dict[str, str],
) -> Dict[str, Any]:
    """
    Generate a Grafana Dashboard ConfigMap from a ProjectContext spec.

    Supports both v1 (nested) and v1alpha1 (flat) schemas.
    Uses configurable metric names from spec.observability.metrics.

    Creates a ConfigMap with grafana_dashboard annotation for sidecar discovery,
    containing a dashboard with request rate, error rate, and latency panels.
    """
    project_id = get_project_id(spec, name)
    service = get_service_name(spec, name)
    criticality = (get_criticality(spec) or "medium").lower()
    owner = get_owner(spec) or "unknown"
    metrics = get_metrics_config(spec)
    requests_metric = metrics["requestsTotal"]
    duration_metric = metrics["durationBucket"]

    dashboard_json = {
        "annotations": {"list": []},
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 0,
        "id": None,
        "links": [],
        "panels": [
            {
                "gridPos": {"h": 1, "w": 24, "x": 0, "y": 0},
                "id": 1,
                "title": f"{service} Metrics",
                "type": "row",
            },
            {
                "datasource": {"type": "prometheus", "uid": "mimir"},
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "axisCenteredZero": False,
                            "axisLabel": "Requests/sec",
                            "axisPlacement": "auto",
                            "drawStyle": "line",
                            "fillOpacity": 0,
                            "lineWidth": 1,
                            "showPoints": "auto",
                        },
                        "mappings": [],
                        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                    },
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 1},
                "id": 2,
                "targets": [
                    {
                        "expr": f'rate({requests_metric}{{project="{project_id}", service="{service}"}}[5m])',
                        "legendFormat": "{{method}} {{path}}",
                        "refId": "A",
                    }
                ],
                "title": "Request Rate",
                "type": "timeseries",
            },
            {
                "datasource": {"type": "prometheus", "uid": "mimir"},
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {
                            "axisLabel": "Error Rate (%)",
                            "drawStyle": "line",
                            "fillOpacity": 10,
                        },
                        "unit": "percent",
                        "thresholds": {
                            "mode": "absolute",
                            "steps": [
                                {"color": "green", "value": None},
                                {"color": "yellow", "value": 1},
                                {"color": "red", "value": 5},
                            ],
                        },
                    },
                },
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 1},
                "id": 3,
                "targets": [
                    {
                        "expr": f'(rate({requests_metric}{{project="{project_id}", service="{service}", status=~"5.."}}[5m]) / rate({requests_metric}{{project="{project_id}", service="{service}"}}[5m])) * 100',
                        "legendFormat": "Error Rate",
                        "refId": "A",
                    }
                ],
                "title": "Error Rate",
                "type": "timeseries",
            },
            {
                "datasource": {"type": "prometheus", "uid": "mimir"},
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {"axisLabel": "Latency (ms)", "drawStyle": "line"},
                        "unit": "ms",
                    },
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 9},
                "id": 4,
                "targets": [
                    {
                        "expr": f'histogram_quantile(0.50, rate({duration_metric}{{project="{project_id}", service="{service}"}}[5m])) * 1000',
                        "legendFormat": "P50",
                        "refId": "A",
                    }
                ],
                "title": "P50 Latency",
                "type": "timeseries",
            },
            {
                "datasource": {"type": "prometheus", "uid": "mimir"},
                "fieldConfig": {
                    "defaults": {
                        "color": {"mode": "palette-classic"},
                        "custom": {"axisLabel": "Latency (ms)", "drawStyle": "line"},
                        "unit": "ms",
                    },
                },
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 9},
                "id": 5,
                "targets": [
                    {
                        "expr": f'histogram_quantile(0.99, rate({duration_metric}{{project="{project_id}", service="{service}"}}[5m])) * 1000',
                        "legendFormat": "P99",
                        "refId": "A",
                    }
                ],
                "title": "P99 Latency",
                "type": "timeseries",
            },
        ],
        "refresh": "30s",
        "schemaVersion": 39,
        "tags": ["contextcore", project_id, criticality],
        "templating": {"list": []},
        "time": {"from": "now-6h", "to": "now"},
        "title": f"{project_id} - {service} Dashboard",
        "uid": f"cc-{project_id.lower()}-{service.lower()}"[:40],
        "version": 1,
    }

    metadata_labels = {
        "contextcore.io/project": project_id,
        "contextcore.io/service": service,
        "contextcore.io/dashboard": "true",
        "contextcore.io/managed-by": "contextcore-operator",
    }
    # Add cost attribution labels
    cost_labels = generate_cost_labels(spec)
    metadata_labels.update(cost_labels)
    metadata_labels.update(labels)

    return {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {
            "name": f"{name}-dashboard",
            "namespace": namespace,
            "labels": metadata_labels,
            "annotations": {
                "grafana_dashboard": "1",
                "contextcore.io/generated": datetime.now(timezone.utc).isoformat(),
                "contextcore.io/owner": owner,
            },
            "ownerReferences": [],
        },
        "data": {
            "dashboard.json": json.dumps(dashboard_json, indent=2),
        },
    }


# =============================================================================
# Kubernetes Resource Management
# =============================================================================


def create_owner_reference(body: Dict[str, Any]) -> Dict[str, Any]:
    """Create an owner reference for garbage collection."""
    return {
        "apiVersion": body.get("apiVersion", "contextcore.io/v1alpha1"),
        "kind": body.get("kind", "ProjectContext"),
        "name": body["metadata"]["name"],
        "uid": body["metadata"]["uid"],
        "controller": True,
        "blockOwnerDeletion": True,
    }


def apply_resource(api: Any, resource: Dict[str, Any], namespace: str) -> str:
    """Apply a Kubernetes resource (create or update)."""
    kind = resource["kind"]
    name = resource["metadata"]["name"]

    try:
        if kind == "ConfigMap":
            try:
                api.read_namespaced_config_map(name, namespace)
                api.patch_namespaced_config_map(name, namespace, resource)
                return "updated"
            except ApiException as e:
                if e.status == 404:
                    api.create_namespaced_config_map(namespace, resource)
                    return "created"
                raise
        else:
            # For CRDs like ServiceMonitor and PrometheusRule
            group, version = resource["apiVersion"].rsplit("/", 1)
            plural = f"{kind.lower()}s"

            custom_api = client.CustomObjectsApi()
            try:
                custom_api.get_namespaced_custom_object(
                    group, version, namespace, plural, name
                )
                custom_api.patch_namespaced_custom_object(
                    group, version, namespace, plural, name, resource
                )
                return "updated"
            except ApiException as e:
                if e.status == 404:
                    custom_api.create_namespaced_custom_object(
                        group, version, namespace, plural, resource
                    )
                    return "created"
                raise
    except ApiException as e:
        logger.error(
            f"Failed to apply {kind}/{name}",
            extra={"kind": kind, "name": name, "error": str(e)},
        )
        raise


def delete_resource(api: Any, kind: str, name: str, namespace: str) -> bool:
    """Delete a Kubernetes resource."""
    try:
        if kind == "ConfigMap":
            api.delete_namespaced_config_map(name, namespace)
        else:
            group, version = "monitoring.coreos.com", "v1"
            plural = f"{kind.lower()}s"
            custom_api = client.CustomObjectsApi()
            custom_api.delete_namespaced_custom_object(
                group, version, namespace, plural, name
            )
        return True
    except ApiException as e:
        if e.status == 404:
            return False  # Already deleted
        raise


# =============================================================================
# Kopf Handlers
# =============================================================================


@kopf.on.startup()
def configure(settings: kopf.OperatorSettings, **_: Any) -> None:
    """Configure operator settings on startup."""
    setup_logging()
    get_tracer()  # Initialize tracer

    # Try to load in-cluster config, fall back to kubeconfig
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster Kubernetes config")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("Loaded kubeconfig")

    settings.posting.level = logging.WARNING
    settings.watching.server_timeout = 600

    logger.info(
        "ContextCore operator started",
        extra={"service": os.environ.get("OTEL_SERVICE_NAME", "contextcore-operator")},
    )


@kopf.on.cleanup()
def cleanup(**_: Any) -> None:
    """Cleanup on operator shutdown."""
    tracer = get_tracer()
    tracer.shutdown()
    logger.info("ContextCore operator shutdown")


@kopf.on.create("contextcore.io", "v1alpha1", "projectcontexts")
@kopf.on.create("contextcore.io", "v1", "projectcontexts")
def on_create(
    body: Dict[str, Any],
    namespace: str,
    name: str,
    patch: kopf.Patch,
    **_: Any,
) -> Dict[str, Any]:
    """Handle ProjectContext creation. Supports both v1 and v1alpha1 schemas."""
    spec = body.get("spec", {})
    project_id = get_project_id(spec, name)
    tracer = get_tracer()

    with tracer.trace_action(
        action="create",
        project_id=project_id,
        resource_name=name,
        resource_namespace=namespace,
    ):
        logger.info(
            "Creating ProjectContext",
            extra={
                "project_id": project_id,
                "resource_name": name,
                "namespace": namespace,
                "action": "create",
            },
        )

        owner_ref = create_owner_reference(body)
        labels = {"app.kubernetes.io/managed-by": "contextcore-operator"}
        core_api = client.CoreV1Api()

        # Generate artifacts
        service_monitor = generate_service_monitor(name, namespace, spec, labels)
        service_monitor["metadata"]["ownerReferences"] = [owner_ref]

        prometheus_rules = generate_prometheus_rules(name, namespace, spec, labels)
        prometheus_rules["metadata"]["ownerReferences"] = [owner_ref]

        dashboard = generate_grafana_dashboard(name, namespace, spec, labels)
        dashboard["metadata"]["ownerReferences"] = [owner_ref]

        # Apply resources
        artifacts = {}

        try:
            result = apply_resource(core_api, dashboard, namespace)
            artifacts["dashboard"] = dashboard["metadata"]["name"]
            logger.info(
                f"Dashboard {result}",
                extra={"artifact": "dashboard", "name": dashboard["metadata"]["name"]},
            )
        except Exception as e:
            logger.warning(f"Failed to create dashboard: {e}")

        try:
            result = apply_resource(None, service_monitor, namespace)
            artifacts["serviceMonitor"] = service_monitor["metadata"]["name"]
            logger.info(
                f"ServiceMonitor {result}",
                extra={"artifact": "serviceMonitor", "name": service_monitor["metadata"]["name"]},
            )
        except Exception as e:
            logger.warning(f"Failed to create ServiceMonitor: {e}")

        try:
            result = apply_resource(None, prometheus_rules, namespace)
            artifacts["prometheusRules"] = [prometheus_rules["metadata"]["name"]]
            logger.info(
                f"PrometheusRule {result}",
                extra={"artifact": "prometheusRules", "name": prometheus_rules["metadata"]["name"]},
            )
        except Exception as e:
            logger.warning(f"Failed to create PrometheusRule: {e}")

        # Update status
        patch.setdefault("status", {})
        patch["status"]["phase"] = "Active"
        patch["status"]["lastUpdated"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "ProjectContext created successfully",
            extra={
                "project_id": project_id,
                "artifacts": list(artifacts.keys()),
                "action": "create",
            },
        )

        return {"generatedArtifacts": artifacts}


@kopf.on.update("contextcore.io", "v1alpha1", "projectcontexts")
@kopf.on.update("contextcore.io", "v1", "projectcontexts")
def on_update(
    body: Dict[str, Any],
    namespace: str,
    name: str,
    patch: kopf.Patch,
    **_: Any,
) -> Dict[str, Any]:
    """Handle ProjectContext updates. Supports both v1 and v1alpha1 schemas."""
    spec = body.get("spec", {})
    project_id = get_project_id(spec, name)
    tracer = get_tracer()

    with tracer.trace_action(
        action="update",
        project_id=project_id,
        resource_name=name,
        resource_namespace=namespace,
    ):
        logger.info(
            "Updating ProjectContext",
            extra={
                "project_id": project_id,
                "resource_name": name,
                "namespace": namespace,
                "action": "update",
            },
        )

        # Regenerate and apply artifacts (same as create)
        owner_ref = create_owner_reference(body)
        labels = {"app.kubernetes.io/managed-by": "contextcore-operator"}
        core_api = client.CoreV1Api()

        dashboard = generate_grafana_dashboard(name, namespace, spec, labels)
        dashboard["metadata"]["ownerReferences"] = [owner_ref]

        service_monitor = generate_service_monitor(name, namespace, spec, labels)
        service_monitor["metadata"]["ownerReferences"] = [owner_ref]

        prometheus_rules = generate_prometheus_rules(name, namespace, spec, labels)
        prometheus_rules["metadata"]["ownerReferences"] = [owner_ref]

        artifacts = {}

        try:
            apply_resource(core_api, dashboard, namespace)
            artifacts["dashboard"] = dashboard["metadata"]["name"]
        except Exception as e:
            logger.warning(f"Failed to update dashboard: {e}")

        try:
            apply_resource(None, service_monitor, namespace)
            artifacts["serviceMonitor"] = service_monitor["metadata"]["name"]
        except Exception as e:
            logger.warning(f"Failed to update ServiceMonitor: {e}")

        try:
            apply_resource(None, prometheus_rules, namespace)
            artifacts["prometheusRules"] = [prometheus_rules["metadata"]["name"]]
        except Exception as e:
            logger.warning(f"Failed to update PrometheusRule: {e}")

        patch.setdefault("status", {})
        patch["status"]["phase"] = "Active"
        patch["status"]["lastUpdated"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "ProjectContext updated successfully",
            extra={"project_id": project_id, "artifacts": list(artifacts.keys())},
        )

        return {"generatedArtifacts": artifacts}


@kopf.on.delete("contextcore.io", "v1alpha1", "projectcontexts")
@kopf.on.delete("contextcore.io", "v1", "projectcontexts")
def on_delete(
    body: Dict[str, Any],
    namespace: str,
    name: str,
    **_: Any,
) -> None:
    """Handle ProjectContext deletion. Supports both v1 and v1alpha1 schemas."""
    spec = body.get("spec", {})
    project_id = get_project_id(spec, name)
    tracer = get_tracer()

    with tracer.trace_action(
        action="delete",
        project_id=project_id,
        resource_name=name,
        resource_namespace=namespace,
    ):
        logger.info(
            "Deleting ProjectContext",
            extra={
                "project_id": project_id,
                "resource_name": name,
                "namespace": namespace,
                "action": "delete",
            },
        )

        # Resources will be garbage collected via ownerReferences
        # Log what would be cleaned up
        status = body.get("status", {})
        if "generatedArtifacts" in status:
            artifacts = status["generatedArtifacts"]
            logger.info(
                "Artifacts will be garbage collected",
                extra={"artifacts": artifacts},
            )

        logger.info(
            "ProjectContext deleted",
            extra={"project_id": project_id, "action": "delete"},
        )


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> None:
    """Run the kopf operator (for local development)."""
    setup_logging()
    logger.info("Starting ContextCore operator in standalone mode")


if __name__ == "__main__":
    main()
