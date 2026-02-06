"""
Dashboard discovery module for auto-discovering dashboards from filesystem and entry points.

This module provides functionality to automatically discover Grafana dashboards from:
1. Filesystem locations (grafana/provisioning/dashboards/{extension}/*.json)
2. Python entry points (contextcore.dashboards group)

Example usage:
    >>> from contextcore.dashboards.discovery import discover_all_dashboards, list_extensions
    >>> dashboards = discover_all_dashboards()
    >>> print(f"Found {len(dashboards)} dashboards")
    >>> for ext in list_extensions():
    ...     print(f"  {ext['name']}: {ext['count']} dashboards")
"""

import json
import logging
from dataclasses import dataclass, field
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union

logger = logging.getLogger(__name__)

__all__ = [
    "EXTENSION_REGISTRY",
    "DashboardConfig",
    "discover_from_filesystem",
    "discover_from_entry_points",
    "discover_all_dashboards",
    "list_extensions",
    "get_dashboard_root",
]


# Extension registry mapping extension keys to metadata
# Matches the providers in grafana/provisioning/dashboards/dashboards.yaml
EXTENSION_REGISTRY: Dict[str, Dict[str, str]] = {
    "core": {
        "name": "Wayfinder Core",
        "folder": "Wayfinder",
        "folder_uid": "wayfinder-core",
        "description": "Core project management dashboards",
    },
    "squirrel": {
        "name": "Squirrel (Skills)",
        "folder": "Wayfinder / Squirrel",
        "folder_uid": "wayfinder-squirrel",
        "description": "Skills library and value capabilities dashboards",
    },
    "rabbit": {
        "name": "Rabbit (Alert Automation)",
        "folder": "Wayfinder / Rabbit",
        "folder_uid": "wayfinder-rabbit",
        "description": "Workflow and alert automation dashboards",
    },
    "beaver": {
        "name": "Beaver (LLM Abstraction)",
        "folder": "Wayfinder / Beaver",
        "folder_uid": "wayfinder-beaver",
        "description": "LLM provider and contractor progress dashboards",
    },
    "fox": {
        "name": "Fox (Context Enrichment)",
        "folder": "Wayfinder / Fox",
        "folder_uid": "wayfinder-fox",
        "description": "Alert automation with context enrichment dashboards",
    },
    "coyote": {
        "name": "Coyote (Multi-Agent Pipeline)",
        "folder": "Wayfinder / Coyote",
        "folder_uid": "wayfinder-coyote",
        "description": "Multi-agent incident resolution dashboards",
    },
    "owl": {
        "name": "Owl (Grafana Plugins)",
        "folder": "Wayfinder / Owl",
        "folder_uid": "wayfinder-owl",
        "description": "Grafana plugin monitoring and configuration dashboards",
    },
    "external": {
        "name": "External",
        "folder": "Wayfinder / External",
        "folder_uid": "wayfinder-external",
        "description": "Third-party and community dashboards",
    },
}


@dataclass
class DashboardConfig:
    """
    Configuration for a Grafana dashboard with auto-discovery support.

    Attributes:
        uid: Unique identifier for the dashboard
        title: Display title of the dashboard
        description: Optional description text
        tags: List of tags for categorization
        extension: Extension this dashboard belongs to
        file_path: Optional explicit file path to dashboard JSON
        file_name: Original filename (for backwards compatibility)
    """

    uid: str
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    extension: str = "core"
    file_path: Optional[Path] = None
    file_name: Optional[str] = None

    @property
    def effective_file_path(self) -> Path:
        """
        Resolve the effective file path for this dashboard.

        Returns the explicit file_path if set and exists, otherwise constructs
        the expected path based on extension and file_name or uid.

        Returns:
            Path to the dashboard JSON file
        """
        if self.file_path and self.file_path.exists():
            return self.file_path

        # Use file_name if available, otherwise construct from uid
        filename = self.file_name or f"{self.uid}.json"
        return get_dashboard_root() / self.extension / filename

    @property
    def folder(self) -> str:
        """Get the Grafana folder name for this dashboard."""
        return EXTENSION_REGISTRY.get(self.extension, {}).get("folder", "Wayfinder")

    @property
    def folder_uid(self) -> str:
        """Get the Grafana folder UID for this dashboard."""
        return EXTENSION_REGISTRY.get(self.extension, {}).get(
            "folder_uid", "wayfinder"
        )


def get_dashboard_root() -> Path:
    """
    Get the root directory for dashboard JSON files.

    Searches for the grafana/provisioning/dashboards directory relative to:
    1. Current working directory
    2. Parent directories up to 5 levels

    Returns:
        Path to the dashboards root directory

    Raises:
        FileNotFoundError: If dashboard directory cannot be found
    """
    # Try relative to cwd first
    candidates = [
        Path.cwd() / "grafana" / "provisioning" / "dashboards",
        Path(__file__).parent.parent.parent.parent
        / "grafana"
        / "provisioning"
        / "dashboards",
    ]

    # Also try parent directories
    cwd = Path.cwd()
    for _ in range(5):
        candidates.append(cwd / "grafana" / "provisioning" / "dashboards")
        cwd = cwd.parent

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    # Fall back to default path (may not exist)
    return Path("grafana/provisioning/dashboards")


def discover_from_filesystem(
    extension: Optional[str] = None,
) -> Generator[DashboardConfig, None, None]:
    """
    Discover dashboards from filesystem JSON files.

    Scans grafana/provisioning/dashboards/{extension}/ for *.json files
    and parses them into DashboardConfig objects.

    Args:
        extension: Optional extension to filter by. If None, scans all extensions.

    Yields:
        DashboardConfig: Parsed dashboard configurations

    Example:
        >>> list(discover_from_filesystem("core"))
        [DashboardConfig(uid='cc-core-portfolio-overview', title='Project Portfolio Overview', ...)]
    """
    extensions_to_scan = [extension] if extension else list(EXTENSION_REGISTRY.keys())
    dashboard_root = get_dashboard_root()

    for ext in extensions_to_scan:
        if ext not in EXTENSION_REGISTRY:
            logger.warning(f"Unknown extension '{ext}', skipping")
            continue

        dashboard_dir = dashboard_root / ext
        logger.debug(f"Scanning for dashboards in {dashboard_dir}")

        if not dashboard_dir.is_dir():
            logger.debug(f"Directory {dashboard_dir} does not exist, skipping")
            continue

        # Scan all JSON files in the extension directory
        for json_file in sorted(dashboard_dir.glob("*.json")):
            config = _parse_dashboard_json(json_file, ext)
            if config:
                yield config


def discover_from_entry_points(
    extension: Optional[str] = None,
) -> Generator[DashboardConfig, None, None]:
    """
    Discover dashboards from Python entry points.

    Loads entry points from the 'contextcore.dashboards' group and calls
    their get_dashboards() function to retrieve dashboard configurations.

    Args:
        extension: Optional extension to filter by

    Yields:
        DashboardConfig: Dashboard configurations from entry points

    Example:
        >>> list(discover_from_entry_points("squirrel"))
        [DashboardConfig(uid='skills-overview', title='Skills Overview', ...)]
    """
    logger.debug("Discovering dashboards from entry points")

    try:
        eps = entry_points(group="contextcore.dashboards")
    except TypeError:
        # Fallback for older Python versions
        all_eps = entry_points()
        eps = all_eps.get("contextcore.dashboards", [])

    for entry_point in eps:
        # Filter by extension if specified
        if extension and entry_point.name != extension:
            continue

        try:
            # Load the entry point module
            module = entry_point.load()

            # Call get_dashboards() function
            if not hasattr(module, "get_dashboards"):
                logger.warning(
                    f"Entry point {entry_point.name} missing get_dashboards() function"
                )
                continue

            dashboards = module.get_dashboards()

            # Convert each dashboard dict to DashboardConfig
            for dashboard_data in dashboards:
                if _validate_entry_point_dashboard(dashboard_data):
                    config = DashboardConfig(
                        uid=dashboard_data["uid"],
                        title=dashboard_data.get("title", ""),
                        description=dashboard_data.get("description", ""),
                        tags=dashboard_data.get("tags", []),
                        extension=entry_point.name,
                        file_name=dashboard_data.get("file_name"),
                    )
                    yield config

        except Exception as e:
            logger.error(f"Failed to load entry point {entry_point.name}: {e}")


def discover_all_dashboards(extension: Optional[str] = None) -> List[DashboardConfig]:
    """
    Discover all dashboards from both filesystem and entry points.

    Combines results from filesystem and entry point discovery, with entry points
    taking precedence over filesystem when UIDs conflict (deduplication).

    Args:
        extension: Optional extension to filter by

    Returns:
        List of unique DashboardConfig objects

    Example:
        >>> dashboards = discover_all_dashboards()
        >>> len(dashboards)
        11
        >>> dashboards[0].uid
        'cc-core-portfolio-overview'
    """
    seen_uids: set[str] = set()
    dashboards: List[DashboardConfig] = []

    # Entry points take precedence - process them first
    for config in discover_from_entry_points(extension):
        if config.uid not in seen_uids:
            seen_uids.add(config.uid)
            dashboards.append(config)
            logger.debug(f"Added entry point dashboard: {config.uid}")

    # Add filesystem dashboards that aren't already present
    for config in discover_from_filesystem(extension):
        if config.uid not in seen_uids:
            seen_uids.add(config.uid)
            dashboards.append(config)
            logger.debug(f"Added filesystem dashboard: {config.uid}")
        else:
            logger.debug(f"Skipped duplicate dashboard: {config.uid}")

    logger.info(f"Discovered {len(dashboards)} total dashboards")
    return dashboards


def list_extensions() -> List[Dict[str, Union[str, int]]]:
    """
    List all extensions with their dashboard counts.

    Returns information about each registered extension including
    the count of dashboards discovered for that extension.

    Returns:
        List of dictionaries with extension metadata and counts

    Example:
        >>> extensions = list_extensions()
        >>> extensions[0]
        {'name': 'Wayfinder Core', 'extension': 'core', 'count': 5, ...}
    """
    extension_stats = []

    for ext_key, metadata in EXTENSION_REGISTRY.items():
        # Count dashboards for this extension
        dashboards = list(discover_from_filesystem(ext_key))
        ep_dashboards = list(discover_from_entry_points(ext_key))

        extension_stats.append(
            {
                "name": metadata["name"],
                "extension": ext_key,
                "folder": metadata["folder"],
                "folder_uid": metadata["folder_uid"],
                "description": metadata.get("description", ""),
                "count": len(dashboards) + len(ep_dashboards),
                "filesystem_count": len(dashboards),
                "entry_point_count": len(ep_dashboards),
            }
        )

    return extension_stats


def _parse_dashboard_json(file_path: Path, extension: str) -> Optional[DashboardConfig]:
    """
    Parse a dashboard JSON file into a DashboardConfig object.

    Args:
        file_path: Path to the JSON file
        extension: Extension this dashboard belongs to

    Returns:
        DashboardConfig object or None if parsing failed
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            dashboard_data = json.load(f)

        # Validate required fields
        if "uid" not in dashboard_data:
            logger.warning(f"Missing 'uid' field in {file_path}")
            return None

        return DashboardConfig(
            uid=dashboard_data["uid"],
            title=dashboard_data.get("title", ""),
            description=dashboard_data.get("description", ""),
            tags=dashboard_data.get("tags", []),
            extension=extension,
            file_path=file_path,
            file_name=file_path.name,
        )

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error parsing {file_path}: {e}")

    return None


def _validate_entry_point_dashboard(dashboard_data: Dict[str, Any]) -> bool:
    """
    Validate dashboard data from an entry point.

    Args:
        dashboard_data: Dictionary containing dashboard information

    Returns:
        True if valid, False otherwise
    """
    if not isinstance(dashboard_data, dict):
        logger.warning("Dashboard data is not a dictionary")
        return False

    if "uid" not in dashboard_data:
        logger.warning("Missing 'uid' field in entry point dashboard data")
        return False

    if not isinstance(dashboard_data["uid"], str) or not dashboard_data["uid"].strip():
        logger.warning("Invalid 'uid' field in entry point dashboard data")
        return False

    return True
