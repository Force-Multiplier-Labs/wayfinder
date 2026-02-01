"""
Validation utilities for ContextCore.

Provides validators for common field types used across models:
- Duration strings (e.g., "200ms", "10s", "5m", "1h")
- Percentage strings (e.g., "99.95")
- Throughput strings (e.g., "1000rps", "10000rpm")

Usage:
    from contextcore.contracts.validators import (
        validate_duration,
        validate_percentage,
        parse_duration_ms,
    )

    # Validate duration format
    validate_duration("200ms")  # Returns "200ms"
    validate_duration("invalid")  # Raises ValueError

    # Parse duration to milliseconds
    parse_duration_ms("10s")  # Returns 10000
"""

from __future__ import annotations

import re
from typing import Optional, Union


# Duration pattern: number (with optional decimal) followed by unit
# Valid units: ms (milliseconds), s (seconds), m (minutes), h (hours)
DURATION_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)(ms|s|m|h)$")

# Percentage pattern: number with optional decimal
PERCENTAGE_PATTERN = re.compile(r"^\d+(?:\.\d+)?$")

# Throughput pattern: number followed by rps (requests per second) or rpm (requests per minute)
THROUGHPUT_PATTERN = re.compile(r"^(\d+(?:\.\d+)?)(rps|rpm|qps|qpm)$")


def validate_duration(value: str) -> str:
    """
    Validate that a string is a valid duration format.

    Valid formats:
    - "100ms" (milliseconds)
    - "10s" (seconds)
    - "5m" (minutes)
    - "1h" (hours)
    - "1.5s" (decimals allowed)

    Args:
        value: Duration string to validate

    Returns:
        The validated duration string

    Raises:
        ValueError: If the format is invalid
    """
    if not value:
        raise ValueError("Duration cannot be empty")

    value = value.strip().lower()

    if not DURATION_PATTERN.match(value):
        raise ValueError(
            f"Invalid duration format: '{value}'. "
            f"Expected format like '200ms', '10s', '5m', or '1h'"
        )

    return value


def validate_duration_optional(value: Optional[str]) -> Optional[str]:
    """
    Validate duration string, allowing None.

    Args:
        value: Duration string or None

    Returns:
        Validated duration string or None
    """
    if value is None:
        return None
    return validate_duration(value)


def parse_duration_ms(value: str) -> int:
    """
    Parse a duration string to milliseconds.

    Args:
        value: Duration string (e.g., "200ms", "10s")

    Returns:
        Duration in milliseconds

    Raises:
        ValueError: If the format is invalid
    """
    value = validate_duration(value)
    match = DURATION_PATTERN.match(value)

    if not match:
        raise ValueError(f"Invalid duration: {value}")

    amount = float(match.group(1))
    unit = match.group(2)

    multipliers = {
        "ms": 1,
        "s": 1000,
        "m": 60 * 1000,
        "h": 60 * 60 * 1000,
    }

    return int(amount * multipliers[unit])


def parse_duration_seconds(value: str) -> float:
    """
    Parse a duration string to seconds.

    Args:
        value: Duration string (e.g., "200ms", "10s")

    Returns:
        Duration in seconds (float for sub-second precision)
    """
    return parse_duration_ms(value) / 1000.0


def format_duration(ms: int) -> str:
    """
    Format milliseconds as a human-readable duration string.

    Picks the most appropriate unit:
    - < 1000ms: "Xms"
    - < 60s: "Xs"
    - < 60m: "Xm"
    - >= 60m: "Xh"

    Args:
        ms: Duration in milliseconds

    Returns:
        Formatted duration string
    """
    if ms < 1000:
        return f"{ms}ms"
    elif ms < 60 * 1000:
        seconds = ms / 1000
        if seconds == int(seconds):
            return f"{int(seconds)}s"
        return f"{seconds:.1f}s"
    elif ms < 60 * 60 * 1000:
        minutes = ms / (60 * 1000)
        if minutes == int(minutes):
            return f"{int(minutes)}m"
        return f"{minutes:.1f}m"
    else:
        hours = ms / (60 * 60 * 1000)
        if hours == int(hours):
            return f"{int(hours)}h"
        return f"{hours:.1f}h"


def validate_percentage(value: str) -> str:
    """
    Validate that a string is a valid percentage format.

    Valid formats:
    - "99.95"
    - "100"
    - "0.05"

    Args:
        value: Percentage string to validate

    Returns:
        The validated percentage string

    Raises:
        ValueError: If the format is invalid
    """
    if not value:
        raise ValueError("Percentage cannot be empty")

    value = value.strip()

    if not PERCENTAGE_PATTERN.match(value):
        raise ValueError(
            f"Invalid percentage format: '{value}'. "
            f"Expected a number like '99.95' or '100'"
        )

    # Validate range
    pct = float(value)
    if pct < 0 or pct > 100:
        raise ValueError(f"Percentage must be between 0 and 100, got {pct}")

    return value


def validate_percentage_optional(value: Optional[str]) -> Optional[str]:
    """
    Validate percentage string, allowing None.

    Args:
        value: Percentage string or None

    Returns:
        Validated percentage string or None
    """
    if value is None:
        return None
    return validate_percentage(value)


def validate_throughput(value: str) -> str:
    """
    Validate that a string is a valid throughput format.

    Valid formats:
    - "1000rps" (requests per second)
    - "10000rpm" (requests per minute)
    - "500qps" (queries per second)
    - "5000qpm" (queries per minute)

    Args:
        value: Throughput string to validate

    Returns:
        The validated throughput string

    Raises:
        ValueError: If the format is invalid
    """
    if not value:
        raise ValueError("Throughput cannot be empty")

    value = value.strip().lower()

    if not THROUGHPUT_PATTERN.match(value):
        raise ValueError(
            f"Invalid throughput format: '{value}'. "
            f"Expected format like '1000rps' or '10000rpm'"
        )

    return value


def validate_throughput_optional(value: Optional[str]) -> Optional[str]:
    """
    Validate throughput string, allowing None.

    Args:
        value: Throughput string or None

    Returns:
        Validated throughput string or None
    """
    if value is None:
        return None
    return validate_throughput(value)


def parse_throughput_per_second(value: str) -> float:
    """
    Parse a throughput string to requests per second.

    Args:
        value: Throughput string (e.g., "1000rps", "60000rpm")

    Returns:
        Throughput in requests per second
    """
    value = validate_throughput(value)
    match = THROUGHPUT_PATTERN.match(value)

    if not match:
        raise ValueError(f"Invalid throughput: {value}")

    amount = float(match.group(1))
    unit = match.group(2)

    if unit in ("rps", "qps"):
        return amount
    else:  # rpm, qpm
        return amount / 60.0


# Pydantic validator functions for use with field_validator
def duration_validator(v: Optional[str]) -> Optional[str]:
    """Pydantic field validator for duration strings."""
    return validate_duration_optional(v)


def percentage_validator(v: Optional[str]) -> Optional[str]:
    """Pydantic field validator for percentage strings."""
    return validate_percentage_optional(v)


def throughput_validator(v: Optional[str]) -> Optional[str]:
    """Pydantic field validator for throughput strings."""
    return validate_throughput_optional(v)
