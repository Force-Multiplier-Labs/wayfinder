"""Tests for parser module."""

import json
import tempfile
from pathlib import Path

import pytest

from contextcore_mole.models import TaskFile
from contextcore_mole.parser import parse_task_file, scan_directory


@pytest.fixture
def sample_task_data() -> dict:
    """Sample task file data."""
    return {
        "project": {
            "id": "test-project",
            "name": "Test Project",
            "description": "A test project",
        },
        "tasks": [
            {
                "id": "TEST-001",
                "title": "First task",
                "type": "task",
                "status": "pending",
                "description": "First task description",
                "parent_id": None,
                "tags": ["tag1", "phase-1"],
            },
            {
                "id": "TEST-002",
                "title": "Second task",
                "type": "story",
                "status": "done",
                "description": "Second task description",
                "parent_id": None,
                "tags": ["tag2", "phase-2"],
            },
            {
                "id": "TEST-003",
                "title": "Cancelled task",
                "type": "task",
                "status": "cancelled",
                "description": "This was cancelled",
                "parent_id": None,
                "tags": ["tag1"],
            },
        ],
    }


@pytest.fixture
def task_file(sample_task_data: dict, tmp_path: Path) -> Path:
    """Create a temporary task file."""
    file_path = tmp_path / "test-tasks.json"
    file_path.write_text(json.dumps(sample_task_data))
    return file_path


def test_parse_task_file(task_file: Path) -> None:
    """Test parsing a task file."""
    result = parse_task_file(task_file)

    assert isinstance(result, TaskFile)
    assert result.project.id == "test-project"
    assert result.project.name == "Test Project"
    assert len(result.tasks) == 3


def test_task_count(task_file: Path) -> None:
    """Test task_count property."""
    result = parse_task_file(task_file)
    assert result.task_count == 3


def test_tasks_by_status(task_file: Path) -> None:
    """Test filtering tasks by status."""
    result = parse_task_file(task_file)

    pending = result.tasks_by_status("pending")
    assert len(pending) == 1
    assert pending[0].id == "TEST-001"

    done = result.tasks_by_status("done")
    assert len(done) == 1
    assert done[0].id == "TEST-002"

    cancelled = result.tasks_by_status("cancelled")
    assert len(cancelled) == 1
    assert cancelled[0].id == "TEST-003"


def test_tasks_by_tag(task_file: Path) -> None:
    """Test filtering tasks by tag."""
    result = parse_task_file(task_file)

    tag1_tasks = result.tasks_by_tag("tag1")
    assert len(tag1_tasks) == 2
    assert {t.id for t in tag1_tasks} == {"TEST-001", "TEST-003"}


def test_status_counts(task_file: Path) -> None:
    """Test status counts."""
    result = parse_task_file(task_file)
    counts = result.status_counts()

    assert counts == {"pending": 1, "done": 1, "cancelled": 1}


def test_scan_directory(task_file: Path) -> None:
    """Test scanning a directory."""
    results = scan_directory(task_file.parent, "*-tasks.json")

    assert len(results) == 1
    path, task_file_obj = results[0]
    assert path.name == "test-tasks.json"
    assert task_file_obj.project.id == "test-project"


def test_scan_single_file(task_file: Path) -> None:
    """Test scanning a single file."""
    results = scan_directory(task_file)

    assert len(results) == 1
    path, task_file_obj = results[0]
    assert path == task_file
