"""Pydantic models for ContextCore task JSON files."""

from pydantic import BaseModel


class Project(BaseModel):
    """Project metadata."""

    id: str
    name: str
    description: str = ""


class Task(BaseModel):
    """A task within a project."""

    id: str
    title: str
    type: str  # epic, story, task, subtask, bug, spike, incident
    status: str  # backlog, todo, in_progress, in_review, blocked, done, cancelled
    description: str = ""
    parent_id: str | None = None
    tags: list[str] = []


class TaskFile(BaseModel):
    """A task JSON file containing project metadata and tasks."""

    project: Project
    tasks: list[Task]

    @property
    def task_count(self) -> int:
        """Return the number of tasks."""
        return len(self.tasks)

    def tasks_by_status(self, status: str) -> list[Task]:
        """Filter tasks by status."""
        return [t for t in self.tasks if t.status == status]

    def tasks_by_tag(self, tag: str) -> list[Task]:
        """Filter tasks by tag."""
        return [t for t in self.tasks if tag in t.tags]

    def status_counts(self) -> dict[str, int]:
        """Return count of tasks by status."""
        counts: dict[str, int] = {}
        for task in self.tasks:
            counts[task.status] = counts.get(task.status, 0) + 1
        return counts
