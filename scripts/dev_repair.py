"""
HOWL Workflow — Human-Orchestrated Watchdog Loop

Coyote's dev mode auto-repair pipeline. When Coyote detects an error, it HOWLs —
triggering a 5-stage AI pipeline with human oversight at approval gates.

HOWL Stages:
  1. Investigate — Root cause analysis (Investigator agent)
  2. Design — Fix specification (Designer agent)
  3. Implement — Code generation (Implementer agent)
  4. Test — Validation and regression check (Tester agent)
  5. Learn — Extract lessons for future prevention (Knowledge agent)

Two integration styles:
  1. Callback: plug into PrimeContractorWorkflow.on_checkpoint_failed
  2. Function: repair_from_error() for ad-hoc "investigate and fix this error"

No Rabbit/HTTP required — Coyote is a Python library in the same workspace.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from scripts.prime_contractor.feature_queue import FeatureSpec
    from scripts.prime_contractor.checkpoint import CheckpointResult

logger = logging.getLogger(__name__)

# Default output directory (matches coyote_bridge convention)
DEFAULT_GENERATED_DIR = Path("generated/coyote")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_relative(filepath: str, project_root: Optional[Path]) -> Path:
    """Return *filepath* relative to *project_root* when possible.

    Handles three cases:
      1. ``project_root`` is None → return the path as-is.
      2. ``filepath`` is already relative → return as-is (``relative_to``
         would raise ``ValueError`` when comparing a relative path against
         an absolute ``project_root``).
      3. ``filepath`` is absolute and under ``project_root`` → relativize.
         If it's absolute but *not* under ``project_root``, fall back to
         the path as-is rather than crashing.
    """
    p = Path(filepath)
    if not project_root or not p.is_absolute():
        return p
    try:
        return p.relative_to(project_root)
    except ValueError:
        return p


# ---------------------------------------------------------------------------
# Skip filter — errors unlikely to benefit from a code fix
# ---------------------------------------------------------------------------
# Each entry: (category, compiled regex pattern)
# Patterns are matched case-insensitively against the full error message.

SKIP_PATTERNS: List[tuple] = [
    # Auth / authz — needs credentials or policy changes, not code
    ("auth", re.compile(
        r"(401\b|403\b|unauthorized|forbidden|authentication failed"
        r"|invalid.?token|expired.?token|access.?denied"
        r"|invalid.?credentials|login.?failed|not.?authenticated"
        r"|permission.?denied.*(?:role|policy|rbac))",
        re.IGNORECASE,
    )),
    # Rate limiting — back off, don't patch code
    ("rate_limit", re.compile(
        r"(429\b|rate.?limit|too.?many.?requests|throttl|quota.?exceeded)",
        re.IGNORECASE,
    )),
    # Infrastructure / connectivity — not a code bug
    ("infrastructure", re.compile(
        r"(connection.?refused|connection.?timed?\s*out|connection.?error"
        r"|ECONNREFUSED|ETIMEDOUT|dns.?resolution|name.?resolution"
        r"|no.?route.?to.?host|network.?unreachable"
        r"|502\b|503\b|504\b|service.?unavailable|bad.?gateway)",
        re.IGNORECASE,
    )),
    # TLS / certificate — config issue
    ("tls", re.compile(
        r"(certificate.?(?:verify|expired|invalid|error|revoked)"
        r"|ssl.?error|tls.?handshake|CERT_|self.?signed)",
        re.IGNORECASE,
    )),
    # Resource exhaustion — needs ops, not code
    ("resources", re.compile(
        r"(out.?of.?memory|OOMKill|cannot.?allocate.?memory"
        r"|disk.?(?:full|space)|no.?space.?left"
        r"|too.?many.?open.?files|EMFILE|ENFILE)",
        re.IGNORECASE,
    )),
    # Cost / budget — needs config change or budget increase, not code
    ("cost_budget", re.compile(
        r"(cost.?limit.?exceeded|budget.?exceeded|cost_budget"
        r"|exceeds?\s+(?:cost|budget|spending).?limit"
        r"|\$[\d.]+\s*>\s*\$[\d.]+"
        r"|max.?cost.?reached|spending.?cap)",
        re.IGNORECASE,
    )),
    # LLM response parsing — transient LLM output issue, not a code bug
    ("llm_parse", re.compile(
        r"(failed to parse json from (?:llm|model|ai)\b"
        r"|expecting value:\s*line\s*\d+\s*column\s*\d+"
        r"|empty.?(?:response|output|json)\s*from\s*(?:llm|model|ai)"
        r"|json\.?decode\.?error.*(?:llm|model|response)"
        r"|invalid json.*(?:llm|model|response)"
        r"|(?:llm|model)\s+returned?\s+empty)",
        re.IGNORECASE,
    )),
    # Quality gate — needs prompt/config tuning, not code fix
    ("quality_gate", re.compile(
        r"(requirements_coverage\s*=\s*0\.0%"
        r"|quality.?gate.?failed"
        r"|coverage.?(?:below|under|less.?than).?threshold"
        r"|translation.?quality.?(?:gate|check|validation).?failed"
        r"|0\.0%\s*coverage)",
        re.IGNORECASE,
    )),
    # Validation / config — misconfigured workflow, not a code bug
    ("validation_config", re.compile(
        r"(at least one agent is required"
        r"|exactly \d+ agents? (?:is|are) required"
        r"|missing required input"
        r"|validation failed:\s"
        r"|required field.+missing"
        r"|invalid.?(?:config|configuration|workflow).?:"
        r"|missing required context keys?:)",
        re.IGNORECASE,
    )),
    # Pipeline / review — generic orchestration failure, not a code bug
    ("pipeline_orchestration", re.compile(
        r"(all reviews? failed"
        r"|pipeline failed"
        r"|did not complete successfully"
        r"|workflow.?(?:aborted|cancelled|timed?.?out)"
        r"|phase .+ failed:.+(?:timeout|cancelled))",
        re.IGNORECASE,
    )),
    # Assessment timeout — transient, retry instead of patching code
    ("timeout", re.compile(
        r"(assessment.?timed?.?out"
        r"|evaluation.?timed?.?out"
        r"|task.?timed?.?out"
        r"|agent.?timed?.?out"
        r"|llm.?(?:call|request).?timed?.?out)",
        re.IGNORECASE,
    )),
    # Missing API key — config/environment issue, not code
    ("api_key_missing", re.compile(
        r"(api\s*key\s+not\s+found"
        r"|missing\s+api\s*key"
        r"|(?:api_key|api-key|apikey)\s+(?:is\s+)?(?:required|missing|not\s+set)"
        r"|no\s+api\s*key\s+(?:provided|configured)"
        r"|failed\s+to\s+resolve\s+agents.*api\s*key"
        r"|(?:ANTHROPIC|OPENAI|AZURE|GOOGLE)_API_KEY\s+(?:is\s+)?(?:not\s+set|missing|required))",
        re.IGNORECASE,
    )),
    # Missing dependency — needs pip install, not code fix
    ("dependency_missing", re.compile(
        r"((?:package|module|library)\s+not\s+installed"
        r"|run:\s*pip3?\s+install"
        r"|ModuleNotFoundError"
        r"|ImportError:\s*No\s+module\s+named"
        r"|cannot\s+import\s+name\b.*from)",
        re.IGNORECASE,
    )),
    # Handler/workflow config — needs workflow setup change, not code fix
    ("handler_config", re.compile(
        r"(feature_serial.*requires\s+handlers"
        r"|unsupported\s+handlers?:"
        r"|handler.*not\s+(?:configured|registered|found)"
        r"|(?:default|base)phasehandler.*feature_serial"
        r"|no\s+(?:handler|stage)\s+registered\s+for)",
        re.IGNORECASE,
    )),
    # Schema/checksum drift — needs re-export, not code fix
    ("schema_drift", re.compile(
        r"(source_checksum\s+mismatch"
        r"|has\s+changed\s+since.*export"
        r"|re-?run.*export\s+to\s+refresh"
        r"|checksum\s+(?:mismatch|validation\s+failed)"
        r"|schema.*(?:drift|out\s+of\s+sync|stale))",
        re.IGNORECASE,
    )),
    # LLM output validation — prompt/schema design issue, not code bug
    ("validation_review", re.compile(
        r"(invalid\s+snippet\s+after\s+retry"
        r"|invalid\s+area\s+'[^']+'\s+\(allowed:"
        r"|table\s+header\s+mismatch"
        r"|missing\s+columns?:\s*\[)",
        re.IGNORECASE,
    )),
    # Coyote self-referencing — recursion guard, never fix the fixer
    ("coyote_self", re.compile(
        r"(source[\"']?\s*:\s*[\"']?(?:dev_repair|coyote|howl)"
        r"|coyote.?(?:pipeline|repair|incident).?(?:failed|error)"
        r"|howl.?(?:pipeline|repair).?(?:failed|error)"
        r"|contextcore.?coyote\.)",
        re.IGNORECASE,
    )),
]


def check_skip_filter(error_message: str) -> Optional[str]:
    """
    Check if an error should skip the repair pipeline.

    Returns:
        Reason string if the error should be skipped, None if repair should proceed.
    """
    for category, pattern in SKIP_PATTERNS:
        match = pattern.search(error_message)
        if match:
            return (
                f"Skipped ({category}): \"{match.group(0)}\" — not a code bug"
            )
    return None


# ---------------------------------------------------------------------------
# Positive filter — errors that ARE likely code bugs worth fixing
# ---------------------------------------------------------------------------
# When observe mode is active, only errors matching a positive pattern are
# candidates for HOWL.  This inverts the default (blocklist → allowlist)
# so we can tune precision before enabling the pipeline.

POSITIVE_PATTERNS: List[tuple] = [
    # Python runtime errors — classic code bugs
    ("runtime_error", re.compile(
        r"(UnboundLocalError"
        r"|NameError:\s*name"
        r"|AttributeError:\s*(?:type\s+object|'[^']+'\s+object\s+has\s+no\s+attribute)"
        r"|TypeError:\s*(?:expected|got\s+an?\s+unexpected|missing\s+\d+\s+required|cannot\s+unpack)"
        r"|KeyError:\s*'[^']+'"
        r"|IndexError:\s*(?:list|tuple|string)\s+index\s+out\s+of\s+range)",
        re.IGNORECASE,
    )),
    # Assertion failures in production code (not tests)
    ("assertion", re.compile(
        r"(AssertionError(?!.*test))",
        re.IGNORECASE,
    )),
    # Traceback pointing to project source files
    ("traceback_src", re.compile(
        r"(File\s+\"[^\"]*(?:src/|lib/)[^\"]+\.py\",\s*line\s+\d+"
        r".*(?:Error|Exception))",
        re.IGNORECASE,
    )),
    # Explicit code-level exceptions with traceback
    ("exception_chain", re.compile(
        r"(Traceback\s+\(most\s+recent\s+call\s+last\))"
        r".*(?:UnboundLocalError|NameError|AttributeError|TypeError|KeyError|IndexError"
        r"|RuntimeError|NotImplementedError|RecursionError|StopIteration"
        r"|ZeroDivisionError|OverflowError)",
        re.IGNORECASE | re.DOTALL,
    )),
]


def check_positive_filter(error_message: str) -> Optional[str]:
    """
    Check if an error positively matches as a code bug worth fixing.

    Returns:
        Category string if the error looks like a code bug, None otherwise.
    """
    for category, pattern in POSITIVE_PATTERNS:
        if pattern.search(error_message):
            return category
    return None


def evaluate_error(error_message: str) -> Dict[str, Any]:
    """
    Evaluate an error against both skip and positive filters.

    Returns a verdict dict for logging/observation:
        {
            "allow": bool,          # Would HOWL process this?
            "positive_match": str | None,  # Positive category matched
            "skip_match": str | None,      # Skip category matched
            "reason": str,          # Human-readable explanation
        }
    """
    skip_reason = check_skip_filter(error_message)
    positive_cat = check_positive_filter(error_message)

    if skip_reason:
        return {
            "allow": False,
            "positive_match": positive_cat,
            "skip_match": skip_reason,
            "reason": skip_reason,
        }

    if positive_cat:
        return {
            "allow": True,
            "positive_match": positive_cat,
            "skip_match": None,
            "reason": f"Allowed ({positive_cat}): looks like a code bug",
        }

    return {
        "allow": False,
        "positive_match": None,
        "skip_match": None,
        "reason": "No positive match — error does not look like a code bug",
    }


# ---------------------------------------------------------------------------
# Codebase context helpers
# ---------------------------------------------------------------------------

def _detect_language(project_root: Path) -> str:
    """Detect the primary language of a project."""
    indicators = {
        "python": ["pyproject.toml", "setup.py", "requirements.txt", "Pipfile"],
        "typescript": ["tsconfig.json", "package.json"],
        "javascript": ["package.json"],
        "go": ["go.mod", "go.sum"],
        "rust": ["Cargo.toml"],
        "java": ["pom.xml", "build.gradle"],
    }

    for lang, files in indicators.items():
        for f in files:
            if (project_root / f).exists():
                # TypeScript takes priority over JavaScript
                if lang == "javascript" and (project_root / "tsconfig.json").exists():
                    continue
                return lang

    return "unknown"


def _build_file_tree(project_root: Path, max_depth: int = 3) -> str:
    """
    Build an abbreviated file tree for the project.

    Prioritizes source directories (src/, lib/, tests/) and excludes
    common non-source directories like node_modules, .git, __pycache__.
    """
    EXCLUDE_DIRS = {
        ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
        ".mypy_cache", ".tox", "dist", "build", "egg-info", ".eggs", "htmlcov",
        ".coverage", ".idea", ".vscode", "target", ".next", ".nuxt",
        ".startd8", ".startd8_state", ".claude", ".ruff_cache",
    }
    EXCLUDE_PATTERNS = {".pyc", ".pyo", ".so", ".dylib", ".egg"}

    # Priority directories that should always be shown (source code locations)
    PRIORITY_DIRS = {"src", "lib", "tests", "test", "pkg", "cmd", "internal", "app"}
    # Key source subdirectories that should be shown when inside src/
    KEY_SOURCE_DIRS = {"workflows", "observability", "utils", "models", "api", "services", "core"}

    lines: List[str] = []

    def walk(path: Path, prefix: str, depth: int) -> None:
        if depth > max_depth:
            return

        try:
            entries = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        except PermissionError:
            return

        # Filter and categorize entries
        priority_dirs = []
        other_dirs = []
        files = []

        for entry in entries:
            if entry.name.startswith(".") and entry.name not in {".github", ".gitlab-ci.yml"}:
                continue
            if entry.is_dir():
                if entry.name in EXCLUDE_DIRS:
                    continue
                if entry.name.endswith(".egg-info"):
                    continue
                # Prioritize source directories and key source subdirectories
                if entry.name in PRIORITY_DIRS or entry.name in KEY_SOURCE_DIRS:
                    priority_dirs.append(entry)
                else:
                    other_dirs.append(entry)
            else:
                if any(entry.name.endswith(p) for p in EXCLUDE_PATTERNS):
                    continue
                files.append(entry)

        # Combine directories with priority dirs first
        dirs = priority_dirs + other_dirs

        # Limit to avoid huge trees, but always include priority dirs
        truncated = False
        if len(dirs) + len(files) > 20:
            # Keep all priority dirs, then fill remaining slots
            max_other = max(0, 10 - len(priority_dirs))
            dirs = priority_dirs + other_dirs[:max_other]
            files = files[:10]
            truncated = True

        for i, d in enumerate(dirs):
            is_last = (i == len(dirs) - 1) and not files
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{d.name}/")
            extension = "    " if is_last else "│   "
            walk(d, prefix + extension, depth + 1)

        for i, f in enumerate(files):
            is_last = i == len(files) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{f.name}")

        if truncated:
            lines.append(f"{prefix}└── ... (truncated)")

    lines.append(f"{project_root.name}/")
    walk(project_root, "", 1)

    return "\n".join(lines[:150])  # Cap at 150 lines


def _extract_key_files(
    project_root: Path,
    error_message: str,
    stack_trace: Optional[str],
) -> Dict[str, str]:
    """
    Extract content snippets from files mentioned in the error/stack trace.
    """
    key_files: Dict[str, str] = {}

    # Find file paths in error message and stack trace
    text = f"{error_message}\n{stack_trace or ''}"

    # Pattern to match Python file paths in tracebacks
    # e.g., File "/path/to/file.py", line 123
    path_pattern = re.compile(r'File "([^"]+\.py)"', re.IGNORECASE)

    for match in path_pattern.finditer(text):
        file_path = match.group(1)
        path = Path(file_path)

        # Check if file exists and is under project root
        if path.exists() and path.is_file():
            try:
                # Check if under project root
                path.relative_to(project_root)
                # Read first 100 lines
                content = path.read_text()
                lines = content.split("\n")[:100]
                key_files[str(path)] = "\n".join(lines)
            except (ValueError, OSError):
                # Not under project root or can't read
                pass

    # Limit to 5 files to avoid huge context
    if len(key_files) > 5:
        key_files = dict(list(key_files.items())[:5])

    return key_files


def _load_capability_index(project_root: Path) -> Optional[str]:
    """
    Load capability index YAMLs from docs/capability-index/ if present.

    These provide semantic context about what the system is *supposed* to do,
    not just what the code does. This helps Coyote understand intent.

    Returns a condensed summary of capabilities, or None if not found.
    """
    capability_dir = project_root / "docs" / "capability-index"
    if not capability_dir.is_dir():
        return None

    # Look for capability manifest files
    capability_files = list(capability_dir.glob("*.capabilities.yaml")) + \
                       list(capability_dir.glob("*.manifest.yaml"))

    if not capability_files:
        return None

    summaries: List[str] = []
    total_chars = 0
    MAX_CHARS = 8000  # Cap total capability context

    for cap_file in sorted(capability_files):
        try:
            content = cap_file.read_text()

            # Extract key sections without parsing full YAML
            # (to avoid yaml dependency and keep it fast)
            lines = content.split("\n")

            manifest_id = ""
            description = ""
            capabilities: List[str] = []

            in_description = False
            in_capabilities = False
            current_capability = ""

            for line in lines:
                # Extract manifest_id
                if line.startswith("manifest_id:"):
                    manifest_id = line.split(":", 1)[1].strip()

                # Extract description (multi-line)
                if line.startswith("description:"):
                    in_description = True
                    desc_part = line.split(":", 1)[1].strip()
                    if desc_part and not desc_part.startswith("|"):
                        description = desc_part
                    continue

                if in_description:
                    if line.startswith("  ") or line.startswith("\t"):
                        description += " " + line.strip()
                    else:
                        in_description = False

                # Extract capability summaries
                if line.strip().startswith("- capability_id:"):
                    current_capability = line.split(":", 1)[1].strip()
                    in_capabilities = True

                if in_capabilities and line.strip().startswith("summary:"):
                    summary = line.split(":", 1)[1].strip().strip('"')
                    capabilities.append(f"  - {current_capability}: {summary}")
                    in_capabilities = False

            # Build summary for this file
            file_summary = f"### {manifest_id or cap_file.name}\n"
            if description:
                file_summary += f"{description[:300]}...\n\n" if len(description) > 300 else f"{description}\n\n"
            if capabilities:
                file_summary += "**Key capabilities:**\n"
                file_summary += "\n".join(capabilities[:15])  # Limit to 15 capabilities
                if len(capabilities) > 15:
                    file_summary += f"\n  ... and {len(capabilities) - 15} more"
            file_summary += "\n\n"

            if total_chars + len(file_summary) > MAX_CHARS:
                break

            summaries.append(file_summary)
            total_chars += len(file_summary)

        except OSError:
            continue

    if not summaries:
        return None

    return "## Capability Index (What the system is supposed to do)\n\n" + "\n".join(summaries)


def coyote_repair_callback(
    feature: "FeatureSpec",
    checkpoint_results: "List[CheckpointResult]",
) -> Optional[str]:
    """
    PrimeContractorWorkflow on_checkpoint_failed compatible callback.

    Assembles error context from the failed feature and checkpoint results,
    then runs Coyote pipeline to investigate and fix.

    Returns:
        Coyote run_id if pipeline ran, None if coyote unavailable.
    """
    # Build error context from feature + checkpoints
    parts: List[str] = []
    if feature.error_message:
        parts.append(feature.error_message)

    failed_checks = [cr for cr in checkpoint_results if not cr.passed]
    for cr in failed_checks:
        parts.append(f"[{cr.checkpoint_name}] {cr.message}")
        for err in cr.errors:
            parts.append(f"  - {err}")

    error_message = "\n".join(parts) if parts else "Unknown checkpoint failure"

    context: Dict[str, Any] = {
        "feature_id": feature.id,
        "feature_name": feature.name,
        "target_files": feature.target_files,
        "generated_files": feature.generated_files,
        "integration_attempts": feature.integration_attempts,
    }

    logger.info(
        "Coyote repair triggered for feature %s (attempt %d)",
        feature.id,
        feature.integration_attempts,
    )

    result = repair_from_error(
        error_message=error_message,
        severity="HIGH",
        context=context,
        auto_apply=False,
    )

    if result["success"]:
        logger.info(
            "Coyote repair completed: run_id=%s, stages=%s",
            result["run_id"],
            result["stages"],
        )
    else:
        logger.warning("Coyote repair failed: %s", result.get("error", "unknown"))

    return result.get("run_id")


def repair_from_error(
    error_message: str,
    severity: str = "HIGH",
    context: Optional[Dict[str, Any]] = None,
    auto_apply: bool = False,
    output_dir: Optional[Path] = None,
    force: bool = False,
    project_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Run Coyote incident resolution pipeline on an error message.

    Args:
        error_message: The error to investigate and fix.
        severity: LOW/MEDIUM/HIGH/CRITICAL (default: HIGH).
        context: Optional dict with labels, affected_files, etc.
        auto_apply: If True, save generated code to generated/coyote/.
        output_dir: Override output directory (default: generated/coyote).
        force: If True, bypass the skip filter and run pipeline anyway.
        project_root: Root directory of the codebase to fix (for context).

    Returns:
        Dict with: success, run_id, incident_id, stages,
                   code_changes_count, generated_dir (if auto_apply).
                   If skipped: success=False, skipped=True, reason=str.
    """
    # Check skip filter (unless forced)
    if not force:
        skip_reason = check_skip_filter(error_message)
        if skip_reason:
            logger.info("Repair skipped: %s", skip_reason)
            return {
                "success": False,
                "skipped": True,
                "reason": skip_reason,
                "run_id": None,
                "incident_id": None,
                "stages": [],
                "code_changes_count": 0,
            }

    try:
        from contextcore_coyote.models import Incident, IncidentSeverity
        from contextcore_coyote.pipeline import Pipeline
        from contextcore_coyote.config import configure, shutdown_tracer
    except ImportError as exc:
        logger.warning("contextcore-coyote not installed: %s", exc)
        return {
            "success": False,
            "error": f"contextcore-coyote not available: {exc}",
            "run_id": None,
            "incident_id": None,
            "stages": [],
            "code_changes_count": 0,
        }

    # Configure for unattended dev-mode execution with telemetry enabled
    configure(auto_proceed=True, contextcore_enabled=True)

    # Map severity string to enum
    severity_upper = severity.upper()
    try:
        sev_enum = IncidentSeverity[severity_upper]
    except KeyError:
        sev_enum = IncidentSeverity.HIGH

    # Create incident from error
    incident = Incident.from_error(
        error_message=error_message,
        severity=sev_enum,
        source="dev_repair",
    )

    # Enrich incident with context
    ctx = context or {}
    if ctx.get("feature_id"):
        incident.labels["feature_id"] = ctx["feature_id"]
    if ctx.get("feature_name"):
        incident.labels["feature_name"] = ctx["feature_name"]
    if ctx.get("target_files"):
        incident.affected_files.extend(ctx["target_files"])
    if ctx.get("generated_files"):
        incident.affected_files.extend(ctx["generated_files"])
    for key, val in ctx.get("labels", {}).items():
        incident.labels[key] = str(val)

    # Build codebase context if project_root provided
    file_tree = None
    project_name = None
    project_language = None
    key_files: Dict[str, str] = {}
    capability_index = None

    if project_root and project_root.is_dir():
        project_name = project_root.name
        project_language = _detect_language(project_root)
        file_tree = _build_file_tree(project_root, max_depth=3)

        # Extract files mentioned in error/stack trace
        key_files = _extract_key_files(project_root, error_message, incident.stack_trace)

        # Load capability index for semantic understanding
        capability_index = _load_capability_index(project_root)
        if capability_index:
            logger.info("Loaded capability index from %s/docs/capability-index/", project_root)

    # Run full pipeline
    pipeline = Pipeline.full()
    try:
        result = pipeline.run(
            incident,
            project_root=str(project_root) if project_root else None,
            project_name=project_name,
            project_language=project_language,
            file_tree=file_tree,
            key_files=key_files,
            capability_index=capability_index,
        )
    finally:
        # Flush spans to the collector before returning
        shutdown_tracer()

    # Collect stage summary
    stages = []
    code_changes: Dict[str, str] = {}
    for sr in result.stage_results:
        stages.append({
            "name": sr.stage_name,
            "status": sr.status.value if hasattr(sr.status, "value") else str(sr.status),
            "summary": sr.summary,
        })
        if sr.code_changes:
            code_changes.update(sr.code_changes)

    output: Dict[str, Any] = {
        "success": result.successful,
        "run_id": incident.id,
        "incident_id": incident.id,
        "stages": stages,
        "code_changes_count": len(code_changes),
    }

    if result.failed_stage:
        output["error"] = result.failed_stage.error or result.failed_stage.summary

    # Always persist generated code for review/audit
    if code_changes:
        generated_dir = _write_output(
            incident_id=incident.id,
            code_changes=code_changes,
            result=result,
            output_dir=output_dir,
            auto_apply=auto_apply,
            project_name=project_name,
            project_root=project_root,
        )
        output["generated_dir"] = str(generated_dir)
        if auto_apply:
            output["applied_files"] = list(code_changes.keys())

    return output


def _write_output(
    incident_id: str,
    code_changes: Dict[str, str],
    result: Any,
    output_dir: Optional[Path] = None,
    auto_apply: bool = False,
    project_name: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> Path:
    """
    Write Coyote pipeline output to disk with repo-mirroring structure.

    Output structure:
        generated/coyote/{project_name}/{incident_id}/
        ├── src/                          # Mirrors repo structure
        │   └── module/
        │       └── file.py
        ├── tests/
        │   └── test_file.py
        └── _coyote_meta/                 # Metadata files
            ├── file_result.json
            └── incident_summary.json

    This allows easy diff/merge with the target repo:
        diff -r ~/dev/project/src generated/coyote/project/INC-xxx/src
        cp -r generated/coyote/project/INC-xxx/src/* ~/dev/project/src/

    Args:
        incident_id: Unique incident identifier.
        code_changes: Dict mapping original filename -> new code content.
        result: PipelineResult from Coyote.
        output_dir: Override output directory (default: generated/coyote).
        auto_apply: If True, apply fixes to the actual target files.
        project_name: Name of the target project (for subdirectory).
        project_root: Root path of the target project (to compute relative paths).

    Returns:
        Path to the generated output directory.
    """
    base_dir = output_dir or DEFAULT_GENERATED_DIR

    # Create project-specific subdirectory
    if project_name:
        incident_dir = base_dir / project_name / incident_id
    else:
        incident_dir = base_dir / incident_id

    incident_dir.mkdir(parents=True, exist_ok=True)

    # Metadata directory for non-code files
    meta_dir = incident_dir / "_coyote_meta"
    meta_dir.mkdir(parents=True, exist_ok=True)

    # Extract root_cause and commit_message from stage results
    root_cause: Optional[str] = None
    commit_message: Optional[str] = None
    for sr in result.stage_results:
        if sr.stage_name == "investigate" and sr.root_cause:
            root_cause = sr.root_cause
        if sr.stage_name == "implement":
            commit_message = getattr(sr, "summary", None)

    files_written: List[str] = []
    files_applied: List[str] = []
    file_metadata: List[Dict[str, Any]] = []

    for filename, code_content in code_changes.items():
        original_path = Path(filename)

        # Compute relative path from project root
        if project_root:
            try:
                rel_path = original_path.relative_to(project_root)
            except ValueError:
                # Not under project root — use the filename as-is
                rel_path = original_path
        else:
            rel_path = original_path

        # Write code file preserving directory structure
        code_file = incident_dir / rel_path
        code_file.parent.mkdir(parents=True, exist_ok=True)
        code_file.write_text(code_content)
        files_written.append(str(code_file))

        # Write metadata to _coyote_meta/
        slug = _slugify(filename)
        meta = {
            "feature": f"{incident_id}-fix-{slug}",
            "success": True,
            "source": "coyote",
            "incident_id": incident_id,
            "root_cause": root_cause,
            "commit_message": commit_message or f"fix: {incident_id}",
            "original_filename": filename,
            "relative_path": str(rel_path),
            "auto_applied": auto_apply,
        }
        meta_file = meta_dir / f"{slug}_result.json"
        meta_file.write_text(json.dumps(meta, indent=2))
        files_written.append(str(meta_file))
        file_metadata.append(meta)

        # If auto_apply, also write to the actual target file
        if auto_apply:
            target_path = Path(filename)
            if target_path.exists():
                logger.info("Applying fix to %s", target_path)
                target_path.write_text(code_content)
                files_applied.append(filename)
            else:
                logger.warning(
                    "Target file does not exist, skipping apply: %s", target_path
                )

    # Write incident summary (JSON)
    summary = {
        "incident_id": incident_id,
        "project_name": project_name,
        "project_root": str(project_root) if project_root else None,
        "root_cause": root_cause,
        "commit_message": commit_message,
        "files_changed": [str(_safe_relative(f, project_root))
                         for f in code_changes.keys()],
        "auto_applied": auto_apply,
        "files_applied": files_applied,
    }
    summary_file = meta_dir / "incident_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2))

    # Write comprehensive incident report (Markdown)
    _write_incident_report(
        incident_dir=incident_dir,
        meta_dir=meta_dir,
        incident_id=incident_id,
        project_name=project_name,
        project_root=project_root,
        result=result,
        code_changes=code_changes,
        root_cause=root_cause,
        commit_message=commit_message,
        auto_apply=auto_apply,
        files_applied=files_applied,
    )

    logger.info(
        "Wrote %d files to %s",
        len(files_written),
        incident_dir,
    )
    if project_name:
        logger.info(
            "  Structure mirrors %s — use 'diff -r' or 'cp -r' to merge",
            project_name,
        )
    if files_applied:
        logger.info(
            "Applied fixes to %d repo files: %s",
            len(files_applied),
            ", ".join(files_applied),
        )

    return incident_dir


def _slugify(filename: str) -> str:
    """Convert a filename to a safe slug for disk paths."""
    base = Path(filename).name
    stem = Path(base).stem
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)


def _write_incident_report(
    incident_dir: Path,
    meta_dir: Path,
    incident_id: str,
    project_name: Optional[str],
    project_root: Optional[Path],
    result: Any,
    code_changes: Dict[str, str],
    root_cause: Optional[str],
    commit_message: Optional[str],
    auto_apply: bool,
    files_applied: List[str],
) -> None:
    """
    Write a comprehensive incident report in Markdown format.

    This report is both human-readable and agent-readable, documenting:
    - What triggered Coyote
    - Why the error occurred (root cause analysis)
    - The suggested fix
    - Generated artifacts and merge instructions

    The report is written to the incident directory root as INCIDENT_REPORT.md.
    """
    lines: List[str] = []

    # Header
    lines.append(f"# Coyote Incident Report: {incident_id}")
    lines.append("")
    lines.append("**Workflow**: HOWL (Human-Orchestrated Watchdog Loop)")
    lines.append(f"**Generated**: {datetime.now().isoformat()}")
    if project_name:
        lines.append(f"**Target Project**: {project_name}")
    if project_root:
        lines.append(f"**Project Root**: `{project_root}`")
    lines.append("")

    # Section 1: What Triggered Coyote
    lines.append("## 1. Trigger Event")
    lines.append("")
    incident = result.incident if hasattr(result, "incident") else None
    if incident:
        lines.append(f"**Incident Title**: {incident.title}")
        lines.append(f"**Severity**: {incident.severity.value if hasattr(incident.severity, 'value') else incident.severity}")
        lines.append(f"**Source**: {incident.source}")
        lines.append("")
        lines.append("### Error Message")
        lines.append("")
        lines.append("```")
        # Truncate very long error messages
        error_msg = incident.error_message[:2000] if len(incident.error_message) > 2000 else incident.error_message
        lines.append(error_msg)
        lines.append("```")
        if incident.stack_trace:
            lines.append("")
            lines.append("### Stack Trace")
            lines.append("")
            lines.append("```")
            # Truncate very long stack traces
            stack = incident.stack_trace[:3000] if len(incident.stack_trace) > 3000 else incident.stack_trace
            lines.append(stack)
            lines.append("```")
        if incident.affected_files:
            lines.append("")
            lines.append("### Affected Files")
            lines.append("")
            for f in incident.affected_files[:10]:
                lines.append(f"- `{f}`")
    else:
        lines.append("*Incident details not available.*")
    lines.append("")

    # Section 2: Root Cause Analysis
    lines.append("## 2. Root Cause Analysis")
    lines.append("")
    if root_cause:
        lines.append(root_cause)
    else:
        # Try to extract from investigator stage
        for sr in result.stage_results:
            if sr.stage_name == "investigate" and sr.summary:
                lines.append(sr.summary)
                break
        else:
            lines.append("*Root cause analysis not available.*")
    lines.append("")

    # Section 3: Pipeline Execution Summary
    lines.append("## 3. Pipeline Execution")
    lines.append("")
    lines.append("| Stage | Status | Duration | Summary |")
    lines.append("|-------|--------|----------|---------|")
    for sr in result.stage_results:
        status_icon = {
            "completed": "✅",
            "failed": "❌",
            "skipped": "⏭️",
            "pending": "⏳",
        }.get(sr.status.value if hasattr(sr.status, "value") else str(sr.status).lower(), "❓")
        status_text = sr.status.value if hasattr(sr.status, "value") else str(sr.status)
        duration = f"{sr.duration_seconds:.1f}s" if sr.duration_seconds else "-"
        summary_text = (sr.summary or "-")[:60] + "..." if sr.summary and len(sr.summary) > 60 else (sr.summary or "-")
        lines.append(f"| {sr.stage_name} | {status_icon} {status_text} | {duration} | {summary_text} |")
    lines.append("")

    # Section 4: Suggested Fix
    lines.append("## 4. Suggested Fix")
    lines.append("")
    if commit_message:
        lines.append("### Commit Message")
        lines.append("")
        lines.append(f"> {commit_message}")
        lines.append("")

    # Extract implementation details from implementer stage
    for sr in result.stage_results:
        if sr.stage_name == "implement" and sr.summary:
            lines.append("### Implementation Notes")
            lines.append("")
            lines.append(sr.summary)
            lines.append("")
            break
    lines.append("")

    # Section 5: Generated Artifacts
    lines.append("## 5. Generated Artifacts")
    lines.append("")
    lines.append("### Directory Structure")
    lines.append("")
    lines.append("```")
    lines.append(f"{incident_dir.name}/")
    # List code changes with their relative paths
    for filename in sorted(code_changes.keys()):
        original_path = Path(filename)
        if project_root:
            try:
                rel_path = original_path.relative_to(project_root)
            except ValueError:
                rel_path = original_path
        else:
            rel_path = original_path
        lines.append(f"├── {rel_path}")
    lines.append(f"└── _coyote_meta/")
    lines.append(f"    ├── incident_summary.json")
    lines.append(f"    ├── INCIDENT_REPORT.md  (this file)")
    lines.append(f"    └── *_result.json")
    lines.append("```")
    lines.append("")

    lines.append("### Files Generated")
    lines.append("")
    lines.append("| File | Lines | Purpose |")
    lines.append("|------|-------|---------|")
    for filename, content in code_changes.items():
        original_path = Path(filename)
        if project_root:
            try:
                rel_path = original_path.relative_to(project_root)
            except ValueError:
                rel_path = original_path
        else:
            rel_path = original_path
        line_count = len(content.splitlines())
        # Infer purpose from path
        if "test" in str(rel_path).lower():
            purpose = "Test coverage"
        elif "_fix" in str(rel_path).lower():
            purpose = "Bug fix"
        else:
            purpose = "Implementation fix"
        lines.append(f"| `{rel_path}` | {line_count} | {purpose} |")
    lines.append("")

    # Section 6: Merge Instructions
    lines.append("## 6. Merge Instructions")
    lines.append("")
    if auto_apply:
        lines.append("⚠️ **AUTO_APPLY was enabled** — fixes have already been applied to the target repository.")
        lines.append("")
        lines.append("Applied files:")
        for f in files_applied:
            lines.append(f"- `{f}`")
    else:
        lines.append("The generated code has **not** been applied to the target repository.")
        lines.append("")
        lines.append("### Review and Merge")
        lines.append("")
        lines.append("1. **Review the changes**:")
        lines.append("   ```bash")
        if project_root:
            lines.append(f"   diff -r {project_root}/ {incident_dir}/")
        else:
            lines.append(f"   # Review files in {incident_dir}/")
        lines.append("   ```")
        lines.append("")
        lines.append("2. **Apply changes selectively**:")
        lines.append("   ```bash")
        lines.append(f"   # Copy specific files")
        for filename in list(code_changes.keys())[:3]:
            original_path = Path(filename)
            if project_root:
                try:
                    rel_path = original_path.relative_to(project_root)
                except ValueError:
                    rel_path = original_path
            else:
                rel_path = original_path
            lines.append(f"   cp {incident_dir}/{rel_path} {filename}")
        if len(code_changes) > 3:
            lines.append(f"   # ... ({len(code_changes) - 3} more files)")
        lines.append("   ```")
        lines.append("")
        lines.append("3. **Or apply all changes**:")
        lines.append("   ```bash")
        if project_root:
            # Get unique top-level directories from code changes
            top_dirs = set()
            for filename in code_changes.keys():
                try:
                    rel = Path(filename).relative_to(project_root)
                    if rel.parts:
                        top_dirs.add(rel.parts[0])
                except ValueError:
                    pass
            for td in sorted(top_dirs)[:3]:
                lines.append(f"   cp -r {incident_dir}/{td}/ {project_root}/{td}/")
        else:
            lines.append(f"   cp -r {incident_dir}/* <target_project>/")
        lines.append("   ```")
    lines.append("")

    # Section 7: Agent Integration
    lines.append("## 7. Agent Integration")
    lines.append("")
    lines.append("This report is designed for both human and agent consumption.")
    lines.append("")
    lines.append("### For Agents")
    lines.append("")
    lines.append("To process this incident programmatically:")
    lines.append("")
    lines.append("```yaml")
    lines.append("# Structured summary for agent parsing")
    lines.append(f"incident_id: {incident_id}")
    lines.append(f"project: {project_name or 'unknown'}")
    lines.append(f"status: {'applied' if auto_apply else 'pending_review'}")
    lines.append(f"files_changed: {len(code_changes)}")
    lines.append(f"root_cause_available: {bool(root_cause)}")
    lines.append(f"merge_ready: {not auto_apply}")
    lines.append("```")
    lines.append("")
    lines.append(f"**JSON metadata**: `{meta_dir.relative_to(incident_dir)}/incident_summary.json`")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Generated by HOWL (Human-Orchestrated Watchdog Loop) — Coyote's incident resolution workflow, part of the Wayfinder observability suite.*")

    # Write the report
    report_path = incident_dir / "INCIDENT_REPORT.md"
    report_path.write_text("\n".join(lines))
    logger.info("Wrote incident report: %s", report_path)
