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

## CRITICAL: Use Real File Paths
You MUST use file paths that actually exist in the codebase. Do NOT hallucinate or guess paths.
- Use the EXACT paths from the investigation and design stages
- If codebase context is provided, only modify files that exist in the file tree
- Match the project's language ({project_language}) — do NOT generate code in other languages

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

Provide the implementation using REAL paths from the codebase:

### Summary
[One-sentence description of changes]

### Files Modified

#### [EXACT path from codebase - e.g., src/startd8/utils/file_operations.py]
```{project_language}
# Show the complete modified function/section
# Include enough context for review
```

#### [Another EXACT path from codebase]
```{project_language}
# Additional changes
```

### New Files (if any)

#### [path/following/project/conventions/new_file.py]
```{project_language}
# Complete new file content
```

### Tests to Add

#### [tests/path/following/project/conventions/test_file.py]
```{project_language}
# Test cases for the fix
```

### Commit Message
```
[type]: [brief description]

[Body explaining what and why]

Fixes: {incident_id}
```

---
{codebase_context}
## Fix Specification

{fix_design}

## Investigation Context

Root Cause: {root_cause}
Affected Files: {affected_files}

---

Implement this fix with production-quality {project_language} code. Use ONLY file paths that exist in the codebase context above.
"""

CODEBASE_CONTEXT_TEMPLATE = """
## Codebase Context

**Project:** {project_name}
**Root:** {project_root}
**Language:** {project_language}

### File Structure
```
{file_tree}
```

{key_files_section}
---
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

        # Build codebase context section if available
        codebase_context = ""
        project_language = ctx.project_language or "python"
        if ctx.has_codebase_context:
            key_files_section = ""
            if ctx.key_files:
                key_files_section = "### Key Files\n"
                for path, content in ctx.key_files.items():
                    key_files_section += f"\n**{path}:**\n```\n{content[:500]}...\n```\n"

            codebase_context = CODEBASE_CONTEXT_TEMPLATE.format(
                project_name=ctx.project_name or "Unknown",
                project_root=ctx.project_root or "Unknown",
                project_language=project_language,
                file_tree=ctx.file_tree or "Not available",
                key_files_section=key_files_section,
            )

        # Add capability index if available (semantic understanding)
        if ctx.has_capability_index:
            codebase_context += f"\n{ctx.capability_index}\n"

        # Build the prompt
        prompt = IMPLEMENTER_PROMPT.format(
            codebase_context=codebase_context,
            project_language=project_language,
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
