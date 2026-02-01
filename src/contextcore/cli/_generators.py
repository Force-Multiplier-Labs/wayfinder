"""Observability artifact generators for CLI commands."""


def generate_service_monitor(name: str, namespace: str, spec: dict) -> dict:
    """Generate ServiceMonitor from ProjectContext spec."""
    business = spec.get("business", {})
    criticality = business.get("criticality", "medium")

    interval = {
        "critical": "10s",
        "high": "30s",
        "medium": "60s",
        "low": "120s",
    }.get(criticality, "60s")

    targets = spec.get("targets", [])
    target_name = targets[0]["name"] if targets else name

    return {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "ServiceMonitor",
        "metadata": {
            "name": f"{name}-monitor",
            "namespace": namespace,
            "labels": {
                "contextcore.io/project": spec.get("project", {}).get("id", ""),
            },
        },
        "spec": {
            "selector": {
                "matchLabels": {
                    "app": target_name,
                },
            },
            "endpoints": [
                {
                    "port": "metrics",
                    "interval": interval,
                },
            ],
        },
    }


def generate_prometheus_rule(name: str, namespace: str, spec: dict) -> dict:
    """Generate PrometheusRule from ProjectContext spec."""
    requirements = spec.get("requirements", {})
    design = spec.get("design", {})
    project = spec.get("project", {})

    rules = []

    # Latency alert from requirements
    latency_p99 = requirements.get("latencyP99")
    if latency_p99:
        # Parse latency (e.g., "200ms" -> 0.2)
        latency_seconds = float(latency_p99.replace("ms", "")) / 1000

        rules.append({
            "alert": f"{name.title().replace('-', '')}LatencyHigh",
            "expr": f'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{name}"}}[5m])) > {latency_seconds}',
            "for": "5m",
            "labels": {
                "severity": "critical",
                "project": project.get("id", ""),
            },
            "annotations": {
                "summary": f"High latency on {name}",
                "design_doc": design.get("doc", ""),
                "adr": design.get("adr", ""),
            },
        })

    # Availability alert
    availability = requirements.get("availability")
    if availability:
        error_rate = 100 - float(availability)

        rules.append({
            "alert": f"{name.title().replace('-', '')}ErrorRateHigh",
            "expr": f'rate(http_requests_total{{service="{name}", status=~"5.."}}[5m]) / rate(http_requests_total{{service="{name}"}}[5m]) > {error_rate / 100}',
            "for": "5m",
            "labels": {
                "severity": "critical",
                "project": project.get("id", ""),
            },
            "annotations": {
                "summary": f"High error rate on {name}",
                "design_doc": design.get("doc", ""),
            },
        })

    return {
        "apiVersion": "monitoring.coreos.com/v1",
        "kind": "PrometheusRule",
        "metadata": {
            "name": f"{name}-slo",
            "namespace": namespace,
        },
        "spec": {
            "groups": [
                {
                    "name": f"{name}.slo",
                    "rules": rules,
                },
            ],
        },
    }


def generate_dashboard(name: str, namespace: str, spec: dict) -> dict:
    """Generate Grafana dashboard JSON from ProjectContext spec."""
    project = spec.get("project", {})
    business = spec.get("business", {})
    design = spec.get("design", {})

    return {
        "title": f"{name} - {project.get('id', 'Unknown')}",
        "tags": [
            f"project:{project.get('id', '')}",
            f"criticality:{business.get('criticality', 'medium')}",
            "contextcore",
        ],
        "annotations": {
            "list": [
                {
                    "name": "Design Doc",
                    "iconColor": "blue",
                    "target": {"url": design.get("doc", "")},
                },
            ],
        },
        "links": [
            {
                "title": "Design Document",
                "url": design.get("doc", ""),
                "type": "link",
            },
            {
                "title": "ADR",
                "url": design.get("adr", ""),
                "type": "link",
            },
        ],
        "panels": [
            {
                "title": "Request Rate",
                "type": "timeseries",
                "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
                "targets": [
                    {
                        "expr": f'rate(http_requests_total{{service="{name}"}}[5m])',
                        "legendFormat": "{{status}}",
                    },
                ],
            },
            {
                "title": "Latency P99",
                "type": "timeseries",
                "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
                "targets": [
                    {
                        "expr": f'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket{{service="{name}"}}[5m]))',
                        "legendFormat": "P99",
                    },
                ],
            },
        ],
        "schemaVersion": 38,
        "version": 1,
    }
