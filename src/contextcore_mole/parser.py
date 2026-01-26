"""Parse ContextCore task JSON files."""

import json
from pathlib import Path

from .models import TaskFile


def parse_task_file(path: Path) -> TaskFile:
    """Parse a single task JSON file.

    Args:
        path: Path to the JSON file

    Returns:
        TaskFile with project and tasks

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
        pydantic.ValidationError: If structure doesn't match schema
    """
    with open(path) as f:
        data = json.load(f)
    return TaskFile.model_validate(data)


def scan_directory(path: Path, pattern: str = "*-tasks.json") -> list[tuple[Path, TaskFile]]:
    """Scan a directory for task JSON files.

    Args:
        path: Directory to scan
        pattern: Glob pattern for task files

    Returns:
        List of (path, TaskFile) tuples for each valid file found
    """
    results: list[tuple[Path, TaskFile]] = []

    if path.is_file():
        # Single file
        task_file = parse_task_file(path)
        results.append((path, task_file))
    else:
        # Directory - find matching files
        for file_path in sorted(path.glob(pattern)):
            try:
                task_file = parse_task_file(file_path)
                results.append((file_path, task_file))
            except (json.JSONDecodeError, Exception):
                # Skip invalid files silently during scan
                continue

    return results


def find_task_files(path: Path) -> list[Path]:
    """Find all potential task JSON files in a path.

    Args:
        path: File or directory to search

    Returns:
        List of paths to JSON files
    """
    if path.is_file():
        return [path] if path.suffix == ".json" else []

    # Common patterns for task files
    patterns = ["*-tasks.json", "*_tasks.json", "tasks.json", "*.tasks.json"]
    found: set[Path] = set()

    for pattern in patterns:
        found.update(path.glob(pattern))
        found.update(path.glob(f"**/{pattern}"))

    return sorted(found)
