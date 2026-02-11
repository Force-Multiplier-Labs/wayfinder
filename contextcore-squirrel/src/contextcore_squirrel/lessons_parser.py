"""
Lessons Learned Parser for ContextCore Squirrel

Parses markdown lesson files and extracts structured data for Tempo emission.
Follows the lesson-learned-schema.yaml specification.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# --- Pydantic Model Definitions ---


class Lesson(BaseModel):
    """Represents a single lesson learned."""

    # Identity
    id: str
    number: int
    title: str

    # Metadata
    domain: str
    leg: str
    leg_number: int
    version: Optional[str] = None
    date: Optional[str] = None
    actor: str = "agent:claude-code"

    # Content summaries
    context_summary: str = ""
    problem_summary: str = ""
    solution_summary: str = ""

    # Reusable knowledge
    heuristic: Optional[str] = None
    pattern_name: Optional[str] = None
    anti_pattern: Optional[str] = None
    has_checklist: bool = False
    has_code_example: bool = False

    # Categorization
    tags: str = ""
    scope: Optional[str] = None
    root_cause: Optional[str] = None

    # Progressive disclosure
    token_budget: int = 0
    summary_tokens: int = 0
    source_file: str = ""
    source_line: int = 0

    # Full content (not emitted as attribute, but stored for reference)
    full_content: str = Field(default="", repr=False)


class LessonLeg(BaseModel):
    """Represents a topic group (leg) of lessons."""

    id: str
    number: int
    name: str
    description: str = ""
    domain: str = ""
    lesson_count: int = 0
    key_patterns: str = ""
    source_file: str = ""
    lessons: List[Lesson] = Field(default_factory=list)


class LessonDomain(BaseModel):
    """Represents a knowledge domain."""

    id: str
    name: str
    description: str = ""
    leg_count: int = 0
    lesson_count: int = 0
    source_path: str = ""
    legs: List[LessonLeg] = Field(default_factory=list)


# --- Utility Functions ---


def estimate_tokens(text: str, code_multiplier: float = 1.2) -> int:
    """Estimate token count for text content."""
    if not text:
        return 0

    code_blocks = re.findall(r"```[\s\S]*?```", text)
    code_chars = sum(len(block) for block in code_blocks)
    prose_chars = len(text) - code_chars

    # ~4 chars per token for prose, multiply for code
    prose_tokens = prose_chars / 4
    code_tokens = (code_chars / 4) * code_multiplier

    return int(prose_tokens + code_tokens)


def summarize_text(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, preserving sentence boundaries if possible."""
    if not text or len(text) <= max_chars:
        return text.strip()

    truncated = text[:max_chars]
    last_period = truncated.rfind(".")
    if last_period > max_chars * 0.6:
        return truncated[: last_period + 1].strip()

    return truncated.strip() + "..."


def extract_field(content: str, field_name: str) -> Optional[str]:
    """Extract a markdown field value like **Context:** or **Problem:**"""
    pattern = rf"\*\*{field_name}:?\*\*\s*(.+?)(?=\n\*\*|\n###|\n---|\Z)"
    match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def extract_reusable_items(content: str) -> dict:
    """Extract reusable items from **Reusable:** section."""
    reusable = extract_field(content, "Reusable")
    if not reusable:
        return {}

    items: dict = {}

    heuristic_match = re.search(
        r"\*\*Heuristic:?\*\*\s*(.+?)(?=\n\s*-\s*\*\*|\n\*\*|\Z)", reusable, re.DOTALL
    )
    if heuristic_match:
        items["heuristic"] = heuristic_match.group(1).strip()

    pattern_match = re.search(r"\*\*Pattern:?\*\*\s*`?([^`\n]+)`?", reusable)
    if pattern_match:
        items["pattern_name"] = pattern_match.group(1).strip()

    anti_match = re.search(
        r"\*\*Anti-pattern:?\*\*\s*(.+?)(?=\n\s*-\s*\*\*|\n\*\*|\Z)", reusable, re.DOTALL
    )
    if anti_match:
        items["anti_pattern"] = anti_match.group(1).strip()

    items["has_checklist"] = bool(re.search(r"\*\*Checklist:?\*\*|\[\s*\]", reusable))

    return items


# --- Parse Functions ---


def parse_lesson(
    content: str,
    lesson_number: int,
    domain_id: str,
    leg_id: str,
    leg_number: int,
    source_file: str,
    source_line: int,
) -> Lesson:
    """Parse a single lesson from markdown content."""

    title_match = re.match(r"#{2,3}\s*\d+\.\s*(.+)", content.strip())
    title = title_match.group(1).strip() if title_match else f"Lesson {lesson_number}"

    lesson_id = f"{domain_id}-{leg_id}-{lesson_number}"

    version = extract_field(content, "Version")
    date = extract_field(content, "Date")
    actor = extract_field(content, "Actor") or "agent:claude-code"

    context = extract_field(content, "Context") or ""
    problem = extract_field(content, "Problem") or ""
    solution = extract_field(content, "Solution") or ""

    reusable = extract_reusable_items(content)

    tags_raw = extract_field(content, "Tags") or ""
    tags = re.sub(r"[\[\]]", "", tags_raw).strip()

    scope = extract_field(content, "Scope")
    root_cause = extract_field(content, "Root cause") or extract_field(content, "Root Cause")

    has_code = bool(re.search(r"```", content))

    full_tokens = estimate_tokens(content)
    summary_tokens = estimate_tokens(f"{title} {context[:150]} {problem[:150]} {solution[:200]}")

    return Lesson(
        id=lesson_id,
        number=lesson_number,
        title=title,
        domain=domain_id,
        leg=leg_id,
        leg_number=leg_number,
        version=version,
        date=date,
        actor=actor,
        context_summary=summarize_text(context, 150),
        problem_summary=summarize_text(problem, 150),
        solution_summary=summarize_text(solution, 200),
        heuristic=summarize_text(reusable.get("heuristic", ""), 200) or None,
        pattern_name=reusable.get("pattern_name"),
        anti_pattern=summarize_text(reusable.get("anti_pattern", ""), 200) or None,
        has_checklist=reusable.get("has_checklist", False),
        has_code_example=has_code,
        tags=tags,
        scope=scope,
        root_cause=summarize_text(root_cause or "", 150) or None,
        token_budget=full_tokens,
        summary_tokens=summary_tokens,
        source_file=source_file,
        source_line=source_line,
        full_content=content,
    )


def parse_leg_file(file_path: Path, domain_id: str) -> Optional[LessonLeg]:
    """Parse a leg/topic markdown file containing multiple lessons."""

    content = file_path.read_text(encoding="utf-8")

    leg_num_match = re.match(r"(\d+)-(.+)\.md", file_path.name)
    if not leg_num_match:
        logger.info(f"Skipping {file_path.name}: doesn't match XX-name.md pattern")
        return None

    leg_number = int(leg_num_match.group(1))
    leg_id = leg_num_match.group(2)

    title_match = re.match(r"#\s*(?:Leg\s*\d+:?\s*)?(.+)", content)
    leg_name = title_match.group(1).strip() if title_match else leg_id.replace("-", " ").title()

    desc_match = re.search(r"^#[^\n]+\n+([^#\n][^\n]+)", content, re.MULTILINE)
    description = desc_match.group(1).strip() if desc_match else ""

    lesson_splits = re.split(r"(?=^#{2,3}\s*\d+\.)", content, flags=re.MULTILINE)

    lessons = []
    for split in lesson_splits:
        if not re.match(r"#{2,3}\s*\d+\.", split.strip()):
            continue

        num_match = re.match(r"#{2,3}\s*(\d+)\.", split.strip())
        if not num_match:
            continue

        lesson_num = int(num_match.group(1))

        source_line = content.find(split.strip()[:50])
        source_line = content[:source_line].count("\n") + 1 if source_line > 0 else 1

        lesson = parse_lesson(
            split, lesson_num, domain_id, leg_id, leg_number, str(file_path), source_line
        )
        lessons.append(lesson)

    if not lessons:
        logger.info(f"No lessons found in {file_path.name}")
        return None

    patterns = [lesson.pattern_name for lesson in lessons if lesson.pattern_name]
    key_patterns = ", ".join(patterns[:5])

    return LessonLeg(
        id=leg_id,
        number=leg_number,
        name=leg_name,
        description=description,
        domain=domain_id,
        lesson_count=len(lessons),
        key_patterns=key_patterns,
        source_file=str(file_path),
        lessons=lessons,
    )


def parse_domain(domain_path: Path) -> Optional[LessonDomain]:
    """Parse a domain directory containing lesson files."""

    lessons_dir = domain_path / "lessons"
    if not lessons_dir.exists():
        logger.info(f"No lessons/ directory in {domain_path.name}")
        return None

    domain_id = domain_path.name.lower().replace(" ", "-").replace("_", "-")

    main_file = domain_path / f"{domain_path.name}_LESSONS_LEARNED.md"
    if not main_file.exists():
        for pattern in ["*_LESSONS_LEARNED.md", "*LESSONS*.md"]:
            matches = list(domain_path.glob(pattern))
            if matches:
                main_file = matches[0]
                break

    description = ""
    if main_file.exists():
        content = main_file.read_text(encoding="utf-8")
        desc_match = re.search(r"^#[^\n]+\n+([^#\n][^\n]+)", content, re.MULTILINE)
        if desc_match:
            description = desc_match.group(1).strip()

    legs = []
    leg_files = sorted(lessons_dir.glob("*.md"))

    for leg_file in leg_files:
        logger.info(f"Parsing {leg_file.name}...")
        leg = parse_leg_file(leg_file, domain_id)
        if leg:
            legs.append(leg)

    if not legs:
        return None

    total_lessons = sum(leg.lesson_count for leg in legs)

    return LessonDomain(
        id=domain_id,
        name=domain_path.name.replace("_", " ").title(),
        description=description,
        leg_count=len(legs),
        lesson_count=total_lessons,
        source_path=str(domain_path),
        legs=legs,
    )


def parse_all_domains(base_path: Path) -> List[LessonDomain]:
    """Parse all domain directories under base path."""

    domains = []

    for item in sorted(base_path.iterdir()):
        if not item.is_dir():
            continue
        if item.name.startswith("."):
            continue

        lessons_dir = item / "lessons"
        if lessons_dir.exists():
            logger.info(f"Parsing domain: {item.name}")
            domain = parse_domain(item)
            if domain:
                domains.append(domain)

    return domains


def to_dict(obj: object) -> dict | object:
    """Convert Pydantic model or object to dict, handling nested objects."""
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    return obj


class LessonsParser:
    """High-level wrapper for parsing lessons learned directories."""

    def __init__(self, base_path: Path | str) -> None:
        self.base_path = Path(base_path)

    def parse(self) -> List[LessonDomain]:
        """Parse all domains under the base path."""
        if (self.base_path / "lessons").exists():
            domain = parse_domain(self.base_path)
            return [domain] if domain else []
        return parse_all_domains(self.base_path)

    def parse_domain(self, domain_name: str) -> Optional[LessonDomain]:
        """Parse a specific domain."""
        domain_path = self.base_path / domain_name
        if not domain_path.exists():
            logger.error(f"Domain {domain_name} not found at {domain_path}")
            return None
        return parse_domain(domain_path)

    def parse_json(self) -> str:
        """Parse all domains and return JSON string."""
        domains = self.parse()
        output = {
            "schema_version": "1.0.0",
            "total_domains": len(domains),
            "total_legs": sum(d.leg_count for d in domains),
            "total_lessons": sum(d.lesson_count for d in domains),
            "domains": [d.model_dump() for d in domains],
        }
        return json.dumps(output, indent=2)
