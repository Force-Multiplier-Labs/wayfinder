"""
Input request model for the INPUT_REQUIRED handoff state.

When an agent needs clarification during a handoff, it creates an InputRequest
specifying the question, expected input type, and optional choices. The requesting
agent then provides a response via provide_input().
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class InputType(str, Enum):
    """Types of input that can be requested."""
    TEXT = "text"
    CHOICE = "choice"
    MULTI_CHOICE = "multi_choice"
    CONFIRMATION = "confirmation"
    FILE = "file"


@dataclass
class InputOption:
    """A selectable option for CHOICE/MULTI_CHOICE input types."""
    value: str
    label: str
    description: str | None = None


@dataclass
class InputRequest:
    """A request for input from the handoff initiator.

    Created when a receiving agent needs clarification (INPUT_REQUIRED state).

    Example:
        request = InputRequest(
            handoff_id="handoff-abc123",
            question="Which deployment method should I use?",
            input_type=InputType.CHOICE,
            options=[
                InputOption("docker", "Docker Compose", "Local dev setup"),
                InputOption("kind", "Kind Cluster", "K8s-native dev"),
            ],
        )
    """
    handoff_id: str
    question: str
    input_type: InputType
    request_id: str = field(default_factory=lambda: f"input-{uuid.uuid4().hex[:8]}")
    options: list[InputOption] | None = None
    default_value: str | None = None
    required: bool = True
    timeout_ms: int = 300_000  # 5 minutes
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class InputResponse:
    """Response to an InputRequest."""
    request_id: str
    handoff_id: str
    value: str
    responded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = [
    "InputType",
    "InputOption",
    "InputRequest",
    "InputResponse",
]
