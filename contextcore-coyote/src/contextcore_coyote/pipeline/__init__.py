"""
Pipeline orchestration for multi-stage incident resolution.
"""

from contextcore_coyote.pipeline.core import Pipeline, PipelineResult
from contextcore_coyote.pipeline.stage import Stage, StageContext

__all__ = [
    "Pipeline",
    "PipelineResult",
    "Stage",
    "StageContext",
]
