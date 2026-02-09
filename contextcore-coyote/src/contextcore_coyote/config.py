"""
Configuration management for ContextCore Coyote.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional, List

_config: Optional["CoyoteConfig"] = None


@dataclass
class CoyoteConfig:
    """Configuration for ContextCore Coyote."""

    # LLM settings
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Pipeline settings
    auto_proceed: bool = False  # Require human approval between stages
    max_retries: int = 3
    timeout_seconds: int = 300

    # Observability endpoints
    prometheus_url: Optional[str] = None
    loki_url: Optional[str] = None
    tempo_url: Optional[str] = None
    pyroscope_url: Optional[str] = None

    # ContextCore integration
    contextcore_enabled: bool = False
    otel_endpoint: str = "localhost:4317"
    otel_service_name: str = "contextcore-coyote"

    # GitHub integration
    github_token: Optional[str] = None
    github_repo: Optional[str] = None

    # Knowledge base
    lessons_file: str = "LESSONS_LEARNED.md"

    # Logging
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "CoyoteConfig":
        """Create configuration from environment variables."""
        return cls(
            llm_provider=os.getenv("COYOTE_LLM_PROVIDER", "anthropic"),
            llm_model=os.getenv("COYOTE_LLM_MODEL", "claude-sonnet-4-20250514"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            auto_proceed=os.getenv("COYOTE_AUTO_PROCEED", "false").lower() == "true",
            max_retries=int(os.getenv("COYOTE_MAX_RETRIES", "3")),
            timeout_seconds=int(os.getenv("COYOTE_TIMEOUT_SECONDS", "300")),
            prometheus_url=os.getenv("PROMETHEUS_URL"),
            loki_url=os.getenv("LOKI_URL"),
            tempo_url=os.getenv("TEMPO_URL"),
            pyroscope_url=os.getenv("PYROSCOPE_URL"),
            contextcore_enabled=os.getenv("COYOTE_CONTEXTCORE_ENABLED", "false").lower()
            == "true",
            otel_endpoint=os.getenv("COYOTE_OTEL_ENDPOINT", "localhost:4317"),
            otel_service_name=os.getenv("COYOTE_OTEL_SERVICE_NAME", "contextcore-coyote"),
            github_token=os.getenv("GITHUB_TOKEN"),
            github_repo=os.getenv("GITHUB_REPOSITORY"),
            lessons_file=os.getenv("COYOTE_LESSONS_FILE", "LESSONS_LEARNED.md"),
            log_level=os.getenv("COYOTE_LOG_LEVEL", "INFO"),
        )


def configure(
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    anthropic_api_key: Optional[str] = None,
    auto_proceed: Optional[bool] = None,
    prometheus_url: Optional[str] = None,
    loki_url: Optional[str] = None,
    tempo_url: Optional[str] = None,
    contextcore_enabled: Optional[bool] = None,
    otel_endpoint: Optional[str] = None,
    github_token: Optional[str] = None,
    log_level: Optional[str] = None,
    **kwargs,
) -> CoyoteConfig:
    """
    Configure ContextCore Coyote.

    Args:
        llm_provider: LLM provider (anthropic, openai)
        llm_model: Model to use
        anthropic_api_key: Anthropic API key
        auto_proceed: Auto-advance through stages without approval
        prometheus_url: Prometheus endpoint
        loki_url: Loki endpoint
        tempo_url: Tempo endpoint
        contextcore_enabled: Enable ContextCore integration
        otel_endpoint: OTLP endpoint
        github_token: GitHub token for repo integration
        log_level: Logging level

    Returns:
        The configured CoyoteConfig instance
    """
    global _config

    config = CoyoteConfig.from_env()

    if llm_provider is not None:
        config.llm_provider = llm_provider
    if llm_model is not None:
        config.llm_model = llm_model
    if anthropic_api_key is not None:
        config.anthropic_api_key = anthropic_api_key
    if auto_proceed is not None:
        config.auto_proceed = auto_proceed
    if prometheus_url is not None:
        config.prometheus_url = prometheus_url
    if loki_url is not None:
        config.loki_url = loki_url
    if tempo_url is not None:
        config.tempo_url = tempo_url
    if contextcore_enabled is not None:
        config.contextcore_enabled = contextcore_enabled
    if otel_endpoint is not None:
        config.otel_endpoint = otel_endpoint
    if github_token is not None:
        config.github_token = github_token
    if log_level is not None:
        config.log_level = log_level

    # Handle any additional kwargs
    for key, value in kwargs.items():
        if hasattr(config, key) and value is not None:
            setattr(config, key, value)

    _config = config
    return config


def get_config() -> CoyoteConfig:
    """Get the current configuration."""
    global _config
    if _config is None:
        _config = CoyoteConfig.from_env()
    return _config
