"""
A2A-compatible Message model for handoff communication.

Messages represent individual turns in an agent conversation, containing
one or more Parts as content. Uses conversation_id (not session_id) to
align with gen_ai.conversation.id OTel convention.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from contextcore.models.part import Part


class MessageRole(str, Enum):
    """Role of the message sender."""
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"


@dataclass
class Message:
    """A single message in an agent conversation.

    Example:
        msg = Message.from_text("Investigate the latency spike", MessageRole.USER)
        msg = Message(
            role=MessageRole.AGENT,
            parts=[Part.text("Found root cause"), Part.trace("abc123")],
        )
    """
    role: MessageRole
    parts: list[Part]
    message_id: str = field(default_factory=lambda: f"msg-{uuid.uuid4().hex[:8]}")
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    # CC extensions
    agent_id: str | None = None
    conversation_id: str | None = None  # OTel: gen_ai.conversation.id
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_text(cls, text: str, role: MessageRole, **kwargs: Any) -> Message:
        """Create a message from plain text."""
        return cls(role=role, parts=[Part.text(text)], **kwargs)

    def to_a2a_dict(self) -> dict[str, Any]:
        """Convert to A2A-compatible Message dict."""
        return {
            "messageId": self.message_id,
            "role": self.role.value,
            "parts": [p.to_a2a_dict() for p in self.parts],
            "timestamp": self.timestamp.isoformat(),
        }


__all__ = ["Message", "MessageRole"]
