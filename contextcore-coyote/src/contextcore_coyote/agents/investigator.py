"""
Investigator agent for root cause analysis.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from contextcore_coyote.pipeline.stage import Stage, StageContext
from contextcore_coyote.models import StageResult, StageStatus


INVESTIGATOR_PROMPT = """You are an expert Investigator Agent specializing in root cause analysis.

## Your Mission
Trace errors to their origin with precision. Find the root cause, identify the code, and locate the PR that introduced the issue.

## CRITICAL: Use Real File Paths
You MUST use file paths that actually exist in the codebase. Do NOT hallucinate or guess paths.
- If a stack trace shows a file path, use that exact path
- If codebase context is provided, only reference files that exist in the file tree
- If you're unsure about a path, say so explicitly rather than guessing

## Investigation Process

1. **Parse the Error**
   - Extract error type, message, and location
   - Identify the failing function/method from the stack trace
   - Note any relevant context (user, request, state)

2. **Trace the Code Path**
   - Follow the stack trace to find the origin
   - Use EXACT file paths from the stack trace
   - Identify the specific line(s) of code involved

3. **Query Observability** (if available)
   - Check metrics for anomalies around the error time
   - Search logs for additional context
   - Find related traces for the full request path

4. **Find the Origin**
   - Use git blame to find when the code was changed
   - Identify the PR that introduced the change
   - Review the PR context to understand intent

## Output Format

Provide a structured investigation report:

### Root Cause
[Clear explanation of what caused the error]

### Affected Code
- File: [EXACT path from stack trace or codebase - e.g., src/startd8/utils/file_operations.py]
- Line(s): [line numbers from stack trace]
- Function: [function name from stack trace]

### Originating Change
- Commit: [hash]
- PR: [number if known]
- Author: [if known]
- Date: [when introduced]

### Severity Assessment
[Critical/High/Medium/Low] - [justification]

### Recommended Next Steps
1. [First recommendation]
2. [Second recommendation]

---
{codebase_context}
## Incident Details

{incident_details}

## Error Information

{error_info}

## Stack Trace

{stack_trace}

---

Investigate this incident and provide your findings. Use ONLY file paths that appear in the stack trace or codebase context above.
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


class Investigator(Stage):
    """
    Agent that investigates incidents to find root causes.

    Uses stack traces, git blame, and observability queries to trace
    errors to their origin.
    """

    name = "investigate"
    description = "Trace errors to their root cause"

    def execute(self, ctx: StageContext) -> StageResult:
        """
        Execute investigation on the incident.

        Args:
            ctx: Stage context with incident

        Returns:
            StageResult with investigation findings
        """
        incident = ctx.incident

        # Build codebase context section if available
        codebase_context = ""
        if ctx.has_codebase_context:
            key_files_section = ""
            if ctx.key_files:
                key_files_section = "### Key Files\n"
                for path, content in ctx.key_files.items():
                    key_files_section += f"\n**{path}:**\n```\n{content[:500]}...\n```\n"

            codebase_context = CODEBASE_CONTEXT_TEMPLATE.format(
                project_name=ctx.project_name or "Unknown",
                project_root=ctx.project_root or "Unknown",
                project_language=ctx.project_language or "Unknown",
                file_tree=ctx.file_tree or "Not available",
                key_files_section=key_files_section,
            )

        # Add capability index if available (semantic understanding)
        if ctx.has_capability_index:
            codebase_context += f"\n{ctx.capability_index}\n"

        # Build the prompt
        prompt = INVESTIGATOR_PROMPT.format(
            codebase_context=codebase_context,
            incident_details=f"""
ID: {incident.id}
Title: {incident.title}
Severity: {incident.severity.value}
Source: {incident.source}
Detected: {incident.detected_at or incident.created_at}
Affected Files: {', '.join(incident.affected_files) if incident.affected_files else 'Unknown'}
""",
            error_info=incident.error_message or incident.description,
            stack_trace=incident.stack_trace or "No stack trace available",
        )

        # Call LLM for investigation
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

        # Parse response to extract key findings
        root_cause = self._extract_section(response, "Root Cause")
        affected_code = self._extract_files(response)
        originating_pr = self._extract_pr(response)

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary=f"Investigation complete: {root_cause[:100]}..." if root_cause else "Investigation complete",
            details=response,
            root_cause=root_cause,
            affected_code=affected_code,
            originating_pr=originating_pr,
            output={"full_report": response},
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

    def _extract_files(self, response: str) -> list:
        """Extract affected file paths from the response."""
        files = []
        for line in response.split("\n"):
            if "File:" in line or "- File:" in line:
                # Extract path from line like "- File: path/to/file.py"
                parts = line.split(":")
                if len(parts) >= 2:
                    path = parts[-1].strip()
                    if path and "/" in path:
                        files.append(path)
        return files

    def _extract_pr(self, response: str) -> Optional[str]:
        """Extract PR reference from the response."""
        for line in response.split("\n"):
            if "PR:" in line or "- PR:" in line:
                parts = line.split(":")
                if len(parts) >= 2:
                    pr = parts[-1].strip()
                    if pr and pr != "[number if known]":
                        return pr
        return None
