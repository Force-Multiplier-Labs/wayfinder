"""
Lesson Emitter module for ContextCore.

Emits lessons as OpenTelemetry spans for storage in Tempo, enabling
persistent learning across agent sessions.
"""

from opentelemetry import trace
from opentelemetry.trace import SpanKind
from typing import List, Optional
import uuid

from contextcore.learning.models import Lesson, LessonCategory, LessonSource

__all__ = ['LessonEmitter']


class LessonEmitter:
    """
    Emits lessons as OpenTelemetry spans for persistent learning storage.
    
    This class creates structured telemetry spans that can be stored in Tempo
    and queried later to provide context across agent sessions.
    """

    def __init__(self, project_id: str, agent_id: str, session_id: Optional[str] = None):
        """
        Initialize the lesson emitter.
        
        Args:
            project_id: Unique identifier for the project
            agent_id: Unique identifier for the agent
            session_id: Optional session identifier, defaults to empty string
        """
        self.project_id = project_id
        self.agent_id = agent_id
        self.session_id = session_id if session_id is not None else ""
        
        # Initialize OpenTelemetry tracer for contextcore.learning namespace
        self._tracer = trace.get_tracer("contextcore.learning")

    def emit_lesson(
        self,
        summary: str,
        category: LessonCategory,
        source: LessonSource,
        applies_to: List[str],
        confidence: float,
        context: str,
        code_example: Optional[str] = None,
        anti_pattern: Optional[str] = None,
        global_lesson: bool = False
    ) -> Lesson:
        """
        Emit a lesson as an OpenTelemetry span.
        
        Args:
            summary: Brief description of the lesson learned
            category: Type of lesson (from LessonCategory enum)
            source: How the lesson was discovered (from LessonSource enum)
            applies_to: List of contexts where this lesson applies
            confidence: Confidence level (0.0-1.0), will be clamped to valid range
            context: Detailed context or description
            code_example: Optional code example demonstrating the lesson
            anti_pattern: Optional example of what not to do
            global_lesson: If True, lesson applies across projects
            
        Returns:
            Lesson object with generated ID and provided attributes
        """
        # Clamp confidence to valid range [0.0, 1.0]
        confidence = max(0.0, min(1.0, confidence))
        
        # Generate unique lesson identifier
        lesson_id = str(uuid.uuid4())
        
        # Build span attributes following OpenTelemetry semantic conventions
        attributes = {
            "insight.type": "lesson",
            "lesson.id": lesson_id,
            "lesson.summary": summary,
            "lesson.category": category.value,
            "lesson.source": source.value,
            "lesson.applies_to": applies_to,  # OpenTelemetry handles list serialization
            "lesson.is_global": global_lesson,
            "lesson.confidence": confidence,
            "lesson.context": context,
            "agent.id": self.agent_id,
            "agent.session_id": self.session_id,
        }
        
        # Add optional attributes if provided
        if code_example is not None:
            attributes["lesson.code_example"] = code_example
        if anti_pattern is not None:
            attributes["lesson.anti_pattern"] = anti_pattern
            
        # Only include project.id for non-global lessons
        if not global_lesson:
            attributes["project.id"] = self.project_id

        # Create and populate the telemetry span
        with self._tracer.start_span("lesson.emit", kind=SpanKind.INTERNAL) as span:
            span.set_attributes(attributes)
            span.add_event("lesson_created")

        # Return structured lesson object
        return Lesson(
            id=lesson_id,
            summary=summary,
            category=category,
            source=source,
            applies_to=applies_to,
            confidence=confidence,
            context=context,
            code_example=code_example,
            anti_pattern=anti_pattern
        )

    def emit_blocker_resolution(
        self,
        blocker_summary: str,
        resolution: str,
        applies_to: List[str],
        confidence: float = 0.9
    ) -> Lesson:
        """
        Convenience method for emitting blocker resolution lessons.
        
        Args:
            blocker_summary: Description of the blocker that was resolved
            resolution: How the blocker was resolved
            applies_to: List of contexts where this resolution applies
            confidence: Confidence level, defaults to 0.9
            
        Returns:
            Lesson object for the blocker resolution
        """
        return self.emit_lesson(
            summary=blocker_summary,
            category=LessonCategory.BLOCKER_RESOLUTION,
            source=LessonSource.CODE_ANALYSIS,
            applies_to=applies_to,
            confidence=confidence,
            context=resolution
        )

    def emit_pattern_discovery(
        self,
        pattern_name: str,
        description: str,
        applies_to: List[str],
        code_example: Optional[str] = None,
        anti_pattern: Optional[str] = None
    ) -> Lesson:
        """
        Convenience method for emitting pattern discovery lessons.
        
        Args:
            pattern_name: Name of the discovered pattern
            description: Detailed description of the pattern
            applies_to: List of contexts where this pattern applies
            code_example: Optional code example showing the pattern
            anti_pattern: Optional example of the anti-pattern
            
        Returns:
            Lesson object for the pattern discovery
        """
        return self.emit_lesson(
            summary=pattern_name,
            category=LessonCategory.PATTERN_DISCOVERY,
            source=LessonSource.CODE_ANALYSIS,
            applies_to=applies_to,
            confidence=1.0,  # Pattern discoveries are typically high confidence
            context=description,
            code_example=code_example,
            anti_pattern=anti_pattern
        )

    def record_application(
        self,
        lesson_id: str,
        success: bool,
        context: str,
        feedback: Optional[str] = None
    ) -> None:
        """
        Record the application of a lesson for tracking effectiveness.
        
        Args:
            lesson_id: ID of the lesson that was applied
            success: Whether the lesson application was successful
            context: Context in which the lesson was applied
            feedback: Optional feedback about the application
        """
        attributes = {
            "lesson.id": lesson_id,
            "lesson.applied": success,  # OpenTelemetry handles boolean serialization
            "lesson.success": success,
            "lesson.application_context": context,
        }
        
        # Add feedback if provided
        if feedback is not None:
            attributes["lesson.feedback"] = feedback

        # Create span to track lesson application
        with self._tracer.start_span("lesson.applied", kind=SpanKind.INTERNAL) as span:
            span.set_attributes(attributes)
