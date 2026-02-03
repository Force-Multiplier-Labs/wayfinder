"""
Sampler Factory.

Centralizes OTel sampler creation based on standard environment variables:
- OTEL_TRACES_SAMPLER (default: parentbased_always_on)
- OTEL_TRACES_SAMPLER_ARG (ratio for ratio-based samplers, 0.0-1.0)

Follows the same factory pattern as exporter_factory.py.
"""

from __future__ import annotations

import logging
import os
import warnings

from opentelemetry.sdk.trace.sampling import (
    ALWAYS_OFF,
    ALWAYS_ON,
    ParentBased,
    Sampler,
    TraceIdRatioBased,
)

logger = logging.getLogger(__name__)

_KNOWN_SAMPLERS = {
    "always_on",
    "always_off",
    "parentbased_always_on",
    "parentbased_always_off",
    "traceidratio",
    "parentbased_traceidratio",
}


def _parse_ratio(raw: str) -> float:
    """
    Validate and clamp a ratio string to [0.0, 1.0].

    Args:
        raw: String representation of the ratio.

    Returns:
        Clamped float between 0.0 and 1.0.
    """
    try:
        ratio = float(raw)
    except (ValueError, TypeError):
        warnings.warn(
            f"Invalid OTEL_TRACES_SAMPLER_ARG '{raw}'. "
            f"Expected a float between 0.0 and 1.0. Defaulting to 1.0.",
            UserWarning,
            stacklevel=3,
        )
        return 1.0

    if ratio < 0.0 or ratio > 1.0:
        clamped = max(0.0, min(1.0, ratio))
        warnings.warn(
            f"OTEL_TRACES_SAMPLER_ARG {ratio} out of range [0.0, 1.0]. "
            f"Clamping to {clamped}.",
            UserWarning,
            stacklevel=3,
        )
        return clamped

    return ratio


def create_sampler() -> Sampler:
    """
    Create a sampler from standard OTel environment variables.

    Reads:
        OTEL_TRACES_SAMPLER: Sampler name (default: parentbased_always_on)
        OTEL_TRACES_SAMPLER_ARG: Ratio argument for ratio-based samplers

    Returns:
        Configured Sampler instance.
    """
    sampler_name = os.environ.get("OTEL_TRACES_SAMPLER", "parentbased_always_on").strip().lower()
    sampler_arg = os.environ.get("OTEL_TRACES_SAMPLER_ARG", "").strip()

    if sampler_name not in _KNOWN_SAMPLERS:
        warnings.warn(
            f"Unknown OTEL_TRACES_SAMPLER '{sampler_name}'. "
            f"Expected one of {sorted(_KNOWN_SAMPLERS)}. "
            f"Defaulting to parentbased_always_on.",
            UserWarning,
            stacklevel=2,
        )
        sampler_name = "parentbased_always_on"

    if sampler_name == "always_on":
        return ALWAYS_ON
    elif sampler_name == "always_off":
        return ALWAYS_OFF
    elif sampler_name == "parentbased_always_on":
        return ParentBased(ALWAYS_ON)
    elif sampler_name == "parentbased_always_off":
        return ParentBased(ALWAYS_OFF)
    elif sampler_name == "traceidratio":
        ratio = _parse_ratio(sampler_arg) if sampler_arg else 1.0
        return TraceIdRatioBased(ratio)
    elif sampler_name == "parentbased_traceidratio":
        ratio = _parse_ratio(sampler_arg) if sampler_arg else 1.0
        return ParentBased(TraceIdRatioBased(ratio))

    # Fallback (shouldn't reach here due to validation above)
    return ParentBased(ALWAYS_ON)
