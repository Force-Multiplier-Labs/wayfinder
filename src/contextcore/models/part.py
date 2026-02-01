"""
Unified Part model supporting both A2A and ContextCore content types.

Parts are the fundamental content units exchanged between agents. They can
represent text, files, structured data, or ContextCore-specific observability
references (traces, log queries, metrics queries).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PartType(str, Enum):
    """Content type for a Part.

    Includes both A2A standard types and ContextCore extensions.
    """
    # A2A standard types
    TEXT = "text"
    FILE = "file"
    DATA = "data"
    JSON = "json"
    FORM = "form"
    # ContextCore extensions
    TRACE = "trace"           # OTel trace reference
    LOG_QUERY = "log_query"   # LogQL query
    METRIC_QUERY = "metric_query"  # PromQL query
    TRACE_QUERY = "trace_query"    # TraceQL query
    REFERENCE = "reference"        # Generic reference


@dataclass
class Part:
    """Unified content unit for agent communication.

    Supports A2A-compatible content types plus ContextCore observability
    extensions for trace, log, and metric references.

    Example:
        # Simple text
        part = Part.text("Analysis complete: 3 issues found")

        # Trace reference
        part = Part.trace("abc123def456", "Root cause span")

        # TraceQL query
        part = Part.query('{ span.project.id = "checkout" }', "traceql")
    """
    part_type: PartType
    # Text content
    text: str | None = None
    # File content
    file_uri: str | None = None
    mime_type: str | None = None
    # Structured data
    data: dict[str, Any] | None = None
    # ContextCore observability
    trace_id: str | None = None
    span_id: str | None = None
    query: str | None = None
    query_type: str | None = None  # "traceql", "logql", "promql"
    # References
    ref: str | None = None
    description: str | None = None
    # CC extension
    tokens: int | None = None  # Token budget hint

    # --- Factory methods ---

    @classmethod
    def text(cls, content: str) -> Part:
        """Create a text part."""
        return cls(part_type=PartType.TEXT, text=content)

    @classmethod
    def trace(cls, trace_id: str, description: str | None = None, span_id: str | None = None) -> Part:
        """Create a trace reference part."""
        return cls(part_type=PartType.TRACE, trace_id=trace_id, span_id=span_id, description=description)

    @classmethod
    def file(cls, uri: str, mime_type: str = "application/octet-stream") -> Part:
        """Create a file part."""
        return cls(part_type=PartType.FILE, file_uri=uri, mime_type=mime_type)

    @classmethod
    def json_data(cls, data: dict[str, Any]) -> Part:
        """Create a JSON/structured data part."""
        return cls(part_type=PartType.DATA, data=data)

    @classmethod
    def query(cls, query_str: str, query_type: str, description: str | None = None) -> Part:
        """Create a query part (TraceQL, LogQL, or PromQL)."""
        type_map = {
            "traceql": PartType.TRACE_QUERY,
            "logql": PartType.LOG_QUERY,
            "promql": PartType.METRIC_QUERY,
        }
        pt = type_map.get(query_type, PartType.TRACE_QUERY)
        return cls(part_type=pt, query=query_str, query_type=query_type, description=description)

    @classmethod
    def reference(cls, ref: str, description: str | None = None) -> Part:
        """Create a generic reference part."""
        return cls(part_type=PartType.REFERENCE, ref=ref, description=description)

    # --- Conversion methods ---

    def to_a2a_dict(self) -> dict[str, Any]:
        """Convert to A2A-compatible Part dict (no CC extensions)."""
        result: dict[str, Any] = {"type": self.part_type.value}
        if self.text is not None:
            result["text"] = self.text
        if self.file_uri is not None:
            result["file"] = {"uri": self.file_uri, "mimeType": self.mime_type}
        if self.data is not None:
            result["data"] = self.data
        return result

    def to_evidence(self) -> "Evidence":
        """Convert to legacy Evidence format for backward compatibility."""
        from contextcore.agent.insights import Evidence
        ev_type = self.part_type.value
        ev_ref = self.trace_id or self.ref or self.file_uri or self.text or ""
        return Evidence(
            type=ev_type,
            ref=ev_ref,
            description=self.description,
            query=self.query,
        )

    @classmethod
    def from_evidence(cls, evidence: "Evidence") -> Part:
        """Create a Part from a legacy Evidence object."""
        from contextcore.agent.insights import Evidence
        if evidence.type == "trace":
            return cls.trace(evidence.ref, evidence.description)
        if evidence.query:
            return cls.query(evidence.query, evidence.type, evidence.description)
        return cls(
            part_type=PartType.REFERENCE,
            ref=evidence.ref,
            description=evidence.description,
        )


__all__ = ["Part", "PartType"]
