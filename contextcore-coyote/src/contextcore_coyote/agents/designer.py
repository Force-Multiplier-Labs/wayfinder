"""
Designer agent for fix specification.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from contextcore_coyote.pipeline.stage import Stage, StageContext
from contextcore_coyote.models import StageResult, StageStatus


DESIGNER_PROMPT = """You are an expert Designer Agent specializing in fix architecture.

## Your Mission
Design minimal, targeted fixes that address the root cause while preserving original intent.

## Design Principles

1. **Minimal Scope**
   - Change only what's necessary to fix the issue
   - Avoid refactoring unrelated code
   - Prefer surgical fixes over broad changes

2. **Preserve Intent**
   - Understand why the original code was written
   - Maintain the original behavior where correct
   - Document any intentional behavior changes

3. **Consider Tradeoffs**
   - Identify risks of the proposed fix
   - Note any performance implications
   - Consider edge cases and failure modes

4. **Enable Rollback**
   - Design fixes that can be easily reverted
   - Avoid changes that create data dependencies
   - Document rollback procedures if needed

## Output Format

Provide a structured fix specification:

### Fix Summary
[One-sentence description of the fix]

### Root Cause (from investigation)
[Brief restatement of what went wrong]

### Proposed Solution
[Detailed description of the fix approach]

### Implementation Details
- Files to modify: [list]
- New code needed: [yes/no]
- Tests to add: [list]

### Tradeoffs
1. [Tradeoff 1]
2. [Tradeoff 2]

### Alternatives Considered
1. [Alternative 1] - Why rejected: [reason]
2. [Alternative 2] - Why rejected: [reason]

### Risk Assessment
- Risk Level: [Low/Medium/High]
- Rollback Strategy: [description]

### Acceptance Criteria
1. [Criterion 1]
2. [Criterion 2]

---

## Investigation Findings

{investigation_report}

## Incident Context

{incident_context}

---

Design a fix for this issue.
"""


class Designer(Stage):
    """
    Agent that designs fix specifications.

    Takes investigation findings and produces a detailed fix plan
    with tradeoffs and alternatives.
    """

    name = "design"
    description = "Design targeted fix specifications"

    def should_skip(self, ctx: StageContext) -> bool:
        """Skip if investigation failed."""
        inv = ctx.investigation_result
        return inv is None or inv.status != StageStatus.COMPLETED

    def execute(self, ctx: StageContext) -> StageResult:
        """
        Execute fix design.

        Args:
            ctx: Stage context with investigation results

        Returns:
            StageResult with fix specification
        """
        incident = ctx.incident
        investigation = ctx.investigation_result

        if not investigation:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                started_at=datetime.now(),
                summary="No investigation results available",
                error="Investigation stage did not complete",
            )

        # Build the prompt
        prompt = DESIGNER_PROMPT.format(
            investigation_report=investigation.details or investigation.summary,
            incident_context=f"""
ID: {incident.id}
Title: {incident.title}
Severity: {incident.severity.value}
Root Cause: {investigation.root_cause or 'Unknown'}
Affected Files: {', '.join(investigation.affected_code) or 'Unknown'}
""",
        )

        # Call LLM for design
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
        fix_summary = self._extract_section(response, "Fix Summary")
        tradeoffs = self._extract_list(response, "Tradeoffs")
        alternatives = self._extract_list(response, "Alternatives Considered")

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary=fix_summary or "Fix design complete",
            details=response,
            fix_specification=response,
            tradeoffs=tradeoffs,
            alternatives=alternatives,
            output={"full_design": response},
        )

    def _extract_section(self, response: str, section: str) -> Optional[str]:
        """Extract a section from the response."""
        lines = response.split("\n")
        in_section = False
        content = []

        for line in lines:
            if line.startswith(f"### {section}"):
                in_section = True
                continue
            if in_section:
                if line.startswith("###"):
                    break
                content.append(line)

        return "\n".join(content).strip() if content else None

    def _extract_list(self, response: str, section: str) -> List[str]:
        """Extract a numbered list from a section."""
        section_content = self._extract_section(response, section)
        if not section_content:
            return []

        items = []
        for line in section_content.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Remove numbering/bullet
                item = line.lstrip("0123456789.-) ").strip()
                if item:
                    items.append(item)

        return items
