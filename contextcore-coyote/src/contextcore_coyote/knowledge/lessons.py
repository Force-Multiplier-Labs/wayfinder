"""
Lessons learned knowledge base.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from contextcore_coyote.models import Lesson
from contextcore_coyote.config import get_config

logger = logging.getLogger(__name__)


class LessonsLearned:
    """
    Knowledge base for lessons learned from incidents.

    Stores lessons in a markdown file and optionally emits to ContextCore.
    """

    def __init__(
        self,
        file_path: Optional[str] = None,
        contextcore_enabled: Optional[bool] = None,
    ) -> None:
        """
        Initialize the lessons knowledge base.

        Args:
            file_path: Path to lessons file (default from config)
            contextcore_enabled: Enable ContextCore integration (default from config)
        """
        config = get_config()
        self.file_path = Path(file_path or config.lessons_file)
        self.contextcore_enabled = (
            contextcore_enabled if contextcore_enabled is not None else config.contextcore_enabled
        )
        self._lessons: List[Lesson] = []
        self._load()

    def _load(self) -> None:
        """Load lessons from the file."""
        if not self.file_path.exists():
            return

        # Parse markdown file to extract lessons
        # This is a simplified parser - in production you might use a proper markdown parser
        try:
            content = self.file_path.read_text()
            self._parse_markdown(content)
        except Exception as e:
            logger.warning(f"Failed to load lessons: {e}")

    def _parse_markdown(self, content: str) -> None:
        """Parse lessons from markdown content."""
        # Simple parser - looks for lesson blocks
        # Format expected:
        # ## INC-123: Title
        # **Category**: null-reference
        # **Lesson**: Always validate...
        # **Prevention**: Add null checks...

        current_lesson = None
        current_field = None

        for line in content.split("\n"):
            if line.startswith("## "):
                if current_lesson:
                    self._lessons.append(current_lesson)

                # Parse incident ID from header
                header = line[3:].strip()
                if ":" in header:
                    incident_id, title = header.split(":", 1)
                    current_lesson = Lesson(
                        id=f"{incident_id.strip()}-L{len(self._lessons) + 1}",
                        incident_id=incident_id.strip(),
                        category="unknown",
                        lesson="",
                        prevention="",
                    )
            elif current_lesson:
                if line.startswith("**Category**:"):
                    current_lesson.category = line.split(":", 1)[1].strip()
                elif line.startswith("**Lesson**:"):
                    current_lesson.lesson = line.split(":", 1)[1].strip()
                elif line.startswith("**Prevention**:"):
                    current_lesson.prevention = line.split(":", 1)[1].strip()
                elif line.startswith("**Tags**:"):
                    tags = line.split(":", 1)[1].strip()
                    current_lesson.tags = [t.strip() for t in tags.split(",")]

        if current_lesson:
            self._lessons.append(current_lesson)

    def add(
        self,
        incident_id: str,
        category: str,
        lesson: str,
        prevention: str,
        related_files: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        confidence: float = 0.8,
    ) -> Lesson:
        """
        Add a lesson to the knowledge base.

        Args:
            incident_id: ID of the incident this lesson came from
            category: Category of the lesson
            lesson: The lesson learned
            prevention: How to prevent this in the future
            related_files: Files this lesson applies to
            tags: Searchable tags
            confidence: Confidence score (0-1)

        Returns:
            The created Lesson
        """
        lesson_obj = Lesson(
            id=f"{incident_id}-L{len(self._lessons) + 1}",
            incident_id=incident_id,
            category=category,
            lesson=lesson,
            prevention=prevention,
            related_files=related_files or [],
            tags=tags or [],
            confidence=confidence,
        )

        self._lessons.append(lesson_obj)
        self._save()

        # Emit to ContextCore if enabled
        if self.contextcore_enabled:
            self._emit_to_contextcore(lesson_obj)

        return lesson_obj

    def _save(self) -> None:
        """Save lessons to the markdown file."""
        lines = ["# Lessons Learned\n"]
        lines.append("Knowledge captured from incident resolutions.\n\n")

        for lesson in self._lessons:
            lines.append(f"## {lesson.incident_id}: Lesson\n")
            lines.append(f"**Date**: {lesson.created_at.strftime('%Y-%m-%d')}\n")
            lines.append(f"**Category**: {lesson.category}\n")
            lines.append(f"**Lesson**: {lesson.lesson}\n")
            lines.append(f"**Prevention**: {lesson.prevention}\n")
            if lesson.related_files:
                lines.append(f"**Related Files**: {', '.join(lesson.related_files)}\n")
            if lesson.tags:
                lines.append(f"**Tags**: {', '.join(lesson.tags)}\n")
            lines.append("\n---\n\n")

        try:
            self.file_path.write_text("".join(lines))
        except Exception as e:
            logger.error(f"Failed to save lessons: {e}")

    def _emit_to_contextcore(self, lesson: Lesson) -> None:
        """Emit a lesson to ContextCore."""
        try:
            from contextcore.agent import InsightEmitter

            emitter = InsightEmitter(
                project_id="coyote",
                agent_id="knowledge-base",
            )

            emitter.emit_lesson(
                summary=lesson.lesson,
                category=lesson.category,
                applies_to=lesson.related_files,
                context={
                    "incident_id": lesson.incident_id,
                    "prevention": lesson.prevention,
                    "confidence": lesson.confidence,
                },
            )

        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Failed to emit lesson to ContextCore: {e}")

    def query(
        self,
        categories: Optional[List[str]] = None,
        files: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        text: Optional[str] = None,
        limit: int = 10,
    ) -> List[Lesson]:
        """
        Query lessons from the knowledge base.

        Args:
            categories: Filter by categories
            files: Filter by related files
            tags: Filter by tags
            text: Full-text search
            limit: Maximum results

        Returns:
            List of matching Lessons
        """
        results = []

        for lesson in self._lessons:
            # Category filter
            if categories and lesson.category not in categories:
                continue

            # File filter
            if files:
                if not any(
                    any(f in related for related in lesson.related_files) for f in files
                ):
                    continue

            # Tag filter
            if tags:
                if not any(tag in lesson.tags for tag in tags):
                    continue

            # Text search
            if text:
                text_lower = text.lower()
                if (
                    text_lower not in lesson.lesson.lower()
                    and text_lower not in lesson.prevention.lower()
                ):
                    continue

            results.append(lesson)

            if len(results) >= limit:
                break

        return results

    def get_by_incident(self, incident_id: str) -> List[Lesson]:
        """Get all lessons for an incident."""
        return [l for l in self._lessons if l.incident_id == incident_id]

    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        return list(set(l.category for l in self._lessons))

    def count(self) -> int:
        """Get total number of lessons."""
        return len(self._lessons)

    def to_json(self) -> str:
        """Export lessons as JSON."""
        return json.dumps([l.to_dict() for l in self._lessons], indent=2)
