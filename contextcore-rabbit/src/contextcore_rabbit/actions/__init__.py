"""
Built-in Rabbit actions.

These actions are automatically registered when Rabbit is imported.
"""

from contextcore_rabbit.actions.log import LogAction
from contextcore_rabbit.actions.beaver_workflow import BeaverWorkflowAction
from contextcore_rabbit.actions.coyote_investigate import CoyoteInvestigateAction
from contextcore_rabbit.actions.coyote_bridge import (
    CoyoteApplyAction,
    CoyoteApplyStatusAction,
    CoyoteSpecAction,
)

__all__ = [
    "LogAction",
    "BeaverWorkflowAction",
    "CoyoteInvestigateAction",
    "CoyoteApplyAction",
    "CoyoteApplyStatusAction",
    "CoyoteSpecAction",
]
