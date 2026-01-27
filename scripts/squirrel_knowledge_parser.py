#!/usr/bin/env python3
"""
Squirrel Knowledge Parser

A parser for capability YAML files that converts structured capability data
into dataclasses for emission. Handles endpoints, skills, tools, workflows,
processes, and projects with robust error handling.

Usage:
    python squirrel_knowledge_parser.py ./skills/dev-tour-guide/index/ --output /tmp/squirrel.json
    python squirrel_knowledge_parser.py ./skills/dev-tour-guide/index/ --stats
"""

import argparse
import dataclasses
import json
import logging
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Type, Union

import yaml

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO, 
    format="%(levelname)s: %(message)s", 
    stream=sys.stdout
)


# --- Dataclass Definitions ---


@dataclass
class CapabilityItem:
    """Base class for all capability items."""
    id: str
    name: str
    category: str  # endpoint|skill|tool|workflow|process|project
    description: str
    tags: str  # Comma-separated string
    tier: str  # public|widely_shared|narrowly_shared|personal
    source_file: str
    token_budget: int = 0


@dataclass
class Endpoint(CapabilityItem):
    """Represents an API endpoint or service endpoint."""
    url: str = ""
    port: int = 0
    protocol: str = "http"
    authentication: str = "none"
    related_skills: str = ""


@dataclass
class Skill(CapabilityItem):
    """Represents a specific skill or capability."""
    location: str = ""
    skill_category: str = ""  # Separate from base 'category' field
    use_when: str = ""
    triggers: str = ""


@dataclass
class Tool(CapabilityItem):
    """Represents a tool, script, or utility."""
    tool_type: str = ""  # script|directory|cli|config
    location: str = ""
    usage: str = ""
    related_skills: str = ""


@dataclass
class Workflow(CapabilityItem):
    """Represents a multi-step process or workflow."""
    workflow_type: str = ""  # methodology|investigation|automation
    step_count: int = 0
    steps_summary: str = ""
    related_skills: str = ""


@dataclass
class Process(CapabilityItem):
    """Represents a process, convention, or methodology."""
    process_type: str = ""  # convention|methodology|checklist
    rules_summary: str = ""
    is_anti_pattern: bool = False


@dataclass
class Project(CapabilityItem):
    """Represents a project or codebase."""
    path: str = ""
    status: str = "active"
    key_docs: str = ""
    related_skills: str = ""


@dataclass
class SquirrelIndex:
    """Complete index of all capability data from a source directory."""
    tier: str
    source_path: str
    endpoints: List[Endpoint] = field(default_factory=list)
    skills: List[Skill] = field(default_factory=list)
    tools: List[Tool] = field(default_factory=list)
    workflows: List[Workflow] = field(default_factory=list)
    processes: List[Process] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Converts the SquirrelIndex to a dictionary suitable for JSON serialization."""
        return dataclasses.asdict(self)

    def get_stats(self) -> Dict[str, int]:
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
        logging.warning(f"Unexpected type for list flattening: {type(data)}. Returning default.")
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
        logging.warning(f"Could not determine tier from path: {path}. Defaulting to 'personal'.")
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
        logging.warning(f"Invalid {field_name} '{value}'. Using default {default}.")
        return default


# --- Individual Parse Functions ---


def _parse_capability_yaml(
    file_path: Path, 
    tier: str, 
    item_type: Type[CapabilityItem], 
    category: str
) -> List[CapabilityItem]:
    """
    Generic function to parse a single YAML file for a capability type.
    
    Args:
        file_path: Path to the YAML file
        tier: Capability tier (public|widely_shared|narrowly_shared|personal)
        item_type: Dataclass type to instantiate
        category: Category string for the items
        
    Returns:
        List of parsed capability items
    """
    items: List[CapabilityItem] = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            
            if not data:
                logging.info(f"Empty YAML file: {file_path}")
                return items
                
            if not isinstance(data, list):
                logging.warning(f"YAML file {file_path} does not contain a list of items. Skipping.")
                return items
                
            for item_index, item_data in enumerate(data):
                if not isinstance(item_data, dict):
                    logging.warning(f"Skipping non-dictionary item #{item_index} in {file_path}")
                    continue

                try:
                    # Validate required fields
                    required_fields = ["id", "name", "description"]
                    for field_name in required_fields:
                        if field_name not in item_data or not str(item_data[field_name]).strip():
                            raise ValueError(f"Missing or empty required field: {field_name}")

                    # Calculate relative source file path
                    try:
                        # Try to get relative path from index root (2 levels up from the YAML file)
                        relative_path = file_path.relative_to(file_path.parents[2])
                    except (ValueError, IndexError):
                        # Fallback to just the filename if path calculation fails
                        relative_path = file_path.name

                    # Prepare base arguments for dataclass instantiation
                    kwargs: Dict[str, Any] = {
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
                            f"token_budget for {item_data['id']}"
                        )
                    }

                    # Map type-specific fields
                    for field_info in dataclasses.fields(item_type):
                        field_name = field_info.name
                        
                        # Skip base class fields already handled
                        if field_name in kwargs:
                            continue

                        yaml_value = item_data.get(field_name)
                        
                        if yaml_value is not None:
                            # Handle special field types
                            if field_name in ["related_skills"]:
                                kwargs[field_name] = _flatten_list_to_string(yaml_value)
                            elif field_name == "authentication":
                                kwargs[field_name] = _parse_authentication(yaml_value)
                            elif field_name == "step_count":
                                kwargs[field_name] = _safe_int_conversion(
                                    yaml_value, 0, f"step_count for {item_data['id']}"
                                )
                            elif field_name == "port":
                                kwargs[field_name] = _safe_int_conversion(
                                    yaml_value, 0, f"port for {item_data['id']}"
                                )
                            elif field_name == "is_anti_pattern":
                                if isinstance(yaml_value, bool):
                                    kwargs[field_name] = yaml_value
                                else:
                                    kwargs[field_name] = str(yaml_value).lower() in ("true", "yes", "1")
                            else:
                                # Direct assignment for other fields
                                kwargs[field_name] = str(yaml_value) if yaml_value else ""

                    # Instantiate the specific dataclass
                    item = item_type(**kwargs)
                    items.append(item)
                    
                except (ValueError, KeyError, TypeError) as e:
                    logging.warning(
                        f"Skipping item #{item_index} in {file_path} due to error: {e}. "
                        f"Item ID: {item_data.get('id', 'N/A')}"
                    )
                    continue

    except FileNotFoundError:
        logging.warning(f"YAML file not found: {file_path}")
    except yaml.YAMLError as e:
        logging.warning(f"Failed to parse YAML file {file_path}: {e}")
    except PermissionError as e:
        logging.error(f"Permission denied for file {file_path}: {e}")
    except Exception as e:
        logging.error(f"Unexpected error processing {file_path}: {e}")

    logging.info(f"Parsed {len(items)} {category}(s) from {file_path.name}")
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
        logging.error(f"Index path does not exist: {index_path}")
        return SquirrelIndex(tier="unknown", source_path=str(index_path))
        
    if not index_path.is_dir():
        logging.error(f"Index path is not a directory: {index_path}")
        return SquirrelIndex(tier="unknown", source_path=str(index_path))

    tier = _get_tier_from_path(index_path)
    logging.info(f"Processing index at: {index_path} with detected tier: {tier}")

    index_data = SquirrelIndex(tier=tier, source_path=str(index_path.resolve()))

    # Define the mapping from filenames to parsing functions
    file_parsers = {
        "endpoints.yaml": (parse_endpoints_yaml, "endpoints"),
        "skills.yaml": (parse_skills_yaml, "skills"),
        "tools.yaml": (parse_tools_yaml, "tools"),
        "workflows.yaml": (parse_workflows_yaml, "workflows"),
        "processes.yaml": (parse_processes_yaml, "processes"),
        "projects.yaml": (parse_projects_yaml, "projects"),
    }

    # Process each expected file
    for filename, (parser_func, attr_name) in file_parsers.items():
        file_path = index_path / filename
        
        if not file_path.exists():
            logging.info(f"Optional file not found: {filename}")
            continue

        try:
            parsed_items = parser_func(file_path, tier)
            # Set the parsed items on the appropriate attribute
            setattr(index_data, attr_name, parsed_items)
        except Exception as e:
            logging.error(f"Failed to parse {filename}: {e}")
            continue

    total_items = index_data.total_items()
    logging.info(f"Successfully parsed {total_items} total items from {index_path}")
    
    return index_data


# --- CLI Interface ---


def main() -> None:
    """CLI entry point for parsing Squirrel knowledge indexes."""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Parse Squirrel knowledge index YAML files into structured data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s ./skills/dev-tour-guide/index/
  %(prog)s ./skills/dev-tour-guide/index/ --output /tmp/squirrel.json
  %(prog)s ./skills/dev-tour-guide/index/ --tier public
        """
    )
    parser.add_argument(
        "index_path",
        type=str,
        help="Path to the index directory containing capability YAML files"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file for JSON dump (prints to stdout if not specified)"
    )
    parser.add_argument(
        "--tier",
        type=str,
        default="public",
        help="Tier name for the index (default: public)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Configure logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    # Parse the index
    index_path = Path(args.index_path)
    if not index_path.exists():
        logging.error(f"Index path does not exist: {index_path}")
        sys.exit(1)

    try:
        index_data = parse_capability_index(index_path, tier=args.tier)
    except Exception as e:
        logging.error(f"Failed to parse index: {e}")
        sys.exit(1)

    # Convert to dict for JSON serialization
    output_dict = {
        "tier": index_data.tier,
        "endpoints": [asdict(e) for e in index_data.endpoints],
        "skills": [asdict(s) for s in index_data.skills],
        "tools": [asdict(t) for t in index_data.tools],
        "workflows": [asdict(w) for w in index_data.workflows],
        "processes": [asdict(p) for p in index_data.processes],
        "projects": [asdict(p) for p in index_data.projects],
        "total_items": index_data.total_items(),
    }

    # Output
    json_str = json.dumps(output_dict, indent=2, default=str)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_str)
        logging.info(f"Wrote {index_data.total_items()} items to {output_path}")
    else:
        print(json_str)


if __name__ == "__main__":
    main()
