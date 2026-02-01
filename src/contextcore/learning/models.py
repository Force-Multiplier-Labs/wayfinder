"""Agent Learning Models module for ContextCore.
__all__ = ['LessonCategory', 'LessonSource', 'Lesson', 'LessonQuery', 'LessonApplication']


This module defines data models for the agent learning system that stores and retrieves
lessons learned during agent work sessions using OpenTelemetry spans in Tempo.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

__all__ = [
    "LessonCategory",
    "LessonSource", 
    "Lesson",
    "LessonQuery",
    "LessonApplication",
]


class LessonCategory(Enum):
    """Categories for classifying lessons learned by agents."""
    ARCHITECTURE = "architecture"
    TESTING = "testing"
    DEBUGGING = "debugging"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DEPLOYMENT = "deployment"
    DOCUMENTATION = "documentation"
    REFACTORING = "refactoring"
    ERROR_HANDLING = "error_handling"
    INTEGRATION = "integration"


class LessonSource(Enum):
    """Sources from which lessons are derived."""
    BLOCKER_RESOLVED = "blocker_resolved"
    ERROR_FIXED = "error_fixed"
    PATTERN_DISCOVERED = "pattern_discovered"
    REVIEW_FEEDBACK = "review_feedback"
    HUMAN_GUIDANCE = "human_guidance"
    DOCUMENTATION = "documentation"


@dataclass(frozen=True)
class Lesson:
    """A lesson learned by an agent during work sessions."""
    
    # Required fields
    id: str
    summary: str
    category: LessonCategory
    source: LessonSource
    confidence: float
    created_at: datetime
    
    # Optional/default fields
    applies_to: List[str] = field(default_factory=list)
    project_id: Optional[str] = None
    validated_by_human: bool = False
    success_count: int = 0
    failure_count: int = 0
    context: str = ""
    code_example: Optional[str] = None
    anti_pattern: Optional[str] = None
    agent_id: str = ""
    trace_id: str = ""
    expires_at: Optional[datetime] = None

    @property
    def effectiveness_score(self) -> float:
        """Calculate effectiveness based on success rate and confidence.
        
        Returns confidence if no usage data, otherwise success rate weighted by confidence.
        """
        total_attempts = self.success_count + self.failure_count
        if total_attempts == 0:
            return self.confidence
        return (self.success_count / total_attempts) * self.confidence


@dataclass(frozen=True)
class LessonQuery:
    """Query parameters for retrieving lessons from storage."""
    
    project_id: Optional[str] = None
    file_pattern: Optional[str] = None
    category: Optional[LessonCategory] = None
    min_confidence: float = 0.5
    include_global: bool = True
    max_results: int = 10
    time_range: str = "30d"  # Format: "1h", "7d", "30d", etc.


@dataclass(frozen=True)
class LessonApplication:
    """Record of a lesson being applied in practice."""
    
    lesson_id: str
    applied_at: datetime
    context: str
    success: bool
    feedback: Optional[str] = None
