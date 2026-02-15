"""
Pipeline orchestration for multi-stage incident resolution.

Includes:
- HOWL Pipeline (core.py): Original sequential pipeline — do not modify.
- Stage base class (stage.py): ABC for pipeline stages.
- Typed Contracts (contracts.py): Pydantic I/O models, gates, and contract protocols
  for the new modular pipeline design (Defense in Depth).
"""

from contextcore_coyote.pipeline.core import Pipeline, PipelineResult
from contextcore_coyote.pipeline.stage import Stage, StageContext
from contextcore_coyote.pipeline.contracts import (
    # Typed outputs
    StageOutput,
    InvestigationOutput,
    DesignOutput,
    ImplementationOutput,
    ValidationOutput,
    LessonOutput,
    # Gates
    Gate,
    GateResult,
    ContractViolation,
    ViolationSeverity,
    # Typed stage protocol
    TypedStage,
    # Utilities
    adapt_legacy_result,
    fingerprint,
    STAGE_OUTPUT_REGISTRY,
)
from contextcore_coyote.pipeline.gates import (
    # Gate implementations
    SchemaGate,
    CompletenessGate,
    IntegrityGate,
    QualityGate,
    CompositeGate,
    # Pre-built configurations
    standard_gate,
    strict_gate,
)
from contextcore_coyote.pipeline.modular import (
    ModularPipeline,
    ModularPipelineResult,
    LegacyStageAdapter,
)

__all__ = [
    # HOWL Pipeline (unchanged)
    "Pipeline",
    "PipelineResult",
    "Stage",
    "StageContext",
    # Typed Contracts (new)
    "StageOutput",
    "InvestigationOutput",
    "DesignOutput",
    "ImplementationOutput",
    "ValidationOutput",
    "LessonOutput",
    # Gates (new)
    "Gate",
    "GateResult",
    "ContractViolation",
    "ViolationSeverity",
    # Typed stage protocol (new)
    "TypedStage",
    # Gate implementations (new)
    "SchemaGate",
    "CompletenessGate",
    "IntegrityGate",
    "QualityGate",
    "CompositeGate",
    "standard_gate",
    "strict_gate",
    # ModularPipeline (new)
    "ModularPipeline",
    "ModularPipelineResult",
    "LegacyStageAdapter",
    # Utilities (new)
    "adapt_legacy_result",
    "fingerprint",
    "STAGE_OUTPUT_REGISTRY",
]
