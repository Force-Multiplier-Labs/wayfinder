"""
Fox (Waagosh) - Context enrichment for alert automation.

Fox enriches alerts with ProjectContext business metadata and routes
them by criticality. It integrates with Rabbit as a registered action.

Span contract (matching fox-alert-automation.json dashboard):
    - fox.alert.received: alert intake
    - fox.context.enrich: ProjectContext lookup + enrichment
    - fox.action.*: dispatched actions (claude_analysis, context_notify, etc.)
"""

from wayfinder_fox.enricher import ProjectContextEnricher, EnrichedAlert
from wayfinder_fox.router import CriticalityRouter
from wayfinder_fox.telemetry import FoxTracer

__all__ = [
    "ProjectContextEnricher",
    "EnrichedAlert",
    "CriticalityRouter",
    "FoxTracer",
]

try:
    from wayfinder_fox.actions.fox_enrich import FoxEnrichAction

    __all__.append("FoxEnrichAction")
except ImportError:
    pass  # contextcore-rabbit not installed; Rabbit integration unavailable

__version__ = "0.1.0"
