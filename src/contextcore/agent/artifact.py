"""
A2A-compatible Artifact model for handoff outputs with ContextCore extensions.

This module provides the Artifact class that represents outputs generated during
handoff execution, with full compatibility with the A2A (Agent-to-Agent) protocol
and additional ContextCore features for OpenTelemetry integration.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING
import uuid

from .part import Part

if TYPE_CHECKING:
    from .insights import Insight


@dataclass
class Artifact:
    """A2A-compatible artifact with ContextCore extensions for handoff outputs.

    Represents structured outputs from agent handoffs, supporting both simple
    single-part artifacts and complex multi-part streaming scenarios.

    A2A Core Fields:
        artifact_id: Unique identifier for the artifact
        parts: List of content parts (text, json, files, etc.)
        media_type: MIME type of the primary content
        index: Sequence number for streaming chunks
        append: Whether this chunk should be appended to previous
        last_chunk: Whether this is the final chunk in a stream

    ContextCore Extensions:
        trace_id: OpenTelemetry trace identifier for correlation
        name: Human-readable artifact name
        description: Detailed description of the artifact
        metadata: Additional key-value metadata
        created_at: UTC timestamp of creation
    """

    # Core A2A fields - maintain exact compatibility
    artifact_id: str | None = None
    parts: list[Part] = field(default_factory=list)
    media_type: str = "application/json"
    index: int = 0
    append: bool = False
    last_chunk: bool = True

    # ContextCore extensions for enhanced functionality
    trace_id: str | None = None  # Link to OTel trace for correlation
    name: str | None = None  # Human-readable identifier
    description: str | None = None  # Detailed description
    metadata: dict[str, Any] = field(default_factory=dict)  # Extensible metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Post-initialization validation and auto-generation."""
        # Generate artifact_id if not provided
        if self.artifact_id is None:
            self.artifact_id = f"artifact-{uuid.uuid4().hex[:12]}"

    def to_a2a_dict(self) -> dict:
        """Convert to A2A Artifact format, excluding ContextCore extensions.

        Returns a dictionary that conforms exactly to the A2A specification
        for maximum interoperability with other A2A-compatible systems.
        """
        return {
            "artifactId": self.artifact_id,
            "parts": [part.to_a2a_dict() for part in self.parts],
            "mediaType": self.media_type,
            "index": self.index,
            "append": self.append,
            "lastChunk": self.last_chunk,
        }

    def to_dict(self) -> dict:
        """Convert to full dictionary with ContextCore extensions included.

        Includes all fields for complete serialization, useful for internal
        storage and debugging scenarios.
        """
        return {
            "artifact_id": self.artifact_id,
            "parts": [part.to_a2a_dict() for part in self.parts],
            "media_type": self.media_type,
            "index": self.index,
            "append": self.append,
            "last_chunk": self.last_chunk,
            "trace_id": self.trace_id,
            "name": self.name,
            "description": self.description,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_a2a_dict(cls, data: dict) -> Artifact:
        """Parse artifact from A2A format dictionary.

        Creates an Artifact instance from a dictionary that conforms to the
        A2A specification. ContextCore extensions will use default values.

        Args:
            data: Dictionary containing A2A artifact fields

        Returns:
            New Artifact instance

        Raises:
            ValueError: If required A2A fields are missing or invalid
        """
        try:
            parts_data = data.get("parts", [])
            parts = [Part.from_a2a_dict(part) for part in parts_data]

            return cls(
                artifact_id=data.get("artifactId"),
                parts=parts,
                media_type=data.get("mediaType", "application/json"),
                index=data.get("index", 0),
                append=data.get("append", False),
                last_chunk=data.get("lastChunk", True),
            )
        except Exception as e:
            raise ValueError(f"Invalid A2A artifact data: {e}") from e

    def is_complete(self) -> bool:
        """Check if artifact represents a complete, non-streaming entity.

        Returns True for complete artifacts or final chunks in a stream.
        Returns False for intermediate streaming chunks.
        """
        return self.last_chunk and not self.append

    @classmethod
    def from_json(cls, data: dict, artifact_id: str = None, name: str = None) -> Artifact:
        """Create artifact from JSON data dictionary.

        Convenience factory for creating artifacts from structured data.
        The entire dictionary becomes a single JSON part.

        Args:
            data: JSON-serializable dictionary
            artifact_id: Optional custom artifact ID
            name: Optional human-readable name
        """
        json_part = Part.json_data(data)
        return cls(
            artifact_id=artifact_id,
            parts=[json_part],
            media_type="application/json",
            name=name,
        )

    @classmethod
    def from_text(cls, text: str, artifact_id: str = None, name: str = None) -> Artifact:
        """Create artifact from plain text content.

        Convenience factory for text-based artifacts like summaries or logs.

        Args:
            text: Text content
            artifact_id: Optional custom artifact ID
            name: Optional human-readable name
        """
        text_part = Part.text(text)
        return cls(
            artifact_id=artifact_id,
            parts=[text_part],
            media_type="text/plain",
            name=name,
        )

    @classmethod
    def from_file(cls, uri: str, mime_type: str, artifact_id: str = None, name: str = None) -> Artifact:
        """Create artifact from file reference.

        Creates an artifact that references an external file resource.

        Args:
            uri: File URI or path
            mime_type: MIME type of the file
            artifact_id: Optional custom artifact ID
            name: Optional human-readable name
        """
        file_part = Part.file(uri, mime_type)
        return cls(
            artifact_id=artifact_id,
            parts=[file_part],
            media_type=mime_type,
            name=name,
        )

    @classmethod
    def from_insight(cls, insight: Insight) -> Artifact:
        """Create artifact from an Insight instance.

        Converts ContextCore Insights into artifacts for handoff scenarios,
        preserving trace correlation and key insight data.

        Args:
            insight: Insight instance to convert
        """
        # Extract key insight data into structured JSON
        insight_data = {
            "id": insight.id,
            "type": insight.type.value,
            "summary": insight.summary,
            "confidence": insight.confidence,
        }

        json_part = Part.json_data(insight_data)
        return cls(
            artifact_id=f"insight-{insight.id}",
            parts=[json_part],
            media_type="application/json",
            name=f"Insight: {insight.summary[:50]}{'...' if len(insight.summary) > 50 else ''}",
            trace_id=insight.trace_id,
        )

    @classmethod
    def create_chunk(
        cls,
        artifact_id: str,
        parts: list[Part],
        index: int,
        is_last: bool,
    ) -> Artifact:
        """Create a streaming chunk for large artifact delivery.

        Used in streaming scenarios where large artifacts are delivered
        in multiple chunks to avoid memory issues or timeouts.

        Args:
            artifact_id: Shared ID across all chunks
            parts: Content parts for this chunk
            index: Sequence number of this chunk
            is_last: Whether this is the final chunk
        """
        return cls(
            artifact_id=artifact_id,
            parts=parts,
            index=index,
            append=True,  # Streaming chunks are always appended
            last_chunk=is_last,
        )


__all__ = ["Artifact"]
