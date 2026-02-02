"""
Installation tracking dashboard for ContextCore.

Provides the Grafana dashboard JSON model for monitoring installation
progress, step status, duration, and attempts. This dashboard is
provisioned alongside the observability stack.
"""

from __future__ import annotations

import json
from typing import Any, Dict

__all__ = [
    "DASHBOARD_UID",
    "get_dashboard_model",
    "get_dashboard_json",
]

DASHBOARD_UID = "wf-install-status"
DASHBOARD_TITLE = "Wayfinder Installation Status"


def _stat_panel(
    panel_id: int,
    title: str,
    expr: str,
    grid_x: int,
    grid_y: int,
    width: int = 6,
    height: int = 4,
    unit: str = "none",
    color_mode: str = "background",
    text_mode: str = "auto",
    thresholds: list | None = None,
) -> Dict[str, Any]:
    """Build a Grafana stat panel definition."""
    if thresholds is None:
        thresholds = [{"color": "green", "value": None}]
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "gridPos": {"h": height, "w": width, "x": grid_x, "y": grid_y},
        "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
        "targets": [
            {
                "expr": expr,
                "legendFormat": title,
                "refId": "A",
            }
        ],
        "fieldConfig": {
            "defaults": {
                "unit": unit,
                "thresholds": {"mode": "absolute", "steps": thresholds},
            }
        },
        "options": {
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": text_mode,
            "colorMode": color_mode,
        },
    }


def get_dashboard_model(datasource_uid: str = "${DS_PROMETHEUS}") -> Dict[str, Any]:
    """Return the installation status dashboard as a Python dict.

    Args:
        datasource_uid: UID of the Prometheus/Mimir datasource.

    Returns:
        Complete Grafana dashboard model ready for provisioning.
    """
    return {
        "dashboard": {
            "id": None,
            "uid": DASHBOARD_UID,
            "title": DASHBOARD_TITLE,
            "tags": ["contextcore", "installation"],
            "style": "dark",
            "timezone": "browser",
            "editable": True,
            "graphTooltip": 0,
            "time": {"from": "now-5m", "to": "now"},
            "refresh": "5s",
            "version": 1,
            "templating": {
                "list": [
                    {
                        "name": "cluster",
                        "type": "query",
                        "datasource": {"type": "prometheus", "uid": datasource_uid},
                        "definition": "label_values(contextcore_install_step_status, cluster)",
                        "query": "label_values(contextcore_install_step_status, cluster)",
                        "current": {"text": "wayfinder-dev", "value": "wayfinder-dev"},
                        "refresh": 2,
                        "includeAll": False,
                        "multi": False,
                        "sort": 1,
                        "hide": 0,
                        "label": "Cluster",
                    }
                ]
            },
            "panels": [
                _stat_panel(
                    100,
                    "Installation Progress",
                    'contextcore_install_progress_ratio{cluster="$cluster"} * 100',
                    grid_x=0, grid_y=0, width=6,
                    unit="percent",
                    thresholds=[
                        {"color": "red", "value": None},
                        {"color": "yellow", "value": 50},
                        {"color": "green", "value": 100},
                    ],
                ),
                _stat_panel(
                    101,
                    "Current Step",
                    'label_replace(contextcore_install_step_status{cluster="$cluster"} == 1, '
                    '"current_step", "$1", "step", "(.*)")',
                    grid_x=6, grid_y=0, width=6,
                    text_mode="name",
                    thresholds=[{"color": "blue", "value": None}],
                ),
                _stat_panel(
                    102,
                    "Steps Completed",
                    'count(contextcore_install_step_status{cluster="$cluster"} == 2)',
                    grid_x=12, grid_y=0, width=4,
                    color_mode="value",
                ),
                _stat_panel(
                    103,
                    "Failed Steps",
                    'count(contextcore_install_step_status{cluster="$cluster"} == 3) or vector(0)',
                    grid_x=16, grid_y=0, width=4,
                    thresholds=[
                        {"color": "green", "value": None},
                        {"color": "red", "value": 1},
                    ],
                ),
                _stat_panel(
                    104,
                    "Installation Duration",
                    'time() - contextcore_install_started_timestamp{cluster="$cluster"}',
                    grid_x=20, grid_y=0, width=4,
                    unit="dtdurations",
                    color_mode="value",
                ),
                {
                    "id": 105,
                    "type": "status-history",
                    "title": "Installation Step Timeline",
                    "gridPos": {"h": 6, "w": 24, "x": 0, "y": 4},
                    "datasource": {"type": "prometheus", "uid": datasource_uid},
                    "targets": [
                        {
                            "expr": 'contextcore_install_step_status{cluster="$cluster"}',
                            "legendFormat": "{{step}}",
                            "refId": "A",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "none",
                            "custom": {"fillOpacity": 80, "lineWidth": 1, "spanNulls": False},
                            "mappings": [
                                {"options": {"0": {"text": "Pending", "color": "gray"}}, "type": "value"},
                                {"options": {"1": {"text": "In Progress", "color": "blue"}}, "type": "value"},
                                {"options": {"2": {"text": "Completed", "color": "green"}}, "type": "value"},
                                {"options": {"3": {"text": "Failed", "color": "red"}}, "type": "value"},
                            ],
                            "thresholds": {"mode": "absolute", "steps": [{"color": "gray", "value": None}]},
                        }
                    },
                    "options": {
                        "legend": {"displayMode": "list", "placement": "bottom"},
                        "tooltip": {"mode": "multi"},
                    },
                },
                {
                    "id": 106,
                    "type": "barchart",
                    "title": "Step Duration",
                    "gridPos": {"h": 6, "w": 12, "x": 0, "y": 10},
                    "datasource": {"type": "prometheus", "uid": datasource_uid},
                    "targets": [
                        {
                            "expr": 'contextcore_install_step_duration_seconds{cluster="$cluster"}',
                            "legendFormat": "{{step}}",
                            "refId": "A",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "unit": "s",
                            "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                        }
                    },
                    "options": {
                        "legend": {"displayMode": "list", "placement": "bottom"},
                        "tooltip": {"mode": "multi"},
                    },
                },
                {
                    "id": 107,
                    "type": "table",
                    "title": "Step Attempts",
                    "gridPos": {"h": 6, "w": 12, "x": 12, "y": 10},
                    "datasource": {"type": "prometheus", "uid": datasource_uid},
                    "targets": [
                        {
                            "expr": 'contextcore_install_step_attempts_total{cluster="$cluster"}',
                            "format": "table",
                            "instant": True,
                            "refId": "A",
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {"unit": "none"},
                    },
                    "options": {"showHeader": True},
                    "transformations": [
                        {
                            "id": "organize",
                            "options": {
                                "excludeByName": {
                                    "Time": True,
                                    "__name__": True,
                                    "cluster": True,
                                    "instance": True,
                                    "job": True,
                                },
                                "renameByName": {"step": "Step", "Value": "Attempts"},
                            },
                        }
                    ],
                },
            ],
            "annotations": {
                "list": [
                    {
                        "builtIn": 1,
                        "datasource": "-- Grafana --",
                        "enable": True,
                        "hide": True,
                        "iconColor": "rgba(0, 211, 255, 1)",
                        "name": "Annotations & Alerts",
                        "type": "dashboard",
                    }
                ]
            },
        }
    }


def get_dashboard_json(datasource_uid: str = "${DS_PROMETHEUS}", indent: int = 2) -> str:
    """Return the dashboard model as a JSON string.

    Args:
        datasource_uid: UID of the Prometheus/Mimir datasource.
        indent: JSON indentation level.

    Returns:
        JSON string of the dashboard model.
    """
    return json.dumps(get_dashboard_model(datasource_uid), indent=indent)
