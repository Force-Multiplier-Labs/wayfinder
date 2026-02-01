"""
A2A Naming Convention Migration tasks for Lead Contractor workflow.

Feature 4.1: Migrate ContextCore APIs to A2A-style resource.action naming.
"""

from ..runner import Feature

INSIGHTS_API_TASK = """
Create a new API facade module that exposes A2A-style naming for the Insights API.

## Goal
Provide A2A-compatible method names (insights.emit, insights.query) while preserving
backward compatibility with existing InsightEmitter/InsightQuerier classes.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/api/insights.py
- Must import from contextcore.agent.insights (InsightEmitter, InsightQuerier, Insight, etc.)
- A2A uses resource.action naming: message.send, tasks.get, etc.

## Requirements

1. Create InsightsAPI class with:
   - __init__(project_id: str, agent_id: str, tempo_url: str = "http://localhost:3200", local_storage_path: str | None = None)
   - Internal _emitter: InsightEmitter instance
   - Internal _querier: InsightQuerier instance

2. Implement emit() method (maps to InsightEmitter.emit):
   - Parameters: type (InsightType | str), summary (str), confidence (float), audience (InsightAudience), rationale (str | None), evidence (list | None), applies_to (list[str] | None), category (str | None)
   - Returns: Insight
   - Handle type as string or enum

3. Implement query() method (maps to InsightQuerier.query):
   - Parameters: project_id (str | None), insight_type (InsightType | str | None), agent_id (str | None), min_confidence (float | None), time_range (str), limit (int), applies_to (str | None), category (str | None)
   - Returns: list[Insight]

4. Implement convenience methods:
   - emit_decision(summary, confidence, **kwargs) -> Insight
   - emit_recommendation(summary, confidence, **kwargs) -> Insight
   - emit_blocker(summary, **kwargs) -> Insight
   - emit_lesson(summary, category, **kwargs) -> Insight
   - get(insight_id: str) -> Insight | None (query by ID)
   - list(limit: int = 100) -> list[Insight] (all recent insights)

5. Implement context manager protocol:
   - __enter__ returns self
   - __exit__ closes querier

## Output Format
Provide clean Python code with:
- Proper type hints using | for unions (Python 3.10+ style)
- Docstrings with usage examples
- __all__ export list
"""

HANDOFFS_API_TASK = """
Create a new API facade module that exposes A2A-style naming for the Handoffs API.

## Goal
Provide A2A-compatible method names (handoffs.create, handoffs.get) while preserving
backward compatibility with existing HandoffManager/HandoffReceiver classes.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/api/handoffs.py
- Must import from contextcore.agent.handoff (HandoffManager, HandoffReceiver, Handoff, etc.)
- A2A uses tasks.get, tasks.cancel patterns

## Requirements

1. Create HandoffsAPI class with:
   - __init__(project_id: str, agent_id: str, namespace: str = "default", storage_type: str | None = None)
   - Internal _manager: HandoffManager instance
   - Internal _receiver: HandoffReceiver | None (created lazily)

2. Implement create() method (maps to HandoffManager.create_handoff):
   - Parameters: to_agent (str), capability_id (str), task (str), inputs (dict), expected_output (ExpectedOutput | dict), priority (HandoffPriority | str), timeout_ms (int)
   - Returns: str (handoff_id)
   - Handle expected_output as dict or ExpectedOutput

3. Implement get() method (maps to HandoffManager.get_handoff_status):
   - Parameters: handoff_id (str)
   - Returns: HandoffResult

4. Implement await_result() method (maps to HandoffManager.await_result):
   - Parameters: handoff_id (str), timeout_ms (int), poll_interval_ms (int)
   - Returns: HandoffResult

5. Implement send() convenience method:
   - Parameters: same as create()
   - Creates handoff and immediately awaits result
   - Returns: HandoffResult

6. Implement cancel() method (NEW):
   - Parameters: handoff_id (str)
   - Updates status to CANCELLED
   - Returns: bool (success)

7. Implement receiver methods (creates _receiver lazily):
   - subscribe(capabilities: list[str], poll_interval_s: float) -> Generator[Handoff]
   - accept(handoff_id: str) -> None
   - complete(handoff_id: str, result_trace_id: str) -> None
   - fail(handoff_id: str, reason: str) -> None

## Output Format
Provide clean Python code with:
- Proper type hints
- Docstrings with usage examples
- __all__ export list
"""

SKILLS_API_TASK = """
Create a new API facade module that exposes A2A-style naming for the Skills API.

## Goal
Provide A2A-compatible method names (skills.emit, skills.query, capabilities.invoke)
while preserving backward compatibility with existing emitter/querier classes.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/api/skills.py
- Must import from contextcore.skill (SkillCapabilityEmitter, models)
- A2A uses agent.getExtendedAgentCard pattern

## Requirements

1. Create SkillsAPI class with:
   - __init__(agent_id: str, session_id: str | None = None, project_id: str | None = None)
   - Internal _emitter: SkillCapabilityEmitter instance

2. Implement emit() method (maps to emit_skill_with_capabilities):
   - Parameters: manifest (SkillManifest), capabilities (list[SkillCapability])
   - Returns: tuple[str, list[str]] (trace_id, span_ids)

3. Implement emit_manifest() method (maps to emit_skill):
   - Parameters: manifest (SkillManifest)
   - Returns: str (trace_id)

4. Implement query() method (placeholder for SkillCapabilityQuerier):
   - Parameters: trigger (str | None), category (str | None), budget (int | None), audience (str | None), min_confidence (float | None)
   - Returns: list[SkillCapability]
   - Note: Implementation depends on existing querier or stub

5. Implement get() method:
   - Parameters: skill_id (str)
   - Returns: SkillManifest | None

6. Implement list() method:
   - Returns: list[SkillManifest]

7. Create CapabilitiesAPI nested class with:
   - emit(skill_id: str, capability: SkillCapability, parent_trace_id: str | None) -> str
   - invoke(skill_id: str, capability_id: str, inputs: dict | None, handoff_id: str | None) -> str
   - complete(skill_id: str, capability_id: str, outputs: dict | None, duration_ms: int | None) -> str
   - fail(skill_id: str, capability_id: str, error: str, duration_ms: int | None) -> str

8. Expose capabilities as property:
   - skills.capabilities.invoke(...)

## Output Format
Provide clean Python code with:
- Proper type hints
- Docstrings with usage examples
- __all__ export list
"""

API_PACKAGE_TASK = """
Create the unified API package that exports all A2A-style facades.

## Goal
Provide a single entry point for all ContextCore APIs with A2A-compatible naming,
enabling clean usage like: api.insights.emit(), api.handoffs.create(), api.skills.query()

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/api/__init__.py
- Must import from the facade modules created in this feature group

## Requirements

1. Import and re-export all API classes:
   - InsightsAPI from .insights
   - HandoffsAPI from .handoffs
   - SkillsAPI from .skills

2. Create factory functions:
   - create_insights_api(project_id: str, agent_id: str, **kwargs) -> InsightsAPI
   - create_handoffs_api(project_id: str, agent_id: str, **kwargs) -> HandoffsAPI
   - create_skills_api(agent_id: str, **kwargs) -> SkillsAPI

3. Create unified ContextCoreAPI class:
   ```python
   class ContextCoreAPI:
       def __init__(
           self,
           project_id: str,
           agent_id: str,
           session_id: str | None = None,
           tempo_url: str = "http://localhost:3200",
           namespace: str = "default",
       ):
           self.insights = InsightsAPI(project_id, agent_id, tempo_url)
           self.handoffs = HandoffsAPI(project_id, agent_id, namespace)
           self.skills = SkillsAPI(agent_id, session_id, project_id)

       def __enter__(self) -> "ContextCoreAPI":
           return self

       def __exit__(self, *args) -> None:
           self.insights._querier.close()
   ```

4. Add comprehensive docstring with usage example:
   ```python
   '''
   Unified API for ContextCore with A2A-compatible naming.

   Example:
       from contextcore.api import ContextCoreAPI

       with ContextCoreAPI(project_id="checkout", agent_id="claude-code") as api:
           # Emit an insight
           api.insights.emit(
               type="decision",
               summary="Selected event-driven architecture",
               confidence=0.92
           )

           # Create a handoff
           result = api.handoffs.send(
               to_agent="o11y",
               capability_id="investigate_error",
               task="Find root cause of latency spike",
               inputs={"time_range": "2h"},
               expected_output={"type": "analysis", "fields": ["root_cause"]}
           )

           # Query skills
           skills = api.skills.query(trigger="format")
   '''
   ```

5. Export __all__ with all public names

## Output Format
Provide clean Python code with:
- Proper type hints
- Comprehensive docstrings
- __all__ export list
"""

NAMING_FEATURES = [
    Feature(
        task=INSIGHTS_API_TASK,
        name="Naming_InsightsAPI",
        output_subdir="a2a/naming",
    ),
    Feature(
        task=HANDOFFS_API_TASK,
        name="Naming_HandoffsAPI",
        output_subdir="a2a/naming",
    ),
    Feature(
        task=SKILLS_API_TASK,
        name="Naming_SkillsAPI",
        output_subdir="a2a/naming",
    ),
    Feature(
        task=API_PACKAGE_TASK,
        name="Naming_APIPackage",
        output_subdir="a2a/naming",
    ),
]
