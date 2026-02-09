"""Tests for agent text parsing — the fragile extraction methods.

These tests validate the parsing logic without calling any LLM.
Each agent's _extract_* methods are tested with realistic response strings.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from contextcore_coyote.config import CoyoteConfig
from contextcore_coyote.models import StageResult, StageStatus
from contextcore_coyote.pipeline.stage import StageContext
import contextcore_coyote.config as config_module


@pytest.fixture(autouse=True)
def _set_test_config():
    """Ensure agents can be instantiated without real config."""
    config_module._config = CoyoteConfig(
        contextcore_enabled=False,
        auto_proceed=True,
        anthropic_api_key="test-key",
    )


# --- Investigator ---


class TestInvestigatorParsing:
    """Test Investigator._extract_* methods."""

    def _make_agent(self):
        from contextcore_coyote.agents.investigator import Investigator

        return Investigator()

    def test_extract_section_found(self, sample_llm_responses):
        agent = self._make_agent()
        result = agent._extract_section(sample_llm_responses["investigator"], "Root Cause")
        assert result is not None
        assert "NullPointerException" in result

    def test_extract_section_not_found(self, sample_llm_responses):
        agent = self._make_agent()
        result = agent._extract_section(sample_llm_responses["investigator"], "Nonexistent")
        assert result is None

    def test_extract_section_stops_at_next_heading(self):
        agent = self._make_agent()
        text = "### Section A\nContent A\n### Section B\nContent B"
        result = agent._extract_section(text, "Section A")
        assert result == "Content A"
        assert "Content B" not in result

    def test_extract_files(self, sample_llm_responses):
        agent = self._make_agent()
        files = agent._extract_files(sample_llm_responses["investigator"])
        assert len(files) >= 1
        assert any("UserService.java" in f for f in files)

    def test_extract_files_no_files(self):
        agent = self._make_agent()
        assert agent._extract_files("No files mentioned here.") == []

    def test_extract_files_requires_slash(self):
        agent = self._make_agent()
        # "File: readme.txt" (no slash) should not be extracted
        assert agent._extract_files("- File: readme.txt") == []

    def test_extract_pr(self, sample_llm_responses):
        agent = self._make_agent()
        pr = agent._extract_pr(sample_llm_responses["investigator"])
        assert pr is not None
        assert "#42" in pr or "42" in pr

    def test_extract_pr_none(self):
        agent = self._make_agent()
        assert agent._extract_pr("No PR mentioned.") is None

    def test_extract_pr_skips_template(self):
        agent = self._make_agent()
        assert agent._extract_pr("- PR: [number if known]") is None


# --- Designer ---


class TestDesignerParsing:
    """Test Designer._extract_* methods."""

    def _make_agent(self):
        from contextcore_coyote.agents.designer import Designer

        return Designer()

    def test_extract_section(self, sample_llm_responses):
        agent = self._make_agent()
        result = agent._extract_section(sample_llm_responses["designer"], "Fix Summary")
        assert result is not None
        assert "null guard" in result.lower()

    def test_extract_list_tradeoffs(self, sample_llm_responses):
        agent = self._make_agent()
        items = agent._extract_list(sample_llm_responses["designer"], "Tradeoffs")
        assert len(items) >= 1

    def test_extract_list_alternatives(self, sample_llm_responses):
        agent = self._make_agent()
        items = agent._extract_list(sample_llm_responses["designer"], "Alternatives Considered")
        assert len(items) >= 1

    def test_extract_list_empty_section(self):
        agent = self._make_agent()
        items = agent._extract_list("No sections here", "Tradeoffs")
        assert items == []

    def test_extract_list_numbered_items(self):
        agent = self._make_agent()
        text = "### Items\n1. First item\n2. Second item\n### Next"
        items = agent._extract_list(text, "Items")
        assert len(items) == 2

    def test_extract_list_bulleted_items(self):
        agent = self._make_agent()
        text = "### Items\n- First item\n- Second item\n### Next"
        items = agent._extract_list(text, "Items")
        assert len(items) == 2


# --- Implementer ---


class TestImplementerParsing:
    """Test Implementer._extract_* methods."""

    def _make_agent(self):
        from contextcore_coyote.agents.implementer import Implementer

        return Implementer()

    def test_extract_code_changes(self, sample_llm_responses):
        agent = self._make_agent()
        changes = agent._extract_code_changes(sample_llm_responses["implementer"])
        assert len(changes) >= 1
        # Should find at least one file with code
        assert any("UserService" in k for k in changes)

    def test_extract_code_changes_empty(self):
        agent = self._make_agent()
        changes = agent._extract_code_changes("No code changes here.")
        assert changes == {}

    def test_extract_code_changes_multiple_files(self, sample_llm_responses):
        agent = self._make_agent()
        changes = agent._extract_code_changes(sample_llm_responses["implementer"])
        assert len(changes) >= 2

    def test_extract_commit_message(self, sample_llm_responses):
        agent = self._make_agent()
        msg = agent._extract_commit_message(sample_llm_responses["implementer"])
        assert msg is not None
        assert "fix" in msg.lower()

    def test_extract_commit_message_none(self):
        agent = self._make_agent()
        assert agent._extract_commit_message("No commit message.") is None

    def test_extract_section(self, sample_llm_responses):
        agent = self._make_agent()
        result = agent._extract_section(sample_llm_responses["implementer"], "Summary")
        assert result is not None
        assert "null guard" in result.lower()


# --- Tester ---


class TestTesterParsing:
    """Test Tester._check_passed and _extract_recommendation."""

    def _make_agent(self):
        from contextcore_coyote.agents.tester import Tester

        return Tester()

    def test_check_passed_approve(self, sample_llm_responses):
        agent = self._make_agent()
        assert agent._check_passed(sample_llm_responses["tester"]) is True

    def test_check_passed_reject(self):
        agent = self._make_agent()
        assert agent._check_passed("REJECT - this fix is incomplete") is False

    def test_check_passed_request_changes(self):
        agent = self._make_agent()
        assert agent._check_passed("REQUEST CHANGES - needs more tests") is False

    def test_check_passed_pass_marker(self):
        agent = self._make_agent()
        assert agent._check_passed("[Pass] - All good") is True

    def test_check_passed_defaults_to_true(self):
        """Default to passed if unclear — documents the risky behavior."""
        agent = self._make_agent()
        assert agent._check_passed("Some ambiguous response with no clear verdict") is True

    def test_check_passed_approve_and_reject(self):
        """If both approve and reject appear, reject wins."""
        agent = self._make_agent()
        assert agent._check_passed("I would approve but must reject this") is False

    def test_extract_recommendation_approve(self, sample_llm_responses):
        agent = self._make_agent()
        rec = agent._extract_recommendation(sample_llm_responses["tester"])
        assert rec == "APPROVE"

    def test_extract_recommendation_reject(self):
        agent = self._make_agent()
        assert agent._extract_recommendation("REJECT\nReason: bad code") == "REJECT"

    def test_extract_recommendation_request_changes(self):
        agent = self._make_agent()
        assert agent._extract_recommendation("REQUEST CHANGES needed") == "REQUEST CHANGES"

    def test_extract_recommendation_none(self):
        agent = self._make_agent()
        assert agent._extract_recommendation("No clear recommendation") is None

    def test_extract_section(self, sample_llm_responses):
        agent = self._make_agent()
        result = agent._extract_section(sample_llm_responses["tester"], "Regression Analysis")
        assert result is not None


# --- KnowledgeAgent ---


class TestKnowledgeAgentParsing:
    """Test KnowledgeAgent._extract_* methods."""

    def _make_agent(self):
        from contextcore_coyote.agents.knowledge import KnowledgeAgent

        return KnowledgeAgent()

    def test_extract_lessons(self, sample_llm_responses):
        agent = self._make_agent()
        lessons = agent._extract_lessons(sample_llm_responses["knowledge"], "INC-001")
        assert len(lessons) >= 1
        assert lessons[0].incident_id == "INC-001"
        assert lessons[0].lesson != ""

    def test_extract_lessons_with_fields(self, sample_llm_responses):
        agent = self._make_agent()
        lessons = agent._extract_lessons(sample_llm_responses["knowledge"], "INC-001")
        # At least one lesson should have non-empty fields
        has_fields = any(l.prevention != "" for l in lessons)
        assert has_fields

    def test_extract_lessons_empty(self):
        agent = self._make_agent()
        lessons = agent._extract_lessons("No lessons here.", "INC-001")
        assert lessons == []

    def test_extract_lessons_numbering(self, sample_llm_responses):
        agent = self._make_agent()
        lessons = agent._extract_lessons(sample_llm_responses["knowledge"], "INC-001")
        if len(lessons) >= 2:
            assert lessons[0].id == "INC-001-L1"
            assert lessons[1].id == "INC-001-L2"

    def test_extract_prevention(self, sample_llm_responses):
        agent = self._make_agent()
        items = agent._extract_prevention(sample_llm_responses["knowledge"])
        assert len(items) >= 1

    def test_extract_prevention_empty(self):
        agent = self._make_agent()
        items = agent._extract_prevention("No checklist here.")
        assert items == []

    def test_extract_category(self, sample_llm_responses):
        agent = self._make_agent()
        category = agent._extract_category(sample_llm_responses["knowledge"])
        assert category == "null-reference"

    def test_extract_category_unknown_default(self):
        agent = self._make_agent()
        category = agent._extract_category("No category section.")
        assert category == "unknown"
