"""Tests for contextcore_squirrel.knowledge_emitter."""

from unittest.mock import MagicMock, patch

import pytest

from contextcore_squirrel.knowledge_parser import (
    Endpoint,
    Process,
    Project,
    Skill,
    SquirrelIndex,
    Tool,
    Workflow,
)


def _make_mock_tracer():
    """Create a mock tracer that supports context manager span creation."""
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)
    mock_tracer.start_as_current_span.return_value = mock_span
    return mock_tracer, mock_span


class TestKnowledgeEmitterInit:
    """Test KnowledgeEmitter initialization."""

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_init_default(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        emitter = KnowledgeEmitter(dry_run=True)
        assert emitter.dry_run is True
        assert emitter.stats["total_spans"] == 0
        emitter.shutdown()

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_normalize_endpoint(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        emitter = KnowledgeEmitter(endpoint="localhost", dry_run=True)
        assert emitter._normalize_endpoint("localhost") == "localhost:4317"
        assert emitter._normalize_endpoint("http://host:4317") == "host:4317"
        assert emitter._normalize_endpoint("") == "http://localhost:4317"
        emitter.shutdown()


class TestKnowledgeEmitterEmit:
    """Test individual emit methods."""

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_emit_endpoint(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        mock_tracer, mock_span = _make_mock_tracer()
        mock_trace.get_tracer.return_value = mock_tracer

        emitter = KnowledgeEmitter(dry_run=True)
        emitter.tracer = mock_tracer

        endpoint = Endpoint(
            id="ep1",
            name="Test",
            category="endpoint",
            description="Test endpoint",
            url="http://localhost",
            port=3000,
        )
        emitter.emit_endpoint(endpoint)

        assert emitter.stats["endpoints_emitted"] == 1
        assert emitter.stats["total_spans"] == 1
        mock_tracer.start_as_current_span.assert_called_with("endpoint:ep1", context=None)
        emitter.shutdown()

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_emit_skill_tracks_tokens(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        mock_tracer, mock_span = _make_mock_tracer()
        mock_trace.get_tracer.return_value = mock_tracer

        emitter = KnowledgeEmitter(dry_run=True)
        emitter.tracer = mock_tracer

        skill = Skill(
            id="s1",
            name="Test Skill",
            category="skill",
            description="A test skill",
            token_budget=1500,
        )
        emitter.emit_skill(skill)

        assert emitter.stats["skills_emitted"] == 1
        assert emitter.stats["total_tokens"] == 1500
        emitter.shutdown()

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_emit_process_anti_pattern(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        mock_tracer, mock_span = _make_mock_tracer()
        mock_trace.get_tracer.return_value = mock_tracer

        emitter = KnowledgeEmitter(dry_run=True)
        emitter.tracer = mock_tracer

        process = Process(
            id="p1",
            name="Anti",
            category="process",
            description="An anti-pattern",
            is_anti_pattern=True,
        )
        emitter.emit_process(process)

        assert emitter.stats["processes_emitted"] == 1
        mock_span.set_attribute.assert_any_call("process.is_anti_pattern", True)
        emitter.shutdown()


class TestKnowledgeEmitterIndex:
    """Test full index emission."""

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_emit_index(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        mock_tracer, mock_span = _make_mock_tracer()
        mock_trace.get_tracer.return_value = mock_tracer
        mock_trace.set_span_in_context.return_value = None

        emitter = KnowledgeEmitter(dry_run=True)
        emitter.tracer = mock_tracer

        index = SquirrelIndex(
            tier="public",
            source_path="/test",
            endpoints=[
                Endpoint(
                    id="e1", name="E1", category="endpoint", description="EP", port=3000
                )
            ],
            skills=[
                Skill(
                    id="s1",
                    name="S1",
                    category="skill",
                    description="SK",
                    token_budget=500,
                )
            ],
            tools=[Tool(id="t1", name="T1", category="tool", description="TL")],
        )

        emitter.emit_index(index)

        assert emitter.stats["endpoints_emitted"] == 1
        assert emitter.stats["skills_emitted"] == 1
        assert emitter.stats["tools_emitted"] == 1
        assert emitter.stats["total_spans"] == 4  # 3 items + 1 parent
        emitter.shutdown()


class TestKnowledgeEmitterShutdown:
    """Test shutdown behavior."""

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_double_shutdown(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        emitter = KnowledgeEmitter(dry_run=True)
        emitter.shutdown()
        emitter.shutdown()  # Should not raise

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_get_stats(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        emitter = KnowledgeEmitter(dry_run=True)
        stats = emitter.get_stats()
        assert "total_spans" in stats
        assert stats["total_spans"] == 0
        emitter.shutdown()


class TestTruncateAttribute:
    """Test attribute truncation."""

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_short_value_unchanged(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        emitter = KnowledgeEmitter(dry_run=True)
        assert emitter._truncate_attribute("short") == "short"
        emitter.shutdown()

    @patch("contextcore_squirrel.knowledge_emitter.trace")
    @patch("contextcore_squirrel.knowledge_emitter.TracerProvider")
    @patch("contextcore_squirrel.knowledge_emitter.OTLPSpanExporter")
    def test_long_value_truncated(self, mock_exporter, mock_provider, mock_trace):
        from contextcore_squirrel.knowledge_emitter import KnowledgeEmitter

        emitter = KnowledgeEmitter(dry_run=True)
        long_value = "x" * 5000
        result = emitter._truncate_attribute(long_value)
        assert len(result) == 4096
        assert result.endswith("...")
        emitter.shutdown()
