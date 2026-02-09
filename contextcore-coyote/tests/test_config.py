"""Tests for contextcore_coyote.config — configuration management."""

from __future__ import annotations

import pytest

from contextcore_coyote.config import CoyoteConfig, configure, get_config
import contextcore_coyote.config as config_module


class TestCoyoteConfigFromEnv:
    """Test CoyoteConfig.from_env() with env var mocking."""

    def test_defaults_no_env_vars(self, monkeypatch):
        # Clear all COYOTE_ and related env vars
        for key in [
            "COYOTE_LLM_PROVIDER",
            "COYOTE_LLM_MODEL",
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
            "COYOTE_AUTO_PROCEED",
            "COYOTE_MAX_RETRIES",
            "COYOTE_TIMEOUT_SECONDS",
            "PROMETHEUS_URL",
            "LOKI_URL",
            "TEMPO_URL",
            "PYROSCOPE_URL",
            "COYOTE_CONTEXTCORE_ENABLED",
            "COYOTE_OTEL_ENDPOINT",
            "COYOTE_OTEL_SERVICE_NAME",
            "GITHUB_TOKEN",
            "GITHUB_REPOSITORY",
            "COYOTE_LESSONS_FILE",
            "COYOTE_LOG_LEVEL",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = CoyoteConfig.from_env()

        assert config.llm_provider == "anthropic"
        assert config.llm_model == "claude-sonnet-4-20250514"
        assert config.anthropic_api_key is None
        assert config.openai_api_key is None
        assert config.auto_proceed is False
        assert config.max_retries == 3
        assert config.timeout_seconds == 300
        assert config.prometheus_url is None
        assert config.loki_url is None
        assert config.tempo_url is None
        assert config.pyroscope_url is None
        assert config.contextcore_enabled is False
        assert config.otel_endpoint == "localhost:4317"
        assert config.otel_service_name == "contextcore-coyote"
        assert config.github_token is None
        assert config.github_repo is None
        assert config.lessons_file == "LESSONS_LEARNED.md"
        assert config.log_level == "INFO"

    def test_reads_env_vars(self, monkeypatch):
        monkeypatch.setenv("COYOTE_LLM_PROVIDER", "openai")
        monkeypatch.setenv("COYOTE_LLM_MODEL", "gpt-4")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("COYOTE_AUTO_PROCEED", "true")
        monkeypatch.setenv("COYOTE_MAX_RETRIES", "5")
        monkeypatch.setenv("COYOTE_TIMEOUT_SECONDS", "600")
        monkeypatch.setenv("PROMETHEUS_URL", "http://prom:9090")
        monkeypatch.setenv("LOKI_URL", "http://loki:3100")
        monkeypatch.setenv("TEMPO_URL", "http://tempo:3200")
        monkeypatch.setenv("COYOTE_CONTEXTCORE_ENABLED", "true")
        monkeypatch.setenv("COYOTE_OTEL_ENDPOINT", "otel:4317")
        monkeypatch.setenv("COYOTE_LOG_LEVEL", "DEBUG")

        config = CoyoteConfig.from_env()

        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.anthropic_api_key == "sk-ant-test"
        assert config.auto_proceed is True
        assert config.max_retries == 5
        assert config.timeout_seconds == 600
        assert config.prometheus_url == "http://prom:9090"
        assert config.loki_url == "http://loki:3100"
        assert config.tempo_url == "http://tempo:3200"
        assert config.contextcore_enabled is True
        assert config.otel_endpoint == "otel:4317"
        assert config.log_level == "DEBUG"

    def test_auto_proceed_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("COYOTE_AUTO_PROCEED", "True")
        config = CoyoteConfig.from_env()
        assert config.auto_proceed is True

    def test_auto_proceed_false_for_non_true(self, monkeypatch):
        monkeypatch.setenv("COYOTE_AUTO_PROCEED", "yes")
        config = CoyoteConfig.from_env()
        assert config.auto_proceed is False

    def test_int_conversion(self, monkeypatch):
        monkeypatch.setenv("COYOTE_MAX_RETRIES", "10")
        monkeypatch.setenv("COYOTE_TIMEOUT_SECONDS", "1000")
        config = CoyoteConfig.from_env()
        assert config.max_retries == 10
        assert config.timeout_seconds == 1000


class TestConfigure:
    """Test configure() function."""

    def test_configure_with_kwargs(self):
        config = configure(llm_provider="openai", llm_model="gpt-4", auto_proceed=True)
        assert config.llm_provider == "openai"
        assert config.llm_model == "gpt-4"
        assert config.auto_proceed is True

    def test_configure_sets_global(self):
        configure(llm_provider="openai")
        config = get_config()
        assert config.llm_provider == "openai"

    def test_configure_none_values_use_env_defaults(self, monkeypatch):
        monkeypatch.delenv("COYOTE_LLM_PROVIDER", raising=False)
        config = configure(llm_provider=None)
        assert config.llm_provider == "anthropic"

    def test_configure_additional_kwargs(self):
        config = configure(lessons_file="custom.md")
        assert config.lessons_file == "custom.md"

    def test_configure_ignores_unknown_kwargs(self):
        config = configure(nonexistent_field="value")
        assert not hasattr(config, "nonexistent_field")


class TestGetConfig:
    """Test get_config() function."""

    def test_returns_default_when_no_global(self):
        config = get_config()
        assert isinstance(config, CoyoteConfig)
        assert config.llm_provider == "anthropic"

    def test_returns_existing_config(self):
        configure(llm_provider="openai")
        config = get_config()
        assert config.llm_provider == "openai"

    def test_creates_config_on_first_call(self):
        assert config_module._config is None
        config = get_config()
        assert config_module._config is not None

    def test_returns_same_instance(self):
        c1 = get_config()
        c2 = get_config()
        assert c1 is c2
