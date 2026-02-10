"""
Tests for startd8/Beaver LLM migration in Coyote.

Covers:
- Feature flag: use_startd8 defaults to False
- call_llm dispatches to _call_via_startd8 when flag is True
- call_llm uses existing provider dispatch when flag is False
- Graceful ImportError when startd8-sdk is not installed
- Config env var COYOTE_USE_STARTD8
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from contextcore_coyote.config import CoyoteConfig
from contextcore_coyote.pipeline.stage import Stage, StageContext
from contextcore_coyote.models import Incident, IncidentSeverity, StageResult, StageStatus


class ConcreteStage(Stage):
    """Minimal concrete stage for testing call_llm dispatch."""

    name = "test_stage"
    description = "Test stage"

    def execute(self, ctx: StageContext) -> StageResult:
        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=ctx.incident.created_at,
            summary="test",
        )


class TestStartd8Config:
    def test_use_startd8_defaults_false(self):
        config = CoyoteConfig()
        assert config.use_startd8 is False

    def test_use_startd8_from_env(self, monkeypatch):
        monkeypatch.setenv("COYOTE_USE_STARTD8", "true")
        config = CoyoteConfig.from_env()
        assert config.use_startd8 is True

    def test_use_startd8_env_false(self, monkeypatch):
        monkeypatch.setenv("COYOTE_USE_STARTD8", "false")
        config = CoyoteConfig.from_env()
        assert config.use_startd8 is False

    def test_use_startd8_env_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("COYOTE_USE_STARTD8", "True")
        config = CoyoteConfig.from_env()
        assert config.use_startd8 is True


class TestCallLlmDispatch:
    @pytest.fixture
    def stage_with_startd8(self):
        """Stage configured with use_startd8=True."""
        import contextcore_coyote.config as config_module

        config_module._config = CoyoteConfig(
            use_startd8=True,
            llm_provider="anthropic",
            llm_model="test-model",
        )
        return ConcreteStage()

    @pytest.fixture
    def stage_without_startd8(self):
        """Stage configured with use_startd8=False."""
        import contextcore_coyote.config as config_module

        config_module._config = CoyoteConfig(
            use_startd8=False,
            llm_provider="anthropic",
            llm_model="test-model",
            anthropic_api_key="test-key",
        )
        return ConcreteStage()

    def test_call_llm_with_startd8_flag(self, stage_with_startd8):
        """When use_startd8=True, call_llm delegates to _call_via_startd8."""
        with patch.object(stage_with_startd8, "_call_via_startd8", return_value="startd8 response") as mock:
            result = stage_with_startd8.call_llm("test prompt")
            mock.assert_called_once_with("test prompt")
            assert result == "startd8 response"

    def test_call_llm_default_unchanged(self, stage_without_startd8):
        """When use_startd8=False, call_llm uses existing provider dispatch."""
        with patch.object(stage_without_startd8, "_call_anthropic", return_value="anthropic response") as mock:
            result = stage_without_startd8.call_llm("test prompt")
            mock.assert_called_once_with("test prompt")
            assert result == "anthropic response"

    def test_startd8_import_error(self, stage_with_startd8):
        """When startd8-sdk is not installed, raises RuntimeError with helpful message."""
        with pytest.raises(RuntimeError, match="startd8-sdk not installed"):
            stage_with_startd8._call_via_startd8("test prompt")

    def test_startd8_calls_provider_registry(self, stage_with_startd8):
        """When startd8 is available, calls ProviderRegistry correctly."""
        mock_response = MagicMock()
        mock_response.text = "generated fix"

        mock_agent = MagicMock()
        mock_agent.generate.return_value = mock_response

        mock_registry = MagicMock()
        mock_registry.create_agent.return_value = mock_agent

        with patch.dict("sys.modules", {"startd8": MagicMock(), "startd8.providers": MagicMock()}):
            with patch("startd8.providers.ProviderRegistry", mock_registry):
                result = stage_with_startd8._call_via_startd8("fix this bug")

                mock_registry.discover.assert_called_once()
                mock_registry.create_agent.assert_called_once_with(
                    provider_name="anthropic",
                    model="test-model",
                )
                mock_agent.generate.assert_called_once_with("fix this bug")
                assert result == "generated fix"
