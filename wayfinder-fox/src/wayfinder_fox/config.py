"""Fox configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class FoxConfig:
    """Configuration for Fox context enrichment."""

    service_name: str = "wayfinder-fox"
    otlp_endpoint: str = field(
        default_factory=lambda: os.environ.get(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "localhost:4317"
        )
    )
    contextcore_yaml_path: str = field(
        default_factory=lambda: os.environ.get(
            "CONTEXTCORE_YAML_PATH", ".contextcore.yaml"
        )
    )
    use_kubernetes: bool = field(
        default_factory=lambda: os.environ.get(
            "FOX_USE_KUBERNETES", "false"
        ).lower() == "true"
    )
    routing_table: Dict[str, List[str]] = field(default_factory=lambda: {
        "critical": ["claude_analysis", "context_notify"],
        "high": ["context_notify"],
        "medium": ["log"],
        "low": ["log"],
    })
