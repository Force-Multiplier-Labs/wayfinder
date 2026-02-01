"""
Agent Learning module for ContextCore.

This module enables agents to learn from past work by storing lessons as
OpenTelemetry spans and retrieving relevant lessons before starting new work,
creating a continuous improvement loop.

Example:
    from contextcore.learning import LearningLoop

    loop = LearningLoop(project_id="my-project", agent_id="claude-code")

    # Before starting work - get relevant lessons
    lessons = loop.before_task(task_type="testing", files=["src/auth/oauth.py"])
    for lesson in lessons:
        print(f"Tip: {lesson.summary}")

    # After work - emit lessons learned
    if encountered_blocker:
        loop.after_task_blocker(
            blocker="OAuth token refresh failed in tests",
            resolution="Mock the token refresh endpoint in conftest.py",
            affected_files=["tests/conftest.py", "src/auth/oauth.py"]
        )
"""

__all__ = [
    # Models
    "LessonCategory",
    "LessonSource",
    "Lesson",
    "LessonQuery",
    "LessonApplication",
    # Emitter
    "LessonEmitter",
    # Retriever
    "LessonRetriever",
    # Loop
    "LearningLoop",
]


def __getattr__(name: str):
    """Lazy import for learning components."""
    if name in ("LessonCategory", "LessonSource", "Lesson", "LessonQuery", "LessonApplication"):
        from contextcore.learning.models import (
            LessonCategory,
            LessonSource,
            Lesson,
            LessonQuery,
            LessonApplication,
        )

        return {
            "LessonCategory": LessonCategory,
            "LessonSource": LessonSource,
            "Lesson": Lesson,
            "LessonQuery": LessonQuery,
            "LessonApplication": LessonApplication,
        }[name]

    if name == "LessonEmitter":
        from contextcore.learning.emitter import LessonEmitter

        return LessonEmitter

    if name == "LessonRetriever":
        from contextcore.learning.retriever import LessonRetriever

        return LessonRetriever

    if name == "LearningLoop":
        from contextcore.learning.loop import LearningLoop

        return LearningLoop

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
