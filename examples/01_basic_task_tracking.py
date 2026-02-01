#!/usr/bin/env python3
"""
Example 1: Basic Task Tracking

This example demonstrates the core "tasks as spans" pattern.
Tasks are modeled as OpenTelemetry spans with lifecycle events.

Prerequisites:
    pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

Run with local Tempo:
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
    python 01_basic_task_tracking.py
"""

import time
from datetime import datetime
from typing import Dict, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource


# =============================================================================
# Setup: Configure OpenTelemetry
# =============================================================================

def setup_tracing(service_name: str = "task-tracker") -> trace.Tracer:
    """Configure OTel tracing with OTLP export."""
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()  # Uses OTEL_EXPORTER_OTLP_ENDPOINT env var
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


# =============================================================================
# Core Pattern: TaskTracker
# =============================================================================

class TaskTracker:
    """
    Track tasks as OpenTelemetry spans.

    Each task becomes a span with:
    - Span name: "task.lifecycle"
    - Attributes: task.id, task.type, task.status, project.id, etc.
    - Events: Status changes recorded as span events
    - Duration: From task creation to completion
    """

    def __init__(self, project_id: str, tracer: Optional[trace.Tracer] = None):
        self.project_id = project_id
        self.tracer = tracer or trace.get_tracer(__name__)
        self._active_spans: Dict[str, trace.Span] = {}

    def start_task(
        self,
        task_id: str,
        title: str,
        task_type: str = "task",
        parent_id: Optional[str] = None,
        assignee: Optional[str] = None,
        story_points: Optional[int] = None,
        priority: str = "medium",
    ) -> None:
        """
        Start tracking a task (creates a span).

        Args:
            task_id: Unique task identifier (e.g., "PROJ-123")
            title: Task title/summary
            task_type: One of: epic, story, task, subtask, bug, spike
            parent_id: Parent task ID for hierarchy
            assignee: Assigned person
            story_points: Estimation points
            priority: One of: critical, high, medium, low
        """
        # Get parent span context if this task has a parent
        parent_context = None
        if parent_id and parent_id in self._active_spans:
            parent_context = trace.set_span_in_context(self._active_spans[parent_id])

        # Start the span
        span = self.tracer.start_span(
            name="task.lifecycle",
            context=parent_context,
            attributes={
                "task.id": task_id,
                "task.title": title,
                "task.type": task_type,
                "task.status": "backlog",
                "task.priority": priority,
                "project.id": self.project_id,
            }
        )

        # Add optional attributes
        if parent_id:
            span.set_attribute("task.parent_id", parent_id)
        if assignee:
            span.set_attribute("task.assignee", assignee)
        if story_points:
            span.set_attribute("task.story_points", story_points)

        # Record creation event
        span.add_event(
            "task.created",
            attributes={
                "task.title": title,
                "task.type": task_type,
            }
        )

        self._active_spans[task_id] = span
        print(f"✓ Started task: {task_id} - {title}")

    def update_status(self, task_id: str, new_status: str, reason: Optional[str] = None) -> None:
        """
        Update task status (adds span event).

        Args:
            task_id: Task identifier
            new_status: New status (backlog, todo, in_progress, in_review, blocked, done)
            reason: Optional reason for status change
        """
        span = self._active_spans.get(task_id)
        if not span:
            print(f"✗ Task not found: {task_id}")
            return

        # Get current status
        # Note: In production, you'd track this separately as spans are write-once
        old_status = "unknown"

        # Update attribute and add event
        span.set_attribute("task.status", new_status)

        event_attrs = {"from": old_status, "to": new_status}
        if reason:
            event_attrs["reason"] = reason

        span.add_event("task.status_changed", attributes=event_attrs)

        # Special handling for blocked status
        if new_status == "blocked":
            span.add_event("task.blocked", attributes={"reason": reason or "unspecified"})

        print(f"✓ Updated {task_id}: status → {new_status}")

    def complete_task(self, task_id: str) -> None:
        """
        Complete a task (ends the span).

        Args:
            task_id: Task identifier
        """
        span = self._active_spans.pop(task_id, None)
        if not span:
            print(f"✗ Task not found: {task_id}")
            return

        span.set_attribute("task.status", "done")
        span.add_event("task.completed")
        span.end()

        print(f"✓ Completed task: {task_id}")

    def cancel_task(self, task_id: str, reason: str) -> None:
        """
        Cancel a task (ends the span with cancelled status).

        Args:
            task_id: Task identifier
            reason: Cancellation reason
        """
        span = self._active_spans.pop(task_id, None)
        if not span:
            print(f"✗ Task not found: {task_id}")
            return

        span.set_attribute("task.status", "cancelled")
        span.add_event("task.cancelled", attributes={"reason": reason})
        span.end()

        print(f"✓ Cancelled task: {task_id} - {reason}")


# =============================================================================
# Example Usage
# =============================================================================

def main():
    """Demonstrate basic task tracking."""

    # Setup tracing
    tracer = setup_tracing("example-project-tracker")

    # Create tracker for a project
    tracker = TaskTracker(project_id="example-project", tracer=tracer)

    print("\n" + "="*60)
    print("Example 1: Basic Task Lifecycle")
    print("="*60 + "\n")

    # Create an epic (parent task)
    tracker.start_task(
        task_id="EPIC-1",
        title="User Authentication System",
        task_type="epic",
        priority="high",
    )

    # Create stories under the epic
    tracker.start_task(
        task_id="STORY-1",
        title="Implement login flow",
        task_type="story",
        parent_id="EPIC-1",
        assignee="alice",
        story_points=5,
    )

    tracker.start_task(
        task_id="STORY-2",
        title="Implement logout flow",
        task_type="story",
        parent_id="EPIC-1",
        assignee="bob",
        story_points=3,
    )

    # Simulate work progress
    print("\n--- Simulating work progress ---\n")

    time.sleep(0.5)  # Simulate time passing
    tracker.update_status("STORY-1", "in_progress")

    time.sleep(0.3)
    tracker.update_status("STORY-2", "in_progress")

    time.sleep(0.5)
    tracker.update_status("STORY-1", "in_review")

    time.sleep(0.2)
    tracker.update_status("STORY-2", "blocked", reason="Waiting for API spec")

    time.sleep(0.3)
    tracker.complete_task("STORY-1")

    time.sleep(0.2)
    tracker.update_status("STORY-2", "in_progress")  # Unblocked

    time.sleep(0.4)
    tracker.complete_task("STORY-2")

    # Complete the epic
    tracker.complete_task("EPIC-1")

    print("\n" + "="*60)
    print("Task tracking complete!")
    print("="*60)
    print("\nQuery your tasks in Tempo with TraceQL:")
    print('  { task.status = "done" && project.id = "example-project" }')
    print('  { task.type = "story" && task.parent_id = "EPIC-1" }')
    print()

    # Give time for spans to export
    time.sleep(2)


if __name__ == "__main__":
    main()
