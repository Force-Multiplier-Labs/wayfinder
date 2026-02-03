"""
ProjectContext reader for Kubernetes CRDs and YAML files.

Looks up business context (criticality, owner, SLOs) from:
1. Kubernetes ProjectContext CRD (if available)
2. .contextcore.yaml file (fallback)
"""

from __future__ import annotations

import logging
import time
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


@dataclass
class _CacheEntry:
    """A cache entry with an expiry timestamp."""

    context: ProjectContext
    expires_at: float


class ProjectContextReader:
    """Reads ProjectContext from K8s CRD or YAML fallback."""

    _MAX_CACHE_SIZE = 1024

    def __init__(
        self,
        yaml_path: Optional[str] = None,
        use_kubernetes: bool = False,
        cache_ttl_seconds: int = 300,
    ):
        self._yaml_path = yaml_path
        self._use_kubernetes = use_kubernetes
        self._cache: Dict[str, _CacheEntry] = {}
        self._cache_ttl = cache_ttl_seconds

    def lookup(
        self,
        namespace: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None,
        project_id: Optional[str] = None,
    ) -> Optional[ProjectContext]:
        """Look up ProjectContext by namespace, labels, or project_id."""
        cache_key = project_id or namespace or ""
        now = time.monotonic()

        entry = self._cache.get(cache_key)
        if entry is not None and now < entry.expires_at:
            return entry.context

        # Remove expired entry if present
        self._cache.pop(cache_key, None)

        ctx = None
        if self._use_kubernetes:
            ctx = self._lookup_kubernetes(namespace, labels, project_id)

        if ctx is None and self._yaml_path:
            ctx = self._from_yaml(self._yaml_path, project_id)

        if ctx is not None:
            # Evict expired entries if cache is at capacity
            if len(self._cache) >= self._MAX_CACHE_SIZE:
                self._evict_expired(now)
            # If still at capacity after eviction, drop the oldest entry
            if len(self._cache) >= self._MAX_CACHE_SIZE:
                oldest_key = min(self._cache, key=lambda k: self._cache[k].expires_at)
                del self._cache[oldest_key]
            self._cache[cache_key] = _CacheEntry(
                context=ctx,
                expires_at=now + self._cache_ttl,
            )

        return ctx

    def _evict_expired(self, now: float) -> None:
        """Remove all expired entries from the cache."""
        expired_keys = [k for k, v in self._cache.items() if now >= v.expires_at]
        for k in expired_keys:
            del self._cache[k]

    def _lookup_kubernetes(
        self,
        namespace: Optional[str],
        labels: Optional[Dict[str, str]],
        project_id: Optional[str] = None,
    ) -> Optional[ProjectContext]:
        """Look up ProjectContext from Kubernetes CRD."""
        try:
            from kubernetes import client, config
        except ImportError:
            logger.debug("kubernetes package not installed")
            return None

        try:
            config.load_incluster_config()
        except Exception:
            try:
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
                    pid = project.get("id", "")

                    # If caller specified a project_id, only return matching CRD
                    if project_id and pid != project_id:
                        continue

                    business = spec.get("business", {})
                    requirements = spec.get("requirements", {})
                    observability = spec.get("observability", {})
                    return ProjectContext(
                        project_id=pid,
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
