"""
Installation tracking metrics for ContextCore.

Emits Prometheus metrics for installation step tracking via the
Prometheus pushgateway or remote-write endpoint. Metrics include:
- contextcore_install_step_status (gauge per step)
- contextcore_install_step_duration_seconds (gauge per step)
- contextcore_install_step_attempts_total (counter per step)
- contextcore_install_progress_ratio (gauge, 0.0-1.0)
- contextcore_install_started_timestamp (gauge, unix epoch)
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import Dict, List, Optional

__all__ = [
    "MetricEmitter",
    "StepMetric",
    "emit_step_status",
    "emit_progress",
    "emit_all_step_status",
]

# Metric status codes matching Grafana dashboard value mappings
STATUS_PENDING = 0
STATUS_IN_PROGRESS = 1
STATUS_COMPLETED = 2
STATUS_FAILED = 3


@dataclass
class StepMetric:
    """Metric data for a single installation step."""

    step_id: str
    status: int = STATUS_PENDING
    duration_seconds: float = 0.0
    attempts: int = 0
    started_at: Optional[float] = None  # Unix timestamp


class MetricEmitter:
    """Emits installation tracking metrics to a Prometheus pushgateway.

    Uses the Prometheus pushgateway HTTP API to push gauge and counter
    metrics for each installation step.
    """

    def __init__(
        self,
        pushgateway_url: str = "http://localhost:9091",
        job_name: str = "contextcore_install",
        cluster_name: str = "wayfinder-dev",
        timeout: int = 5,
    ) -> None:
        """Initialize the metric emitter.

        Args:
            pushgateway_url: URL of the Prometheus pushgateway.
            job_name: Prometheus job label.
            cluster_name: Cluster label for multi-cluster support.
            timeout: HTTP request timeout in seconds.
        """
        self.pushgateway_url = pushgateway_url.rstrip("/")
        self.job_name = job_name
        self.cluster_name = cluster_name
        self.timeout = timeout
        self._steps: Dict[str, StepMetric] = {}

    def _get_step(self, step_id: str) -> StepMetric:
        """Get or create a StepMetric."""
        if step_id not in self._steps:
            self._steps[step_id] = StepMetric(step_id=step_id)
        return self._steps[step_id]

    def mark_running(self, step_id: str) -> None:
        """Mark a step as in-progress and record start time."""
        step = self._get_step(step_id)
        step.status = STATUS_IN_PROGRESS
        step.started_at = time.time()
        step.attempts += 1

    def mark_completed(self, step_id: str, duration_seconds: Optional[float] = None) -> None:
        """Mark a step as completed with optional duration override."""
        step = self._get_step(step_id)
        step.status = STATUS_COMPLETED
        if duration_seconds is not None:
            step.duration_seconds = duration_seconds
        elif step.started_at is not None:
            step.duration_seconds = time.time() - step.started_at

    def mark_failed(self, step_id: str) -> None:
        """Mark a step as failed."""
        step = self._get_step(step_id)
        step.status = STATUS_FAILED
        if step.started_at is not None:
            step.duration_seconds = time.time() - step.started_at

    def emit_step_status(self, step_id: str) -> bool:
        """Push metrics for a single step to the pushgateway.

        Args:
            step_id: The step to emit metrics for.

        Returns:
            True if the push succeeded, False otherwise.
        """
        step = self._get_step(step_id)
        lines = [
            f'contextcore_install_step_status{{step="{step_id}",cluster="{self.cluster_name}"}} {step.status}',
            f'contextcore_install_step_duration_seconds{{step="{step_id}",cluster="{self.cluster_name}"}} {step.duration_seconds}',
            f'contextcore_install_step_attempts_total{{step="{step_id}",cluster="{self.cluster_name}"}} {step.attempts}',
        ]
        return self._push_metrics("\n".join(lines) + "\n")

    def emit_progress(self) -> bool:
        """Push overall installation progress metric.

        Returns:
            True if the push succeeded, False otherwise.
        """
        total = len(self._steps) or 1
        completed = sum(1 for s in self._steps.values() if s.status == STATUS_COMPLETED)
        ratio = completed / total

        lines = [
            f'contextcore_install_progress_ratio{{cluster="{self.cluster_name}"}} {ratio}',
        ]
        return self._push_metrics("\n".join(lines) + "\n")

    def emit_all_step_status(self) -> bool:
        """Push metrics for all tracked steps in a single request.

        Returns:
            True if the push succeeded, False otherwise.
        """
        lines: List[str] = []
        for step in self._steps.values():
            lines.append(
                f'contextcore_install_step_status{{step="{step.step_id}",cluster="{self.cluster_name}"}} {step.status}'
            )
            lines.append(
                f'contextcore_install_step_duration_seconds{{step="{step.step_id}",cluster="{self.cluster_name}"}} {step.duration_seconds}'
            )
            lines.append(
                f'contextcore_install_step_attempts_total{{step="{step.step_id}",cluster="{self.cluster_name}"}} {step.attempts}'
            )

        total = len(self._steps) or 1
        completed = sum(1 for s in self._steps.values() if s.status == STATUS_COMPLETED)
        lines.append(
            f'contextcore_install_progress_ratio{{cluster="{self.cluster_name}"}} {completed / total}'
        )

        return self._push_metrics("\n".join(lines) + "\n")

    def _push_metrics(self, body: str) -> bool:
        """Push Prometheus text-format metrics to the pushgateway.

        Args:
            body: Prometheus exposition format text.

        Returns:
            True on success, False on failure.
        """
        url = f"{self.pushgateway_url}/metrics/job/{self.job_name}"
        try:
            req = urllib.request.Request(
                url,
                data=body.encode("utf-8"),
                method="POST",
                headers={"Content-Type": "text/plain"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout):
                return True
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            return False


# Module-level convenience functions

_default_emitter: Optional[MetricEmitter] = None


def _get_emitter() -> MetricEmitter:
    """Get or create the default MetricEmitter."""
    global _default_emitter
    if _default_emitter is None:
        _default_emitter = MetricEmitter()
    return _default_emitter


def emit_step_status(step_id: str) -> bool:
    """Push metrics for a single step using the default emitter."""
    return _get_emitter().emit_step_status(step_id)


def emit_progress() -> bool:
    """Push overall progress metric using the default emitter."""
    return _get_emitter().emit_progress()


def emit_all_step_status() -> bool:
    """Push metrics for all steps using the default emitter."""
    return _get_emitter().emit_all_step_status()
