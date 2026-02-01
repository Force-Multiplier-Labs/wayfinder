# File: src/contextcore/learning/loop.py
__all__ = ['LearningLoop']


from typing import List, Optional, Callable
from contextcore.learning.emitter import LessonEmitter
from contextcore.learning.retriever import LessonRetriever
from contextcore.types import Lesson, LessonCategory

class LearningLoop:
    """
    A high-level integration class that manages the learning loop workflow for agents.
    
    This class provides simplified methods for retrieving relevant lessons before agent tasks
    and emitting new lessons after task completion.

    Example usage:
    