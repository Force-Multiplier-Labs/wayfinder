"""
A2A Part Model Unification tasks for Lead Contractor workflow.

Feature 4.4: Unify Evidence and content types into A2A-compatible Part model.
"""

from ..runner import Feature

PART_MODEL_TASK = """
Create unified Part model that supports both A2A and ContextCore content types.

## Goal
Define a single Part model that can represent A2A content types (TextPart, FilePart, etc.)
and ContextCore observability types (trace references, log queries, etc.).

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/models/part.py
- A2A Part types: TextPart, FilePart, DataPart, JsonPart, FormPart, etc.
- ContextCore Evidence types: trace, log_query, file, commit, adr, doc, etc.

## Requirements

1. Create PartType enum with all supported types:
   ```python
   class PartType(str, Enum):
       # A2A-compatible types
       TEXT = "text"
       FILE = "file"
       DATA = "data"
       JSON = "json"
       FORM = "form"
       IFRAME = "iframe"
       VIDEO = "video"
       AUDIO = "audio"
       ACTION = "action"
       # ContextCore observability types
       TRACE = "trace"
       SPAN = "span"
       LOG_QUERY = "log_query"
       METRIC_QUERY = "metric_query"
       # ContextCore artifact types
       COMMIT = "commit"
       PR = "pr"
       ADR = "adr"
       DOC = "doc"
       CAPABILITY = "capability"
       INSIGHT = "insight"
       TASK = "task"
   ```

2. Create Part dataclass with all possible fields:
   ```python
   @dataclass
   class Part:
       '''Unified content part (A2A-compatible with ContextCore extensions).'''
       type: PartType

       # Text content (TEXT type)
       text: str | None = None

       # File content (FILE type)
       file_uri: str | None = None
       mime_type: str | None = None
       file_name: str | None = None

       # Structured data (DATA, JSON, FORM types)
       data: dict[str, Any] | None = None

       # ContextCore observability (TRACE, SPAN, LOG_QUERY, METRIC_QUERY)
       trace_id: str | None = None
       span_id: str | None = None
       query: str | None = None  # TraceQL, LogQL, PromQL

       # Reference (COMMIT, PR, ADR, DOC, CAPABILITY, INSIGHT, TASK)
       ref: str | None = None
       ref_url: str | None = None
       description: str | None = None

       # Token budget (ContextCore extension)
       tokens: int | None = None

       # Timestamp
       timestamp: datetime | None = None

       # Validation
       def __post_init__(self):
           self._validate()

       def _validate(self):
           '''Validate that required fields are present for the part type.'''
           ...
   ```

3. Implement conversion methods:
   ```python
   def to_a2a_dict(self) -> dict:
       '''Convert to A2A Part format (only A2A-compatible fields).'''
       if self.type == PartType.TEXT:
           return {"text": self.text}
       elif self.type == PartType.FILE:
           return {"fileUri": self.file_uri, "mimeType": self.mime_type}
       elif self.type in (PartType.DATA, PartType.JSON):
           return {"json": self.data}
       # ... handle other types
       else:
           # CC extension types - represent as data
           return {"json": self.to_dict()}

   def to_dict(self) -> dict:
       '''Convert to full dict representation.'''
       ...

   @classmethod
   def from_dict(cls, data: dict) -> "Part":
       '''Parse from dict (handles both A2A and CC formats).'''
       ...

   @classmethod
   def from_a2a_dict(cls, data: dict) -> "Part":
       '''Parse from A2A Part format.'''
       ...
   ```

4. Implement factory methods:
   ```python
   @classmethod
   def text(cls, text: str) -> "Part":
       return cls(type=PartType.TEXT, text=text)

   @classmethod
   def file(cls, uri: str, mime_type: str, name: str = None) -> "Part":
       return cls(type=PartType.FILE, file_uri=uri, mime_type=mime_type, file_name=name)

   @classmethod
   def json_data(cls, data: dict) -> "Part":
       return cls(type=PartType.JSON, data=data)

   @classmethod
   def trace(cls, trace_id: str, description: str = None) -> "Part":
       return cls(type=PartType.TRACE, trace_id=trace_id, description=description)

   @classmethod
   def log_query(cls, query: str, description: str = None) -> "Part":
       return cls(type=PartType.LOG_QUERY, query=query, description=description)

   @classmethod
   def commit(cls, sha: str, description: str = None, url: str = None) -> "Part":
       return cls(type=PartType.COMMIT, ref=sha, description=description, ref_url=url)

   @classmethod
   def adr(cls, ref: str, description: str = None, url: str = None) -> "Part":
       return cls(type=PartType.ADR, ref=ref, description=description, ref_url=url)
   ```

5. Implement Evidence compatibility:
   ```python
   def to_evidence(self) -> "Evidence":
       '''Convert to legacy Evidence format for backward compatibility.'''
       from contextcore.agent.insights import Evidence
       return Evidence(
           type=self._type_to_evidence_type(),
           ref=self.ref or self.trace_id or self.file_uri or "",
           description=self.description,
           query=self.query,
           timestamp=self.timestamp,
       )

   @classmethod
   def from_evidence(cls, evidence: "Evidence") -> "Part":
       '''Create Part from legacy Evidence.'''
       ...
   ```

## Output Format
Provide clean Python code with:
- Proper type hints
- Validation logic
- Comprehensive factory methods
- __all__ export list
"""

MESSAGE_MODEL_TASK = """
Create A2A-compatible Message model for handoff communication.

## Goal
Define a Message model compatible with A2A that wraps Parts and includes
ContextCore extensions for agent attribution and metadata.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/models/message.py
- A2A Message has: role, parts, messageId, timestamp
- ContextCore adds: agent_id, session_id, metadata

## Requirements

1. Create MessageRole enum:
   ```python
   class MessageRole(str, Enum):
       USER = "user"      # Client/caller
       AGENT = "agent"    # Remote agent
       SYSTEM = "system"  # System-generated (CC extension)
   ```

2. Create Message dataclass:
   ```python
   @dataclass
   class Message:
       '''A2A-compatible message with ContextCore extensions.'''
       message_id: str
       role: MessageRole
       parts: list[Part]
       timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
       # ContextCore extensions
       agent_id: str | None = None
       session_id: str | None = None
       metadata: dict[str, Any] = field(default_factory=dict)

       def __post_init__(self):
           if not self.message_id:
               self.message_id = f"msg-{uuid.uuid4().hex[:12]}"
   ```

3. Implement A2A conversion:
   ```python
   def to_a2a_dict(self) -> dict:
       '''Convert to A2A Message format.'''
       return {
           "messageId": self.message_id,
           "role": self.role.value,
           "parts": [p.to_a2a_dict() for p in self.parts],
           "timestamp": self.timestamp.isoformat(),
       }

   def to_dict(self) -> dict:
       '''Convert to full dict with CC extensions.'''
       ...

   @classmethod
   def from_a2a_dict(cls, data: dict) -> "Message":
       '''Parse from A2A Message format.'''
       ...

   @classmethod
   def from_dict(cls, data: dict) -> "Message":
       '''Parse from dict (handles both formats).'''
       ...
   ```

4. Implement factory methods:
   ```python
   @classmethod
   def from_text(cls, text: str, role: MessageRole = MessageRole.USER, **kwargs) -> "Message":
       '''Create message from plain text.'''
       return cls(
           message_id=f"msg-{uuid.uuid4().hex[:12]}",
           role=role,
           parts=[Part.text(text)],
           **kwargs
       )

   @classmethod
   def from_parts(cls, parts: list[Part], role: MessageRole = MessageRole.USER, **kwargs) -> "Message":
       '''Create message from parts.'''
       ...

   @classmethod
   def system_message(cls, text: str, **kwargs) -> "Message":
       '''Create system message.'''
       return cls.from_text(text, role=MessageRole.SYSTEM, **kwargs)

   @classmethod
   def agent_message(cls, text: str, agent_id: str, **kwargs) -> "Message":
       '''Create agent message with attribution.'''
       return cls.from_text(text, role=MessageRole.AGENT, agent_id=agent_id, **kwargs)
   ```

5. Implement utility methods:
   ```python
   def get_text_content(self) -> str:
       '''Extract all text content from parts.'''
       return " ".join(p.text for p in self.parts if p.type == PartType.TEXT and p.text)

   def get_files(self) -> list[Part]:
       '''Get all file parts.'''
       return [p for p in self.parts if p.type == PartType.FILE]

   def add_part(self, part: Part) -> "Message":
       '''Add a part and return self for chaining.'''
       self.parts.append(part)
       return self
   ```

## Output Format
Provide clean Python code with:
- Proper type hints
- Factory methods
- Utility methods
- __all__ export list
"""

ARTIFACT_MODEL_TASK = """
Create A2A-compatible Artifact model for handoff outputs.

## Goal
Define an Artifact model compatible with A2A for representing outputs generated
during handoff execution, with ContextCore extensions for OTel linking.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/models/artifact.py
- A2A Artifact has: artifactId, parts, mediaType, index, append, lastChunk
- ContextCore adds: trace_id, metadata

## Requirements

1. Create Artifact dataclass:
   ```python
   @dataclass
   class Artifact:
       '''A2A-compatible artifact with ContextCore extensions.'''
       artifact_id: str
       parts: list[Part]
       media_type: str = "application/json"
       # A2A streaming support
       index: int = 0
       append: bool = False
       last_chunk: bool = True
       # ContextCore extensions
       trace_id: str | None = None  # Link to OTel trace
       name: str | None = None  # Human-readable name
       description: str | None = None
       metadata: dict[str, Any] = field(default_factory=dict)
       created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

       def __post_init__(self):
           if not self.artifact_id:
               self.artifact_id = f"artifact-{uuid.uuid4().hex[:12]}"
   ```

2. Implement A2A conversion:
   ```python
   def to_a2a_dict(self) -> dict:
       '''Convert to A2A Artifact format.'''
       return {
           "artifactId": self.artifact_id,
           "parts": [p.to_a2a_dict() for p in self.parts],
           "mediaType": self.media_type,
           "index": self.index,
           "append": self.append,
           "lastChunk": self.last_chunk,
       }

   def to_dict(self) -> dict:
       '''Convert to full dict with CC extensions.'''
       ...

   @classmethod
   def from_a2a_dict(cls, data: dict) -> "Artifact":
       '''Parse from A2A Artifact format.'''
       ...
   ```

3. Implement factory methods:
   ```python
   @classmethod
   def from_json(cls, data: dict, artifact_id: str = None, name: str = None) -> "Artifact":
       '''Create artifact from JSON data.'''
       return cls(
           artifact_id=artifact_id or f"artifact-{uuid.uuid4().hex[:12]}",
           parts=[Part.json_data(data)],
           media_type="application/json",
           name=name,
       )

   @classmethod
   def from_text(cls, text: str, artifact_id: str = None, name: str = None) -> "Artifact":
       '''Create artifact from text.'''
       return cls(
           artifact_id=artifact_id or f"artifact-{uuid.uuid4().hex[:12]}",
           parts=[Part.text(text)],
           media_type="text/plain",
           name=name,
       )

   @classmethod
   def from_file(cls, uri: str, mime_type: str, artifact_id: str = None, name: str = None) -> "Artifact":
       '''Create artifact from file reference.'''
       return cls(
           artifact_id=artifact_id or f"artifact-{uuid.uuid4().hex[:12]}",
           parts=[Part.file(uri, mime_type)],
           media_type=mime_type,
           name=name,
       )

   @classmethod
   def from_insight(cls, insight: "Insight") -> "Artifact":
       '''Create artifact from Insight.'''
       return cls(
           artifact_id=f"insight-{insight.id}",
           parts=[Part.json_data({
               "id": insight.id,
               "type": insight.type.value,
               "summary": insight.summary,
               "confidence": insight.confidence,
           })],
           media_type="application/json",
           name=f"Insight: {insight.summary[:50]}",
           trace_id=insight.trace_id,
       )
   ```

4. Implement streaming support:
   ```python
   @classmethod
   def create_chunk(
       cls,
       artifact_id: str,
       parts: list[Part],
       index: int,
       is_last: bool,
   ) -> "Artifact":
       '''Create a streaming chunk.'''
       return cls(
           artifact_id=artifact_id,
           parts=parts,
           index=index,
           append=True,
           last_chunk=is_last,
       )

   def is_complete(self) -> bool:
       '''Check if this is a complete (non-streaming) artifact.'''
       return self.last_chunk and not self.append
   ```

## Output Format
Provide clean Python code with:
- Proper type hints
- Factory methods for common patterns
- Streaming support
- __all__ export list
"""

MODELS_PACKAGE_TASK = """
Create models package with backward compatibility for Evidence.

## Goal
Create the package init file that exports all model classes and maintains
backward compatibility with the legacy Evidence class.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/models/__init__.py
- Must maintain Evidence compatibility for existing code

## Requirements

1. Import and re-export all model classes:
   ```python
   from .part import Part, PartType
   from .message import Message, MessageRole
   from .artifact import Artifact
   ```

2. Create Evidence alias for backward compatibility:
   ```python
   import warnings

   def _create_evidence_alias():
       '''Create Evidence as deprecated alias for Part.'''

       class Evidence(Part):
           '''
           DEPRECATED: Use Part instead.

           This class is maintained for backward compatibility.
           '''
           def __init__(self, type: str, ref: str, description: str = None, query: str = None, timestamp = None):
               warnings.warn(
                   "Evidence is deprecated, use Part instead",
                   DeprecationWarning,
                   stacklevel=2
               )
               # Map old Evidence fields to Part
               part_type = self._map_evidence_type(type)
               super().__init__(
                   type=part_type,
                   ref=ref,
                   description=description,
                   query=query,
                   timestamp=timestamp,
               )

           @staticmethod
           def _map_evidence_type(evidence_type: str) -> PartType:
               '''Map legacy Evidence type strings to PartType.'''
               mapping = {
                   "trace": PartType.TRACE,
                   "log_query": PartType.LOG_QUERY,
                   "metric_query": PartType.METRIC_QUERY,
                   "file": PartType.FILE,
                   "commit": PartType.COMMIT,
                   "pr": PartType.PR,
                   "adr": PartType.ADR,
                   "doc": PartType.DOC,
                   "task": PartType.TASK,
                   "capability": PartType.CAPABILITY,
               }
               return mapping.get(evidence_type, PartType.DATA)

       return Evidence

   Evidence = _create_evidence_alias()
   ```

3. Add module docstring with migration guide:
   ```python
   '''
   ContextCore Data Models

   This package provides A2A-compatible data models with ContextCore extensions.

   Core Models:
   - Part: Unified content unit (replaces Evidence)
   - Message: Communication with role and parts
   - Artifact: Generated outputs

   Migration from Evidence to Part:
   ```python
   # Old way (deprecated)
   from contextcore.agent.insights import Evidence
   ev = Evidence(type="trace", ref="abc123", description="...")

   # New way
   from contextcore.models import Part
   part = Part.trace(trace_id="abc123", description="...")
   ```

   A2A Compatibility:
   ```python
   from contextcore.models import Message, Part

   msg = Message.from_text("Hello", role=MessageRole.USER)
   a2a_dict = msg.to_a2a_dict()  # A2A-compatible format
   ```
   '''
   ```

4. Export __all__ with all public names:
   ```python
   __all__ = [
       # Part model
       "Part",
       "PartType",
       # Message model
       "Message",
       "MessageRole",
       # Artifact model
       "Artifact",
       # Backward compatibility
       "Evidence",
   ]
   ```

## Output Format
Provide clean Python code with:
- Proper imports
- Backward compatibility
- Documentation
- __all__ export list
"""

PARTS_FEATURES = [
    Feature(
        task=PART_MODEL_TASK,
        name="Parts_PartModel",
        output_subdir="a2a/parts",
    ),
    Feature(
        task=MESSAGE_MODEL_TASK,
        name="Parts_MessageModel",
        output_subdir="a2a/parts",
    ),
    Feature(
        task=ARTIFACT_MODEL_TASK,
        name="Parts_ArtifactModel",
        output_subdir="a2a/parts",
    ),
    Feature(
        task=MODELS_PACKAGE_TASK,
        name="Parts_ModelsPackage",
        output_subdir="a2a/parts",
    ),
]
