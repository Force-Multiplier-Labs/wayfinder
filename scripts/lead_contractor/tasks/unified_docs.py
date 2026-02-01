"""
Phase 9: Documentation tasks for unified alignment plan.

Tasks:
- 9.1: Unified Documentation Update
"""

from ..runner import Feature

UNIFIED_DOCS_TASK = """
Comprehensive documentation update reflecting both OTel GenAI and A2A alignment.

## Goal
Update all documentation to reflect the unified protocol alignment, including
migration guides, updated attribute references, and A2A interoperability docs.

## Context
- This is for the ContextCore project
- Must update existing docs and create new migration guides
- Position ContextCore as "OTel GenAI + A2A + project management extensions"

## Requirements

1. Update docs/semantic-conventions.md:
   - Add "OTel GenAI Alignment" section
   - Document all gen_ai.* attributes used
   - Show mapping table from ContextCore-specific to OTel
   - Add CONTEXTCORE_EMIT_MODE configuration documentation

2. Update docs/agent-semantic-conventions.md:
   - Update attribute tables with OTel equivalents
   - Add "Dual-Emit Mode" section explaining migration
   - Update TraceQL query examples to show both formats:
     ```
     # Legacy query
     { agent.id = "claude" && insight.type = "decision" }

     # OTel query
     { gen_ai.agent.id = "claude" && insight.type = "decision" }
     ```

3. Create docs/OTEL_GENAI_MIGRATION_GUIDE.md:
   - Executive summary of changes
   - Step-by-step migration for existing users
   - Query migration examples (legacy → OTel TraceQL)
   - Code migration examples (InsightEmitter → InsightsAPI)
   - Environment variable configuration
   - Timeline for deprecation of legacy attributes
   - FAQ section

4. Create docs/A2A_INTEROPERABILITY.md:
   - A2A protocol overview and why we support it
   - AgentCard configuration and customization
   - Discovery endpoint setup (.well-known)
   - Server setup guide (contextcore a2a serve)
   - Client usage guide (A2AClient)
   - Handoff ↔ Task mapping reference table
   - State mapping (HandoffStatus ↔ TaskState)
   - Part/Message/Artifact model reference
   - Example: communicating with external A2A agent
   - Example: exposing ContextCore agent via A2A

5. Update README.md:
   - Add "Standards Compliance" section mentioning:
     - OTel GenAI semantic conventions
     - A2A protocol interoperability
   - Add badges or notes for compliance
   - Link to new documentation
   - Update quick start to show new API style

6. Update CLAUDE.md:
   - Add links to new documentation in Documentation section
   - Update code examples to use new API style

## Output Format
Provide complete Markdown content for:
- Updated docs/semantic-conventions.md sections
- Updated docs/agent-semantic-conventions.md sections
- New docs/OTEL_GENAI_MIGRATION_GUIDE.md
- New docs/A2A_INTEROPERABILITY.md
- README.md updates
"""

DOCS_FEATURES = [
    Feature(
        task=UNIFIED_DOCS_TASK,
        name="Docs_UnifiedUpdate",
        output_subdir="unified/phase9",
    ),
]
