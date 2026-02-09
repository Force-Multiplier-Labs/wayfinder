"""
Pre-built agent personalities for incident resolution.

Each agent specializes in one stage of the pipeline:
- Investigator: Root cause analysis
- Designer: Fix specification
- Implementer: Code generation
- Tester: Validation
- KnowledgeAgent: Lessons learned
"""

from contextcore_coyote.agents.investigator import Investigator
from contextcore_coyote.agents.designer import Designer
from contextcore_coyote.agents.implementer import Implementer
from contextcore_coyote.agents.tester import Tester
from contextcore_coyote.agents.knowledge import KnowledgeAgent

__all__ = [
    "Investigator",
    "Designer",
    "Implementer",
    "Tester",
    "KnowledgeAgent",
]


def full_pipeline():
    """Get all agents for a full pipeline."""
    return [
        Investigator(),
        Designer(),
        Implementer(),
        Tester(),
        KnowledgeAgent(),
    ]
