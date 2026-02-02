# src/contextcore/compat/operations.py
"""Operation name constants for OpenTelemetry GenAI semantic conventions.

This module provides standardized operation names for consistent tracking
across all ContextCore span types.
"""
from typing import Dict

__all__ = ['OPERATION_NAMES']

# Standard operation name mappings following module.action convention
OPERATION_NAMES: Dict[str, str] = {
    # Task operations - core workflow tracking
    "task_start": "task.start",
    "task_update": "task.update",
    "task_complete": "task.complete",

    # Insight operations - analytics and monitoring
    "insight_emit": "insight.emit",
    "insight_query": "insight.query",

    # Handoff operations - inter-agent communication
    "handoff_create": "handoff.create",
    "handoff_accept": "handoff.accept",
    "handoff_complete": "handoff.complete",
    "handoff_fail": "handoff.fail",
    "handoff_cancel": "handoff.cancel",

    # Skill operations - capability execution
    "skill_emit": "skill.emit",
    "skill_invoke": "skill.invoke",
    "skill_complete": "skill.complete",
    "skill_fail": "skill.fail",
}
