"""
ContextCore Squirrel (Ajidamoo) - Skills library for token-efficient agent discovery.

Provides parsers and emitters for knowledge items and lessons learned,
emitting structured data as OpenTelemetry spans to Tempo.
"""

__version__ = "0.1.0"

from contextcore_squirrel.knowledge_parser import (
    CapabilityItem,
    Endpoint,
    KnowledgeParser,
    Process,
    Project,
    Skill,
    SquirrelIndex,
    Tool,
    Workflow,
    parse_capability_index,
    parse_endpoints_yaml,
    parse_processes_yaml,
    parse_projects_yaml,
    parse_skills_yaml,
    parse_tools_yaml,
    parse_workflows_yaml,
)
from contextcore_squirrel.lessons_parser import (
    Lesson,
    LessonDomain,
    LessonLeg,
    LessonsParser,
)

__all__ = [
    # Knowledge parser
    "CapabilityItem",
    "Endpoint",
    "KnowledgeParser",
    "Process",
    "Project",
    "Skill",
    "SquirrelIndex",
    "Tool",
    "Workflow",
    "parse_capability_index",
    "parse_endpoints_yaml",
    "parse_processes_yaml",
    "parse_projects_yaml",
    "parse_skills_yaml",
    "parse_tools_yaml",
    "parse_workflows_yaml",
    # Lessons parser
    "Lesson",
    "LessonDomain",
    "LessonLeg",
    "LessonsParser",
]
