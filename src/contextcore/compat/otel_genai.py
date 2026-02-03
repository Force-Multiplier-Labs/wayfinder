"""
Dual-emit compatibility layer for ContextCore attribute emission.

This module allows ContextCore to emit both legacy (agent.*, insight.*, handoff.*)
and new (gen_ai.*) span attributes during the migration period.

OpenTelemetry GenAI semantic conventions compatibility layer.
"""

from enum import Enum
from typing import Any, Dict, Optional, Set
import os
import warnings


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ATTRIBUTE_MAPPINGS: Dict[str, str] = {
    "agent.id": "gen_ai.agent.id",
    "agent.type": "gen_ai.agent.type",
    "agent.session_id": "gen_ai.conversation.id",
    "handoff.capability_id": "gen_ai.tool.name",
    "handoff.inputs": "gen_ai.tool.call.arguments",
    "handoff.id": "gen_ai.tool.call.id",
    "context.id": "gen_ai.request.id",
    "context.model": "gen_ai.request.model",
    "insight.type": "gen_ai.insight.type",
    "insight.value": "gen_ai.insight.value",
    "insight.confidence": "gen_ai.insight.confidence",
}

TOOL_ATTRIBUTES: Dict[str, str] = {
    "gen_ai.tool.type": "agent_handoff",
}


# ---------------------------------------------------------------------------
# Emit mode
# ---------------------------------------------------------------------------

class EmitMode(str, Enum):
    """Emission mode for span attributes."""
    LEGACY = "legacy"  # Only old attributes
    DUAL = "dual"      # Both old and new
    OTEL = "otel"      # Only new gen_ai.* attributes


# Cache for emission mode to avoid repeated environment variable lookups
_cached_mode: Optional[EmitMode] = None


def get_emit_mode() -> EmitMode:
    """
    Get the current emission mode.

    Resolution order:
    1. CONTEXTCORE_EMIT_MODE env var (explicit, project-specific)
    2. OTEL_SEMCONV_STABILITY_OPT_IN env var (OTel standard)
       - Contains 'gen_ai_latest_experimental' -> EmitMode.OTEL
    3. Default: EmitMode.DUAL
    """
    global _cached_mode
    if _cached_mode is not None:
        return _cached_mode

    # 1. ContextCore-specific env var takes precedence
    cc_mode = os.getenv("CONTEXTCORE_EMIT_MODE", "").strip().lower()
    if cc_mode:
        try:
            _cached_mode = EmitMode(cc_mode)
            return _cached_mode
        except ValueError:
            warnings.warn(
                f"Invalid CONTEXTCORE_EMIT_MODE '{cc_mode}'. "
                f"Checking OTEL_SEMCONV_STABILITY_OPT_IN.",
                UserWarning,
                stacklevel=2,
            )

    # 2. OTel standard env var (comma-separated token list)
    otel_opt_in = os.getenv("OTEL_SEMCONV_STABILITY_OPT_IN", "").strip().lower()
    if otel_opt_in:
        tokens = {t.strip() for t in otel_opt_in.split(",")}
        if "gen_ai_latest_experimental" in tokens:
            _cached_mode = EmitMode.OTEL
            return _cached_mode

    # 3. Default
    _cached_mode = EmitMode.DUAL
    return _cached_mode


def warn_legacy_attribute(attr_name: str) -> None:
    """
    Emit deprecation warning for legacy attribute usage.

    Args:
        attr_name: Name of the legacy attribute being used.

    Examples:
        >>> warn_legacy_attribute("agent.id")
        # Emits: DeprecationWarning: Legacy attribute 'agent.id' is deprecated...
    """
    new_attr = ATTRIBUTE_MAPPINGS.get(attr_name, "gen_ai.*")
    warnings.warn(
        f"Legacy attribute '{attr_name}' is deprecated. "
        f"Use '{new_attr}' instead.",
        DeprecationWarning,
        stacklevel=3  # Skip this function and the transform method
    )


# ---------------------------------------------------------------------------
# Attribute transformation classes
# ---------------------------------------------------------------------------

class DualEmitAttributes:
    """
    Handler for dual-emit attribute transformation based on emission mode.

    This class transforms span attributes according to the configured emission mode:
    - LEGACY: Only emit original attributes
    - DUAL: Emit both original and gen_ai.* attributes
    - OTEL: Only emit gen_ai.* attributes (with warnings for legacy usage)
    """

    def __init__(self, mode: Optional[EmitMode] = None):
        """
        Initialize the dual-emit attributes handler.

        Args:
            mode: Override the emission mode. If None, uses get_emit_mode().
        """
        self.mode = mode or get_emit_mode()
        self._warned_attributes: Set[str] = set()  # Track warned attributes

    def transform(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform attributes based on emit mode.

        Args:
            attributes: Dictionary of span attributes to transform.

        Returns:
            Dict[str, Any]: Transformed attributes according to emission mode.

        Raises:
            TypeError: If attributes is not a dictionary.

        Examples:
            >>> emitter = DualEmitAttributes(EmitMode.DUAL)
            >>> attrs = {"agent.id": "test-agent", "custom.attr": "value"}
            >>> result = emitter.transform(attrs)
            >>> "agent.id" in result and "gen_ai.agent.id" in result
            True
        """
        if not isinstance(attributes, dict):
            raise TypeError("Attributes must be a dictionary")

        if self.mode == EmitMode.LEGACY:
            return self._legacy_mode(attributes)
        elif self.mode == EmitMode.DUAL:
            return self._dual_mode(attributes)
        else:  # EmitMode.OTEL
            return self._otel_mode(attributes)

    def _legacy_mode(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Return attributes unchanged for legacy mode."""
        return attributes.copy()

    def _dual_mode(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Return both legacy and gen_ai attributes for dual mode."""
        result = attributes.copy()

        # Add gen_ai equivalents for mapped legacy attributes
        for legacy_key, value in attributes.items():
            if legacy_key in ATTRIBUTE_MAPPINGS:
                gen_ai_key = ATTRIBUTE_MAPPINGS[legacy_key]
                result[gen_ai_key] = value

        return result

    def _otel_mode(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy attributes to gen_ai equivalents for otel mode."""
        result = {}

        for key, value in attributes.items():
            if key in ATTRIBUTE_MAPPINGS:
                # Emit deprecation warning (once per attribute)
                if key not in self._warned_attributes:
                    warn_legacy_attribute(key)
                    self._warned_attributes.add(key)
                # Use gen_ai equivalent
                result[ATTRIBUTE_MAPPINGS[key]] = value
            else:
                # Pass through non-legacy attributes unchanged
                result[key] = value

        return result


class DualEmitLayer:
    """
    Transforms attributes to include both legacy and OpenTelemetry gen_ai conventions.
    Preserves original attributes while adding mapped equivalents.
    """

    def transform(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform attributes using dual-emit pattern.

        Args:
            attributes: Original attribute dictionary

        Returns:
            Dictionary containing both original and mapped attributes
        """
        # Start with original attributes (legacy support)
        result = attributes.copy()

        # Add mapped attributes for OTel compatibility
        for original_key, value in attributes.items():
            if original_key in ATTRIBUTE_MAPPINGS:
                mapped_key = ATTRIBUTE_MAPPINGS[original_key]
                result[mapped_key] = value

        return result


# ---------------------------------------------------------------------------
# Transform functions
# ---------------------------------------------------------------------------

def transform(attributes: Dict[str, Any], legacy_mode: bool = False) -> Dict[str, Any]:
    """
    Transform attributes using dual-emit pattern for backward compatibility.

    In non-legacy mode, keeps original attributes and adds OTel standard equivalents.
    In legacy mode, only keeps original attributes.

    Args:
        attributes: Original attributes dict
        legacy_mode: If True, skip OTel transformations

    Returns:
        Transformed attributes dict with both old and new keys (when not in legacy mode)
    """
    result = attributes.copy()  # Never modify input dict

    if not legacy_mode:
        for old_key, new_key in ATTRIBUTE_MAPPINGS.items():
            if old_key in result:
                result[new_key] = result[old_key]  # Add new key, keep old

    return result


def transform_attributes(attributes: Dict[str, Any], mode: Optional[EmitMode] = None) -> Dict[str, Any]:
    """
    Convenience function to transform attributes using the specified or default emission mode.

    Args:
        attributes: Dictionary of span attributes to transform.
        mode: Override the emission mode. If None, uses get_emit_mode().
    Returns:
        Dict[str, Any]: Transformed attributes according to emission mode.
    Examples:
        >>> attrs = {"agent.id": "test", "handoff.inputs": "data"}
        >>> result = transform_attributes(attrs, EmitMode.OTEL)
        >>> list(result.keys())
        ['gen_ai.agent.id', 'gen_ai.tool.call.arguments']
    """
    emitter = DualEmitAttributes(mode)
    return emitter.transform(attributes)


# ---------------------------------------------------------------------------
# AttributeMapper (singleton used by agent modules)
# ---------------------------------------------------------------------------

class AttributeMapper:
    """
    Attribute mapper for dual-emit compatibility.
    Provides map_attributes() method expected by insights.py.
    """

    def __init__(self):
        self._emitter = DualEmitAttributes()

    def map_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map attributes using dual-emit transformation.

        Args:
            attributes: Dictionary of span attributes

        Returns:
            Transformed attributes with both legacy and OTel keys
        """
        return self._emitter.transform(attributes)


# Singleton mapper instance for import
mapper = AttributeMapper()


__all__ = [
    'ATTRIBUTE_MAPPINGS',
    'TOOL_ATTRIBUTES',
    'AttributeMapper',
    'DualEmitAttributes',
    'DualEmitLayer',
    'EmitMode',
    'get_emit_mode',
    'mapper',
    'transform',
    'transform_attributes',
    'warn_legacy_attribute',
]
