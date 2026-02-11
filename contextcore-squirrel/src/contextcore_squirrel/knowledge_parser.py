"""
Squirrel Knowledge Parser

Parses capability YAML files and converts structured capability data
into Pydantic models for emission. Handles endpoints, skills, tools,
workflows, processes, and projects with robust error handling.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, ClassVar, List, Optional, Type

import yaml
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Pydantic Model Definitions ---


class CapabilityItem(BaseModel):
    """Base class for all capability items."""

    id: str
    name: str
    category: str  # endpoint|skill|tool|workflow|process|project
    description: str
    tags: str = ""  # Comma-separated string
    tier: str = "personal"  # public|widely_shared|narrowly_shared|personal
    source_file: str = ""
    token_budget: int = 0


class Endpoint(CapabilityItem):
    """Represents an API endpoint or service endpoint."""

    url: str = ""
    port: int = 0
    protocol: str = "http"
    authentication: str = "none"
    related_skills: str = ""


class Skill(CapabilityItem):
    """Represents a specific skill or capability."""

    location: str = ""
    skill_category: str = ""
    use_when: str = ""
    triggers: str = ""


class Tool(CapabilityItem):
    """Represents a tool, script, or utility."""

    tool_type: str = ""  # script|directory|cli|config
    location: str = ""
    usage: str = ""
    related_skills: str = ""


class Workflow(CapabilityItem):
    """Represents a multi-step process or workflow."""

    workflow_type: str = ""  # methodology|investigation|automation
    step_count: int = 0
    steps_summary: str = ""
    related_skills: str = ""


class Process(CapabilityItem):
    """Represents a process, convention, or methodology."""

    process_type: str = ""  # convention|methodology|checklist
    rules_summary: str = ""
    is_anti_pattern: bool = False


class Project(CapabilityItem):
    """Represents a project or codebase."""

    path: str = ""
    status: str = "active"
    key_docs: str = ""
    related_skills: str = ""


class SquirrelIndex(BaseModel):
    """Complete index of all capability data from a source directory."""

    tier: str
    source_path: str = ""
    endpoints: List[Endpoint] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    tools: List[Tool] = Field(default_factory=list)
    workflows: List[Workflow] = Field(default_factory=list)
    processes: List[Process] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)

    def get_stats(self) -> dict[str, int]:
        """Returns a dictionary of statistics for the index."""
        return {
            "endpoints": len(self.endpoints),
            "skills": len(self.skills),
            "tools": len(self.tools),
            "workflows": len(self.workflows),
            "processes": len(self.processes),
            "projects": len(self.projects),
        }

    def total_items(self) -> int:
        """Returns the total number of items across all categories."""
        return sum(self.get_stats().values())


# --- Utility Functions ---


def _flatten_list_to_string(data: Any, default: str = "") -> str:
    """
    Converts a list (or other data) to a comma-separated string.

    Args:
        data: The data to flatten (list, str, int, float, or None)
        default: Default value if data is None or unexpected type

    Returns:
        Comma-separated string representation
    """
    if isinstance(data, list):
        return ",".join(str(item).strip() for item in data if item)
    elif isinstance(data, (str, int, float)):
        return str(data).strip()
    elif data is None:
        return default
    else:
        logger.warning(f"Unexpected type for list flattening: {type(data)}. Returning default.")
        return default


def _parse_authentication(auth_data: Any) -> str:
    """
    Parses authentication data, flattening dictionaries to a string.

    Args:
        auth_data: Authentication data from YAML (dict, str, or other)

    Returns:
        String representation of authentication type
    """
    if isinstance(auth_data, dict):
        return auth_data.get("type", "none")
    elif isinstance(auth_data, str):
        return auth_data
    else:
        return "none"


def _get_tier_from_path(path: Path) -> str:
    """
    Determines the tier from the directory path structure.

    Args:
        path: Path to analyze for tier information

    Returns:
        Tier string (public|widely_shared|narrowly_shared|personal)
    """
    path_parts = [part.lower() for part in path.parts]

    if "public" in path_parts:
        return "public"
    elif "widely_shared" in path_parts:
        return "widely_shared"
    elif "narrowly_shared" in path_parts:
        return "narrowly_shared"
    elif "personal" in path_parts:
        return "personal"
    else:
        logger.warning(f"Could not determine tier from path: {path}. Defaulting to 'personal'.")
        return "personal"


def _safe_int_conversion(value: Any, default: int = 0, field_name: str = "field") -> int:
    """
    Safely converts a value to integer with logging on failure.

    Args:
        value: Value to convert
        default: Default value if conversion fails
        field_name: Name of field for logging purposes

    Returns:
        Integer value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        logger.warning(f"Invalid {field_name} '{value}'. Using default {default}.")
        return default


# --- Type-specific field names that need special handling ---

_LIST_FIELDS = {"related_skills"}
_AUTH_FIELDS = {"authentication"}
_INT_FIELDS = {"step_count", "port"}
_BOOL_FIELDS = {"is_anti_pattern"}


# --- Individual Parse Functions ---


def _parse_capability_yaml(
    file_path: Path,
    tier: str,
    item_type: Type[CapabilityItem],
    category: str,
) -> list:
    """
    Generic function to parse a single YAML file for a capability type.

    Args:
        file_path: Path to the YAML file
        tier: Capability tier (public|widely_shared|narrowly_shared|personal)
        item_type: Pydantic model type to instantiate
        category: Category string for the items

    Returns:
        List of parsed capability items
    """
    items: list = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

            if not data:
                logger.info(f"Empty YAML file: {file_path}")
                return items

            # Handle both formats:
            # 1. Direct list: [item1, item2, ...]
            # 2. Keyed list: endpoints: [item1, item2, ...] or skills: [...]
            if isinstance(data, dict):
                possible_keys = [f"{category}s", category, file_path.stem]
                items_list = None
                for key in possible_keys:
                    if key in data and isinstance(data[key], list):
                        items_list = data[key]
                        break

                if items_list is None:
                    for key, value in data.items():
                        if isinstance(value, list):
                            items_list = value
                            break

                if items_list is None:
                    logger.warning(
                        f"YAML file {file_path} does not contain a list of items. Skipping."
                    )
                    return items

                data = items_list
            elif not isinstance(data, list):
                logger.warning(
                    f"YAML file {file_path} does not contain a list of items. Skipping."
                )
                return items

            for item_index, item_data in enumerate(data):
                if not isinstance(item_data, dict):
                    logger.warning(f"Skipping non-dictionary item #{item_index} in {file_path}")
                    continue

                try:
                    # Validate required fields
                    required_fields = ["id", "name", "description"]
                    for field_name in required_fields:
                        if field_name not in item_data or not str(item_data[field_name]).strip():
                            raise ValueError(f"Missing or empty required field: {field_name}")

                    # Calculate relative source file path
                    try:
                        relative_path = file_path.relative_to(file_path.parents[2])
                    except (ValueError, IndexError):
                        relative_path = Path(file_path.name)

                    # Prepare base arguments
                    kwargs: dict[str, Any] = {
                        "id": str(item_data["id"]).strip(),
                        "name": str(item_data["name"]).strip(),
                        "description": str(item_data["description"]).strip(),
                        "category": category,
                        "tier": tier,
                        "source_file": relative_path.as_posix(),
                        "tags": _flatten_list_to_string(item_data.get("tags", "")),
                        "token_budget": _safe_int_conversion(
                            item_data.get("token_budget", 0),
                            0,
                            f"token_budget for {item_data['id']}",
                        ),
                    }

                    # Map type-specific fields from the Pydantic model
                    for field_name, field_info in item_type.model_fields.items():
                        if field_name in kwargs:
                            continue

                        yaml_value = item_data.get(field_name)

                        if yaml_value is not None:
                            if field_name in _LIST_FIELDS:
                                kwargs[field_name] = _flatten_list_to_string(yaml_value)
                            elif field_name in _AUTH_FIELDS:
                                kwargs[field_name] = _parse_authentication(yaml_value)
                            elif field_name in _INT_FIELDS:
                                kwargs[field_name] = _safe_int_conversion(
                                    yaml_value, 0, f"{field_name} for {item_data['id']}"
                                )
                            elif field_name in _BOOL_FIELDS:
                                if isinstance(yaml_value, bool):
                                    kwargs[field_name] = yaml_value
                                else:
                                    kwargs[field_name] = str(yaml_value).lower() in (
                                        "true",
                                        "yes",
                                        "1",
                                    )
                            else:
                                kwargs[field_name] = str(yaml_value) if yaml_value else ""

                    item = item_type(**kwargs)
                    items.append(item)

                except (ValueError, KeyError, TypeError) as e:
                    logger.warning(
                        f"Skipping item #{item_index} in {file_path} due to error: {e}. "
                        f"Item ID: {item_data.get('id', 'N/A')}"
                    )
                    continue

    except FileNotFoundError:
        logger.warning(f"YAML file not found: {file_path}")
    except yaml.YAMLError as e:
        logger.warning(f"Failed to parse YAML file {file_path}: {e}")
    except PermissionError as e:
        logger.error(f"Permission denied for file {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing {file_path}: {e}")

    logger.info(f"Parsed {len(items)} {category}(s) from {file_path.name}")
    return items


def parse_endpoints_yaml(path: Path, tier: str) -> List[Endpoint]:
    """Parse endpoints.yaml file and return list of Endpoint objects."""
    return _parse_capability_yaml(path, tier, Endpoint, "endpoint")


def parse_skills_yaml(path: Path, tier: str) -> List[Skill]:
    """Parse skills.yaml file and return list of Skill objects."""
    return _parse_capability_yaml(path, tier, Skill, "skill")


def parse_tools_yaml(path: Path, tier: str) -> List[Tool]:
    """Parse tools.yaml file and return list of Tool objects."""
    return _parse_capability_yaml(path, tier, Tool, "tool")


def parse_workflows_yaml(path: Path, tier: str) -> List[Workflow]:
    """Parse workflows.yaml file and return list of Workflow objects."""
    return _parse_capability_yaml(path, tier, Workflow, "workflow")


def parse_processes_yaml(path: Path, tier: str) -> List[Process]:
    """Parse processes.yaml file and return list of Process objects."""
    return _parse_capability_yaml(path, tier, Process, "process")


def parse_projects_yaml(path: Path, tier: str) -> List[Project]:
    """Parse projects.yaml file and return list of Project objects."""
    return _parse_capability_yaml(path, tier, Project, "project")


# --- Master Parse Function ---


def parse_capability_index(index_path: Path) -> SquirrelIndex:
    """
    Parse entire capability index directory and return SquirrelIndex object.

    Args:
        index_path: Path to the root directory of the capability index

    Returns:
        SquirrelIndex object containing all parsed capabilities
    """
    if not index_path.exists():
        logger.error(f"Index path does not exist: {index_path}")
        return SquirrelIndex(tier="unknown", source_path=str(index_path))

    if not index_path.is_dir():
        logger.error(f"Index path is not a directory: {index_path}")
        return SquirrelIndex(tier="unknown", source_path=str(index_path))

    tier = _get_tier_from_path(index_path)
    logger.info(f"Processing index at: {index_path} with detected tier: {tier}")

    index_data = SquirrelIndex(tier=tier, source_path=str(index_path.resolve()))

    # Check for capabilities subdirectory (common structure)
    capabilities_dir = index_path / "capabilities"
    if capabilities_dir.exists() and capabilities_dir.is_dir():
        logger.info(f"Found capabilities subdirectory, using: {capabilities_dir}")
        index_path = capabilities_dir

    # Define the mapping from filenames to parsing functions
    file_parsers = {
        "endpoints.yaml": (parse_endpoints_yaml, "endpoints"),
        "skills.yaml": (parse_skills_yaml, "skills"),
        "tools.yaml": (parse_tools_yaml, "tools"),
        "workflows.yaml": (parse_workflows_yaml, "workflows"),
        "processes.yaml": (parse_processes_yaml, "processes"),
        "projects.yaml": (parse_projects_yaml, "projects"),
    }

    for filename, (parser_func, attr_name) in file_parsers.items():
        file_path = index_path / filename

        if not file_path.exists():
            logger.info(f"Optional file not found: {filename}")
            continue

        try:
            parsed_items = parser_func(file_path, tier)
            setattr(index_data, attr_name, parsed_items)
        except Exception as e:
            logger.error(f"Failed to parse {filename}: {e}")
            continue

    total_items = index_data.total_items()
    logger.info(f"Successfully parsed {total_items} total items from {index_path}")

    return index_data


class KnowledgeParser:
    """High-level wrapper for parsing Squirrel knowledge indexes."""

    def __init__(self, index_path: Path | str) -> None:
        self.index_path = Path(index_path)

    def parse(self) -> SquirrelIndex:
        """Parse the capability index and return a SquirrelIndex."""
        return parse_capability_index(self.index_path)

    def parse_json(self) -> str:
        """Parse the capability index and return JSON string."""
        index = self.parse()
        return json.dumps(index.model_dump(), indent=2, default=str)
