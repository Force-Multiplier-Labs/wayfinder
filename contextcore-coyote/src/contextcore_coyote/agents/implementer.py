"""
Implementer agent for code generation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from contextcore_coyote.pipeline.stage import Stage, StageContext
from contextcore_coyote.models import StageResult, StageStatus


IMPLEMENTER_PROMPT = """You are an expert Implementer Agent specializing in production-quality code.

## Your Mission
Write precise, professional code that implements the designed fix while matching existing conventions.

## Implementation Standards

1. **Match Existing Patterns**
   - Follow the codebase's naming conventions
   - Use consistent formatting and style
   - Match existing error handling patterns

2. **Professional Comments**
   - Explain "why", not "what"
   - Document non-obvious decisions
   - Reference the incident ID in fix comments

3. **Quality Checklist**
   - No debug code or console logs
   - Proper error handling
   - Edge cases covered
   - No security vulnerabilities

4. **Self-Documenting Code**
   - Use clear, descriptive names
   - Prefer explicit over clever
   - Keep functions focused

## Output Format

Provide the implementation:

### Summary
[One-sentence description of changes]

### Files Modified

#### [path/to/file.py]
```python
# Show the complete modified function/section
# Include enough context for review
```

#### [path/to/another/file.py]
```python
# Additional changes
```

### New Files (if any)

#### [path/to/new_file.py]
```python
# Complete new file content
```

### Tests to Add

#### [path/to/test_file.py]
```python
# Test cases for the fix
```

### Commit Message
```
[type]: [brief description]

[Body explaining what and why]

Fixes: {incident_id}
```

---

## Fix Specification

{fix_design}

## Investigation Context

Root Cause: {root_cause}
Affected Files: {affected_files}

---

Implement this fix with production-quality code.
"""


class Implementer(Stage):
    """
    Agent that implements code fixes.

    Takes fix specifications and produces production-quality code
    that matches existing conventions.
    """

    name = "implement"
    description = "Write production-quality code fixes"

    def should_skip(self, ctx: StageContext) -> bool:
        """Skip if design failed."""
        design = ctx.design_result
        return design is None or design.status != StageStatus.COMPLETED

    def execute(self, ctx: StageContext) -> StageResult:
        """
        Execute code implementation.

        Args:
            ctx: Stage context with design results

        Returns:
            StageResult with code changes
        """
        incident = ctx.incident
        investigation = ctx.investigation_result
        design = ctx.design_result

        if not design:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                started_at=datetime.now(),
                summary="No design results available",
                error="Design stage did not complete",
            )

        # Build the prompt
        prompt = IMPLEMENTER_PROMPT.format(
            fix_design=design.fix_specification or design.details,
            root_cause=investigation.root_cause if investigation else "Unknown",
            affected_files=", ".join(investigation.affected_code) if investigation else "Unknown",
            incident_id=incident.id,
        )

        # Call LLM for implementation
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

        # Parse response to extract code changes
        code_changes = self._extract_code_changes(response)
        commit_message = self._extract_commit_message(response)

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary=self._extract_section(response, "Summary") or "Implementation complete",
            details=response,
            code_changes=code_changes,
            output={
                "full_implementation": response,
                "commit_message": commit_message,
            },
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

    def _extract_code_changes(self, response: str) -> Dict[str, str]:
        """Extract code changes from the response."""
        changes = {}
        lines = response.split("\n")
        current_file = None
        current_code = []
        in_code_block = False

        for line in lines:
            # Check for file header
            if line.startswith("#### ") and "/" in line:
                if current_file and current_code:
                    changes[current_file] = "\n".join(current_code)
                current_file = line[5:].strip()
                current_code = []
                in_code_block = False
                continue

            # Check for code block
            if line.startswith("```"):
                if in_code_block:
                    in_code_block = False
                else:
                    in_code_block = True
                continue

            # Collect code
            if in_code_block and current_file:
                current_code.append(line)

        # Don't forget the last file
        if current_file and current_code:
            changes[current_file] = "\n".join(current_code)

        return changes

    def _extract_commit_message(self, response: str) -> Optional[str]:
        """Extract commit message from the response."""
        lines = response.split("\n")
        in_commit = False
        commit_lines = []

        for line in lines:
            if "### Commit Message" in line:
                in_commit = True
                continue
            if in_commit:
                if line.startswith("```"):
                    if commit_lines:
                        break
                    continue
                if line.startswith("###"):
                    break
                commit_lines.append(line)

        return "\n".join(commit_lines).strip() if commit_lines else None
