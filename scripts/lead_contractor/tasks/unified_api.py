"""
Phase 2: API Facade tasks for unified alignment plan.

Tasks:
- 2.1: Insights API Facade
- 2.2: Handoffs API Facade
- 2.3: Skills API Facade
- 2.4: API Package Init
"""

from ..runner import Feature

INSIGHTS_API_TASK = """
Create a new facade module that exposes A2A-style naming for the Insights API.

## Goal
Provide a modern API surface using resource.action naming pattern while maintaining
backward compatibility with existing InsightEmitter and InsightQuerier classes.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/api/insights.py
- Must use dual-emit layer from src/contextcore/compat/otel_genai.py
- Existing code: src/contextcore/agent/insights.py

## Requirements

1. Create InsightsAPI class:
   ```python
   class InsightsAPI:
       '''A2A-style API for agent insights.

       Example:
           api = InsightsAPI(project_id="checkout", agent_id="claude")
           api.emit(type="decision", summary="Chose X over Y", confidence=0.9)
           decisions = api.query(type="decision", time_range="7d")
       '''

       def __init__(
           self,
           project_id: str,
           agent_id: str,
           tempo_url: str | None = None,
       ):
           self._emitter = InsightEmitter(project_id, agent_id)
           self._querier = InsightQuerier(tempo_url)
           self._dual_emit = DualEmitAttributes()
   ```

2. Implement methods that map to existing functionality:
   - emit(type, summary, confidence, evidence, ...) → InsightEmitter.emit()
   - query(project_id, type, time_range, ...) → InsightQuerier.query()
   - get(insight_id) → new method to fetch single insight by ID
   - list(project_id, limit) → alias for query with minimal filters

3. Ensure all span emissions use DualEmitAttributes.transform()

4. Add deprecation warnings when InsightEmitter/InsightQuerier are used directly:
   ```python
   # In insights.py
   class InsightEmitter:
       def __init__(self, ...):
           warnings.warn(
               "InsightEmitter is deprecated, use InsightsAPI instead",
               DeprecationWarning,
               stacklevel=2
           )
   ```

5. Export both old and new APIs from module

## Output Format
Provide clean Python code with:
- Type hints throughout
- Docstrings with usage examples
- Integration with dual-emit layer
- __all__ export list
"""

HANDOFFS_API_TASK = """
Create a new facade module that exposes A2A-style naming for the Handoffs API.

## Goal
Provide a modern API surface using resource.action naming pattern for agent-to-agent
handoffs, mapping to existing HandoffManager and HandoffReceiver functionality.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/api/handoffs.py
- Must use dual-emit layer from src/contextcore/compat/otel_genai.py
- Existing code: src/contextcore/agent/handoff.py

## Requirements

1. Create HandoffsAPI class:
   ```python
   class HandoffsAPI:
       '''A2A-style API for agent handoffs.

       Example:
           api = HandoffsAPI(project_id="checkout", agent_id="claude")
           handoff = api.create(
               to_agent="o11y-agent",
               capability_id="investigate",
               task="Find root cause of latency spike",
               inputs={"trace_id": "abc123"}
           )
           result = api.await_(handoff.id, timeout_ms=30000)
       '''

       def __init__(
           self,
           project_id: str,
           agent_id: str,
           storage: HandoffStorage | None = None,
       ):
           self._manager = HandoffManager(project_id, agent_id, storage)
           self._receiver = HandoffReceiver(agent_id, storage)
           self._dual_emit = DualEmitAttributes()
   ```

2. Implement client-side methods (HandoffManager mapping):
   - create(to_agent, capability_id, task, inputs, ...) → create_handoff()
   - get(handoff_id) → get_handoff_status()
   - await_(handoff_id, timeout_ms) → await_result()  # Note: await_ to avoid keyword
   - cancel(handoff_id) → new method to cancel pending handoff
   - send(to_agent, capability_id, task, inputs, timeout_ms) → create() + await_() combined

3. Implement server-side methods (HandoffReceiver mapping):
   - accept(handoff_id) → accept()
   - complete(handoff_id, result_trace_id) → complete()
   - fail(handoff_id, reason) → fail()
   - subscribe(project_id) → poll_handoffs() as generator

4. Ensure all span emissions use DualEmitAttributes.transform()

5. Add deprecation warnings for direct HandoffManager/HandoffReceiver usage

## Output Format
Provide clean Python code with:
- Type hints throughout
- Docstrings with usage examples
- Integration with dual-emit layer
- __all__ export list
"""

SKILLS_API_TASK = """
Create a new facade module that exposes A2A-style naming for the Skills API.

## Goal
Provide a modern API surface using resource.action naming pattern for skill
registration and invocation, mapping to existing SkillCapabilityEmitter/Querier.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/api/skills.py
- Must use dual-emit layer from src/contextcore/compat/otel_genai.py
- Existing code: src/contextcore/skill/

## Requirements

1. Create SkillsAPI class:
   ```python
   class SkillsAPI:
       '''A2A-style API for agent skills.

       Example:
           api = SkillsAPI(agent_id="claude-code")

           # Register skill
           api.emit(manifest=my_manifest, capabilities=[cap1, cap2])

           # Query skills
           matching = api.query(trigger="format code", budget_tokens=1000)

           # Invoke capability
           api.capabilities.invoke("skill-1", "format", inputs={"code": "..."})
       '''

       def __init__(
           self,
           agent_id: str,
           tempo_url: str | None = None,
       ):
           self._emitter = SkillCapabilityEmitter(agent_id)
           self._querier = SkillCapabilityQuerier(tempo_url)
           self.capabilities = CapabilitiesAPI(self._emitter)
   ```

2. Implement skill-level methods:
   - emit(manifest, capabilities) → emit_skill_with_capabilities()
   - query(trigger, category, budget_tokens) → querier methods
   - get(skill_id) → fetch single skill manifest
   - list() → list all registered skills

3. Create nested CapabilitiesAPI class:
   ```python
   class CapabilitiesAPI:
       def emit(self, skill_id, capability) → emit_capability()
       def invoke(self, skill_id, capability_id, inputs) → emit_invoked()
       def complete(self, skill_id, capability_id, outputs) → emit_succeeded()
       def fail(self, skill_id, capability_id, error) → emit_failed()
   ```

4. Ensure all span emissions use DualEmitAttributes.transform()

## Output Format
Provide clean Python code with:
- Type hints throughout
- Docstrings with usage examples
- Integration with dual-emit layer
- __all__ export list
"""

API_PACKAGE_TASK = """
Create the unified API package that exports all facades.

## Goal
Create a package init file that exports all API facades and provides a unified
ContextCoreAPI class that combines insights, handoffs, and skills APIs.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/api/__init__.py
- Must export InsightsAPI, HandoffsAPI, SkillsAPI

## Requirements

1. Export all API classes

2. Create convenience factory functions:
   ```python
   def create_insights_api(project_id: str, agent_id: str, **kwargs) -> InsightsAPI:
       '''Create configured InsightsAPI instance.'''
       return InsightsAPI(project_id=project_id, agent_id=agent_id, **kwargs)

   def create_handoffs_api(project_id: str, agent_id: str, **kwargs) -> HandoffsAPI:
       '''Create configured HandoffsAPI instance.'''
       return HandoffsAPI(project_id=project_id, agent_id=agent_id, **kwargs)

   def create_skills_api(agent_id: str, **kwargs) -> SkillsAPI:
       '''Create configured SkillsAPI instance.'''
       return SkillsAPI(agent_id=agent_id, **kwargs)
   ```

3. Create unified ContextCoreAPI class:
   ```python
   class ContextCoreAPI:
       '''Unified API for all ContextCore agent operations.

       Example:
           api = ContextCoreAPI(project_id="checkout", agent_id="claude-code")

           # Emit insight
           api.insights.emit(type="decision", summary="...", confidence=0.9)

           # Create handoff
           handoff = api.handoffs.create(
               to_agent="o11y",
               capability_id="investigate",
               task="Find root cause"
           )

           # Query skills
           skills = api.skills.query(trigger="format")
       '''

       def __init__(
           self,
           project_id: str,
           agent_id: str,
           tempo_url: str | None = None,
           storage: HandoffStorage | None = None,
       ):
           self.insights = InsightsAPI(project_id, agent_id, tempo_url)
           self.handoffs = HandoffsAPI(project_id, agent_id, storage)
           self.skills = SkillsAPI(agent_id, tempo_url)
           self.project_id = project_id
           self.agent_id = agent_id
   ```

4. Add module docstring with comprehensive usage examples

## Output Format
Provide clean Python code with:
- All exports in __all__
- Type hints
- Comprehensive docstrings
"""

API_FEATURES = [
    Feature(
        task=INSIGHTS_API_TASK,
        name="API_InsightsAPI",
        output_subdir="unified/phase2",
    ),
    Feature(
        task=HANDOFFS_API_TASK,
        name="API_HandoffsAPI",
        output_subdir="unified/phase2",
    ),
    Feature(
        task=SKILLS_API_TASK,
        name="API_SkillsAPI",
        output_subdir="unified/phase2",
    ),
    Feature(
        task=API_PACKAGE_TASK,
        name="API_Package",
        output_subdir="unified/phase2",
    ),
]
