"""Tests for contextcore_coyote.knowledge.lessons — LessonsLearned knowledge base."""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from contextcore_coyote.config import CoyoteConfig
from contextcore_coyote.knowledge.lessons import LessonsLearned
from contextcore_coyote.models import Lesson
import contextcore_coyote.config as config_module


@pytest.fixture(autouse=True)
def _set_test_config():
    """Set test config to avoid real endpoints."""
    config_module._config = CoyoteConfig(
        contextcore_enabled=False,
        lessons_file="LESSONS_LEARNED.md",
    )


# --- Construction and loading ---


class TestLessonsLearnedConstruction:
    """Test construction and file loading."""

    def test_empty_directory(self, tmp_path):
        kb = LessonsLearned(file_path=str(tmp_path / "LESSONS_LEARNED.md"))
        assert kb.count() == 0

    def test_load_existing_file(self, tmp_knowledge_dir):
        kb = LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))
        assert kb.count() == 2

    def test_load_nonexistent_file(self, tmp_path):
        kb = LessonsLearned(file_path=str(tmp_path / "nonexistent.md"))
        assert kb.count() == 0


# --- Markdown parsing ---


class TestMarkdownParsing:
    """Test _parse_markdown()."""

    def test_parses_incident_id(self, tmp_knowledge_dir):
        kb = LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))
        lessons = kb.get_by_incident("INC-001")
        assert len(lessons) == 1
        assert lessons[0].incident_id == "INC-001"

    def test_parses_category(self, tmp_knowledge_dir):
        kb = LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))
        lessons = kb.get_by_incident("INC-001")
        assert lessons[0].category == "null-reference"

    def test_parses_lesson_text(self, tmp_knowledge_dir):
        kb = LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))
        lessons = kb.get_by_incident("INC-001")
        assert "validate" in lessons[0].lesson.lower()

    def test_parses_prevention(self, tmp_knowledge_dir):
        kb = LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))
        lessons = kb.get_by_incident("INC-001")
        assert "null check" in lessons[0].prevention.lower()

    def test_parses_tags(self, tmp_knowledge_dir):
        kb = LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))
        lessons = kb.get_by_incident("INC-001")
        assert "null-check" in lessons[0].tags

    def test_parses_multiple_incidents(self, tmp_knowledge_dir):
        kb = LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))
        assert kb.count() == 2
        assert len(kb.get_by_incident("INC-002")) == 1

    def test_empty_content(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("")
        kb = LessonsLearned(file_path=str(f))
        assert kb.count() == 0

    def test_no_colon_in_header(self, tmp_path):
        f = tmp_path / "lessons.md"
        f.write_text("## No colon here\n**Category**: test\n")
        kb = LessonsLearned(file_path=str(f))
        # Header without colon is not parsed as a lesson
        assert kb.count() == 0


# --- Adding lessons ---


class TestAddLesson:
    """Test add() method."""

    def test_add_increments_count(self, tmp_path):
        kb = LessonsLearned(file_path=str(tmp_path / "LESSONS_LEARNED.md"))
        kb.add(
            incident_id="INC-100",
            category="test",
            lesson="Test lesson",
            prevention="Test prevention",
        )
        assert kb.count() == 1

    def test_add_returns_lesson(self, tmp_path):
        kb = LessonsLearned(file_path=str(tmp_path / "LESSONS_LEARNED.md"))
        lesson = kb.add(
            incident_id="INC-100",
            category="test",
            lesson="Test lesson",
            prevention="Test prevention",
        )
        assert isinstance(lesson, Lesson)
        assert lesson.incident_id == "INC-100"

    def test_add_persists_to_file(self, tmp_path):
        filepath = str(tmp_path / "LESSONS_LEARNED.md")
        kb = LessonsLearned(file_path=filepath)
        kb.add(
            incident_id="INC-100",
            category="test",
            lesson="Test lesson",
            prevention="Test prevention",
        )
        # Re-read file and verify content
        kb2 = LessonsLearned(file_path=filepath)
        assert kb2.count() == 1

    def test_add_with_optional_fields(self, tmp_path):
        kb = LessonsLearned(file_path=str(tmp_path / "LESSONS_LEARNED.md"))
        lesson = kb.add(
            incident_id="INC-100",
            category="test",
            lesson="Test lesson",
            prevention="Test prevention",
            related_files=["file.py"],
            tags=["tag1", "tag2"],
            confidence=0.95,
        )
        assert lesson.related_files == ["file.py"]
        assert lesson.tags == ["tag1", "tag2"]
        assert lesson.confidence == 0.95

    def test_add_generates_id(self, tmp_path):
        kb = LessonsLearned(file_path=str(tmp_path / "LESSONS_LEARNED.md"))
        l1 = kb.add("INC-1", "test", "lesson 1", "prevention 1")
        l2 = kb.add("INC-2", "test", "lesson 2", "prevention 2")
        assert l1.id == "INC-1-L1"
        assert l2.id == "INC-2-L2"


# --- Querying ---


class TestQuery:
    """Test query() method with various filters."""

    @pytest.fixture
    def populated_kb(self, tmp_knowledge_dir):
        return LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))

    def test_query_all(self, populated_kb):
        results = populated_kb.query()
        assert len(results) == 2

    def test_query_by_category(self, populated_kb):
        results = populated_kb.query(categories=["null-reference"])
        assert len(results) == 1
        assert results[0].category == "null-reference"

    def test_query_by_category_no_match(self, populated_kb):
        results = populated_kb.query(categories=["nonexistent"])
        assert len(results) == 0

    def test_query_by_tags(self, populated_kb):
        results = populated_kb.query(tags=["null-check"])
        assert len(results) == 1

    def test_query_by_text(self, populated_kb):
        results = populated_kb.query(text="validate")
        assert len(results) >= 1

    def test_query_by_text_case_insensitive(self, populated_kb):
        results = populated_kb.query(text="VALIDATE")
        assert len(results) >= 1

    def test_query_by_text_in_prevention(self, populated_kb):
        results = populated_kb.query(text="SELECT FOR UPDATE")
        assert len(results) == 1

    def test_query_limit(self, populated_kb):
        results = populated_kb.query(limit=1)
        assert len(results) == 1

    def test_query_combined_filters(self, populated_kb):
        results = populated_kb.query(categories=["null-reference"], tags=["validation"])
        assert len(results) == 1


# --- Other methods ---


class TestKnowledgeBaseMethods:
    """Test get_by_incident, get_categories, count, to_json."""

    @pytest.fixture
    def populated_kb(self, tmp_knowledge_dir):
        return LessonsLearned(file_path=str(tmp_knowledge_dir / "LESSONS_LEARNED.md"))

    def test_get_by_incident(self, populated_kb):
        lessons = populated_kb.get_by_incident("INC-001")
        assert len(lessons) == 1
        assert lessons[0].incident_id == "INC-001"

    def test_get_by_incident_not_found(self, populated_kb):
        assert populated_kb.get_by_incident("INC-999") == []

    def test_get_categories(self, populated_kb):
        cats = populated_kb.get_categories()
        assert set(cats) == {"null-reference", "race-condition"}

    def test_count(self, populated_kb):
        assert populated_kb.count() == 2

    def test_to_json(self, populated_kb):
        j = populated_kb.to_json()
        data = json.loads(j)
        assert len(data) == 2
        assert all("id" in lesson for lesson in data)
        assert all("incident_id" in lesson for lesson in data)
