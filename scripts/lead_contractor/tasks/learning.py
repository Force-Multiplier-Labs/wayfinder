"""
Agent Learning Loop feature tasks for Lead Contractor workflow.
"""

from ..runner import Feature

LEARNING_MODELS_TASK = """
Implement the Agent Learning Models module for ContextCore.

## Goal
Define data models for the agent learning system that stores and retrieves
lessons learned during agent work sessions.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/learning/models.py
- Uses dataclasses and enums, Python 3.9+
- Lessons are stored as OpenTelemetry spans in Tempo

## Requirements
1. Create LessonCategory enum with values:
   - ARCHITECTURE, TESTING, DEBUGGING, PERFORMANCE, SECURITY
   - DEPLOYMENT, DOCUMENTATION, REFACTORING, ERROR_HANDLING, INTEGRATION

2. Create LessonSource enum with values:
   - BLOCKER_RESOLVED: Learned from fixing a blocker
   - ERROR_FIXED: Learned from fixing an error
   - PATTERN_DISCOVERED: Discovered a reusable pattern
   - REVIEW_FEEDBACK: Learned from code review
   - HUMAN_GUIDANCE: Human provided the lesson
   - DOCUMENTATION: Extracted from documentation

3. Create Lesson dataclass with:
   - id: str (unique identifier)
   - summary: str (1-2 sentence description)
   - category: LessonCategory
   - source: LessonSource
   - applies_to: List[str] (file patterns like "src/auth/**", "*.test.py")
   - project_id: Optional[str] (None for global lessons)
   - confidence: float (0.0-1.0)
   - validated_by_human: bool (default False)
   - success_count: int (times applied successfully, default 0)
   - failure_count: int (times didn't help, default 0)
   - context: str (extended description, default "")
   - code_example: Optional[str]
   - anti_pattern: Optional[str] (what NOT to do)
   - agent_id: str (default "")
   - trace_id: str (default "")
   - created_at: datetime
   - expires_at: Optional[datetime]
   - @property effectiveness_score: float (success_count / total * confidence, or just confidence if no usage)

4. Create LessonQuery dataclass with:
   - project_id: Optional[str]
   - file_pattern: Optional[str]
   - category: Optional[LessonCategory]
   - min_confidence: float (default 0.5)
   - include_global: bool (default True)
   - max_results: int (default 10)
   - time_range: str (default "30d", e.g., "1h", "7d", "30d")

5. Create LessonApplication dataclass with:
   - lesson_id: str
   - applied_at: datetime
   - context: str (where/how applied)
   - success: bool
   - feedback: Optional[str]

## Output Format
Provide clean, production-ready Python code with:
- Proper type hints and docstrings
- Default values using field(default_factory=...) for mutable defaults
- __all__ export list
"""

LEARNING_EMITTER_TASK = """
Implement the Lesson Emitter module for ContextCore.

## Goal
Emit lessons as OpenTelemetry spans for storage in Tempo, enabling
persistent learning across agent sessions.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/learning/emitter.py
- Uses OpenTelemetry SDK for span creation
- Imports models from contextcore.learning.models

## Requirements
1. Create LessonEmitter class with:
   - __init__(project_id: str, agent_id: str, session_id: Optional[str] = None)
   - project_id, agent_id, session_id attributes
   - _tracer from trace.get_tracer("contextcore.learning")

2. Implement emit_lesson() method:
   - Parameters: summary, category (LessonCategory), source (LessonSource),
     applies_to (List[str]), confidence (float), context (str),
     code_example (Optional[str]), anti_pattern (Optional[str]),
     global_lesson (bool)
   - Create span with name "lesson.emit", kind=SpanKind.INTERNAL
   - Set span attributes:
     - insight.type = "lesson"
     - lesson.id, lesson.summary, lesson.category, lesson.source
     - lesson.applies_to (as list), lesson.is_global
     - lesson.confidence, lesson.context, lesson.code_example, lesson.anti_pattern
     - project.id (if not global), agent.id, agent.session_id
   - Add event "lesson_created"
   - Return Lesson object

3. Implement convenience methods:
   - emit_blocker_resolution(blocker_summary, resolution, applies_to, confidence=0.9) -> Lesson
   - emit_pattern_discovery(pattern_name, description, applies_to, code_example, anti_pattern) -> Lesson

4. Implement record_application(lesson_id, success, context, feedback) -> None:
   - Create span "lesson.applied"
   - Set attributes: lesson.id, lesson.applied, lesson.success, lesson.application_context, lesson.feedback

## Output Format
Provide clean, production-ready Python code with:
- from opentelemetry import trace
- from opentelemetry.trace import SpanKind
- Proper type hints and docstrings
- __all__ export list
"""

LEARNING_RETRIEVER_TASK = """
Implement the Lesson Retriever module for ContextCore.

## Goal
Query lessons from Tempo using TraceQL for agent work sessions,
enabling continuous learning from past experiences.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/learning/retriever.py
- Uses HTTP requests to Tempo's API
- Imports models from contextcore.learning.models

## Requirements
1. Create LessonRetriever class with:
   - __init__(tempo_url: str = "http://localhost:3200")
   - tempo_url attribute (strip trailing slash)

2. Implement retrieve(query: LessonQuery) -> List[Lesson]:
   - Build TraceQL query from LessonQuery
   - Execute query against Tempo
   - Parse results into Lesson objects
   - Filter by min_confidence
   - Sort by effectiveness_score descending
   - Return top max_results

3. Implement convenience methods:
   - get_lessons_for_file(file_path, project_id, category) -> List[Lesson]
   - get_lessons_for_task(task_type, project_id) -> List[Lesson]
     (Map task types to categories: testing->TESTING, debugging->DEBUGGING, etc.)
   - get_global_lessons(category, min_confidence=0.9) -> List[Lesson]

4. Implement _build_traceql(query: LessonQuery) -> str:
   - Start with: span.insight.type = "lesson"
   - Add project.id condition if specified (or include global)
   - Add category condition if specified
   - Add file pattern regex matching for applies_to
   - Return "{ condition1 && condition2 && ... }"

5. Implement _query_tempo(traceql: str, time_range: str) -> List[dict]:
   - Parse time_range to start/end timestamps
   - Make GET request to {tempo_url}/api/search with q, start, end params
   - Return traces list from response

6. Implement _parse_results(raw_results: List[dict]) -> List[Lesson]:
   - Extract spans from traces
   - Parse attributes into Lesson objects
   - Handle applies_to as JSON string

7. Implement _parse_time_range(time_range: str) -> timedelta:
   - Parse "1h", "7d", "30d", "1m" (m=30 days)
   - Default to 7 days

## Output Format
Provide clean, production-ready Python code with:
- Use urllib.request for HTTP (standard library)
- import json for parsing
- Proper error handling with try/except
- __all__ export list
"""

LEARNING_LOOP_TASK = """
Implement the Learning Loop Integration module for ContextCore.

## Goal
Provide a high-level integration class that agents use for the complete
learning loop: query lessons before tasks, emit lessons after tasks.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/learning/loop.py
- Imports from contextcore.learning.emitter and contextcore.learning.retriever
- Designed for easy integration into agent workflows

## Requirements
1. Create LearningLoop class with:
   - __init__(project_id: str, agent_id: str, tempo_url: str = "http://localhost:3200")
   - project_id attribute
   - emitter: LessonEmitter instance
   - retriever: LessonRetriever instance

2. Implement before_task(task_type: str, files: Optional[List[str]], custom_query: Optional[Callable]) -> List[Lesson]:
   - Get task-type lessons
   - Get file-specific lessons for each file
   - Get high-confidence global lessons
   - Deduplicate by lesson.id
   - Sort by effectiveness_score descending
   - Return top 10 lessons

3. Implement after_task methods:
   - after_task_blocker(blocker: str, resolution: str, affected_files: List[str], confidence=0.9) -> Lesson
   - after_task_discovery(pattern_name: str, description: str, affected_files: List[str], code_example: str, anti_pattern: Optional[str]) -> Lesson
   - after_task_general(summary: str, category: LessonCategory, affected_files: List[str], context: str, is_global: bool) -> Lesson

4. Implement feedback methods:
   - record_lesson_success(lesson_id: str, context: str) -> None
   - record_lesson_failure(lesson_id: str, context: str, feedback: str) -> None

5. Include docstring with usage example:
   ```
   loop = LearningLoop(project_id="my-project", agent_id="claude-code")

   # Before starting work
   lessons = loop.before_task(task_type="testing", files=["src/auth/oauth.py"])
   for lesson in lessons:
       print(f"Tip: {lesson.summary}")

   # After completing work
   if encountered_blocker:
       loop.after_task_blocker(
           blocker="OAuth token refresh failed in tests",
           resolution="Mock the token refresh endpoint in conftest.py",
           affected_files=["tests/conftest.py", "src/auth/oauth.py"]
       )
   ```

## Output Format
Provide clean, production-ready Python code with:
- Proper type hints and docstrings
- Clear usage documentation
- __all__ export list
"""

LEARNING_FEATURES = [
    Feature(
        task=LEARNING_MODELS_TASK,
        name="Learning_Models",
        output_subdir="learning",
    ),
    Feature(
        task=LEARNING_EMITTER_TASK,
        name="Learning_Emitter",
        output_subdir="learning",
    ),
    Feature(
        task=LEARNING_RETRIEVER_TASK,
        name="Learning_Retriever",
        output_subdir="learning",
    ),
    Feature(
        task=LEARNING_LOOP_TASK,
        name="Learning_Loop",
        output_subdir="learning",
    ),
]
