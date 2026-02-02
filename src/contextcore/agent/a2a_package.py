# src/contextcore/a2a/__init__.py
"""
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
"""

from contextcore.agent.a2a_adapter import TaskAdapter, TaskState
from contextcore.agent.a2a_messagehandler import A2AMessageHandler, A2AErrorCode
from contextcore.agent.a2a_server import A2AServer, create_a2a_server
from contextcore.agent.a2a_client import A2AClient, A2AError

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
