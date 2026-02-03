"""
ProjectContext reader for Kubernetes CRDs and YAML files.

Looks up business context (criticality, owner, SLOs) from:
1. Kubernetes ProjectContext CRD (if available)
2. .contextcore.yaml file (fallback)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ProjectContext:
    """Business context for a project."""

    project_id: str
    criticality: str = "medium"
    owner: str = ""
    alert_channels: List[str] = field(default_factory=list)
    availability_slo: str = ""
    latency_p99: str = ""


class ProjectContextReader:
    """Reads ProjectContext from K8s CRD or YAML fallback."""

    def __init__(
        self,
        yaml_path: Optional[str] = None,
        use_kubernetes: bool = False,
    ):
        self._yaml_path = yaml_path
        self._use_kubernetes = use_kubernetes
        self._cache: Dict[str, ProjectContext] = {}

    def lookup(
        self,
        namespace: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        project_id: Optional[str] = None,
    ) -> Optional[ProjectContext]:
        """Look up ProjectContext by namespace, labels, or project_id."""
        cache_key = project_id or namespace or ""
        if cache_key in self._cache:
            return self._cache[cache_key]

        ctx = None
        if self._use_kubernetes:
            ctx = self._lookup_kubernetes(namespace, labels)

        if ctx is None and self._yaml_path:
            ctx = self._from_yaml(self._yaml_path, project_id)

        if ctx is not None:
            self._cache[cache_key] = ctx

        return ctx

    def _lookup_kubernetes(
        self,
        namespace: Optional[str],
        labels: Optional[Dict[str, str]],
    ) -> Optional[ProjectContext]:
        """Look up ProjectContext from Kubernetes CRD."""
        try:
            from kubernetes import client, config

            config.load_incluster_config()
        except Exception:
            try:
                from kubernetes import client, config

                config.load_kube_config()
            except Exception:
                logger.debug("Kubernetes not available for ProjectContext lookup")
                return None

        try:
            api = client.CustomObjectsApi()
            if namespace:
                items = api.list_namespaced_custom_object(
                    group="contextcore.io",
                    version="v1",
                    namespace=namespace,
                    plural="projectcontexts",
                )
                for item in items.get("items", []):
                    spec = item.get("spec", {})
                    project = spec.get("project", {})
                    business = spec.get("business", {})
                    requirements = spec.get("requirements", {})
                    observability = spec.get("observability", {})
                    return ProjectContext(
                        project_id=project.get("id", ""),
                        criticality=business.get("criticality", "medium"),
                        owner=business.get("owner", ""),
                        alert_channels=observability.get("alertChannels", []),
                        availability_slo=requirements.get("availability", ""),
                        latency_p99=requirements.get("latencyP99", ""),
                    )
        except Exception as e:
            logger.debug("Failed to read ProjectContext CRD: %s", e)

        return None

    def _from_yaml(
        self, path: str, project_id: Optional[str] = None
    ) -> Optional[ProjectContext]:
        """Read ProjectContext from .contextcore.yaml file."""
        yaml_path = Path(path)
        if not yaml_path.exists():
            return None

        try:
            with open(yaml_path) as f:
                data = yaml.safe_load(f)

            if data is None:
                return None

            project = data.get("project", {})
            business = data.get("business", {})
            requirements = data.get("requirements", {})

            pid = project.get("id", "")
            if project_id and pid != project_id:
                return None

            return ProjectContext(
                project_id=pid,
                criticality=business.get("criticality", "medium"),
                owner=business.get("owner", ""),
                alert_channels=[],
                availability_slo=requirements.get("availability", ""),
                latency_p99=requirements.get("latencyP99", ""),
            )
        except Exception as e:
            logger.warning("Failed to read %s: %s", path, e)
            return None
