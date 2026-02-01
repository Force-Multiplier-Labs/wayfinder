"""
ContextCore - Unified metadata model from project initiation to operations.

This package provides Kubernetes Custom Resource Definitions (CRDs) that inject
project management context (business value, design documents, requirements, risk
signals) directly into the cluster alongside deployments.

Key Features:
- ProjectContext CRD links K8s resources to project artifacts
- Value-based observability derivation (SLOs, alerts from requirements)
- OTel Resource Detector injects context into all telemetry
- Sync adapters for Jira, GitHub, Notion

Example usage:
    from contextcore import ProjectContextDetector
    from opentelemetry.sdk.resources import get_aggregated_resources

    # Auto-detect project context from K8s annotations
    resource = get_aggregated_resources([ProjectContextDetector()])

    # All traces/metrics/logs now include project context:
    # - project.id, project.epic, project.task
    # - business.criticality, business.value, business.owner
    # - design.doc, design.adr
    # - requirement.availability, requirement.latency_p99
"""

__version__ = "0.1.0"
