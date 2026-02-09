"""
ContextCore Coyote (Wiisagi-ma'iingan) - Multi-agent incident resolution pipeline.

Coyote automates the debugging lifecycle:
    Error Detection → Investigation → Fix Design → Implementation → Testing → Knowledge Capture

Each stage is handled by a specialized agent. The pipeline can run autonomously
or with human checkpoints.

Formerly known as agent-pipeline.
"""

from contextcore_coyote.config import configure, get_config, CoyoteConfig
from contextcore_coyote.pipeline import Pipeline, PipelineResult
from contextcore_coyote.models import Incident, StageResult, StageStatus

__version__ = "0.1.0"

__all__ = [
    # Config
    "configure",
    "get_config",
    "CoyoteConfig",
    # Pipeline
    "Pipeline",
    "PipelineResult",
    # Models
    "Incident",
    "StageResult",
    "StageStatus",
    # Version
    "__version__",
]
