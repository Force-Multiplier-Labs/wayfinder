"""
Mimir query module for verifying metrics in debug mode.

Provides functions to query Mimir's Prometheus API and verify that
emitted metrics are correctly received.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Optional

import httpx


def _get_mimir_url() -> str:
    """Get Mimir URL from environment."""
    return os.environ.get("MIMIR_URL", "http://localhost:9009")


@dataclass
class MetricQueryResult:
    """Result of querying a metric from Mimir."""

    metric_name: str
    labels: dict[str, str]
    expected_value: float
    actual_value: Optional[float]
    found: bool
    matches: bool
    error: Optional[str] = None


def query_metric(
    metric_name: str,
    labels: Optional[dict[str, str]] = None,
    mimir_url: Optional[str] = None,
    timeout: float = 5.0,
) -> tuple[Optional[float], Optional[str]]:
    """
    Query Mimir for a specific metric value.

    Args:
        metric_name: The Prometheus metric name (e.g., contextcore_install_completeness_percent)
        labels: Optional label matchers
        mimir_url: Mimir URL (defaults to MIMIR_URL env var or localhost:9009)
        timeout: Request timeout in seconds

    Returns:
        Tuple of (value, error). Value is None if not found or error occurred.
    """
    url = mimir_url or _get_mimir_url()

    # Build PromQL query with label matchers
    if labels:
        label_matchers = ",".join(f'{k}="{v}"' for k, v in labels.items())
        query = f"{metric_name}{{{label_matchers}}}"
    else:
        query = metric_name

    try:
        response = httpx.get(
            f"{url}/prometheus/api/v1/query",
            params={"query": query},
            timeout=timeout,
        )

        if response.status_code != 200:
            return None, f"HTTP {response.status_code}: {response.text}"

        data = response.json()

        if data.get("status") != "success":
            return None, f"Query failed: {data.get('error', 'Unknown error')}"

        results = data.get("data", {}).get("result", [])

        if not results:
            return None, None  # Metric not found (not an error)

        # Get the most recent value
        # Mimir returns [timestamp, value] pairs
        value_pair = results[0].get("value", [])
        if len(value_pair) >= 2:
            return float(value_pair[1]), None

        return None, "No value in result"

    except httpx.ConnectError:
        return None, f"Cannot connect to Mimir at {url}"
    except httpx.TimeoutException:
        return None, f"Timeout querying Mimir at {url}"
    except Exception as e:
        return None, f"Error querying Mimir: {e}"


def verify_metric_emitted(
    metric_name: str,
    expected_value: float,
    labels: Optional[dict[str, str]] = None,
    mimir_url: Optional[str] = None,
    tolerance: float = 0.01,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> MetricQueryResult:
    """
    Check if a metric exists in Mimir with the expected value.

    Retries with delay to account for metric propagation delay.

    Args:
        metric_name: The Prometheus metric name
        expected_value: Expected metric value
        labels: Optional label matchers
        mimir_url: Mimir URL
        tolerance: Acceptable difference between expected and actual (for floats)
        max_retries: Number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        MetricQueryResult with verification status
    """
    for attempt in range(max_retries):
        value, error = query_metric(metric_name, labels, mimir_url)

        if error and "Cannot connect" in error:
            # Connection error - no point retrying
            return MetricQueryResult(
                metric_name=metric_name,
                labels=labels or {},
                expected_value=expected_value,
                actual_value=None,
                found=False,
                matches=False,
                error=error,
            )

        if value is not None:
            # Metric found - check value
            matches = abs(value - expected_value) <= tolerance
            return MetricQueryResult(
                metric_name=metric_name,
                labels=labels or {},
                expected_value=expected_value,
                actual_value=value,
                found=True,
                matches=matches,
                error=None,
            )

        # Not found yet - retry after delay
        if attempt < max_retries - 1:
            time.sleep(retry_delay)

    # Metric not found after all retries
    return MetricQueryResult(
        metric_name=metric_name,
        labels=labels or {},
        expected_value=expected_value,
        actual_value=None,
        found=False,
        matches=False,
        error=error if error else "Metric not found in Mimir",
    )


def query_multiple_metrics(
    metrics: list[dict],
    mimir_url: Optional[str] = None,
    tolerance: float = 0.01,
) -> list[MetricQueryResult]:
    """
    Query multiple metrics from Mimir.

    Args:
        metrics: List of dicts with keys: metric_name, expected_value, labels (optional)
        mimir_url: Mimir URL
        tolerance: Acceptable difference for value comparison

    Returns:
        List of MetricQueryResult for each metric
    """
    results = []

    for metric in metrics:
        result = verify_metric_emitted(
            metric_name=metric["metric_name"],
            expected_value=metric["expected_value"],
            labels=metric.get("labels"),
            mimir_url=mimir_url,
            tolerance=tolerance,
        )
        results.append(result)

    return results


def check_mimir_available(mimir_url: Optional[str] = None) -> tuple[bool, str]:
    """
    Check if Mimir is available and ready.

    Args:
        mimir_url: Mimir URL

    Returns:
        Tuple of (available, message)
    """
    url = mimir_url or _get_mimir_url()

    try:
        response = httpx.get(f"{url}/ready", timeout=5.0)
        if response.status_code == 200:
            return True, f"Mimir ready at {url}"
        return False, f"Mimir not ready: HTTP {response.status_code}"
    except httpx.ConnectError:
        return False, f"Cannot connect to Mimir at {url}"
    except Exception as e:
        return False, f"Error checking Mimir: {e}"
