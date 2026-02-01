"""
Phase 1: Foundation tasks for unified alignment plan.

Tasks:
- 1.1: Gap Analysis Document (OTel GenAI)
- 1.2: Dual-Emit Compatibility Layer
"""

from ..runner import Feature

GAP_ANALYSIS_TASK = """
Analyze ContextCore's current semantic conventions against OTel GenAI conventions.

## Goal
Create a comprehensive gap analysis document comparing ContextCore's custom namespaces
(agent.*, insight.*, handoff.*) against OTel GenAI semantic conventions (gen_ai.*).

## Context
- This is for the ContextCore project
- Output should be saved as docs/OTEL_GENAI_GAP_ANALYSIS.md
- OTel GenAI spec: https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md

## Requirements

1. Read and analyze current ContextCore conventions:
   - docs/semantic-conventions.md
   - docs/agent-semantic-conventions.md

2. Compare against OTel GenAI conventions for:
   - Agent identification attributes
   - Operation/action naming
   - Session/conversation tracking
   - Tool/function call attributes
   - Provider and model identification

3. Create attribute-by-attribute comparison table with columns:
   - Current ContextCore attribute
   - OTel GenAI equivalent (if exists)
   - Recommendation: ALIAS (emit both), MIGRATE (replace), ADD (new), PRESERVE (keep CC-only)
   - Breaking change risk (none, low, medium, high)
   - Migration complexity (1-5)

4. Document:
   - Which attributes have direct OTel equivalents
   - Which are ContextCore-specific (no OTel equivalent)
   - Which OTel attributes we should add
   - Recommended adoption order

## Output Format
Markdown document with:
- Executive summary
- Comparison tables
- Migration recommendations
- Timeline suggestion
"""

DUAL_EMIT_TASK = """
Implement a dual-emit compatibility layer for ContextCore attribute emission.

## Goal
Create a module that allows ContextCore to emit both legacy (agent.*, insight.*, handoff.*)
and new (gen_ai.*) span attributes during the migration period.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/compat/otel_genai.py
- Must integrate with existing span emission in tracker.py, insights.py, handoff.py

## Requirements

1. Create attribute mapping registry:
   ```python
   ATTRIBUTE_MAPPINGS = {
       "agent.id": "gen_ai.agent.id",
       "agent.type": "gen_ai.agent.type",
       "agent.session_id": "gen_ai.conversation.id",
       "handoff.capability_id": "gen_ai.tool.name",
       "handoff.inputs": "gen_ai.tool.call.arguments",
       # ... etc
   }
   ```

2. Create EmitMode enum:
   ```python
   class EmitMode(str, Enum):
       LEGACY = "legacy"  # Only old attributes
       DUAL = "dual"      # Both old and new
       OTEL = "otel"      # Only new gen_ai.* attributes
   ```

3. Create get_emit_mode() function:
   - Read from CONTEXTCORE_EMIT_MODE environment variable
   - Default to "dual" during migration

4. Create DualEmitAttributes class or decorator:
   ```python
   class DualEmitAttributes:
       def __init__(self, mode: EmitMode = None):
           self.mode = mode or get_emit_mode()

       def transform(self, attributes: dict) -> dict:
           '''Transform attributes based on emit mode.'''
           if self.mode == EmitMode.LEGACY:
               return attributes
           elif self.mode == EmitMode.DUAL:
               return self._add_otel_attributes(attributes)
           else:  # OTEL
               return self._convert_to_otel(attributes)
   ```

5. Add deprecation warning utility:
   ```python
   def warn_legacy_attribute(attr_name: str) -> None:
       '''Emit deprecation warning for legacy attribute usage.'''
       ...
   ```

6. Create unit tests for all three modes

## Output Format
Provide clean Python code with:
- Type hints throughout
- Docstrings with examples
- Unit tests in tests/test_compat_otel_genai.py
- __all__ export list
"""

FOUNDATION_FEATURES = [
    Feature(
        task=GAP_ANALYSIS_TASK,
        name="Foundation_GapAnalysis",
        output_subdir="unified/phase1",
    ),
    Feature(
        task=DUAL_EMIT_TASK,
        name="Foundation_DualEmit",
        output_subdir="unified/phase1",
    ),
]
