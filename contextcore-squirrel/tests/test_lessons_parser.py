"""Tests for contextcore_squirrel.lessons_parser."""

from pathlib import Path

import pytest

from contextcore_squirrel.lessons_parser import (
    Lesson,
    LessonDomain,
    LessonLeg,
    LessonsParser,
    estimate_tokens,
    extract_field,
    extract_reusable_items,
    parse_domain,
    parse_leg_file,
    parse_lesson,
    summarize_text,
    to_dict,
)


class TestEstimateTokens:
    """Test token estimation."""

    def test_empty_text(self):
        assert estimate_tokens("") == 0

    def test_prose_text(self):
        text = "a" * 400  # 400 chars = ~100 tokens
        tokens = estimate_tokens(text)
        assert tokens == 100

    def test_code_blocks(self):
        text = "some prose\n```python\nprint('hello')\n```\nmore prose"
        tokens = estimate_tokens(text)
        assert tokens > 0

    def test_code_multiplier(self):
        text = "```code```"
        tokens_default = estimate_tokens(text)
        tokens_high = estimate_tokens(text, code_multiplier=2.0)
        assert tokens_high > tokens_default


class TestSummarizeText:
    """Test text summarization."""

    def test_short_text(self):
        assert summarize_text("Short text.", 100) == "Short text."

    def test_empty_text(self):
        assert summarize_text("", 100) == ""

    def test_truncation_at_sentence(self):
        text = "First sentence. Second sentence. Third sentence that is very long."
        result = summarize_text(text, 40)
        assert result.endswith(".")
        assert len(result) <= 40

    def test_truncation_with_ellipsis(self):
        text = "A very long word " * 20
        result = summarize_text(text, 30)
        assert result.endswith("...")


class TestExtractField:
    """Test markdown field extraction."""

    def test_extract_context(self):
        content = "**Context:** Building a system\n**Problem:** It broke"
        result = extract_field(content, "Context")
        assert result == "Building a system"

    def test_extract_problem(self):
        content = "**Problem:** The server crashed"
        result = extract_field(content, "Problem")
        assert "server crashed" in result

    def test_extract_missing_field(self):
        content = "**Context:** Something"
        assert extract_field(content, "Problem") is None

    def test_extract_with_colon_in_value(self):
        content = "**Context:** Key: value pair\n**Problem:** Issue"
        result = extract_field(content, "Context")
        assert "Key: value pair" in result


class TestExtractReusableItems:
    """Test reusable items extraction."""

    def test_extract_heuristic(self, single_lesson_content):
        items = extract_reusable_items(single_lesson_content)
        assert "heuristic" in items
        assert "validate" in items["heuristic"].lower() or "endpoints" in items["heuristic"].lower()

    def test_extract_pattern(self, single_lesson_content):
        items = extract_reusable_items(single_lesson_content)
        assert items.get("pattern_name") == "Fail-Fast Connectivity Check"

    def test_no_reusable_section(self):
        content = "**Context:** Something\n**Problem:** Issue"
        items = extract_reusable_items(content)
        assert items == {}


class TestParseLesson:
    """Test single lesson parsing."""

    def test_parse_basic_lesson(self, single_lesson_content):
        lesson = parse_lesson(
            single_lesson_content,
            lesson_number=1,
            domain_id="observability",
            leg_id="tracing",
            leg_number=1,
            source_file="01-tracing.md",
            source_line=1,
        )
        assert lesson.id == "observability-tracing-1"
        assert lesson.number == 1
        assert "Validate OTLP" in lesson.title
        assert lesson.version == "2.0.0"
        assert lesson.actor == "human"
        assert lesson.pattern_name == "Fail-Fast Connectivity Check"
        assert lesson.scope == "backend"

    def test_parse_lesson_token_budget(self, single_lesson_content):
        lesson = parse_lesson(
            single_lesson_content, 1, "obs", "tracing", 1, "file.md", 1
        )
        assert lesson.token_budget > 0
        assert lesson.summary_tokens > 0
        assert lesson.summary_tokens < lesson.token_budget

    def test_parse_lesson_tags(self, single_lesson_content):
        lesson = parse_lesson(
            single_lesson_content, 1, "obs", "tracing", 1, "file.md", 1
        )
        assert "otlp" in lesson.tags
        assert "tempo" in lesson.tags


class TestParseLegFile:
    """Test leg file parsing."""

    def test_parse_leg_file(self, tmp_lessons):
        leg_file = tmp_lessons / "observability" / "lessons" / "01-tracing.md"
        leg = parse_leg_file(leg_file, "observability")
        assert leg is not None
        assert leg.id == "tracing"
        assert leg.number == 1
        assert leg.lesson_count == 2
        assert len(leg.lessons) == 2

    def test_parse_leg_file_patterns(self, tmp_lessons):
        leg_file = tmp_lessons / "observability" / "lessons" / "01-tracing.md"
        leg = parse_leg_file(leg_file, "observability")
        assert leg is not None
        assert "Structured-First Observability" in leg.key_patterns

    def test_parse_leg_bad_filename(self, tmp_path):
        bad_file = tmp_path / "not-numbered.md"
        bad_file.write_text("# Some content")
        assert parse_leg_file(bad_file, "test") is None

    def test_parse_second_leg_with_code(self, tmp_lessons):
        leg_file = tmp_lessons / "observability" / "lessons" / "02-metrics.md"
        leg = parse_leg_file(leg_file, "observability")
        assert leg is not None
        assert leg.id == "metrics"
        assert leg.lessons[0].has_code_example is True


class TestParseDomain:
    """Test domain parsing."""

    def test_parse_domain(self, tmp_lessons):
        domain = parse_domain(tmp_lessons / "observability")
        assert domain is not None
        assert domain.id == "observability"
        assert domain.leg_count == 2
        assert domain.lesson_count == 3  # 2 from leg 1 + 1 from leg 2

    def test_parse_domain_no_lessons_dir(self, tmp_path):
        assert parse_domain(tmp_path) is None


class TestToDict:
    """Test to_dict conversion."""

    def test_pydantic_model(self):
        lesson = Lesson(
            id="test-1",
            number=1,
            title="Test",
            domain="test",
            leg="basics",
            leg_number=1,
        )
        result = to_dict(lesson)
        assert isinstance(result, dict)
        assert result["id"] == "test-1"

    def test_plain_dict(self):
        d = {"key": "value"}
        assert to_dict(d) == d


class TestLessonsParserClass:
    """Test the LessonsParser wrapper class."""

    def test_parse(self, tmp_lessons):
        parser = LessonsParser(tmp_lessons)
        domains = parser.parse()
        assert len(domains) == 1
        assert domains[0].id == "observability"

    def test_parse_single_domain(self, tmp_lessons):
        parser = LessonsParser(tmp_lessons)
        domain = parser.parse_domain("observability")
        assert domain is not None
        assert domain.lesson_count == 3

    def test_parse_json(self, tmp_lessons):
        parser = LessonsParser(tmp_lessons)
        json_str = parser.parse_json()
        import json

        data = json.loads(json_str)
        assert data["total_domains"] == 1
        assert data["total_lessons"] == 3


class TestPydanticModels:
    """Test Pydantic model features."""

    def test_lesson_model(self):
        lesson = Lesson(
            id="test-1",
            number=1,
            title="Test Lesson",
            domain="test",
            leg="basics",
            leg_number=1,
        )
        assert lesson.actor == "agent:claude-code"  # default
        dumped = lesson.model_dump()
        assert dumped["id"] == "test-1"

    def test_lesson_leg_model(self):
        leg = LessonLeg(id="tracing", number=1, name="Tracing")
        assert leg.lessons == []
        assert leg.lesson_count == 0

    def test_lesson_domain_model(self):
        domain = LessonDomain(id="obs", name="Observability")
        assert domain.legs == []
