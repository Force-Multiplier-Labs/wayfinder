"""
ContextCore models package.

Re-exports all CRD models from core.py (backward compatible) plus new
A2A-aligned Part, Message, and Artifact models.
"""

from __future__ import annotations

# CRD models (backward compatible - previously in models.py)
from contextcore.models.core import (
    BusinessSpec,
    DesignSpec,
    GeneratedArtifacts,
    ObservabilitySpec,
    ProjectContextSpec,
    ProjectContextStatus,
    ProjectSpec,
    RequirementsSpec,
    RiskSpec,
    TargetKind,
    TargetSpec,
    derive_observability,
)

# Contract types (re-exported for backward compat - previously accessible via models.py)
from contextcore.contracts.types import (
    AlertPriority,
    BusinessValue,
    Criticality,
    DashboardPlacement,
    LogLevel,
    RiskType,
)

# A2A-aligned models
from contextcore.models.part import Part, PartType
from contextcore.models.message import Message, MessageRole
from contextcore.models.artifact import Artifact

# Legacy alias
Evidence = Part  # Evidence is now Part; use Part.from_evidence() for conversion

__all__ = [
    # CRD models
    "BusinessSpec",
    "DesignSpec",
    "GeneratedArtifacts",
    "ObservabilitySpec",
    "ProjectContextSpec",
    "ProjectContextStatus",
    "ProjectSpec",
    "RequirementsSpec",
    "RiskSpec",
    "TargetKind",
    "TargetSpec",
    "derive_observability",
    # Contract types
    "AlertPriority",
    "BusinessValue",
    "Criticality",
    "DashboardPlacement",
    "LogLevel",
    "RiskType",
    # A2A models
    "Part",
    "PartType",
    "Message",
    "MessageRole",
    "Artifact",
    # Legacy
    "Evidence",
]
