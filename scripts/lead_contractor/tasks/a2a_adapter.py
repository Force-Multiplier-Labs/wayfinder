"""
A2A Protocol Adapter tasks for Lead Contractor workflow.

Feature 4.5: Create adapter layer for bidirectional A2A protocol support.
"""

from ..runner import Feature

TASK_ADAPTER_TASK = """
Create adapter to translate between A2A Task and ContextCore Handoff.

## Goal
Implement bidirectional translation between A2A Task format and ContextCore Handoff,
enabling interoperability with A2A-compatible agents.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/a2a/task_adapter.py
- A2A Task: taskId, contextId, status, messages, artifacts, timestamps
- ContextCore Handoff: id, from_agent, to_agent, capability_id, status, etc.

## Requirements

1. Create TaskState enum (A2A states):
   ```python
   class TaskState(str, Enum):
       PENDING = "PENDING"
       WORKING = "WORKING"
       INPUT_REQUIRED = "INPUT_REQUIRED"
       COMPLETED = "COMPLETED"
       FAILED = "FAILED"
       CANCELLED = "CANCELLED"
       REJECTED = "REJECTED"
   ```

2. Create TaskAdapter class:
   ```python
   class TaskAdapter:
       '''Bidirectional translation between A2A Task and CC Handoff.'''

       # Status mapping tables
       _HANDOFF_TO_TASK: dict[HandoffStatus, TaskState] = {
           HandoffStatus.PENDING: TaskState.PENDING,
           HandoffStatus.ACCEPTED: TaskState.WORKING,
           HandoffStatus.IN_PROGRESS: TaskState.WORKING,
           HandoffStatus.INPUT_REQUIRED: TaskState.INPUT_REQUIRED,
           HandoffStatus.COMPLETED: TaskState.COMPLETED,
           HandoffStatus.FAILED: TaskState.FAILED,
           HandoffStatus.TIMEOUT: TaskState.FAILED,
           HandoffStatus.CANCELLED: TaskState.CANCELLED,
           HandoffStatus.REJECTED: TaskState.REJECTED,
       }

       _TASK_TO_HANDOFF: dict[TaskState, HandoffStatus] = {
           TaskState.PENDING: HandoffStatus.PENDING,
           TaskState.WORKING: HandoffStatus.IN_PROGRESS,
           TaskState.INPUT_REQUIRED: HandoffStatus.INPUT_REQUIRED,
           TaskState.COMPLETED: HandoffStatus.COMPLETED,
           TaskState.FAILED: HandoffStatus.FAILED,
           TaskState.CANCELLED: HandoffStatus.CANCELLED,
           TaskState.REJECTED: HandoffStatus.REJECTED,
       }
   ```

3. Implement Handoff to Task conversion:
   ```python
   @classmethod
   def handoff_to_task(cls, handoff: Handoff, messages: list[Message] = None, artifacts: list[Artifact] = None) -> dict:
       '''Convert ContextCore Handoff to A2A Task JSON.'''
       return {
           "taskId": handoff.id,
           "contextId": f"{handoff.from_agent}:{handoff.to_agent}",
           "status": cls._status_to_task_state(handoff.status).value,
           "messages": [m.to_a2a_dict() for m in (messages or [])],
           "artifacts": [a.to_a2a_dict() for a in (artifacts or [])],
           "createdTime": handoff.created_at.isoformat(),
           "updatedTime": datetime.now(timezone.utc).isoformat(),
           # A2A metadata
           "metadata": {
               "contextcore": {
                   "from_agent": handoff.from_agent,
                   "to_agent": handoff.to_agent,
                   "capability_id": handoff.capability_id,
                   "priority": handoff.priority.value,
               }
           }
       }

   @classmethod
   def _status_to_task_state(cls, status: HandoffStatus) -> TaskState:
       return cls._HANDOFF_TO_TASK.get(status, TaskState.PENDING)
   ```

4. Implement Task to Handoff conversion:
   ```python
   @classmethod
   def task_to_handoff(
       cls,
       task: dict,
       from_agent: str,
       to_agent: str,
       capability_id: str = "unknown",
   ) -> Handoff:
       '''Convert A2A Task JSON to ContextCore Handoff.'''
       # Extract CC metadata if present
       cc_meta = task.get("metadata", {}).get("contextcore", {})

       status = cls._task_state_to_status(task.get("status", "PENDING"))

       return Handoff(
           id=task.get("taskId", f"task-{uuid.uuid4().hex[:12]}"),
           from_agent=cc_meta.get("from_agent", from_agent),
           to_agent=cc_meta.get("to_agent", to_agent),
           capability_id=cc_meta.get("capability_id", capability_id),
           task=cls._extract_task_description(task),
           inputs=cls._extract_inputs(task),
           expected_output=ExpectedOutput(type="any", fields=[]),
           priority=HandoffPriority(cc_meta.get("priority", "normal")),
           status=status,
           created_at=cls._parse_timestamp(task.get("createdTime")),
       )

   @classmethod
   def _task_state_to_status(cls, state: str) -> HandoffStatus:
       task_state = TaskState(state) if state in TaskState.__members__ else TaskState.PENDING
       return cls._TASK_TO_HANDOFF.get(task_state, HandoffStatus.PENDING)

   @classmethod
   def _extract_task_description(cls, task: dict) -> str:
       '''Extract task description from first text message.'''
       for msg in task.get("messages", []):
           for part in msg.get("parts", []):
               if "text" in part:
                   return part["text"]
       return ""

   @classmethod
   def _extract_inputs(cls, task: dict) -> dict:
       '''Extract inputs from task messages.'''
       # Look for JSON/data parts in messages
       ...
   ```

5. Implement Message conversion helpers:
   ```python
   @classmethod
   def messages_from_task(cls, task: dict) -> list[Message]:
       '''Extract Messages from A2A Task.'''
       return [Message.from_a2a_dict(m) for m in task.get("messages", [])]

   @classmethod
   def artifacts_from_task(cls, task: dict) -> list[Artifact]:
       '''Extract Artifacts from A2A Task.'''
       return [Artifact.from_a2a_dict(a) for a in task.get("artifacts", [])]
   ```

## Output Format
Provide clean Python code with:
- Complete bidirectional conversion
- Proper type hints
- Helper methods
- __all__ export list
"""

MESSAGE_HANDLER_TASK = """
Create JSON-RPC message handler for A2A protocol methods.

## Goal
Implement a handler that processes A2A JSON-RPC 2.0 requests and routes them
to appropriate ContextCore operations.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/a2a/message_handler.py
- A2A uses JSON-RPC 2.0 with methods: message.send, tasks.get, tasks.cancel, etc.
- Must integrate with ContextCore HandoffsAPI and SkillsAPI

## Requirements

1. Create JSON-RPC error codes:
   ```python
   class A2AErrorCode(IntEnum):
       PARSE_ERROR = -32700
       INVALID_REQUEST = -32600
       METHOD_NOT_FOUND = -32601
       INVALID_PARAMS = -32602
       INTERNAL_ERROR = -32603
       # A2A-specific errors
       TASK_NOT_FOUND = -32001
       TASK_CANCELLED = -32002
       CONTENT_TYPE_NOT_SUPPORTED = -32003
       VERSION_NOT_SUPPORTED = -32004
   ```

2. Create A2AMessageHandler class:
   ```python
   class A2AMessageHandler:
       '''Handle A2A JSON-RPC messages.'''

       def __init__(
           self,
           handoffs_api: HandoffsAPI,
           skills_api: SkillsAPI,
           agent_card: AgentCard,
       ):
           self.handoffs = handoffs_api
           self.skills = skills_api
           self.agent_card = agent_card
           self._methods: dict[str, Callable] = {
               "message.send": self._handle_message_send,
               "tasks.get": self._handle_tasks_get,
               "tasks.list": self._handle_tasks_list,
               "tasks.cancel": self._handle_tasks_cancel,
               "agent.getExtendedAgentCard": self._handle_get_agent_card,
           }
   ```

3. Implement main handler:
   ```python
   def handle(self, request: dict) -> dict:
       '''Handle JSON-RPC 2.0 request.'''
       # Validate request structure
       if not self._is_valid_request(request):
           return self._error_response(None, A2AErrorCode.INVALID_REQUEST, "Invalid request")

       method = request.get("method")
       params = request.get("params", {})
       request_id = request.get("id")

       if method not in self._methods:
           return self._error_response(request_id, A2AErrorCode.METHOD_NOT_FOUND, f"Method not found: {method}")

       try:
           result = self._methods[method](params)
           return self._success_response(request_id, result)
       except ValueError as e:
           return self._error_response(request_id, A2AErrorCode.INVALID_PARAMS, str(e))
       except Exception as e:
           return self._error_response(request_id, A2AErrorCode.INTERNAL_ERROR, str(e))
   ```

4. Implement method handlers:
   ```python
   def _handle_message_send(self, params: dict) -> dict:
       '''Handle message.send - creates handoff.'''
       message = params.get("message", {})
       context_id = params.get("contextId")

       # Extract task from message
       task_text = self._extract_text(message)

       # Create handoff
       handoff_id = self.handoffs.create(
           to_agent=self.agent_card.agent_id,
           capability_id=params.get("capabilityId", "default"),
           task=task_text,
           inputs=self._extract_inputs(message),
           expected_output={"type": "any", "fields": []},
       )

       # Return task representation
       return TaskAdapter.handoff_to_task(
           self.handoffs.get(handoff_id),
           messages=[Message.from_a2a_dict(message)],
       )

   def _handle_tasks_get(self, params: dict) -> dict:
       '''Handle tasks.get - returns task status.'''
       task_id = params.get("taskId")
       if not task_id:
           raise ValueError("taskId is required")

       result = self.handoffs.get(task_id)
       return TaskAdapter.handoff_to_task(result)

   def _handle_tasks_list(self, params: dict) -> dict:
       '''Handle tasks.list - returns list of tasks.'''
       # Implement listing logic
       ...

   def _handle_tasks_cancel(self, params: dict) -> dict:
       '''Handle tasks.cancel - cancels a task.'''
       task_id = params.get("taskId")
       if not task_id:
           raise ValueError("taskId is required")

       success = self.handoffs.cancel(task_id)
       return {"taskId": task_id, "status": "CANCELLED" if success else "FAILED"}

   def _handle_get_agent_card(self, params: dict) -> dict:
       '''Handle agent.getExtendedAgentCard.'''
       return self.agent_card.to_a2a_json()
   ```

5. Implement helper methods:
   ```python
   def _success_response(self, request_id: Any, result: Any) -> dict:
       return {"jsonrpc": "2.0", "result": result, "id": request_id}

   def _error_response(self, request_id: Any, code: int, message: str) -> dict:
       return {"jsonrpc": "2.0", "error": {"code": code, "message": message}, "id": request_id}

   def _is_valid_request(self, request: dict) -> bool:
       return (
           isinstance(request, dict)
           and request.get("jsonrpc") == "2.0"
           and "method" in request
       )
   ```

## Output Format
Provide clean Python code with:
- Complete JSON-RPC 2.0 handling
- All method implementations
- Error handling
- __all__ export list
"""

A2A_SERVER_TASK = """
Create HTTP server that speaks A2A protocol.

## Goal
Implement an HTTP server that serves A2A protocol endpoints, including
discovery (.well-known) and JSON-RPC message handling.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/a2a/server.py
- Must serve both discovery endpoints and JSON-RPC handler
- Should support optional SSE streaming

## Requirements

1. Create A2AServer class:
   ```python
   class A2AServer:
       '''HTTP server implementing A2A protocol endpoints.'''

       def __init__(
           self,
           agent_card: AgentCard,
           handoffs_api: HandoffsAPI,
           skills_api: SkillsAPI,
           host: str = "0.0.0.0",
           port: int = 8080,
       ):
           self.agent_card = agent_card
           self.handler = A2AMessageHandler(handoffs_api, skills_api, agent_card)
           self.discovery = DiscoveryEndpoint(agent_card)
           self.host = host
           self.port = port
           self._app = None
   ```

2. Implement Flask app creation:
   ```python
   def create_flask_app(self):
       '''Create Flask application.'''
       from flask import Flask, request, jsonify

       app = Flask(__name__)

       @app.route("/.well-known/agent.json")
       def get_agent_json():
           return jsonify(self.discovery.get_a2a_agent_json())

       @app.route("/.well-known/contextcore.json")
       def get_contextcore_json():
           return jsonify(self.discovery.get_contextcore_json())

       @app.route("/a2a", methods=["POST"])
       def handle_a2a():
           req = request.get_json()
           result = self.handler.handle(req)
           return jsonify(result)

       # Health check
       @app.route("/health")
       def health():
           return jsonify({"status": "ok", "agent_id": self.agent_card.agent_id})

       self._app = app
       return app
   ```

3. Implement FastAPI app creation (alternative):
   ```python
   def create_fastapi_app(self):
       '''Create FastAPI application.'''
       from fastapi import FastAPI, Request
       from fastapi.responses import JSONResponse

       app = FastAPI(title=self.agent_card.name, version=self.agent_card.version)

       @app.get("/.well-known/agent.json")
       async def get_agent_json():
           return self.discovery.get_a2a_agent_json()

       @app.get("/.well-known/contextcore.json")
       async def get_contextcore_json():
           return self.discovery.get_contextcore_json()

       @app.post("/a2a")
       async def handle_a2a(request: Request):
           req = await request.json()
           result = self.handler.handle(req)
           return JSONResponse(content=result)

       @app.get("/health")
       async def health():
           return {"status": "ok", "agent_id": self.agent_card.agent_id}

       self._app = app
       return app
   ```

4. Implement run methods:
   ```python
   def run_flask(self, debug: bool = False):
       '''Start Flask server.'''
       app = self.create_flask_app()
       app.run(host=self.host, port=self.port, debug=debug)

   def run_uvicorn(self, reload: bool = False):
       '''Start FastAPI server with uvicorn.'''
       import uvicorn
       app = self.create_fastapi_app()
       uvicorn.run(app, host=self.host, port=self.port, reload=reload)

   def run(self, framework: str = "flask", **kwargs):
       '''Start server with specified framework.'''
       if framework == "flask":
           self.run_flask(**kwargs)
       elif framework == "fastapi":
           self.run_uvicorn(**kwargs)
       else:
           raise ValueError(f"Unknown framework: {framework}")
   ```

5. Create factory function:
   ```python
   def create_a2a_server(
       agent_id: str,
       agent_name: str,
       base_url: str,
       project_id: str,
       host: str = "0.0.0.0",
       port: int = 8080,
       tempo_url: str = "http://localhost:3200",
   ) -> A2AServer:
       '''Factory to create A2A server with all dependencies.'''
       from contextcore.api import HandoffsAPI, SkillsAPI

       agent_card = AgentCard(
           agent_id=agent_id,
           name=agent_name,
           description=f"ContextCore agent: {agent_name}",
           url=base_url,
           version="1.0.0",
           capabilities=AgentCapabilities(),
           skills=[],
           tempo_url=tempo_url,
       )

       handoffs = HandoffsAPI(project_id=project_id, agent_id=agent_id)
       skills = SkillsAPI(agent_id=agent_id)

       return A2AServer(agent_card, handoffs, skills, host, port)
   ```

## Output Format
Provide clean Python code with:
- Flask and FastAPI support
- Complete endpoint implementations
- Factory function
- __all__ export list
"""

A2A_CLIENT_TASK = """
Create client for communicating with A2A-compatible agents.

## Goal
Implement a client that can send A2A JSON-RPC messages to remote agents
and convert responses to ContextCore objects.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/a2a/client.py
- Must send JSON-RPC 2.0 requests and handle responses
- Should support both sync and async operations

## Requirements

1. Create A2AClient class:
   ```python
   class A2AClient:
       '''Client for communicating with A2A-compatible agents.'''

       def __init__(
           self,
           base_url: str,
           auth: AuthConfig | None = None,
           timeout_seconds: float = 30.0,
       ):
           self.base_url = base_url.rstrip("/")
           self.auth = auth
           self.timeout = timeout_seconds
           self._http: httpx.Client | None = None
           self._request_counter = 0
   ```

2. Implement HTTP client management:
   ```python
   def __enter__(self) -> "A2AClient":
       self._http = httpx.Client(timeout=self.timeout)
       return self

   def __exit__(self, *args) -> None:
       if self._http:
           self._http.close()

   def _get_client(self) -> httpx.Client:
       if self._http is None:
           self._http = httpx.Client(timeout=self.timeout)
       return self._http

   def _next_request_id(self) -> str:
       self._request_counter += 1
       return f"req-{self._request_counter}"
   ```

3. Implement JSON-RPC request:
   ```python
   def _request(self, method: str, params: dict | None = None) -> dict:
       '''Send JSON-RPC request.'''
       request = {
           "jsonrpc": "2.0",
           "method": method,
           "params": params or {},
           "id": self._next_request_id(),
       }

       headers = {"Content-Type": "application/json"}
       if self.auth:
           headers.update(self._get_auth_headers())

       response = self._get_client().post(
           f"{self.base_url}/a2a",
           json=request,
           headers=headers,
       )
       response.raise_for_status()

       result = response.json()
       if "error" in result:
           raise A2AError(result["error"]["code"], result["error"]["message"])

       return result.get("result", {})
   ```

4. Implement A2A methods:
   ```python
   def send_message(
       self,
       message: Message,
       context_id: str | None = None,
       capability_id: str | None = None,
   ) -> dict:
       '''Send message to remote agent (message.send).'''
       params = {
           "message": message.to_a2a_dict(),
       }
       if context_id:
           params["contextId"] = context_id
       if capability_id:
           params["capabilityId"] = capability_id

       return self._request("message.send", params)

   def get_task(self, task_id: str) -> dict:
       '''Get task status (tasks.get).'''
       return self._request("tasks.get", {"taskId": task_id})

   def list_tasks(self, context_id: str | None = None, limit: int = 100) -> list[dict]:
       '''List tasks (tasks.list).'''
       params = {"limit": limit}
       if context_id:
           params["contextId"] = context_id
       result = self._request("tasks.list", params)
       return result.get("tasks", [])

   def cancel_task(self, task_id: str) -> dict:
       '''Cancel task (tasks.cancel).'''
       return self._request("tasks.cancel", {"taskId": task_id})

   def get_agent_card(self) -> AgentCard:
       '''Fetch agent card from .well-known/agent.json.'''
       response = self._get_client().get(f"{self.base_url}/.well-known/agent.json")
       response.raise_for_status()
       return AgentCard.from_json(response.json())
   ```

5. Implement ContextCore conversion methods:
   ```python
   def send_and_await(
       self,
       message: Message,
       timeout_ms: int = 300000,
       poll_interval_ms: int = 1000,
   ) -> Handoff:
       '''Send message and wait for completion, returning as Handoff.'''
       task = self.send_message(message)
       task_id = task.get("taskId")

       deadline = time.time() + (timeout_ms / 1000)
       while time.time() < deadline:
           task = self.get_task(task_id)
           status = task.get("status")

           if status in ("COMPLETED", "FAILED", "CANCELLED", "REJECTED"):
               return TaskAdapter.task_to_handoff(task, "local", "remote")

           time.sleep(poll_interval_ms / 1000)

       raise TimeoutError(f"Task {task_id} did not complete within {timeout_ms}ms")

   def send_text(self, text: str, **kwargs) -> dict:
       '''Convenience method to send text message.'''
       return self.send_message(Message.from_text(text), **kwargs)
   ```

6. Create A2AError exception:
   ```python
   class A2AError(Exception):
       '''Error from A2A JSON-RPC response.'''
       def __init__(self, code: int, message: str):
           self.code = code
           self.message = message
           super().__init__(f"A2A Error {code}: {message}")
   ```

## Output Format
Provide clean Python code with:
- Complete client implementation
- Error handling
- Conversion methods
- __all__ export list
"""

A2A_PACKAGE_TASK = """
Create A2A package with CLI integration.

## Goal
Create the package init file and CLI commands for A2A protocol operations.

## Context
- This is for the ContextCore project
- Package init at src/contextcore/a2a/__init__.py
- CLI at src/contextcore/cli/a2a.py
- Must integrate with existing CLI structure

## Requirements

1. Create src/contextcore/a2a/__init__.py:
   ```python
   '''
   A2A Protocol Adapter for ContextCore

   This package provides bidirectional compatibility with the A2A Protocol,
   enabling ContextCore agents to communicate with A2A-compatible agents.

   Components:
   - TaskAdapter: Convert between A2A Task and CC Handoff
   - A2AMessageHandler: Handle JSON-RPC 2.0 requests
   - A2AServer: HTTP server for A2A endpoints
   - A2AClient: Client for remote A2A agents

   Example Server:
       from contextcore.a2a import create_a2a_server

       server = create_a2a_server(
           agent_id="my-agent",
           agent_name="My Agent",
           base_url="http://localhost:8080",
           project_id="my-project",
       )
       server.run()

   Example Client:
       from contextcore.a2a import A2AClient
       from contextcore.models import Message

       with A2AClient("http://remote-agent:8080") as client:
           result = client.send_text("Hello, remote agent!")
           print(result)
   '''

   from .task_adapter import TaskAdapter, TaskState
   from .message_handler import A2AMessageHandler, A2AErrorCode
   from .server import A2AServer, create_a2a_server
   from .client import A2AClient, A2AError

   __all__ = [
       "TaskAdapter",
       "TaskState",
       "A2AMessageHandler",
       "A2AErrorCode",
       "A2AServer",
       "create_a2a_server",
       "A2AClient",
       "A2AError",
   ]
   ```

2. Create src/contextcore/cli/a2a.py with Click commands:

   a) serve command:
   ```python
   @click.command("serve")
   @click.option("--agent-id", required=True, help="Agent identifier")
   @click.option("--name", required=True, help="Agent display name")
   @click.option("--project-id", required=True, help="Project identifier")
   @click.option("--host", default="0.0.0.0", help="Server host")
   @click.option("--port", default=8080, help="Server port")
   @click.option("--framework", type=click.Choice(["flask", "fastapi"]), default="flask")
   def serve_command(...):
       '''Start A2A protocol server.'''
   ```

   b) send command:
   ```python
   @click.command("send")
   @click.option("--url", required=True, help="Remote agent URL")
   @click.option("--message", "-m", required=True, help="Message text")
   @click.option("--wait/--no-wait", default=True, help="Wait for completion")
   @click.option("--timeout", default=300000, help="Timeout in milliseconds")
   def send_command(...):
       '''Send message to remote A2A agent.'''
   ```

   c) status command:
   ```python
   @click.command("status")
   @click.option("--url", required=True, help="Remote agent URL")
   @click.option("--task-id", required=True, help="Task ID to check")
   def status_command(...):
       '''Get status of remote task.'''
   ```

   d) card command:
   ```python
   @click.command("card")
   @click.option("--url", required=True, help="Remote agent URL")
   def card_command(...):
       '''Fetch AgentCard from remote agent.'''
   ```

3. Create a2a group and register with main CLI:
   ```python
   @click.group("a2a")
   def a2a_group():
       '''A2A protocol commands.'''
       pass

   a2a_group.add_command(serve_command)
   a2a_group.add_command(send_command)
   a2a_group.add_command(status_command)
   a2a_group.add_command(card_command)
   ```

4. Output both files in response

## Output Format
Provide clean Python code for both files with:
- Proper Click decorators
- Error handling
- __all__ export list
"""

A2A_ADAPTER_FEATURES = [
    Feature(
        task=TASK_ADAPTER_TASK,
        name="A2A_TaskAdapter",
        output_subdir="a2a/adapter",
    ),
    Feature(
        task=MESSAGE_HANDLER_TASK,
        name="A2A_MessageHandler",
        output_subdir="a2a/adapter",
    ),
    Feature(
        task=A2A_SERVER_TASK,
        name="A2A_Server",
        output_subdir="a2a/adapter",
    ),
    Feature(
        task=A2A_CLIENT_TASK,
        name="A2A_Client",
        output_subdir="a2a/adapter",
    ),
    Feature(
        task=A2A_PACKAGE_TASK,
        name="A2A_Package",
        output_subdir="a2a/adapter",
    ),
]
