"""
Tester agent for validation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from contextcore_coyote.pipeline.stage import Stage, StageContext
from contextcore_coyote.models import StageResult, StageStatus


TESTER_PROMPT = """You are an expert Tester Agent specializing in validation and quality assurance.

## Your Mission
Validate that the fix addresses the root cause, check for regressions, and provide a clear recommendation.

## Validation Process

1. **Verify Fix Addresses Root Cause**
   - Confirm the implementation matches the design
   - Check that the specific error condition is handled
   - Verify the fix would prevent the original incident

2. **Regression Analysis**
   - Identify code paths affected by the change
   - Check for unintended side effects
   - Verify existing functionality is preserved

3. **Edge Case Testing**
   - Consider boundary conditions
   - Check null/undefined handling
   - Test concurrent access if applicable

4. **Code Quality Review**
   - Check for proper error handling
   - Verify no security vulnerabilities
   - Confirm code meets standards

## Output Format

Provide a structured test report:

### Validation Summary
[Pass/Fail] - [One-sentence summary]

### Root Cause Verification
- Original Issue: [brief description]
- Fix Addresses Issue: [Yes/No with explanation]
- Evidence: [how verified]

### Regression Analysis
- Affected Code Paths: [list]
- Potential Side Effects: [list or "None identified"]
- Existing Tests: [Pass/Fail/N/A]

### Edge Cases Tested
1. [Edge case 1] - [Result]
2. [Edge case 2] - [Result]

### Code Quality
- Error Handling: [Adequate/Needs improvement]
- Security: [No issues/Concerns noted]
- Standards Compliance: [Yes/No]

### Recommendation
[APPROVE / REQUEST CHANGES / REJECT]

Reason: [Detailed justification]

### Suggested Improvements (if any)
1. [Improvement 1]
2. [Improvement 2]

---

## Implementation to Test

{implementation}

## Original Investigation

Root Cause: {root_cause}
Incident: {incident_id}

## Fix Design

{fix_design}

---

Validate this implementation and provide your recommendation.
"""


class Tester(Stage):
    """
    Agent that validates fixes.

    Reviews implementation against design, checks for regressions,
    and provides pass/fail recommendation.
    """

    name = "test"
    description = "Validate fixes and check for regressions"

    def should_skip(self, ctx: StageContext) -> bool:
        """Skip if implementation failed."""
        impl = ctx.implementation_result
        return impl is None or impl.status != StageStatus.COMPLETED

    def execute(self, ctx: StageContext) -> StageResult:
        """
        Execute validation testing.

        Args:
            ctx: Stage context with implementation results

        Returns:
            StageResult with test findings
        """
        incident = ctx.incident
        investigation = ctx.investigation_result
        design = ctx.design_result
        implementation = ctx.implementation_result

        if not implementation:
            return StageResult(
                stage_name=self.name,
                status=StageStatus.FAILED,
                started_at=datetime.now(),
                summary="No implementation results available",
                error="Implementation stage did not complete",
            )

        # Build the prompt
        prompt = TESTER_PROMPT.format(
            implementation=implementation.details,
            root_cause=investigation.root_cause if investigation else "Unknown",
            incident_id=incident.id,
            fix_design=design.fix_specification if design else "No design available",
        )

        # Call LLM for testing
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
        tests_passed = self._check_passed(response)
        recommendation = self._extract_recommendation(response)
        regression_risk = self._extract_section(response, "Regression Analysis")

        return StageResult(
            stage_name=self.name,
            status=StageStatus.COMPLETED,
            started_at=datetime.now(),
            summary=f"Validation: {recommendation}" if recommendation else "Validation complete",
            details=response,
            tests_passed=tests_passed,
            test_output=response,
            regression_risk=regression_risk,
            output={
                "full_report": response,
                "recommendation": recommendation,
                "passed": tests_passed,
            },
        )

    def _check_passed(self, response: str) -> bool:
        """Check if tests passed based on recommendation."""
        response_lower = response.lower()
        if "approve" in response_lower and "reject" not in response_lower:
            return True
        if "[pass]" in response_lower:
            return True
        if "request changes" in response_lower or "reject" in response_lower:
            return False
        return True  # Default to passed if unclear

    def _extract_recommendation(self, response: str) -> Optional[str]:
        """Extract recommendation from response."""
        for line in response.split("\n"):
            if "APPROVE" in line.upper():
                return "APPROVE"
            if "REJECT" in line.upper():
                return "REJECT"
            if "REQUEST CHANGES" in line.upper():
                return "REQUEST CHANGES"
        return None

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
