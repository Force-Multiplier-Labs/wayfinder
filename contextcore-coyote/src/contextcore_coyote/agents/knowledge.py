"""
Knowledge agent for lessons learned.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from contextcore_coyote.pipeline.stage import Stage, StageContext
from contextcore_coyote.models import StageResult, StageStatus, Lesson


KNOWLEDGE_PROMPT = """You are an expert Knowledge Agent specializing in organizational learning.

## Your Mission
Extract actionable lessons from incidents to prevent future occurrences and build team knowledge.

## Learning Extraction Process

1. **Identify the Pattern**
   - What type of error was this? (null reference, race condition, etc.)
   - Is this part of a larger pattern we've seen before?
   - What category does this belong to?

2. **Extract Actionable Lessons**
   - What should developers know to avoid this?
   - What checks could prevent this in code review?
   - What automated tests could catch this?

3. **Document Prevention Steps**
   - Specific code patterns to use
   - Review checklist items to add
   - Automated checks to implement

4. **Consider Broader Impact**
   - Are there similar issues elsewhere in the codebase?
   - Should this be a linting rule?
   - Is training needed?

## Output Format

Provide structured lessons:

### Incident Summary
[Brief description of what happened]

### Category
[Error type category: null-reference, type-error, race-condition, security, performance, etc.]

### Lessons Learned

#### Lesson 1
**Lesson**: [What we learned]
**Prevention**: [How to prevent this]
**Related Files**: [Files where this applies]
**Tags**: [searchable tags]

#### Lesson 2
**Lesson**: [What we learned]
**Prevention**: [How to prevent this]
**Related Files**: [Files where this applies]
**Tags**: [searchable tags]

### Prevention Checklist
- [ ] [Checklist item 1]
- [ ] [Checklist item 2]

### Broader Recommendations
1. [Recommendation 1]
2. [Recommendation 2]

### Knowledge Base Update
```markdown
## {incident_id}: {title}

**Date**: {date}
**Category**: {category}

### What Happened
[Description]

### Root Cause
[Root cause]

### Prevention
[How to prevent]

### Related
- Files: [list]
- Tags: [list]
```

---

## Incident Details

ID: {incident_id}
Title: {title}
Severity: {severity}

## Investigation Findings

{investigation}

## Fix Details

{fix_design}

## Implementation

{implementation}

## Test Results

{test_results}

---

Extract lessons from this incident for our knowledge base.
"""


class KnowledgeAgent(Stage):
    """
    Agent that extracts lessons learned.

    Analyzes completed incidents to capture patterns and prevention
    strategies for the knowledge base.
    """

    name = "learn"
    description = "Extract and document lessons learned"

    def execute(self, ctx: StageContext) -> StageResult:
        """
        Execute knowledge extraction.

        Args:
            ctx: Stage context with all previous results

        Returns:
            StageResult with lessons learned
        """
        incident = ctx.incident
        investigation = ctx.investigation_result
        design = ctx.design_result
        implementation = ctx.implementation_result
        test = ctx.get_result("test")

        # Build the prompt
        prompt = KNOWLEDGE_PROMPT.format(
            incident_id=incident.id,
            title=incident.title,
            severity=incident.severity.value,
            date=datetime.now().strftime("%Y-%m-%d"),
            investigation=investigation.details if investigation else "No investigation",
            fix_design=design.details if design else "No design",
            implementation=implementation.details if implementation else "No implementation",
            test_results=test.details if test else "No test results",
        )

        # Call LLM for knowledge extraction
        try:
            response = self.call_llm(prompt)
        except Exception as e:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                started_at=datetime.now(),
                summary="Failed to call LLM",
                error=str(e),
            )

        # Parse response
        lessons = self._extract_lessons(response, incident.id)
        prevention_steps = self._extract_prevention(response)
        category = self._extract_category(response)

        # Emit to ContextCore if enabled
        if self.config.contextcore_enabled:
            self._emit_to_contextcore(lessons, incident)

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary=f"Extracted {len(lessons)} lessons in category: {category}",
            details=response,
            lessons=[l.lesson for l in lessons],
            prevention_steps=prevention_steps,
            output={
                "full_report": response,
                "lessons": [l.to_dict() for l in lessons],
                "category": category,
            },
        )

    def _extract_lessons(self, response: str, incident_id: str) -> List[Lesson]:
        """Extract structured lessons from the response."""
        lessons = []
        lines = response.split("\n")
        current_lesson = None
        current_field = None

        for line in lines:
            if line.startswith("#### Lesson"):
                if current_lesson:
                    lessons.append(current_lesson)
                lesson_num = len(lessons) + 1
                current_lesson = Lesson(
                    id=f"{incident_id}-L{lesson_num}",
                    incident_id=incident_id,
                    category="unknown",
                    lesson="",
                    prevention="",
                )
            elif current_lesson:
                if line.startswith("**Lesson**:"):
                    current_lesson.lesson = line.split(":", 1)[1].strip()
                elif line.startswith("**Prevention**:"):
                    current_lesson.prevention = line.split(":", 1)[1].strip()
                elif line.startswith("**Related Files**:"):
                    files = line.split(":", 1)[1].strip()
                    current_lesson.related_files = [f.strip() for f in files.split(",")]
                elif line.startswith("**Tags**:"):
                    tags = line.split(":", 1)[1].strip()
                    current_lesson.tags = [t.strip() for t in tags.split(",")]

        if current_lesson:
            lessons.append(current_lesson)

        return lessons

    def _extract_prevention(self, response: str) -> List[str]:
        """Extract prevention checklist items."""
        items = []
        in_checklist = False

        for line in response.split("\n"):
            if "### Prevention Checklist" in line:
                in_checklist = True
                continue
            if in_checklist:
                if line.startswith("###"):
                    break
                if line.strip().startswith("- ["):
                    item = line.split("]", 1)[1].strip() if "]" in line else line
                    if item:
                        items.append(item)

        return items

    def _extract_category(self, response: str) -> str:
        """Extract the category from the response."""
        for line in response.split("\n"):
            if line.startswith("### Category"):
                # Get the next non-empty line
                idx = response.split("\n").index(line)
                for next_line in response.split("\n")[idx + 1 :]:
                    if next_line.strip():
                        return next_line.strip()
        return "unknown"

    def _emit_to_contextcore(self, lessons: List[Lesson], incident) -> None:
        """Emit lessons to ContextCore as insights."""
        try:
            from contextcore.agent import InsightEmitter

            emitter = InsightEmitter(
                project_id="coyote",
                agent_id="knowledge-agent",
            )

            for lesson in lessons:
                emitter.emit_lesson(
                    summary=lesson.lesson,
                    category=lesson.category,
                    applies_to=lesson.related_files,
                    context={
                        "incident_id": incident.id,
                        "prevention": lesson.prevention,
                        "tags": lesson.tags,
                    },
                )

        except ImportError:
            pass  # ContextCore not available
        except Exception:
            pass  # Don't fail the stage for emission errors
