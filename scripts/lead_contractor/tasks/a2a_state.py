"""
A2A State Model Enhancement tasks for Lead Contractor workflow.

Feature 4.2: Enhance HandoffStatus and add new state-related models.
"""

from ..runner import Feature

ENHANCED_STATUS_TASK = """
Extend HandoffStatus enum with A2A-aligned states and helper methods.

## Goal
Add INPUT_REQUIRED, CANCELLED, and REJECTED states to HandoffStatus,
along with helper methods for state management and transition validation.

## Context
- This is for the ContextCore project
- Update src/contextcore/agent/handoff.py
- A2A TaskState includes: PENDING, WORKING, INPUT_REQUIRED, COMPLETED, FAILED, CANCELLED, REJECTED
- ContextCore currently has: pending, accepted, in_progress, completed, failed, timeout

## Requirements

1. Update HandoffStatus enum to include new states:
   ```python
   class HandoffStatus(str, Enum):
       # Existing states
       PENDING = "pending"
       ACCEPTED = "accepted"
       IN_PROGRESS = "in_progress"
       COMPLETED = "completed"
       FAILED = "failed"
       TIMEOUT = "timeout"
       # NEW: A2A-aligned states
       INPUT_REQUIRED = "input_required"
       CANCELLED = "cancelled"
       REJECTED = "rejected"
   ```

2. Add class methods to HandoffStatus:
   - is_terminal() -> bool: Returns True for COMPLETED, FAILED, TIMEOUT, CANCELLED, REJECTED
   - is_active() -> bool: Returns True for PENDING, ACCEPTED, IN_PROGRESS, INPUT_REQUIRED
   - can_accept_messages() -> bool: Returns True if handoff can receive new messages

3. Create StateTransition dataclass for tracking transitions:
   ```python
   @dataclass
   class StateTransition:
       from_status: HandoffStatus
       to_status: HandoffStatus
       timestamp: datetime
       reason: str | None = None
       triggered_by: str | None = None  # agent_id that triggered
   ```

4. Create VALID_TRANSITIONS constant defining allowed state changes:
   - PENDING → ACCEPTED, REJECTED, CANCELLED
   - ACCEPTED → IN_PROGRESS, CANCELLED
   - IN_PROGRESS → INPUT_REQUIRED, COMPLETED, FAILED, CANCELLED
   - INPUT_REQUIRED → IN_PROGRESS, COMPLETED, FAILED, CANCELLED

5. Add validate_transition(from_status, to_status) -> bool function

6. Update Handoff dataclass to track transition history:
   - Add field: transitions: list[StateTransition] = field(default_factory=list)

7. Preserve backward compatibility - existing code using old states must still work

## Output Format
Provide the complete updated handoff.py file with:
- All existing functionality preserved
- New states and methods added
- Proper type hints
- Docstrings for new additions
"""

STATE_EVENTS_TASK = """
Create state transition event model for tracking handoff lifecycle via OTel.

## Goal
Define event types and an emitter for tracking handoff state changes as OTel span events,
enabling monitoring and debugging of handoff lifecycle.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/agent/events.py
- Must emit OTel spans for state transitions
- Integrates with existing HandoffManager

## Requirements

1. Create HandoffEventType enum:
   ```python
   class HandoffEventType(str, Enum):
       CREATED = "handoff.created"
       STATUS_UPDATE = "handoff.status_update"
       INPUT_REQUIRED = "handoff.input_required"
       INPUT_PROVIDED = "handoff.input_provided"
       ARTIFACT_ADDED = "handoff.artifact_added"
       MESSAGE_ADDED = "handoff.message_added"
       TIMEOUT_WARNING = "handoff.timeout_warning"
       COMPLETED = "handoff.completed"
       FAILED = "handoff.failed"
   ```

2. Create HandoffEvent dataclass:
   ```python
   @dataclass
   class HandoffEvent:
       event_type: HandoffEventType
       handoff_id: str
       timestamp: datetime
       from_status: HandoffStatus | None = None
       to_status: HandoffStatus | None = None
       agent_id: str | None = None
       message: str | None = None
       metadata: dict[str, Any] = field(default_factory=dict)
   ```

3. Create HandoffEventEmitter class:
   - __init__(tracer_name: str = "contextcore.handoffs")
   - _tracer from trace.get_tracer(tracer_name)

4. Implement emit methods:
   - emit_created(handoff_id, from_agent, to_agent, capability_id) -> None
   - emit_status_update(handoff_id, from_status, to_status, agent_id, reason) -> None
   - emit_input_required(handoff_id, question, options) -> None
   - emit_input_provided(handoff_id, request_id, value) -> None
   - emit_artifact_added(handoff_id, artifact_id, artifact_type) -> None
   - emit_message_added(handoff_id, message_id, role) -> None
   - emit_completed(handoff_id, result_trace_id, duration_ms) -> None
   - emit_failed(handoff_id, error_message, duration_ms) -> None

5. Each emit method should:
   - Create an OTel span with appropriate name
   - Set span attributes for all parameters
   - Add span event with event details
   - Log at appropriate level

6. Create global default emitter instance

## Output Format
Provide clean Python code with:
- from opentelemetry import trace
- Proper type hints
- Docstrings
- __all__ export list
"""

INPUT_REQUEST_TASK = """
Create model for INPUT_REQUIRED state requests and responses.

## Goal
Define data structures for requesting input from users/agents when a handoff
enters the INPUT_REQUIRED state, enabling interactive workflows.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/agent/input_request.py
- A2A has INPUT_REQUIRED state for when agent needs clarification
- Should integrate with HandoffReceiver

## Requirements

1. Create InputType enum:
   ```python
   class InputType(str, Enum):
       TEXT = "text"                # Free-form text input
       CHOICE = "choice"            # Single selection from options
       MULTI_CHOICE = "multi_choice"  # Multiple selections
       CONFIRMATION = "confirmation"   # Yes/No confirmation
       FILE = "file"                # File upload
       JSON = "json"                # Structured JSON input
   ```

2. Create InputOption dataclass:
   ```python
   @dataclass
   class InputOption:
       value: str
       label: str
       description: str | None = None
       is_default: bool = False
   ```

3. Create InputRequest dataclass:
   ```python
   @dataclass
   class InputRequest:
       request_id: str
       handoff_id: str
       question: str
       input_type: InputType
       options: list[InputOption] | None = None
       default_value: str | None = None
       required: bool = True
       timeout_ms: int = 300000  # 5 minutes default
       validation_pattern: str | None = None  # Regex for TEXT type
       min_selections: int | None = None  # For MULTI_CHOICE
       max_selections: int | None = None  # For MULTI_CHOICE
       created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
       expires_at: datetime | None = None

       def is_expired(self) -> bool:
           if self.expires_at:
               return datetime.now(timezone.utc) > self.expires_at
           return False

       def validate_response(self, value: Any) -> tuple[bool, str | None]:
           '''Validate input response. Returns (is_valid, error_message).'''
           ...
   ```

4. Create InputResponse dataclass:
   ```python
   @dataclass
   class InputResponse:
       request_id: str
       handoff_id: str
       value: Any  # str, list[str], bool, dict depending on InputType
       responded_by: str  # agent_id or user_id
       responded_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
   ```

5. Create InputRequestManager class:
   - __init__(storage: StorageBackend)
   - create_request(handoff_id, question, input_type, options, ...) -> InputRequest
   - get_request(request_id) -> InputRequest | None
   - get_pending_requests(handoff_id) -> list[InputRequest]
   - submit_response(request_id, value, responded_by) -> InputResponse
   - cancel_request(request_id) -> bool

6. Factory methods for common patterns:
   - InputRequest.confirmation(handoff_id, question) -> InputRequest
   - InputRequest.choice(handoff_id, question, options) -> InputRequest
   - InputRequest.text(handoff_id, question, validation_pattern) -> InputRequest

## Output Format
Provide clean Python code with:
- Proper type hints
- Validation logic
- Docstrings with examples
- __all__ export list
"""

STATE_FEATURES = [
    Feature(
        task=ENHANCED_STATUS_TASK,
        name="State_EnhancedStatus",
        output_subdir="a2a/state",
    ),
    Feature(
        task=STATE_EVENTS_TASK,
        name="State_Events",
        output_subdir="a2a/state",
    ),
    Feature(
        task=INPUT_REQUEST_TASK,
        name="State_InputRequest",
        output_subdir="a2a/state",
    ),
]
