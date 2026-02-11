"""
Dev Mode Auto-Repair — Direct Python calls to Coyote pipeline.

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
        r"(connection.?refused|connection.?timed?\s*out|ECONNREFUSED"
        r"|ETIMEDOUT|dns.?resolution|name.?resolution"
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
                f"Skipped ({category}): \"{match.group(0)}\" suggests this is not a code bug. "
                f"Use --force to override."
            )
    return None


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

    # Run full pipeline
    pipeline = Pipeline.full()
    try:
        result = pipeline.run(incident)
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

    # Write output if auto_apply and we have code changes
    if auto_apply and code_changes:
        generated_dir = _write_output(
            incident_id=incident.id,
            code_changes=code_changes,
            result=result,
            output_dir=output_dir,
        )
        output["generated_dir"] = str(generated_dir)

    return output


def _write_output(
    incident_id: str,
    code_changes: Dict[str, str],
    result: Any,
    output_dir: Optional[Path] = None,
) -> Path:
    """
    Write Coyote pipeline output to disk.

    Mirrors the format from coyote_bridge._write_coyote_output but works
    directly from PipelineResult instead of the shared _coyote_runs dict.
    """
    base_dir = output_dir or DEFAULT_GENERATED_DIR
    incident_dir = base_dir / incident_id
    incident_dir.mkdir(parents=True, exist_ok=True)

    # Extract root_cause and commit_message from stage results
    root_cause: Optional[str] = None
    commit_message: Optional[str] = None
    for sr in result.stage_results:
        if sr.stage_name == "investigate" and sr.root_cause:
            root_cause = sr.root_cause
        if sr.stage_name == "implement":
            commit_message = getattr(sr, "summary", None)

    files_written: List[str] = []
    for filename, code_content in code_changes.items():
        slug = _slugify(filename)
        code_file = incident_dir / f"{slug}.py"
        code_file.write_text(code_content)
        files_written.append(str(code_file))

        # Write metadata for Prime Contractor
        meta = {
            "feature": f"{incident_id}-fix-{slug}",
            "success": True,
            "source": "coyote",
            "incident_id": incident_id,
            "root_cause": root_cause,
            "commit_message": commit_message or f"fix: {incident_id}",
            "original_filename": filename,
        }
        meta_file = incident_dir / f"{slug}_result.json"
        meta_file.write_text(json.dumps(meta, indent=2))
        files_written.append(str(meta_file))

    logger.info(
        "Wrote %d files to %s",
        len(files_written),
        incident_dir,
    )
    return incident_dir


def _slugify(filename: str) -> str:
    """Convert a filename to a safe slug for disk paths."""
    base = Path(filename).name
    stem = Path(base).stem
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)
