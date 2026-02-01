"""
OpenAPI specification parser for contract drift detection.

Supports both JSON and YAML formats from URLs or local file paths.

Prime Contractor Pattern: Spec by Claude, drafts by GPT-4o-mini, integration by Claude.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from urllib.request import urlopen
from urllib.error import URLError
import json

__all__ = ['EndpointSpec', 'parse_openapi']


@dataclass
class EndpointSpec:
    """Represents a parsed OpenAPI endpoint specification."""
    path: str
    method: str
    operation_id: Optional[str]
    request_content_type: Optional[str]
    response_content_type: Optional[str]
    response_schema: Optional[Dict[str, Any]]
    parameters: List[Dict[str, Any]]


def parse_openapi(spec_url_or_path: str) -> List[EndpointSpec]:
    """
    Parse OpenAPI specification from URL or file path.

    Args:
        spec_url_or_path: URL (http/https) or local file path to OpenAPI spec

    Returns:
        List of parsed endpoint specifications

    Raises:
        ValueError: If spec cannot be loaded or parsed
    """
    try:
        spec = _load_spec(spec_url_or_path)
    except Exception as e:
        raise ValueError(f"Failed to load OpenAPI spec from {spec_url_or_path}: {e}") from e

    endpoints = []
    paths = spec.get("paths", {})

    http_methods = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace'}

    for path, methods in paths.items():
        if not isinstance(methods, dict):
            continue

        for method, operation in methods.items():
            if method.lower() not in http_methods:
                continue
            if not isinstance(operation, dict):
                continue

            endpoint = EndpointSpec(
                path=path,
                method=method.upper(),
                operation_id=operation.get("operationId"),
                request_content_type=_get_request_content_type(operation),
                response_content_type=_get_response_content_type(operation),
                response_schema=_get_response_schema(operation, spec),
                parameters=operation.get("parameters", []),
            )
            endpoints.append(endpoint)

    return endpoints


def _load_spec(spec_url_or_path: str) -> Dict[str, Any]:
    """Load specification from URL or file path."""
    # Try to import yaml, fall back to JSON-only if not available
    try:
        import yaml
        has_yaml = True
    except ImportError:
        has_yaml = False

    if spec_url_or_path.startswith(("http://", "https://")):
        # Load from URL
        try:
            with urlopen(spec_url_or_path, timeout=30) as response:
                content = response.read().decode('utf-8')
        except URLError as e:
            raise ValueError(f"Failed to fetch URL: {e}") from e

        if spec_url_or_path.endswith(".json"):
            return json.loads(content)
        elif has_yaml:
            return yaml.safe_load(content)
        else:
            # Try JSON first, then fail
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                raise ValueError("YAML support requires PyYAML package")
    else:
        # Load from file
        with open(spec_url_or_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if spec_url_or_path.endswith(".json"):
            return json.loads(content)
        elif has_yaml:
            return yaml.safe_load(content)
        else:
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                raise ValueError("YAML support requires PyYAML package")


def _get_request_content_type(operation: Dict[str, Any]) -> Optional[str]:
    """Extract request content type from operation."""
    request_body = operation.get("requestBody", {})
    content = request_body.get("content", {})
    return next(iter(content.keys()), None) if content else None


def _get_response_content_type(operation: Dict[str, Any]) -> Optional[str]:
    """Extract response content type from operation (defaults to 200 response)."""
    responses = operation.get("responses", {})
    success_response = responses.get("200", responses.get("201", {}))
    content = success_response.get("content", {})
    return next(iter(content.keys()), None) if content else None


def _get_response_schema(operation: Dict[str, Any], spec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract and resolve response schema from operation."""
    responses = operation.get("responses", {})
    success_response = responses.get("200", responses.get("201", {}))
    content = success_response.get("content", {})

    # Try to get schema from JSON content type first, then any available
    schema_def = None
    if "application/json" in content:
        schema_def = content["application/json"].get("schema")
    elif content:
        first_content = next(iter(content.values()), {})
        schema_def = first_content.get("schema")

    if not schema_def:
        return None

    # Resolve $ref if present
    if "$ref" in schema_def:
        return _resolve_ref(schema_def["$ref"], spec)

    return schema_def


def _resolve_ref(ref: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve JSON Schema $ref reference within the specification.

    Args:
        ref: Reference string like "#/components/schemas/User"
        spec: Full OpenAPI specification

    Returns:
        Resolved schema dictionary
    """
    if not ref or not ref.startswith("#/"):
        return {}

    # Split reference path and navigate through spec
    path_parts = ref[2:].split("/")  # Remove "#/" prefix
    current = spec

    for part in path_parts:
        if not isinstance(current, dict) or part not in current:
            return {}
        current = current[part]

    return current if isinstance(current, dict) else {}
