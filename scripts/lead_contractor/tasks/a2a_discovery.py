"""
A2A AgentCard & Discovery tasks for Lead Contractor workflow.

Feature 4.3: Implement A2A-compatible agent discovery with ContextCore extensions.
"""

from ..runner import Feature

AGENT_CARD_TASK = """
Create AgentCard model compatible with A2A specification plus ContextCore extensions.

## Goal
Define a data model for agent self-description that is compatible with A2A's AgentCard
while adding ContextCore-specific extensions for OTel discovery.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/discovery/agent_card.py
- A2A AgentCard includes: name, url, version, capabilities, skills, authentication
- ContextCore extensions: tempo_url, traceql_prefix, project_refs

## Requirements

1. Create AgentCapabilities dataclass:
   ```python
   @dataclass
   class AgentCapabilities:
       # A2A standard capabilities
       streaming: bool = False
       push_notifications: bool = False
       state_transition_history: bool = False
       # ContextCore extensions
       insights: bool = True
       handoffs: bool = True
       skills: bool = True
       otel_native: bool = True
   ```

2. Create SkillDescriptor dataclass (A2A-compatible skill definition):
   ```python
   @dataclass
   class SkillDescriptor:
       id: str
       name: str
       description: str
       tags: list[str] = field(default_factory=list)
       examples: list[str] = field(default_factory=list)
       input_modes: list[str] = field(default_factory=lambda: ["application/json"])
       output_modes: list[str] = field(default_factory=lambda: ["application/json"])
   ```

3. Create AuthScheme enum:
   ```python
   class AuthScheme(str, Enum):
       BEARER = "Bearer"
       BASIC = "Basic"
       API_KEY = "ApiKey"
       OAUTH2 = "OAuth2"
       NONE = "None"
   ```

4. Create AuthConfig dataclass:
   ```python
   @dataclass
   class AuthConfig:
       schemes: list[AuthScheme]
       credentials_url: str | None = None
       oauth2_config: dict | None = None
   ```

5. Create ProviderInfo dataclass:
   ```python
   @dataclass
   class ProviderInfo:
       organization: str
       url: str | None = None
       contact: str | None = None
   ```

6. Create AgentCard dataclass:
   ```python
   @dataclass
   class AgentCard:
       # A2A required fields
       agent_id: str
       name: str
       description: str
       url: str
       version: str
       capabilities: AgentCapabilities
       skills: list[SkillDescriptor]
       # A2A optional fields
       authentication: AuthConfig | None = None
       default_input_modes: list[str] = field(default_factory=lambda: ["application/json", "text/plain"])
       default_output_modes: list[str] = field(default_factory=lambda: ["application/json", "text/plain"])
       documentation_url: str | None = None
       provider: ProviderInfo | None = None
       # ContextCore extensions
       tempo_url: str | None = None
       traceql_prefix: str | None = None
       project_refs: list[str] = field(default_factory=list)
       # Metadata
       created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
       updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

       def to_a2a_json(self) -> dict:
           '''Export as A2A-compatible JSON (no CC extensions).'''
           ...

       def to_contextcore_json(self) -> dict:
           '''Export with ContextCore extensions.'''
           ...

       @classmethod
       def from_json(cls, data: dict) -> "AgentCard":
           '''Parse from JSON (handles both A2A and CC formats).'''
           ...

       @classmethod
       def from_skill_manifest(cls, manifest: "SkillManifest", agent_id: str, url: str) -> "AgentCard":
           '''Create AgentCard from existing SkillManifest.'''
           ...
   ```

7. Add to_a2a_json() implementation following A2A spec exactly
8. Add to_contextcore_json() including all extensions

## Output Format
Provide clean Python code with:
- Proper type hints
- JSON serialization methods
- Docstrings with examples
- __all__ export list
"""

DISCOVERY_ENDPOINT_TASK = """
Create well-known discovery endpoint handler for serving agent cards.

## Goal
Implement HTTP endpoint handlers that serve .well-known/agent.json (A2A)
and .well-known/contextcore.json (extended) discovery documents.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/discovery/endpoint.py
- Must serve both A2A-compatible and ContextCore-extended discovery
- Should be framework-agnostic (return dicts, let caller handle HTTP)

## Requirements

1. Create DiscoveryDocument dataclass for CC extended format:
   ```python
   @dataclass
   class DiscoveryDocument:
       version: str
       protocol: str  # "contextcore"
       agent: dict  # AgentCard as dict
       discovery: dict  # tempo_url, traceql_prefix
       endpoints: dict  # API endpoint paths
   ```

2. Create DiscoveryEndpoint class:
   ```python
   class DiscoveryEndpoint:
       def __init__(
           self,
           agent_card: AgentCard,
           insights_path: str = "/api/v1/insights",
           handoffs_path: str = "/api/v1/handoffs",
           skills_path: str = "/api/v1/skills",
       ):
           self.agent_card = agent_card
           self.endpoints = {
               "insights": insights_path,
               "handoffs": handoffs_path,
               "skills": skills_path,
           }

       def get_a2a_agent_json(self) -> dict:
           '''Returns A2A-compatible agent.json content.'''
           return self.agent_card.to_a2a_json()

       def get_contextcore_json(self) -> dict:
           '''Returns full ContextCore discovery document.'''
           return {
               "version": "1.0",
               "protocol": "contextcore",
               "agent": self.agent_card.to_contextcore_json(),
               "discovery": {
                   "tempo_url": self.agent_card.tempo_url,
                   "traceql_prefix": self.agent_card.traceql_prefix,
               },
               "endpoints": self.endpoints,
           }

       def get_well_known_paths(self) -> dict[str, callable]:
           '''Returns mapping of paths to handler methods.'''
           return {
               "/.well-known/agent.json": self.get_a2a_agent_json,
               "/.well-known/contextcore.json": self.get_contextcore_json,
           }
   ```

3. Create Flask blueprint factory (optional):
   ```python
   def create_discovery_blueprint(endpoint: DiscoveryEndpoint) -> "flask.Blueprint":
       '''Create Flask blueprint for discovery endpoints.'''
       ...
   ```

4. Create FastAPI router factory (optional):
   ```python
   def create_discovery_router(endpoint: DiscoveryEndpoint) -> "fastapi.APIRouter":
       '''Create FastAPI router for discovery endpoints.'''
       ...
   ```

5. Handle content negotiation:
   - Accept: application/json → return JSON
   - Accept: text/html → return simple HTML page with JSON

## Output Format
Provide clean Python code with:
- Framework-agnostic core implementation
- Optional Flask/FastAPI integrations
- Proper type hints
- __all__ export list
"""

DISCOVERY_CLIENT_TASK = """
Create client for discovering remote agents via HTTP and Tempo.

## Goal
Implement a client that can discover agent capabilities from remote endpoints
(.well-known) and from Tempo spans (OTel-native discovery).

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/discovery/client.py
- Must support both A2A HTTP discovery and ContextCore Tempo discovery
- Should cache results with TTL

## Requirements

1. Create DiscoveryClient class:
   ```python
   class DiscoveryClient:
       def __init__(
           self,
           cache_ttl_seconds: int = 300,
           tempo_url: str | None = None,
           timeout_seconds: float = 10.0,
       ):
           self._cache: dict[str, tuple[AgentCard, datetime]] = {}
           self.cache_ttl = cache_ttl_seconds
           self.tempo_url = tempo_url
           self.timeout = timeout_seconds
           self._http: httpx.Client | None = None
   ```

2. Implement HTTP discovery methods:
   ```python
   def discover(self, base_url: str) -> AgentCard:
       '''Fetch AgentCard from remote agent.'''
       # Try /.well-known/contextcore.json first (has more info)
       # Fall back to /.well-known/agent.json (A2A standard)
       # Cache result
       ...

   def _fetch_contextcore_card(self, base_url: str) -> AgentCard | None:
       '''Fetch ContextCore discovery document.'''
       ...

   def _fetch_a2a_card(self, base_url: str) -> AgentCard | None:
       '''Fetch A2A agent.json.'''
       ...
   ```

3. Implement Tempo-based discovery (ContextCore-native):
   ```python
   def discover_from_tempo(self, agent_id: str) -> AgentCard | None:
       '''Discover agent from Tempo spans.'''
       # Query: { agent.id = "{agent_id}" && name =~ "skill:.*" }
       # Build AgentCard from skill manifest spans
       # Aggregate capabilities from skill spans
       ...

   def list_agents_from_tempo(self, time_range: str = "24h") -> list[str]:
       '''List all agent IDs found in Tempo.'''
       # Query: { name =~ "skill:.*" } | select(agent.id) | distinct
       ...
   ```

4. Implement cache management:
   ```python
   def get_cached(self, agent_id: str) -> AgentCard | None:
       '''Get agent from cache if not expired.'''
       ...

   def invalidate(self, agent_id: str) -> None:
       '''Remove agent from cache.'''
       ...

   def clear_cache(self) -> None:
       '''Clear all cached agents.'''
       ...

   def list_known_agents(self) -> list[AgentCard]:
       '''Return all cached agents (even if expired).'''
       ...
   ```

5. Implement context manager for HTTP client lifecycle:
   ```python
   def __enter__(self) -> "DiscoveryClient":
       self._http = httpx.Client(timeout=self.timeout)
       return self

   def __exit__(self, *args) -> None:
       if self._http:
           self._http.close()
   ```

6. Handle errors gracefully:
   - Return None for unreachable agents
   - Log warnings for malformed responses
   - Raise only on critical errors (invalid arguments)

## Output Format
Provide clean Python code with:
- import httpx
- Proper error handling
- Type hints
- Docstrings
- __all__ export list
"""

DISCOVERY_PACKAGE_TASK = """
Create discovery package with CLI integration.

## Goal
Create the package init file and CLI commands for agent discovery operations.

## Context
- This is for the ContextCore project
- Package init at src/contextcore/discovery/__init__.py
- CLI at src/contextcore/cli/discovery.py
- Must integrate with existing CLI structure

## Requirements

1. Create src/contextcore/discovery/__init__.py:
   - Import and export all public classes:
     - AgentCard, AgentCapabilities, SkillDescriptor, AuthConfig, AuthScheme, ProviderInfo
     - DiscoveryEndpoint, DiscoveryDocument
     - DiscoveryClient
   - Add module docstring with usage examples

2. Create src/contextcore/cli/discovery.py with Click commands:

   a) card command - Generate AgentCard:
   ```
   @click.command("card")
   @click.option("--agent-id", required=True, help="Agent identifier")
   @click.option("--name", required=True, help="Agent display name")
   @click.option("--url", required=True, help="Agent base URL")
   @click.option("--description", default="", help="Agent description")
   @click.option("--output", "-o", type=click.Path(), help="Output file path")
   @click.option("--format", type=click.Choice(["a2a", "contextcore"]), default="contextcore")
   def card_command(...):
       '''Generate an AgentCard JSON file.'''
   ```

   b) serve command - Start discovery server:
   ```
   @click.command("serve")
   @click.option("--port", default=8080, help="Server port")
   @click.option("--host", default="0.0.0.0", help="Server host")
   @click.option("--agent-card", type=click.Path(exists=True), help="AgentCard JSON file")
   def serve_command(...):
       '''Serve discovery endpoints (.well-known).'''
   ```

   c) fetch command - Fetch remote AgentCard:
   ```
   @click.command("fetch")
   @click.option("--url", required=True, help="Remote agent base URL")
   @click.option("--output", "-o", type=click.Path(), help="Output file path")
   def fetch_command(...):
       '''Fetch AgentCard from remote agent.'''
   ```

   d) list command - List agents from Tempo:
   ```
   @click.command("list")
   @click.option("--tempo-url", default="http://localhost:3200", help="Tempo URL")
   @click.option("--time-range", default="24h", help="Time range to search")
   def list_command(...):
       '''List agents discovered from Tempo.'''
   ```

3. Create discovery group and register with main CLI:
   ```python
   @click.group("discovery")
   def discovery_group():
       '''Agent discovery commands.'''
       pass

   discovery_group.add_command(card_command)
   discovery_group.add_command(serve_command)
   discovery_group.add_command(fetch_command)
   discovery_group.add_command(list_command)
   ```

4. Output both files in response

## Output Format
Provide clean Python code for both files with:
- Proper Click decorators
- Error handling with click.echo
- __all__ export list in __init__.py
"""

DISCOVERY_FEATURES = [
    Feature(
        task=AGENT_CARD_TASK,
        name="Discovery_AgentCard",
        output_subdir="a2a/discovery",
    ),
    Feature(
        task=DISCOVERY_ENDPOINT_TASK,
        name="Discovery_Endpoint",
        output_subdir="a2a/discovery",
    ),
    Feature(
        task=DISCOVERY_CLIENT_TASK,
        name="Discovery_Client",
        output_subdir="a2a/discovery",
    ),
    Feature(
        task=DISCOVERY_PACKAGE_TASK,
        name="Discovery_Package",
        output_subdir="a2a/discovery",
    ),
]
