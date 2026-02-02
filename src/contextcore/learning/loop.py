"""Integration point for agent learning loop.

This module provides the LearningLoop class that integrates lesson
emission and retrieval into agent work sessions.
"""

__all__ = ["LearningLoop"]

from typing import Callable, List, Optional

from contextcore.learning.emitter import LessonEmitter
from contextcore.learning.models import Lesson, LessonCategory, LessonQuery, LessonSource
from contextcore.learning.retriever import LessonRetriever


class LearningLoop:
    """Integrate learning into agent work sessions.

    The LearningLoop provides a high-level interface for the complete
    learning cycle:

    1. Before starting work: Query relevant lessons
    2. During work: Apply lessons to avoid mistakes
    3. After work: Emit new lessons learned

    Example:
        loop = LearningLoop(project_id="my-project", agent_id="claude-code")

        # Before starting work
        lessons = loop.before_task(
            task_type="testing",
            files=["src/auth/oauth.py"]
        )
        for lesson in lessons:
            print(f"Tip: {lesson.summary}")

        # Do work...

        # After completing work
        if encountered_blocker:
            loop.after_task_blocker(
                blocker="OAuth token refresh failed in tests",
                resolution="Mock the token refresh endpoint in conftest.py",
                affected_files=["tests/conftest.py", "src/auth/oauth.py"]
            )

        # Record feedback on lessons that were helpful
        if helpful_lesson:
            loop.record_lesson_success(helpful_lesson.id, "Used in test_oauth.py")
    """

    def __init__(
        self,
        project_id: str,
        agent_id: str,
        tempo_url: str = "http://localhost:3200",
    ) -> None:
        """Initialize the learning loop.

        Args:
            project_id: The project this loop is associated with
            agent_id: Identifier for the agent
            tempo_url: URL of the Tempo instance for lesson storage
        """
        self.project_id = project_id
        self.emitter = LessonEmitter(project_id, agent_id)
        self.retriever = LessonRetriever(tempo_url)

    def before_task(
        self,
        task_type: str,
        files: Optional[List[str]] = None,
        custom_query: Optional[Callable] = None,
    ) -> List[Lesson]:
        """Retrieve relevant lessons before starting a task.

        This method queries for lessons that may help with the upcoming task,
        including:
        - Task-type specific lessons (e.g., testing, debugging)
        - File-specific lessons for files that will be modified
        - High-confidence global lessons

        Args:
            task_type: Type of task (testing, debugging, refactoring, etc.)
            files: Files that will be modified
            custom_query: Optional custom query function

        Returns:
            Relevant lessons sorted by effectiveness
        """
        lessons: List[Lesson] = []

        # Get task-type lessons
        task_lessons = self.retriever.get_lessons_for_task(task_type, self.project_id)
        lessons.extend(task_lessons)

        # Get file-specific lessons
        if files:
            for file_path in files:
                file_lessons = self.retriever.get_lessons_for_file(
                    file_path, self.project_id
                )
                lessons.extend(file_lessons)

        # Get global lessons
        global_lessons = self.retriever.get_global_lessons(min_confidence=0.9)
        lessons.extend(global_lessons)

        # Deduplicate by lesson ID
        seen_ids: set = set()
        unique_lessons: List[Lesson] = []
        for lesson in lessons:
            if lesson.id not in seen_ids:
                seen_ids.add(lesson.id)
                unique_lessons.append(lesson)

        # Sort by effectiveness
        unique_lessons.sort(key=lambda l: l.effectiveness_score, reverse=True)

        return unique_lessons[:10]

    def after_task_blocker(
        self,
        blocker: str,
        resolution: str,
        affected_files: List[str],
        confidence: float = 0.9,
    ) -> Lesson:
        """Record a lesson from resolving a blocker.

        Call this after successfully resolving a blocker during work.
        The lesson will help future sessions avoid or quickly resolve
        similar blockers.

        Args:
            blocker: Description of what the blocker was
            resolution: How the blocker was resolved
            affected_files: Files that were involved
            confidence: Confidence in this lesson

        Returns:
            The created Lesson object
        """
        return self.emitter.emit_blocker_resolution(
            blocker_summary=blocker,
            resolution=resolution,
            applies_to=affected_files,
            confidence=confidence,
        )

    def after_task_discovery(
        self,
        pattern_name: str,
        description: str,
        affected_files: List[str],
        code_example: str,
        anti_pattern: Optional[str] = None,
    ) -> Lesson:
        """Record a pattern discovery.

        Call this when you discover a useful pattern during work.
        The pattern will be suggested to future sessions working on
        similar files.

        Args:
            pattern_name: Name of the discovered pattern
            description: Description of when/how to use the pattern
            affected_files: Files where this pattern applies
            code_example: Example code showing the pattern
            anti_pattern: Example of what NOT to do

        Returns:
            The created Lesson object
        """
        return self.emitter.emit_pattern_discovery(
            pattern_name=pattern_name,
            description=description,
            applies_to=affected_files,
            code_example=code_example,
            anti_pattern=anti_pattern,
        )

    def after_task_general(
        self,
        summary: str,
        category: LessonCategory,
        affected_files: List[str],
        context: str = "",
        is_global: bool = False,
    ) -> Lesson:
        """Record a general lesson.

        Use this for lessons that don't fit the blocker or pattern
        categories.

        Args:
            summary: Brief description of the lesson
            category: Category for the lesson
            affected_files: Files this lesson applies to
            context: Extended description
            is_global: Whether this applies globally

        Returns:
            The created Lesson object
        """
        return self.emitter.emit_lesson(
            summary=summary,
            category=category,
            source=LessonSource.PATTERN_DISCOVERED,
            applies_to=affected_files,
            confidence=0.8,
            context=context,
            global_lesson=is_global,
        )

    def after_task_error(
        self,
        error_type: str,
        fix_description: str,
        affected_files: List[str],
        code_example: Optional[str] = None,
    ) -> Lesson:
        """Record a lesson from fixing an error.

        Call this after fixing a recurring or tricky error.

        Args:
            error_type: Type of error that was fixed
            fix_description: How the error was fixed
            affected_files: Files involved in the fix
            code_example: Example code showing the fix

        Returns:
            The created Lesson object
        """
        return self.emitter.emit_lesson(
            summary=f"Fix: {error_type}",
            category=LessonCategory.ERROR_HANDLING,
            source=LessonSource.ERROR_FIXED,
            applies_to=affected_files,
            confidence=0.9,
            context=fix_description,
            code_example=code_example,
        )

    def record_human_guidance(
        self,
        guidance: str,
        category: LessonCategory,
        affected_files: List[str],
        context: str = "",
        is_global: bool = False,
    ) -> Lesson:
        """Record guidance provided by a human.

        Use this when a human provides guidance that should be
        remembered for future sessions.

        Args:
            guidance: The guidance provided
            category: Category for the lesson
            affected_files: Files this applies to
            context: Additional context
            is_global: Whether this applies globally

        Returns:
            The created Lesson object
        """
        return self.emitter.emit_lesson(
            summary=guidance,
            category=category,
            source=LessonSource.HUMAN_GUIDANCE,
            applies_to=affected_files,
            confidence=1.0,
            context=context,
            global_lesson=is_global,
        )

    def record_lesson_success(self, lesson_id: str, context: str) -> None:
        """Record that a retrieved lesson was helpful.

        Call this when a lesson from before_task() was actually helpful.
        This improves the lesson's effectiveness score for future retrieval.

        Args:
            lesson_id: ID of the lesson that was helpful
            context: How/where the lesson was applied
        """
        self.emitter.record_application(lesson_id, success=True, context=context)

    def record_lesson_failure(
        self, lesson_id: str, context: str, feedback: str
    ) -> None:
        """Record that a retrieved lesson was not helpful.

        Call this when a lesson from before_task() was not helpful or
        was misleading. This decreases the lesson's effectiveness score.

        Args:
            lesson_id: ID of the lesson
            context: How/where the lesson was tried
            feedback: Why the lesson wasn't helpful
        """
        self.emitter.record_application(
            lesson_id, success=False, context=context, feedback=feedback
        )

    def get_project_lessons(self, max_results: int = 20) -> List[Lesson]:
        """Get all lessons for this project.

        Args:
            max_results: Maximum number of lessons to return

        Returns:
            List of lessons for this project
        """
        query = LessonQuery(
            project_id=self.project_id,
            include_global=False,
            max_results=max_results,
        )
        return self.retriever.retrieve(query)

    def get_recent_lessons(self, hours: int = 24) -> List[Lesson]:
        """Get recent lessons from this project.

        Args:
            hours: Number of hours to look back

        Returns:
            List of recent lessons
        """
        query = LessonQuery(
            project_id=self.project_id,
            time_range=f"{hours}h",
        )
        return self.retriever.retrieve(query)
