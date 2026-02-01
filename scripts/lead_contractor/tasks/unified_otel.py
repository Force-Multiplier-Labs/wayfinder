"""
Phase 4 & 7: OTel GenAI attribute tasks for unified alignment plan.

Phase 4 Tasks (Core Attributes):
- 4.1: gen_ai.operation.name Support
- 4.2: gen_ai.conversation.id Migration

Phase 7 Tasks (Extended Attributes):
- 7.1: Provider and Model Tracking
- 7.2: Tool Mapping for Handoffs
"""

from ..runner import Feature

OPERATION_NAME_TASK = """
Add gen_ai.operation.name attribute to all ContextCore span types.

## Goal
Track the operation being performed in each span using OTel GenAI's standard
operation.name attribute, enabling consistent querying across all span types.

## Context
- This is for the ContextCore project
- Must update multiple modules: tracker.py, insights.py, handoff.py, skill/emitter.py
- Must use dual-emit layer from src/contextcore/compat/otel_genai.py

## Requirements

1. Define operation name mappings:
   ```python
   # In src/contextcore/compat/operations.py
   OPERATION_NAMES = {
       # Task operations
       "task_start": "task.start",
       "task_update": "task.update",
       "task_complete": "task.complete",

       # Insight operations
       "insight_emit": "insight.emit",
       "insight_query": "insight.query",

       # Handoff operations
       "handoff_create": "handoff.create",
       "handoff_accept": "handoff.accept",
       "handoff_complete": "handoff.complete",
       "handoff_fail": "handoff.fail",
       "handoff_cancel": "handoff.cancel",

       # Skill operations
       "skill_emit": "skill.emit",
       "skill_invoke": "skill.invoke",
       "skill_complete": "skill.complete",
       "skill_fail": "skill.fail",
   }
   ```

2. Update TaskTracker to emit gen_ai.operation.name:
   ```python
   def start_task(self, ...):
       attributes = {
           "task.id": task_id,
           # ... existing attributes
       }
       # Add operation name via dual-emit
       attributes = self._dual_emit.add_operation_name(attributes, "task_start")
       # This adds: gen_ai.operation.name = "task.start" when mode != legacy
   ```

3. Update InsightEmitter similarly for insight operations

4. Update HandoffManager/HandoffReceiver for handoff operations

5. Update SkillCapabilityEmitter for skill operations

6. Add helper method to DualEmitAttributes:
   ```python
   def add_operation_name(self, attributes: dict, operation_key: str) -> dict:
       '''Add gen_ai.operation.name attribute based on emit mode.'''
       if self.mode == EmitMode.LEGACY:
           return attributes
       op_name = OPERATION_NAMES.get(operation_key, operation_key)
       attributes["gen_ai.operation.name"] = op_name
       return attributes
   ```

7. Update docs/semantic-conventions.md with new attribute

## Output Format
Provide:
- Updated code snippets for each module
- New operations.py module
- Test cases verifying operation names are emitted
"""

CONVERSATION_ID_TASK = """
Replace agent.session_id with gen_ai.conversation.id per OTel conventions.

## Goal
Migrate session tracking from the ContextCore-specific agent.session_id to the
OTel standard gen_ai.conversation.id while maintaining backward compatibility.

## Context
- This is for the ContextCore project
- Affects: insights.py, handoff.py, CLI commands
- Must use dual-emit layer for backward compatibility

## Requirements

1. Update attribute mapping in compat/otel_genai.py:
   ```python
   ATTRIBUTE_MAPPINGS = {
       # ... existing mappings
       "agent.session_id": "gen_ai.conversation.id",
   }
   ```

2. Update InsightEmitter to use conversation_id parameter name:
   ```python
   def emit(
       self,
       insight_type: str,
       summary: str,
       confidence: float,
       conversation_id: str | None = None,  # Renamed from session_id
       session_id: str | None = None,  # Deprecated alias
       ...
   ):
       if session_id is not None:
           warnings.warn(
               "session_id is deprecated, use conversation_id instead",
               DeprecationWarning,
               stacklevel=2
           )
           conversation_id = conversation_id or session_id

       attributes = {
           "agent.session_id": conversation_id,  # Legacy
       }
       attributes = self._dual_emit.transform(attributes)
       # Now also has gen_ai.conversation.id when mode != legacy
   ```

3. Update InsightsAPI to use conversation_id

4. Update CLI commands:
   - contextcore insight emit --conversation-id X  (new)
   - contextcore insight emit --session-id X  (deprecated, shows warning)

5. Update InsightQuerier to accept both parameter names

6. Update all docstrings and type hints

7. Add migration note to CHANGELOG.md

## Output Format
Provide:
- Updated code for affected modules
- CLI changes
- CHANGELOG entry
- Updated docstrings
"""

PROVIDER_MODEL_TASK = """
Add provider and model tracking to insight spans.

## Goal
Track which LLM provider and model generated agent insights, enabling queries
like "show all decisions made by Claude Opus" or "compare confidence by model".

## Context
- This is for the ContextCore project
- Adds gen_ai.provider.name and gen_ai.request.model attributes
- Must use dual-emit layer

## Requirements

1. Add new parameters to InsightEmitter:
   ```python
   def emit(
       self,
       insight_type: str,
       summary: str,
       confidence: float,
       provider: str | None = None,  # NEW: "anthropic", "openai", etc.
       model: str | None = None,      # NEW: "claude-opus-4-5-20251101", etc.
       ...
   ):
       ...
   ```

2. Implement auto-detection when not provided:
   ```python
   def _detect_provider_model(self) -> tuple[str | None, str | None]:
       '''Auto-detect provider and model from environment.'''
       provider = os.environ.get("LLM_PROVIDER")
       model = os.environ.get("LLM_MODEL")

       if not provider:
           # Try to detect from OTEL_SERVICE_NAME
           service_name = os.environ.get("OTEL_SERVICE_NAME", "")
           if "claude" in service_name.lower():
               provider = "anthropic"
           elif "gpt" in service_name.lower():
               provider = "openai"
           # ... etc

       return provider, model
   ```

3. Add attributes via dual-emit:
   ```python
   if provider:
       attributes["gen_ai.provider.name"] = provider
   if model:
       attributes["gen_ai.request.model"] = model
   ```

4. Update InsightsAPI to accept provider/model parameters

5. Update CLI:
   ```
   contextcore insight emit --provider anthropic --model claude-opus-4-5
   ```

6. Add to semantic conventions documentation

## Output Format
Provide:
- Updated InsightEmitter code
- Updated InsightsAPI code
- CLI changes
- Documentation updates
"""

TOOL_MAPPING_TASK = """
Map ContextCore handoff attributes to OTel gen_ai.tool.* conventions.

## Goal
Align handoff span attributes with OTel's tool execution conventions, enabling
standard tooling to understand ContextCore handoffs as tool calls.

## Context
- This is for the ContextCore project
- Maps handoff.* attributes to gen_ai.tool.* attributes
- Must use dual-emit layer

## Requirements

1. Update attribute mapping:
   ```python
   ATTRIBUTE_MAPPINGS = {
       # ... existing
       "handoff.capability_id": "gen_ai.tool.name",
       "handoff.inputs": "gen_ai.tool.call.arguments",
       "handoff.id": "gen_ai.tool.call.id",
   }

   # Additional tool attributes (no legacy equivalent)
   TOOL_ATTRIBUTES = {
       "gen_ai.tool.type": "agent_handoff",  # ContextCore-specific tool type
   }
   ```

2. Update HandoffManager.create_handoff():
   ```python
   def create_handoff(self, ...):
       attributes = {
           "handoff.id": handoff_id,
           "handoff.capability_id": capability_id,
           "handoff.inputs": json.dumps(inputs),
           # ... existing
       }

       # Add tool type
       attributes["gen_ai.tool.type"] = "agent_handoff"

       # Transform via dual-emit
       attributes = self._dual_emit.transform(attributes)
   ```

3. Update handoff completion to record result:
   ```python
   def complete_handoff(self, handoff_id: str, result_trace_id: str):
       # ... existing logic

       # Add tool result attribute
       attributes["gen_ai.tool.call.result"] = json.dumps({
           "status": "success",
           "trace_id": result_trace_id,
       })
   ```

4. Document gen_ai.tool.type="agent_handoff" as ContextCore extension in docs

5. Update agent-semantic-conventions.md with mappings

## Output Format
Provide:
- Updated HandoffManager code
- Updated compat/otel_genai.py mappings
- Documentation updates
"""

CORE_OTEL_FEATURES = [
    Feature(
        task=OPERATION_NAME_TASK,
        name="OTel_OperationName",
        output_subdir="unified/phase4",
    ),
    Feature(
        task=CONVERSATION_ID_TASK,
        name="OTel_ConversationId",
        output_subdir="unified/phase4",
    ),
]

EXTENDED_OTEL_FEATURES = [
    Feature(
        task=PROVIDER_MODEL_TASK,
        name="OTel_ProviderModel",
        output_subdir="unified/phase7",
    ),
    Feature(
        task=TOOL_MAPPING_TASK,
        name="OTel_ToolMapping",
        output_subdir="unified/phase7",
    ),
]
