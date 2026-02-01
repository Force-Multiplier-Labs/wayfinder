"""Helper functions to extract fields from ProjectContext CRD schemas.

Supports both v1 (nested structure) and v1alpha1 (flat structure) schemas.
"""

from typing import Any, Dict


def get_project_id(spec: Dict[str, Any], default: str) -> str:
    """Extract project ID from spec.

    Supports both v1 and v1alpha1 schemas:
    - v1: spec.project.id (nested object)
    - v1alpha1: spec.project (string directly)

    Args:
        spec: The spec dict from ProjectContext resource.
        default: Default value if project ID not found.

    Returns:
        The project ID string, or default if not found.
    """
    if not spec:
        return default

    project = spec.get("project")
    if project is None:
        return default

    if isinstance(project, dict):
        return project.get("id", default)
    elif isinstance(project, str):
        return project
    else:
        return default


def get_service_name(spec: Dict[str, Any], default: str) -> str:
    """Extract service name from spec.

    Supports both v1 and v1alpha1 schemas:
    - v1: spec.targets[0].name (first target in array)
    - v1alpha1: spec.service (string directly)

    Args:
        spec: The spec dict from ProjectContext resource.
        default: Default value if service name not found.

    Returns:
        The service name string, or default if not found.
    """
    if not spec:
        return default

    service = spec.get("service")
    if service is not None:
        if isinstance(service, str):
            return service

    targets = spec.get("targets")
    if targets and isinstance(targets, list) and len(targets) > 0:
        first_target = targets[0]
        if isinstance(first_target, dict):
            target_name = first_target.get("name")
            if isinstance(target_name, str):
                return target_name

    return default


def get_criticality(spec: Dict[str, Any]) -> str:
    """Extract criticality level from spec.

    Supports both v1 and v1alpha1 schemas:
    - v1: spec.business.criticality (nested)
    - v1alpha1: spec.criticality (string directly)

    Args:
        spec: The spec dict from ProjectContext resource.

    Returns:
        The criticality string, or empty string if not found.
    """
    if not spec:
        return ""

    criticality = spec.get("criticality")
    if criticality and isinstance(criticality, str):
        return criticality

    business = spec.get("business")
    if business and isinstance(business, dict):
        criticality = business.get("criticality")
        if isinstance(criticality, str):
            return criticality

    return ""


def get_owner(spec: Dict[str, Any]) -> str:
    """Extract owner information from spec.

    Supports both v1 and v1alpha1 schemas:
    - v1: spec.business.owner (nested)
    - v1alpha1: spec.owner (string directly)

    Args:
        spec: The spec dict from ProjectContext resource.

    Returns:
        The owner string, or empty string if not found.
    """
    if not spec:
        return ""

    owner = spec.get("owner")
    if owner and isinstance(owner, str):
        return owner

    business = spec.get("business")
    if business and isinstance(business, dict):
        owner = business.get("owner")
        if isinstance(owner, str):
            return owner

    return ""


def get_metrics_config(spec: Dict[str, Any]) -> Dict[str, str]:
    """Extract metrics configuration from spec.

    Supports both v1 and v1alpha1 schemas:
    - v1: spec.observability.metrics (nested dict)
    - v1alpha1: Returns defaults

    Returns dict with keys 'requestsTotal' and 'durationBucket' for metric names.

    Args:
        spec: The spec dict from ProjectContext resource.

    Returns:
        Dict with 'requestsTotal' and 'durationBucket' keys containing metric names.
        Defaults: http_requests_total, http_request_duration_seconds_bucket
    """
    defaults = {
        "requestsTotal": "http_requests_total",
        "durationBucket": "http_request_duration_seconds_bucket",
    }

    if not spec:
        return defaults

    observability = spec.get("observability")
    if observability and isinstance(observability, dict):
        metrics = observability.get("metrics")
        if metrics and isinstance(metrics, dict):
            result = defaults.copy()
            requests_total = metrics.get("requestsTotal")
            if isinstance(requests_total, str):
                result["requestsTotal"] = requests_total
            duration_bucket = metrics.get("durationBucket")
            if isinstance(duration_bucket, str):
                result["durationBucket"] = duration_bucket
            return result

    return defaults
