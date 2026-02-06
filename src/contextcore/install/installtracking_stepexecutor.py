"""
Step executor for ContextCore installation tracking.

Executes installation steps with retry logic, dependency checking,
idempotency, and integrated state/metric tracking. Designed to work
with installtracking_statefile.py and installtracking_metrics.py.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from contextcore.install.installtracking_statefile import (
    StateFile,
    StepStatus,
)

__all__ = [
    "ExitCode",
    "StepDefinition",
    "StepExecutor",
    "run_step",
]


class ExitCode(int, Enum):
    """Exit codes for step execution."""

    SUCCESS = 0
    STEP_FAILURE = 1
    DEPENDENCY_FAILURE = 2


@dataclass
class StepDefinition:
    """Definition of an installation step."""

    step_id: str
    name: str
    command: Optional[str] = None
    callable: Optional[Callable[[], bool]] = None
    dependencies: List[str] = field(default_factory=list)
    max_retries: int = 3
    retry_delay_seconds: float = 5.0
    timeout_seconds: int = 300
    idempotent: bool = True


class StepExecutor:
    """Executes installation steps with retry, dependency, and state tracking.

    Integrates with StateFile for persistence and supports both shell
    commands and Python callables as step implementations.
    """

    def __init__(
        self,
        state_file: Optional[StateFile] = None,
        dry_run: bool = False,
    ) -> None:
        """Initialize the step executor.

        Args:
            state_file: StateFile instance for persistence. Creates default if None.
            dry_run: If True, log steps without executing them.
        """
        self.state_file = state_file or StateFile()
        self.dry_run = dry_run
        self._steps: Dict[str, StepDefinition] = {}

    def register(self, step: StepDefinition) -> None:
        """Register a step definition.

        Args:
            step: The step to register.
        """
        self._steps[step.step_id] = step

    def check_dependencies(self, step_id: str) -> bool:
        """Check if all dependencies for a step are satisfied.

        Args:
            step_id: The step whose dependencies to check.

        Returns:
            True if all dependencies are completed, False otherwise.
        """
        step = self._steps.get(step_id)
        if step is None:
            return False

        for dep_id in step.dependencies:
            status = self.state_file.get_step_status(dep_id)
            if status != StepStatus.COMPLETED:
                return False
        return True

    def should_skip(self, step_id: str) -> bool:
        """Check if a step should be skipped (already completed and idempotent).

        Args:
            step_id: The step to check.

        Returns:
            True if the step should be skipped.
        """
        step = self._steps.get(step_id)
        if step is None:
            return False

        if not step.idempotent:
            return False

        return self.state_file.get_step_status(step_id) == StepStatus.COMPLETED

    def run_step(self, step_id: str) -> ExitCode:
        """Execute a single step with retry logic.

        Args:
            step_id: ID of the step to execute.

        Returns:
            ExitCode indicating the result.
        """
        step = self._steps.get(step_id)
        if step is None:
            return ExitCode.STEP_FAILURE

        # Check dependencies
        if not self.check_dependencies(step_id):
            return ExitCode.DEPENDENCY_FAILURE

        # Check idempotency
        if self.should_skip(step_id):
            return ExitCode.SUCCESS

        # Dry-run mode
        if self.dry_run:
            print(f"[dry-run] Would execute: {step.name}")
            return ExitCode.SUCCESS

        # Execute with retries
        last_error = ""
        for attempt in range(1, step.max_retries + 1):
            self.state_file.mark_running(step_id)

            try:
                success = self._execute_step(step)
                if success:
                    self.state_file.mark_completed(step_id)
                    return ExitCode.SUCCESS

                last_error = f"Step returned failure on attempt {attempt}"
            except subprocess.TimeoutExpired:
                last_error = f"Step timed out after {step.timeout_seconds}s"
            except subprocess.CalledProcessError as e:
                last_error = f"Command failed with exit code {e.returncode}"
            except Exception as e:
                last_error = str(e)

            # Retry delay (skip on last attempt)
            if attempt < step.max_retries:
                time.sleep(step.retry_delay_seconds)

        self.state_file.mark_failed(step_id, last_error)
        return ExitCode.STEP_FAILURE

    def run_all(self, step_ids: Optional[List[str]] = None) -> ExitCode:
        """Execute multiple steps in order.

        Args:
            step_ids: Steps to run. If None, runs all registered steps.

        Returns:
            ExitCode.SUCCESS if all steps pass, otherwise the first failure code.
        """
        ids = step_ids or list(self._steps.keys())

        for step_id in ids:
            result = self.run_step(step_id)
            if result != ExitCode.SUCCESS:
                return result

        return ExitCode.SUCCESS

    def _execute_step(self, step: StepDefinition) -> bool:
        """Execute a step's command or callable.

        Args:
            step: The step definition to execute.

        Returns:
            True if the step succeeded, False otherwise.
        """
        if step.callable is not None:
            return step.callable()

        if step.command is not None:
            # On Windows, avoid shell=True (uses cmd.exe, not bash).
            # Split command string into a list for cross-platform safety.
            if sys.platform == "win32":
                cmd = shlex.split(step.command, posix=False)
            else:
                cmd = shlex.split(step.command)
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=step.timeout_seconds,
                text=True,
            )
            if result.returncode == 0:
                self.state_file.mark_completed(step.step_id, output=result.stdout)
                return True

            return False

        # No command or callable
        return True


# Module-level convenience function

def run_step(
    step_id: str,
    name: str,
    command: Optional[str] = None,
    callable: Optional[Callable[[], bool]] = None,
    dependencies: Optional[List[str]] = None,
    max_retries: int = 3,
    dry_run: bool = False,
) -> ExitCode:
    """Run a single step with default state tracking.

    Convenience function for simple step execution without managing
    a StepExecutor instance.

    Args:
        step_id: Unique identifier for the step.
        name: Human-readable step name.
        command: Shell command to execute.
        callable: Python callable returning True on success.
        dependencies: Step IDs that must complete first.
        max_retries: Number of retry attempts.
        dry_run: If True, skip actual execution.

    Returns:
        ExitCode indicating the result.
    """
    executor = StepExecutor(dry_run=dry_run)
    step = StepDefinition(
        step_id=step_id,
        name=name,
        command=command,
        callable=callable,
        dependencies=dependencies or [],
        max_retries=max_retries,
    )
    executor.register(step)
    return executor.run_step(step_id)
