"""
W3C Baggage Propagation for ContextCore.

Configures the global TextMapPropagator to use a composite of TraceContext
and Baggage propagators, and provides helpers for setting/getting
ContextCore-specific baggage items.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from opentelemetry import baggage, context
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.context import Context
from opentelemetry.propagate import get_global_textmap, set_global_textmap
from opentelemetry.propagators.composite import CompositeHTTPPropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

_propagator_configured = False


def configure_propagator() -> None:
    """
    Set the global TextMapPropagator to a composite of TraceContext + Baggage.

    Idempotent -- safe to call multiple times.
    """
    global _propagator_configured
    if _propagator_configured:
        return

    propagator = CompositeHTTPPropagator([
        TraceContextTextMapPropagator(),
        W3CBaggagePropagator(),
    ])
    set_global_textmap(propagator)
    _propagator_configured = True
    logger.debug("Configured composite propagator (TraceContext + Baggage)")


def set_project_baggage(
    project_id: str,
    criticality: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> Context:
    """
    Set ContextCore-specific baggage items on the given (or current) context.

    Args:
        project_id: The project identifier.
        criticality: Optional business criticality level.
        ctx: Optional context to modify. Uses current context if None.

    Returns:
        New context with baggage items set.
    """
    ctx = ctx or context.get_current()
    ctx = baggage.set_baggage("project.id", project_id, ctx)
    if criticality:
        ctx = baggage.set_baggage("business.criticality", criticality, ctx)
    return ctx


def get_project_baggage(ctx: Optional[Context] = None) -> Dict[str, str]:
    """
    Read ContextCore-specific baggage items from the given (or current) context.

    Args:
        ctx: Optional context to read from. Uses current context if None.

    Returns:
        Dictionary of ContextCore baggage items found.
    """
    ctx = ctx or context.get_current()
    result: Dict[str, str] = {}

    project_id = baggage.get_baggage("project.id", ctx)
    if project_id is not None:
        result["project.id"] = project_id

    criticality = baggage.get_baggage("business.criticality", ctx)
    if criticality is not None:
        result["business.criticality"] = criticality

    return result
