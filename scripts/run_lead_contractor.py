#!/usr/bin/env python3
"""
Run Lead Contractor Workflow for ContextCore Phase 2 Implementation.

This script uses the startd8 SDK's Lead Contractor workflow to implement
the Phase 2 features from PHASE2_MEDIUM_EFFORT.md.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add startd8 SDK to path
sys.path.insert(0, "/Users/neilyashinsky/Documents/dev/startd8-sdk/src")

from startd8.workflows.builtin.lead_contractor_workflow import LeadContractorWorkflow

# Feature 2.1: SLO-Driven Test Generation
FEATURE_2_1_TASK = """
Implement an SLO-Driven Test Generation module for ContextCore.

## Goal
Generate load tests (k6) and chaos tests (chaos-mesh) directly from ProjectContext requirements,
eliminating manual test specification.

## Context
- This is for the ContextCore project at /Users/neilyashinsky/Documents/dev/ContextCore
- The module should be placed at src/contextcore/generators/slo_tests.py
- ContextCore uses Pydantic v2 for models, Click for CLI
- ProjectContext has spec fields: requirements (latencyP99, latencyP50, throughput, availability, errorBudget),
  targets (Service, Deployment with name/namespace), business (criticality: critical/high/medium/low)

## Requirements
1. Create a TestType enum with values: LOAD, CHAOS, AVAILABILITY, LATENCY
2. Create a GeneratedTest dataclass with: name, test_type, derived_from, content, file_extension
3. Implement parse_duration(duration_str) to convert "200ms", "1s", "5m" to milliseconds
4. Implement parse_throughput(throughput_str) to convert "100rps" to integer
5. Create SLOTestGenerator class with:
   - __init__(templates_dir: Optional[Path])
   - generate(project_id, spec, test_types) -> List[GeneratedTest]
   - _get_service_endpoint(targets, spec) -> str
   - _generate_latency_test(project_id, requirements, endpoint) -> GeneratedTest (k6 script)
   - _generate_load_test(project_id, requirements, endpoint) -> GeneratedTest (k6 script)
   - _generate_chaos_tests(project_id, requirements, targets, business) -> List[GeneratedTest] (chaos-mesh YAML)
6. Implement write_tests(tests, output_dir) -> List[Path]

## k6 Script Requirements
- Include proper imports: http, check, sleep, Rate, Trend
- Set thresholds from ProjectContext values
- Include handleSummary function for JSON output
- Generate staged load profiles for latency tests
- Generate constant-arrival-rate and spike scenarios for throughput tests

## Chaos-Mesh YAML Requirements
- Generate PodChaos for pod-kill tests
- Generate NetworkChaos for latency injection (for critical/high criticality)
- Generate StressChaos for CPU stress (for critical criticality only)
- Include proper labels: contextcore.io/project, contextcore.io/test-type

## Output Format
Provide clean, production-ready Python code with:
- Proper type hints
- Docstrings
- Standard library imports only (no external dependencies beyond dataclasses, enum, pathlib, typing, re)
"""

# Feature 2.2: Risk-Based PR Review Guidance
FEATURE_2_2_TASK = """
Implement a Risk-Based PR Review Guidance module for ContextCore.

## Goal
Create a GitHub PR review analyzer that generates review guidance, checklists, and required
reviewer suggestions based on ProjectContext risks.

## Context
- This is for the ContextCore project
- The module should be placed at src/contextcore/integrations/github_review.py
- ProjectContext has spec fields: risks (type, scope, priority, description, mitigation, controls),
  business (criticality, owner)

## Requirements
1. Create ReviewPriority enum with values: CRITICAL, HIGH, MEDIUM, LOW
2. Create ReviewFocus dataclass with: area, reason, priority, checklist, required_reviewers
3. Create ReviewGuidance dataclass with: pr_number, project_id, focus_areas, overall_priority,
   auto_checklist, warnings, and a to_markdown() method
4. Create PRReviewAnalyzer class with:
   - RISK_CHECKLISTS dict mapping risk types (security, compliance, data-integrity, availability,
     financial) to checklist items
   - RISK_REVIEWERS dict mapping risk types to reviewer teams
   - analyze(pr_number, changed_files, project_context_spec) -> ReviewGuidance
   - _get_project_id(spec) -> str
   - _match_files(files, pattern) -> List[str] using fnmatch
   - _priority_from_string(priority_str) -> ReviewPriority (P1->CRITICAL, P2->HIGH, P3->MEDIUM, P4->LOW)
   - _generate_general_checklist(files) -> List[str]

## Checklist Mappings
- security: credentials, input validation, SQL/XSS injection, auth checks, sensitive data logging
- compliance: audit logging, data retention, PII handling, change documentation
- data-integrity: transactions, idempotency, validation, backup impact
- availability: graceful degradation, circuit breakers, timeouts, health checks
- financial: cost impact, rate limiting, billing accuracy

## Markdown Output
- Include priority badge emoji (CRITICAL=🚨, HIGH=⚠️, MEDIUM=📋, LOW=ℹ️)
- Include warnings section for critical/high services
- Include focus areas with checklists as markdown checkboxes
- Include required reviewers as @mentions
- Include footer noting "Generated by ContextCore"

## Output Format
Provide clean, production-ready Python code with proper type hints and docstrings.
"""

# Feature 2.3: Contract Drift Detection
FEATURE_2_3_TASK = """
Implement a Contract Drift Detection module for ContextCore.

## Goal
Continuously verify that service implementations match their API contracts specified in
ProjectContext, detecting drift early.

## Context
- This requires two files:
  1. src/contextcore/integrations/openapi_parser.py - Parse OpenAPI specifications
  2. src/contextcore/integrations/contract_drift.py - Detect contract drift

## Part 1: OpenAPI Parser (openapi_parser.py)
1. Create EndpointSpec dataclass with: path, method, operation_id, request_content_type,
   response_content_type, response_schema, parameters
2. Implement parse_openapi(spec_url_or_path) -> List[EndpointSpec]:
   - Load from URL (http/https) or file path
   - Parse YAML or JSON based on file extension
   - Extract all endpoints from paths
3. Helper functions:
   - _get_request_content_type(operation) -> Optional[str]
   - _get_response_content_type(operation) -> Optional[str]
   - _get_response_schema(operation, spec) -> Optional[Dict]
   - _resolve_ref(ref, spec) -> Dict

## Part 2: Contract Drift Detector (contract_drift.py)
1. Create DriftIssue dataclass with: path, method, issue_type, expected, actual, severity
2. Create DriftReport dataclass with: project_id, contract_url, service_url, issues,
   endpoints_checked, endpoints_passed, and methods: has_drift, critical_issues, to_markdown()
3. Create ContractDriftDetector class with:
   - __init__(timeout: int = 10)
   - detect(project_id, contract_url, service_url, sample_requests) -> DriftReport
   - _check_endpoint(endpoint, service_url, sample_requests) -> List[DriftIssue]
   - _validate_schema(schema, data, path, method) -> List[DriftIssue]

## Issue Types
- contract_parse_error: Failed to parse OpenAPI spec
- endpoint_unreachable: Could not connect to endpoint
- content_type_mismatch: Wrong content-type in response
- invalid_json_response: Expected JSON but got invalid
- missing_required_property: Required schema property missing
- unexpected_properties: Extra properties in response

## Severities
- critical: parse errors, unreachable endpoints, missing required properties, invalid JSON
- warning: content type mismatch
- info: unexpected properties

## Output Format
Provide clean, production-ready Python code. Use only standard library (urllib, json, yaml).
"""

def run_workflow(task_description: str, feature_name: str, context: dict = None) -> dict:
    """Run Lead Contractor workflow for a feature."""
    print(f"\n{'='*60}")
    print(f"Running Lead Contractor for: {feature_name}")
    print(f"{'='*60}\n")

    workflow = LeadContractorWorkflow()

    config = {
        "task_description": task_description,
        "context": context or {
            "language": "Python 3.9+",
            "framework": "Click CLI, Pydantic v2",
            "project": "ContextCore",
            "style": "PEP 8, type hints, docstrings"
        },
        "lead_agent": "anthropic:claude-sonnet-4-20250514",
        "drafter_agent": "openai:gpt-4o-mini",
        "max_iterations": 3,
        "pass_threshold": 80,
        "integration_instructions": """
        Finalize the code for production use:
        1. Ensure all imports are at the top
        2. Add proper __all__ export list
        3. Verify type hints are complete
        4. Add inline comments for complex logic
        5. Ensure the code is self-contained and can be dropped into the project
        """
    }

    result = workflow.run(config=config)

    return {
        "feature": feature_name,
        "success": result.success,
        "final_implementation": result.output.get("final_implementation", ""),
        "summary": result.output.get("summary", {}),
        "error": result.error,
        "total_cost": result.metrics.total_cost if result.metrics else 0,
        "total_iterations": result.metadata.get("total_iterations", 0),
    }


def extract_code_blocks(text: str) -> str:
    """Extract Python code from markdown code blocks."""
    import re
    # Find code blocks between ```python and ```
    pattern = r'```python\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return "\n\n".join(matches)

    # Try generic code blocks
    pattern = r'```\n(.*?)```'
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return "\n\n".join(matches)

    return text


def save_result(result: dict, output_dir: Path):
    """Save workflow result to files."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save full result as JSON
    result_file = output_dir / f"{result['feature'].replace(' ', '_').lower()}_result.json"
    with open(result_file, 'w') as f:
        json.dump({
            "feature": result["feature"],
            "success": result["success"],
            "summary": result["summary"],
            "error": result["error"],
            "total_cost": result["total_cost"],
            "total_iterations": result["total_iterations"],
        }, f, indent=2)

    # Save implementation code
    code_file = output_dir / f"{result['feature'].replace(' ', '_').lower()}_code.py"
    code = extract_code_blocks(result["final_implementation"])
    with open(code_file, 'w') as f:
        f.write(code)

    print(f"Saved result to: {result_file}")
    print(f"Saved code to: {code_file}")


def main():
    """Run Lead Contractor workflow for all Phase 2 features."""
    output_dir = Path("/Users/neilyashinsky/Documents/dev/ContextCore/generated")

    features = [
        (FEATURE_2_1_TASK, "Feature_2_1_SLO_Tests"),
        (FEATURE_2_2_TASK, "Feature_2_2_PR_Review"),
        (FEATURE_2_3_TASK, "Feature_2_3_Contract_Drift"),
    ]

    # Check which feature to run (can pass index as argument)
    if len(sys.argv) > 1:
        try:
            idx = int(sys.argv[1]) - 1
            if 0 <= idx < len(features):
                features = [features[idx]]
            else:
                print(f"Invalid feature index. Use 1-{len(features)}")
                sys.exit(1)
        except ValueError:
            print("Usage: python run_lead_contractor.py [feature_number]")
            sys.exit(1)

    results = []
    for task, name in features:
        try:
            result = run_workflow(task, name)
            results.append(result)
            save_result(result, output_dir)

            print(f"\n{name} Result:")
            print(f"  Success: {result['success']}")
            print(f"  Iterations: {result['total_iterations']}")
            print(f"  Cost: ${result['total_cost']:.4f}")
            if result['error']:
                print(f"  Error: {result['error']}")
        except Exception as e:
            print(f"Error running {name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("All workflows complete")
    print(f"{'='*60}")

    total_cost = sum(r['total_cost'] for r in results)
    print(f"Total cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
