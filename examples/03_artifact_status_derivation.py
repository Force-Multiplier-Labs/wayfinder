#!/usr/bin/env python3
"""
Example 3: Artifact-Based Status Derivation

This example demonstrates automatically deriving task status from
development artifacts (commits, PRs, CI results) instead of manual updates.

Prerequisites:
    pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp

Run with local Tempo:
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
    python 03_artifact_status_derivation.py
"""

import re
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource


# =============================================================================
# Setup
# =============================================================================

def setup_tracing(service_name: str = "artifact-tracker") -> trace.Tracer:
    """Configure OTel tracing with OTLP export."""
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
    })

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    return trace.get_tracer(__name__)


# =============================================================================
# Data Models
# =============================================================================

class TaskStatus(str, Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"
    DONE = "done"


@dataclass
class Commit:
    sha: str
    message: str
    author: str
    timestamp: datetime


@dataclass
class PullRequest:
    id: int
    title: str
    author: str
    state: str  # open, merged, closed
    commits: List[Commit]


@dataclass
class CIResult:
    pipeline_id: str
    status: str  # success, failure, pending
    commit_sha: str


# =============================================================================
# Core Pattern: ArtifactDerivedTracker
# =============================================================================

class ArtifactDerivedTracker:
    """
    Derive task status from development artifacts.

    Status derivation rules:
    - Commit with task ID → in_progress
    - PR opened → in_review
    - PR merged → done
    - CI failure → blocked (with reason)
    - No activity for N days → stale (detected separately)
    """

    # Regex to extract task IDs from commit messages
    TASK_ID_PATTERN = re.compile(r'([A-Z]+-\d+)')

    def __init__(self, project_id: str, tracer: Optional[trace.Tracer] = None):
        self.project_id = project_id
        self.tracer = tracer or trace.get_tracer(__name__)
        self._active_spans: Dict[str, trace.Span] = {}
        self._task_status: Dict[str, TaskStatus] = {}

    def _ensure_task_span(self, task_id: str) -> trace.Span:
        """Get or create a span for a task."""
        if task_id not in self._active_spans:
            span = self.tracer.start_span(
                name="task.lifecycle",
                attributes={
                    "task.id": task_id,
                    "task.status": TaskStatus.BACKLOG.value,
                    "project.id": self.project_id,
                    "task.status_derived": True,  # Flag that status is auto-derived
                }
            )
            self._active_spans[task_id] = span
            self._task_status[task_id] = TaskStatus.BACKLOG
            print(f"✓ Created task span: {task_id}")

        return self._active_spans[task_id]

    def _update_status(self, task_id: str, new_status: TaskStatus, reason: Optional[str] = None) -> None:
        """Update task status with event."""
        span = self._ensure_task_span(task_id)
        old_status = self._task_status.get(task_id, TaskStatus.BACKLOG)

        if old_status == new_status:
            return  # No change

        span.set_attribute("task.status", new_status.value)

        event_attrs = {"from": old_status.value, "to": new_status.value}
        if reason:
            event_attrs["reason"] = reason
            event_attrs["derived_from"] = "artifact"

        span.add_event("task.status_changed", attributes=event_attrs)
        self._task_status[task_id] = new_status

        print(f"  → {task_id}: {old_status.value} → {new_status.value}" +
              (f" ({reason})" if reason else ""))

    def extract_task_ids(self, text: str) -> List[str]:
        """Extract task IDs from text (commit message, PR title, etc.)."""
        matches = self.TASK_ID_PATTERN.findall(text)
        return list(set(matches))  # Deduplicate

    # =========================================================================
    # Artifact Handlers
    # =========================================================================

    def on_commit(self, commit: Commit) -> None:
        """
        Handle a new commit.

        Derivation: Commit with task ID → in_progress
        """
        task_ids = self.extract_task_ids(commit.message)

        if not task_ids:
            return

        print(f"\n📝 Commit: {commit.sha[:8]} - {commit.message[:50]}...")

        for task_id in task_ids:
            span = self._ensure_task_span(task_id)

            # Add commit event
            span.add_event("task.commit", attributes={
                "commit.sha": commit.sha,
                "commit.author": commit.author,
                "commit.message": commit.message[:100],
            })

            # Derive status: work has started
            current_status = self._task_status.get(task_id, TaskStatus.BACKLOG)
            if current_status in [TaskStatus.BACKLOG, TaskStatus.TODO]:
                self._update_status(
                    task_id,
                    TaskStatus.IN_PROGRESS,
                    reason=f"Commit {commit.sha[:8]}"
                )

    def on_pull_request_opened(self, pr: PullRequest) -> None:
        """
        Handle PR opened.

        Derivation: PR opened → in_review
        """
        # Extract task IDs from PR title and commit messages
        task_ids = self.extract_task_ids(pr.title)
        for commit in pr.commits:
            task_ids.extend(self.extract_task_ids(commit.message))
        task_ids = list(set(task_ids))

        if not task_ids:
            return

        print(f"\n🔀 PR Opened: #{pr.id} - {pr.title[:50]}...")

        for task_id in task_ids:
            span = self._ensure_task_span(task_id)

            # Add PR event
            span.add_event("task.pr_opened", attributes={
                "pr.id": pr.id,
                "pr.title": pr.title,
                "pr.author": pr.author,
            })

            # Derive status: code is ready for review
            self._update_status(
                task_id,
                TaskStatus.IN_REVIEW,
                reason=f"PR #{pr.id} opened"
            )

    def on_pull_request_merged(self, pr: PullRequest) -> None:
        """
        Handle PR merged.

        Derivation: PR merged → done
        """
        task_ids = self.extract_task_ids(pr.title)
        for commit in pr.commits:
            task_ids.extend(self.extract_task_ids(commit.message))
        task_ids = list(set(task_ids))

        if not task_ids:
            return

        print(f"\n✅ PR Merged: #{pr.id} - {pr.title[:50]}...")

        for task_id in task_ids:
            span = self._active_spans.get(task_id)
            if not span:
                continue

            # Add merge event
            span.add_event("task.pr_merged", attributes={
                "pr.id": pr.id,
                "pr.title": pr.title,
            })

            # Derive status: work is done
            self._update_status(
                task_id,
                TaskStatus.DONE,
                reason=f"PR #{pr.id} merged"
            )

            # End the span - task is complete
            span.add_event("task.completed", attributes={
                "completed_by": "pr_merge",
                "pr.id": pr.id,
            })
            span.end()
            del self._active_spans[task_id]

    def on_ci_result(self, result: CIResult) -> None:
        """
        Handle CI pipeline result.

        Derivation: CI failure → blocked
        """
        # In a real implementation, you'd look up which tasks are associated
        # with this commit SHA. For this example, we'll simulate.
        print(f"\n🔧 CI Result: {result.pipeline_id} - {result.status}")

        if result.status == "failure":
            # Find tasks associated with this commit
            # (simplified - in production, query by commit SHA)
            for task_id, span in list(self._active_spans.items()):
                # Check if this task has the commit
                # (simplified check for example)
                if self._task_status.get(task_id) in [TaskStatus.IN_PROGRESS, TaskStatus.IN_REVIEW]:
                    span.add_event("task.ci_failure", attributes={
                        "pipeline.id": result.pipeline_id,
                        "commit.sha": result.commit_sha,
                    })

                    self._update_status(
                        task_id,
                        TaskStatus.BLOCKED,
                        reason=f"CI failure: {result.pipeline_id}"
                    )

    def on_ci_fixed(self, result: CIResult) -> None:
        """Handle CI pipeline success after failure (unblock)."""
        print(f"\n🔧 CI Fixed: {result.pipeline_id} - {result.status}")

        for task_id, span in self._active_spans.items():
            if self._task_status.get(task_id) == TaskStatus.BLOCKED:
                span.add_event("task.unblocked", attributes={
                    "reason": "CI passed",
                    "pipeline.id": result.pipeline_id,
                })

                self._update_status(
                    task_id,
                    TaskStatus.IN_REVIEW,
                    reason="CI fixed"
                )


# =============================================================================
# Example Usage
# =============================================================================

def main():
    """Demonstrate artifact-based status derivation."""

    tracer = setup_tracing("artifact-derived-tracker")
    tracker = ArtifactDerivedTracker(project_id="my-project", tracer=tracer)

    print("\n" + "="*60)
    print("Example 3: Artifact-Based Status Derivation")
    print("="*60)
    print("\nWatching for development artifacts...\n")

    # Simulate a development workflow

    # 1. Developer starts working - first commit
    tracker.on_commit(Commit(
        sha="abc123def456",
        message="PROJ-101: Add user model and migrations",
        author="alice",
        timestamp=datetime.now(),
    ))
    time.sleep(0.3)

    # 2. More commits
    tracker.on_commit(Commit(
        sha="def456ghi789",
        message="PROJ-101: Add user repository",
        author="alice",
        timestamp=datetime.now(),
    ))
    time.sleep(0.3)

    # 3. Another task starts
    tracker.on_commit(Commit(
        sha="ghi789jkl012",
        message="PROJ-102: Implement login endpoint",
        author="bob",
        timestamp=datetime.now(),
    ))
    time.sleep(0.3)

    # 4. PR opened for first task
    tracker.on_pull_request_opened(PullRequest(
        id=42,
        title="PROJ-101: Add user management",
        author="alice",
        state="open",
        commits=[
            Commit("abc123def456", "PROJ-101: Add user model", "alice", datetime.now()),
            Commit("def456ghi789", "PROJ-101: Add user repository", "alice", datetime.now()),
        ],
    ))
    time.sleep(0.3)

    # 5. CI fails!
    tracker.on_ci_result(CIResult(
        pipeline_id="pipeline-123",
        status="failure",
        commit_sha="def456ghi789",
    ))
    time.sleep(0.3)

    # 6. Developer fixes the issue
    tracker.on_commit(Commit(
        sha="mno345pqr678",
        message="PROJ-101: Fix failing test",
        author="alice",
        timestamp=datetime.now(),
    ))
    time.sleep(0.3)

    # 7. CI passes
    tracker.on_ci_fixed(CIResult(
        pipeline_id="pipeline-124",
        status="success",
        commit_sha="mno345pqr678",
    ))
    time.sleep(0.3)

    # 8. PR merged!
    tracker.on_pull_request_merged(PullRequest(
        id=42,
        title="PROJ-101: Add user management",
        author="alice",
        state="merged",
        commits=[
            Commit("abc123def456", "PROJ-101: Add user model", "alice", datetime.now()),
            Commit("def456ghi789", "PROJ-101: Add user repository", "alice", datetime.now()),
            Commit("mno345pqr678", "PROJ-101: Fix failing test", "alice", datetime.now()),
        ],
    ))

    print("\n" + "="*60)
    print("Artifact tracking complete!")
    print("="*60)
    print("\nStatus was automatically derived from:")
    print("  - Commits → in_progress")
    print("  - PR opened → in_review")
    print("  - CI failure → blocked")
    print("  - CI success → in_review (unblocked)")
    print("  - PR merged → done")
    print("\nNo manual status updates required!")
    print("\nQuery task history:")
    print('  { task.id = "PROJ-101" && task.status_derived = true }')
    print()

    time.sleep(2)


if __name__ == "__main__":
    main()
