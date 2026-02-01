"""
A2A-compatible Artifact model for handoff outputs.

Artifacts represent the deliverables produced by an agent during a handoff.
They can contain multiple Parts and support streaming via chunking.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from contextcore.models.part import Part


@dataclass
class Artifact:
    """Output artifact from a handoff.

    Example:
        artifact = Artifact.from_json(
            {"root_cause": "DB connection pool exhausted", "evidence": ["trace-abc"]},
            artifact_id="art-001",
        )
    """
    parts: list[Part]
    artifact_id: str = field(default_factory=lambda: f"art-{uuid.uuid4().hex[:8]}")
    media_type: str = "application/json"
    index: int = 0
    append: bool = False
    last_chunk: bool = True
    # CC extensions
    trace_id: str | None = None  # Link to OTel trace
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any], artifact_id: str | None = None) -> Artifact:
        """Create an artifact from JSON data."""
        return cls(
            parts=[Part.json_data(data)],
            artifact_id=artifact_id or f"art-{uuid.uuid4().hex[:8]}",
            media_type="application/json",
        )

    @classmethod
    def from_insight(cls, insight: Any) -> Artifact:
        """Create an artifact from an Insight object."""
        parts = [Part.text(insight.summary)]
        if hasattr(insight, "trace_id") and insight.trace_id:
            parts.append(Part.trace(insight.trace_id, "Insight trace"))
        return cls(
            parts=parts,
            artifact_id=f"art-{uuid.uuid4().hex[:8]}",
            metadata={"insight_id": insight.id, "insight_type": insight.type.value}
            if hasattr(insight, "type") else {},
        )

    def to_a2a_dict(self) -> dict[str, Any]:
        """Convert to A2A-compatible Artifact dict."""
        return {
            "artifactId": self.artifact_id,
            "parts": [p.to_a2a_dict() for p in self.parts],
            "mediaType": self.media_type,
            "index": self.index,
            "append": self.append,
            "lastChunk": self.last_chunk,
        }


__all__ = ["Artifact"]
