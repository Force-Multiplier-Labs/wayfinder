"""
Backup and restore functionality for ContextCore.

Provides:
- Export Grafana dashboards
- Export datasource configurations
- Export ContextCore state
- Restore from backup directory
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx


@dataclass
class BackupManifest:
    """Metadata about a backup."""

    created_at: str
    version: str = "1.0"
    dashboards_count: int = 0
    datasources_count: int = 0
    has_state: bool = False

    def to_dict(self) -> dict:
        return {
            "created_at": self.created_at,
            "version": self.version,
            "dashboards_count": self.dashboards_count,
            "datasources_count": self.datasources_count,
            "has_state": self.has_state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BackupManifest":
        return cls(
            created_at=data.get("created_at", ""),
            version=data.get("version", "1.0"),
            dashboards_count=data.get("dashboards_count", 0),
            datasources_count=data.get("datasources_count", 0),
            has_state=data.get("has_state", False),
        )


@dataclass
class BackupResult:
    """Result of a backup operation."""

    success: bool
    path: Path
    manifest: BackupManifest
    errors: list[str]


def export_grafana_dashboards(
    backup_dir: Path,
    grafana_url: str = "http://localhost:3000",
    auth: tuple[str, str] = ("admin", "admin"),
) -> tuple[int, list[str]]:
    """
    Export all Grafana dashboards to backup directory.

    Returns:
        Tuple of (count, errors)
    """
    dashboards_dir = backup_dir / "dashboards"
    dashboards_dir.mkdir(parents=True, exist_ok=True)
    errors = []
    count = 0

    try:
        with httpx.Client(timeout=10) as client:
            # Get list of dashboards
            response = client.get(
                f"{grafana_url}/api/search?type=dash-db",
                auth=auth,
            )
            if response.status_code != 200:
                errors.append(f"Failed to list dashboards: HTTP {response.status_code}")
                return 0, errors

            dashboards = response.json()

            for db in dashboards:
                uid = db.get("uid")
                if not uid:
                    continue

                # Get full dashboard
                response = client.get(
                    f"{grafana_url}/api/dashboards/uid/{uid}",
                    auth=auth,
                )
                if response.status_code == 200:
                    data = response.json()
                    filepath = dashboards_dir / f"{uid}.json"
                    with open(filepath, "w") as f:
                        json.dump(data, f, indent=2)
                    count += 1
                else:
                    errors.append(f"Failed to export dashboard {uid}")

    except httpx.ConnectError:
        errors.append("Could not connect to Grafana")
    except Exception as e:
        errors.append(f"Error exporting dashboards: {e}")

    return count, errors


def export_grafana_datasources(
    backup_dir: Path,
    grafana_url: str = "http://localhost:3000",
    auth: tuple[str, str] = ("admin", "admin"),
) -> tuple[int, list[str]]:
    """
    Export Grafana datasources to backup directory.

    Returns:
        Tuple of (count, errors)
    """
    datasources_dir = backup_dir / "datasources"
    datasources_dir.mkdir(parents=True, exist_ok=True)
    errors = []

    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(
                f"{grafana_url}/api/datasources",
                auth=auth,
            )
            if response.status_code == 200:
                datasources = response.json()
                filepath = datasources_dir / "datasources.json"
                with open(filepath, "w") as f:
                    json.dump(datasources, f, indent=2)
                return len(datasources), errors
            else:
                errors.append(f"Failed to export datasources: HTTP {response.status_code}")
                return 0, errors
    except httpx.ConnectError:
        errors.append("Could not connect to Grafana")
        return 0, errors
    except Exception as e:
        errors.append(f"Error exporting datasources: {e}")
        return 0, errors


def backup(
    output_dir: Optional[Path] = None,
    grafana_url: str = "http://localhost:3000",
    grafana_auth: tuple[str, str] = ("admin", "admin"),
) -> BackupResult:
    """
    Create a full backup of ContextCore state.

    Args:
        output_dir: Base directory for backups (default: ./backups/YYYYMMDD-HHMMSS)
        grafana_url: Grafana base URL
        grafana_auth: Grafana authentication (username, password)

    Returns:
        BackupResult with path and manifest
    """
    # Create timestamped backup directory
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    if output_dir is None:
        output_dir = Path("backups") / timestamp
    else:
        output_dir = Path(output_dir) / timestamp

    output_dir.mkdir(parents=True, exist_ok=True)

    errors = []

    # Export dashboards
    dashboards_count, dashboard_errors = export_grafana_dashboards(
        output_dir, grafana_url, grafana_auth
    )
    errors.extend(dashboard_errors)

    # Export datasources
    datasources_count, datasource_errors = export_grafana_datasources(
        output_dir, grafana_url, grafana_auth
    )
    errors.extend(datasource_errors)

    # Create manifest
    manifest = BackupManifest(
        created_at=datetime.now(timezone.utc).isoformat(),
        dashboards_count=dashboards_count,
        datasources_count=datasources_count,
    )

    # Write manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest.to_dict(), f, indent=2)

    return BackupResult(
        success=len(errors) == 0,
        path=output_dir,
        manifest=manifest,
        errors=errors,
    )


def import_grafana_dashboards(
    backup_dir: Path,
    grafana_url: str = "http://localhost:3000",
    auth: tuple[str, str] = ("admin", "admin"),
) -> tuple[int, list[str]]:
    """
    Import dashboards from backup directory to Grafana.

    Returns:
        Tuple of (count, errors)
    """
    dashboards_dir = backup_dir / "dashboards"
    if not dashboards_dir.exists():
        return 0, ["No dashboards directory in backup"]

    errors = []
    count = 0

    try:
        with httpx.Client(timeout=10) as client:
            for filepath in dashboards_dir.glob("*.json"):
                with open(filepath) as f:
                    data = json.load(f)

                # Prepare import payload
                dashboard = data.get("dashboard", data)
                payload = {
                    "dashboard": dashboard,
                    "overwrite": True,
                }

                response = client.post(
                    f"{grafana_url}/api/dashboards/db",
                    auth=auth,
                    json=payload,
                )
                if response.status_code == 200:
                    count += 1
                else:
                    errors.append(f"Failed to import {filepath.name}: HTTP {response.status_code}")

    except httpx.ConnectError:
        errors.append("Could not connect to Grafana")
    except Exception as e:
        errors.append(f"Error importing dashboards: {e}")

    return count, errors


def restore(
    backup_path: Path,
    grafana_url: str = "http://localhost:3000",
    grafana_auth: tuple[str, str] = ("admin", "admin"),
) -> tuple[bool, list[str]]:
    """
    Restore from a backup directory.

    Args:
        backup_path: Path to backup directory
        grafana_url: Grafana base URL
        grafana_auth: Grafana authentication

    Returns:
        Tuple of (success, errors)
    """
    backup_path = Path(backup_path)

    if not backup_path.exists():
        return False, [f"Backup path does not exist: {backup_path}"]

    errors = []

    # Import dashboards
    count, dashboard_errors = import_grafana_dashboards(
        backup_path, grafana_url, grafana_auth
    )
    errors.extend(dashboard_errors)

    if count > 0:
        errors.insert(0, f"Imported {count} dashboard(s)")

    return len([e for e in errors if not e.startswith("Imported")]) == 0, errors


def list_backups(base_dir: Optional[Path] = None) -> list[tuple[Path, BackupManifest]]:
    """
    List available backups.

    Args:
        base_dir: Base directory to search (default: ./backups)

    Returns:
        List of (path, manifest) tuples sorted by date descending
    """
    if base_dir is None:
        base_dir = Path("backups")

    if not base_dir.exists():
        return []

    backups = []

    for entry in base_dir.iterdir():
        if entry.is_dir():
            manifest_path = entry / "manifest.json"
            if manifest_path.exists():
                try:
                    with open(manifest_path) as f:
                        data = json.load(f)
                    manifest = BackupManifest.from_dict(data)
                    backups.append((entry, manifest))
                except Exception:
                    pass

    # Sort by creation date descending
    backups.sort(key=lambda x: x[1].created_at, reverse=True)

    return backups
