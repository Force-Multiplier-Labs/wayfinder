"""Parse ContextCore task JSON files and OpenTelemetry trace exports.

This module provides parsing functionality for:
1. Simple ContextCore task JSON files (project + tasks structure)
2. OpenTelemetry trace JSON format exported from Grafana Tempo
3. Time-based filtering for task data
"""

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel

from .models import TaskFile

__all__ = [
    # Original task file parsing
    'parse_task_file',
    'scan_directory',
    'find_task_files',
    # OTel trace parsing
    'OTelTraceParser',
    'TaskData',
    'OTelAttribute',
    'OTelEvent',
    'OTelSpan',
    'parse_tempo_export',
    # Time filtering
    'TimeParser',
    'TimeFilter',
]

logger = logging.getLogger(__name__)


# =============================================================================
# Time Parsing and Filtering
# =============================================================================

class TimeParser:
    """Utility class for parsing time strings into Unix nanoseconds."""

    @staticmethod
    def parse_time_string(time_str: str) -> int:
        """
        Parse time string in either relative format (7d, 1w, 30d) or ISO 8601 format.

        Args:
            time_str: Time string to parse

        Returns:
            Unix timestamp in nanoseconds

        Raises:
            ValueError: If time string format is invalid
        """
        if re.match(r'^\d+[dwmyh]$', time_str):
            return TimeParser.parse_relative_time(time_str)
        elif re.match(
            r'^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})?)?$',
            time_str
        ):
            return TimeParser.parse_iso_8601(time_str)
        else:
            raise ValueError(
                f"Invalid time format: {time_str}. "
                "Use ISO 8601 or relative format (e.g., '7d', '1w')"
            )

    @staticmethod
    def parse_iso_8601(iso_string: str) -> int:
        """Parse ISO 8601 formatted date/time string."""
        # Handle Z suffix for UTC
        if iso_string.endswith('Z'):
            iso_string = iso_string[:-1] + '+00:00'

        # Parse the datetime, adding UTC timezone if none specified
        try:
            dt = datetime.fromisoformat(iso_string)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ValueError(f"Invalid ISO 8601 format: {iso_string}") from e

        return TimeParser.to_unix_nanos(dt)

    @staticmethod
    def parse_relative_time(relative_string: str) -> int:
        """Parse relative time string like '7d', '1w', '2h'."""
        amount = int(relative_string[:-1])
        unit = relative_string[-1]

        now = datetime.now(timezone.utc)

        # Calculate target datetime based on unit
        if unit == 'd':
            dt = now - timedelta(days=amount)
        elif unit == 'w':
            dt = now - timedelta(weeks=amount)
        elif unit == 'h':
            dt = now - timedelta(hours=amount)
        elif unit == 'm':
            dt = now - timedelta(minutes=amount)
        elif unit == 'y':
            dt = now - timedelta(days=amount * 365)  # Approximate year
        else:
            raise ValueError(
                f"Invalid time unit: {unit}. Supported units: d, w, h, m, y"
            )

        return TimeParser.to_unix_nanos(dt)

    @staticmethod
    def to_unix_nanos(dt: datetime) -> int:
        """Convert datetime to Unix nanoseconds."""
        return int(dt.timestamp() * 1_000_000_000)

    @staticmethod
    def from_unix_nanos(nanos: int) -> datetime:
        """Convert Unix nanoseconds to datetime."""
        return datetime.fromtimestamp(nanos / 1_000_000_000, tz=timezone.utc)


@dataclass
class TimeFilter:
    """Filter for time-based task filtering."""
    since_nanos: Optional[int] = None
    until_nanos: Optional[int] = None

    def matches(self, start_time_nanos: int) -> bool:
        """
        Check if a task's start time matches the filter criteria.

        Args:
            start_time_nanos: Task start time in Unix nanoseconds

        Returns:
            True if task matches filter criteria
        """
        if self.since_nanos is not None and start_time_nanos < self.since_nanos:
            return False
        if self.until_nanos is not None and start_time_nanos > self.until_nanos:
            return False
        return True

    def matches_datetime(self, dt: Optional[datetime]) -> bool:
        """
        Check if a datetime matches the filter criteria.

        Args:
            dt: datetime to check (None always matches)

        Returns:
            True if datetime matches filter criteria
        """
        if dt is None:
            return True  # No timestamp = include by default
        nanos = TimeParser.to_unix_nanos(dt)
        return self.matches(nanos)


# =============================================================================
# Original Task File Parsing (ContextCore simple JSON format)
# =============================================================================

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


# =============================================================================
# OpenTelemetry Trace Parsing (Tempo export format)
# =============================================================================

class OTelAttribute(BaseModel):
    """OpenTelemetry attribute key-value pair."""
    key: str
    value: Union[str, int, float, bool]


class OTelEvent(BaseModel):
    """OpenTelemetry event with timestamp and attributes."""
    timeUnixNano: str
    name: str
    attributes: List[OTelAttribute] = []


class OTelSpan(BaseModel):
    """OpenTelemetry span containing trace data."""
    traceId: str
    spanId: str
    parentSpanId: Optional[str] = None
    name: str
    startTimeUnixNano: str
    endTimeUnixNano: str
    attributes: List[OTelAttribute] = []
    events: List[OTelEvent] = []
    status: Optional[Dict[str, Any]] = None


class OTelScopeSpans(BaseModel):
    """Container for spans within a scope."""
    scope: Optional[Dict[str, Any]] = None
    spans: List[OTelSpan] = []


class OTelResourceSpans(BaseModel):
    """Container for scope spans within a resource."""
    resource: Optional[Dict[str, Any]] = None
    scopeSpans: List[OTelScopeSpans] = []


class TaskData(BaseModel):
    """Extracted task data from OpenTelemetry spans."""
    task_id: Optional[str] = None
    task_title: Optional[str] = None
    task_status: Optional[str] = None
    task_type: Optional[str] = None
    project_id: Optional[str] = None
    created_at: Optional[datetime] = None
    status_changed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    span_id: str
    trace_id: str


class OTelTraceParser:
    """Parser for OpenTelemetry trace JSON format from Tempo exports."""

    def __init__(self, validate_schema: bool = True):
        """
        Initialize the parser.

        Args:
            validate_schema: Whether to validate extracted data against schema
        """
        self.validate_schema = validate_schema
        self.errors: List[str] = []

    def parse_trace_file(self, file_path: Path) -> List[TaskData]:
        """
        Parse OTel trace JSON file and extract task data.

        Args:
            file_path: Path to the JSON file containing trace data

        Returns:
            List of extracted TaskData objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
            return self.parse_trace_data(json_data)
        except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
            error_msg = f"Failed to read or parse file {file_path}: {e}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return []

    def parse_trace_data(self, json_data: Dict[str, Any]) -> List[TaskData]:
        """
        Parse OTel trace data structure from dictionary.

        Args:
            json_data: Dictionary containing OTel trace data

        Returns:
            List of extracted TaskData objects
        """
        task_data_list = []

        # Handle both direct resourceSpans and batches containing resourceSpans
        resource_spans_list = []

        if "batches" in json_data:
            # Tempo export format with batches
            for batch in json_data["batches"]:
                if "resourceSpans" in batch:
                    resource_spans_list.extend(batch["resourceSpans"])
                # Also check for scopeSpans directly in batch (alternate format)
                if "scopeSpans" in batch:
                    resource_spans_list.append(batch)
        elif "resourceSpans" in json_data:
            # Direct resourceSpans format
            resource_spans_list = json_data["resourceSpans"]
        else:
            error_msg = "No 'batches' or 'resourceSpans' found in JSON data"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return task_data_list

        # Process each resource span
        for resource_span in resource_spans_list:
            self._process_resource_spans(resource_span, task_data_list)

        logger.info(f"Extracted {len(task_data_list)} task records from trace data")
        return task_data_list

    def _process_resource_spans(
        self, resource_span: Dict[str, Any], task_data_list: List[TaskData]
    ) -> None:
        """Process resource spans and extract scope spans."""
        if "scopeSpans" not in resource_span:
            return

        for scope_span in resource_span["scopeSpans"]:
            self._process_scope_spans(scope_span, task_data_list)

    def _process_scope_spans(
        self, scope_span: Dict[str, Any], task_data_list: List[TaskData]
    ) -> None:
        """Process scope spans and extract individual spans."""
        if "spans" not in scope_span:
            return

        for span_data in scope_span["spans"]:
            try:
                # Validate span structure
                span = OTelSpan(**span_data)
                task_data = self._extract_task_data(span)
                if task_data:
                    task_data_list.append(task_data)
            except Exception as e:
                error_msg = f"Failed to process span: {e}"
                logger.warning(error_msg)
                self.errors.append(error_msg)

    def _extract_task_data(self, span: OTelSpan) -> Optional[TaskData]:
        """
        Extract task data from an OpenTelemetry span.

        Args:
            span: OTel span to extract data from

        Returns:
            TaskData object if extraction successful, None otherwise
        """
        # Extract task attributes from span attributes
        task_attributes = self._extract_task_attributes(span)

        # Extract task events from span events
        task_events = self._extract_task_events(span)

        # Skip spans without required task attributes
        if not task_attributes.get("task_id") or not task_attributes.get("task_title"):
            logger.debug(f"Skipping span {span.spanId}: missing required task attributes")
            return None

        # Create TaskData object
        try:
            task_data = TaskData(
                task_id=task_attributes.get("task_id"),
                task_title=task_attributes.get("task_title"),
                task_status=task_attributes.get("task_status"),
                task_type=task_attributes.get("task_type"),
                project_id=task_attributes.get("project_id"),
                created_at=task_events.get("created"),
                status_changed_at=task_events.get("status_changed"),
                completed_at=task_events.get("completed"),
                span_id=span.spanId,
                trace_id=span.traceId,
            )

            # Validate if schema validation is enabled
            if self.validate_schema:
                task_data.model_validate(task_data.model_dump())

            return task_data

        except Exception as e:
            error_msg = f"Failed to create TaskData for span {span.spanId}: {e}"
            logger.warning(error_msg)
            self.errors.append(error_msg)
            return None

    def _extract_task_attributes(self, span: OTelSpan) -> Dict[str, Optional[str]]:
        """
        Extract task-related attributes from span attributes.

        Args:
            span: OTel span containing attributes

        Returns:
            Dictionary mapping attribute names to values
        """
        task_attrs: Dict[str, Optional[str]] = {}
        target_keys = {"task.id", "task.title", "task.status", "task.type", "project.id"}

        for attr in span.attributes:
            if attr.key in target_keys:
                # Convert attribute key format (task.id -> task_id)
                key = attr.key.replace(".", "_")
                # Ensure string conversion for IDs
                task_attrs[key] = str(attr.value)

        return task_attrs

    def _extract_task_events(self, span: OTelSpan) -> Dict[str, Optional[datetime]]:
        """
        Extract task lifecycle events from span events.

        Args:
            span: OTel span containing events

        Returns:
            Dictionary mapping event types to timestamps
        """
        events_map: Dict[str, Optional[datetime]] = {
            "created": None,
            "status_changed": None,
            "completed": None,
        }
        target_events = {"task.created", "task.status_changed", "task.completed"}

        for event in span.events:
            if event.name in target_events:
                timestamp = self._convert_unix_nano_to_datetime(event.timeUnixNano)
                if timestamp:
                    # Map event name to simplified key
                    if event.name == "task.created":
                        events_map["created"] = timestamp
                    elif event.name == "task.status_changed":
                        events_map["status_changed"] = timestamp
                    elif event.name == "task.completed":
                        events_map["completed"] = timestamp

        return events_map

    def _convert_unix_nano_to_datetime(self, unix_nano: str) -> Optional[datetime]:
        """
        Convert Unix nanosecond timestamp to datetime object.

        Args:
            unix_nano: Unix timestamp in nanoseconds as string

        Returns:
            datetime object or None if conversion fails
        """
        try:
            # Convert from nanoseconds to seconds
            timestamp_seconds = int(unix_nano) / 1_000_000_000
            return datetime.fromtimestamp(timestamp_seconds)
        except (ValueError, OverflowError) as e:
            error_msg = f"Invalid timestamp conversion: {unix_nano} - {e}"
            logger.warning(error_msg)
            self.errors.append(error_msg)
            return None

    def parse_otel_trace(self, source: Union[str, Path, Dict]) -> List[TaskData]:
        """
        Parse OpenTelemetry trace data from various source types.

        Args:
            source: File path (str/Path) or dictionary containing trace data

        Returns:
            List of extracted TaskData objects
        """
        # Clear previous errors
        self.errors = []

        if isinstance(source, (str, Path)):
            return self.parse_trace_file(Path(source))
        elif isinstance(source, dict):
            return self.parse_trace_data(source)
        else:
            error_msg = f"Unsupported source type: {type(source)}"
            logger.error(error_msg)
            self.errors.append(error_msg)
            return []


def parse_tempo_export(path: Path) -> List[TaskData]:
    """Convenience function to parse a Tempo trace export file.

    Args:
        path: Path to the Tempo export JSON file

    Returns:
        List of TaskData objects extracted from the trace
    """
    parser = OTelTraceParser()
    return parser.parse_trace_file(path)
