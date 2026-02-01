"""
Generate operational runbooks from ProjectContext metadata.

This module produces Markdown runbooks that include:
- Service overview and business context
- SLO definitions and alert thresholds
- Known risks and mitigations
- Kubernetes resource inspection commands
- Common operational procedures
- Escalation contacts

Prime Contractor Pattern: Spec by Opus, implementation validated by review.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def generate_runbook(
    project_id: str,
    spec: Dict[str, Any],
    output_format: str = "markdown",
) -> str:
    """
    Generate operational runbook from ProjectContext spec.

    Args:
        project_id: Project identifier
        spec: ProjectContext spec dictionary
        output_format: Output format ("markdown" supported, "html" planned)

    Returns:
        Formatted runbook content
    """
    sections: List[str] = []

    # Header
    sections.append(f"# {project_id} Operational Runbook")
    sections.append(f"\n_Generated: {datetime.now(timezone.utc).isoformat()}_")
    sections.append("_Source: ProjectContext CRD_\n")

    # Service Overview
    sections.append("## Service Overview\n")
    sections.append(_generate_overview_section(spec))

    # SLOs
    requirements = spec.get("requirements", {})
    if requirements:
        sections.append("## Service Level Objectives\n")
        sections.append(_generate_slo_section(requirements))

    # Known Risks
    risks = spec.get("risks", [])
    if risks:
        sections.append("## Known Risks & Mitigations\n")
        sections.append(_generate_risks_section(risks))

    # Kubernetes Resources
    targets = spec.get("targets", [])
    if targets:
        sections.append("## Kubernetes Resources\n")
        sections.append(_generate_resources_section(targets))

    # Dependencies
    dependencies = spec.get("dependencies", [])
    if dependencies:
        sections.append("## Dependencies\n")
        sections.append(_generate_dependencies_section(dependencies))

    # Common Procedures
    sections.append("## Common Procedures\n")
    sections.append(_generate_procedures_section(spec))

    # Alerting Rules
    sections.append("## Alert Response\n")
    sections.append(_generate_alert_response_section(spec))

    # Escalation
    sections.append("## Escalation\n")
    sections.append(_generate_escalation_section(spec))

    return "\n".join(sections)


def _generate_overview_section(spec: Dict[str, Any]) -> str:
    """Generate service overview section."""
    project = spec.get("project", {})
    business = spec.get("business", {})
    design = spec.get("design", {})

    lines: List[str] = []
    lines.append("| Field | Value |")
    lines.append("|-------|-------|")

    # Project info
    if isinstance(project, dict):
        lines.append(f"| Project ID | {project.get('id', 'N/A')} |")
        if project.get("epic"):
            lines.append(f"| Epic | {project['epic']} |")
        if project.get("tasks"):
            tasks = ", ".join(project["tasks"][:5])
            lines.append(f"| Tasks | {tasks} |")
    else:
        lines.append(f"| Project ID | {project} |")

    # Business context
    if business:
        lines.append(f"| Owner | {business.get('owner', 'N/A')} |")
        lines.append(f"| Criticality | {business.get('criticality', 'N/A')} |")
        lines.append(f"| Business Value | {business.get('value', 'N/A')} |")
        if business.get("costCenter"):
            lines.append(f"| Cost Center | {business['costCenter']} |")

    # Design references
    if design:
        if design.get("doc"):
            lines.append(f"| Design Doc | [{design['doc']}]({design['doc']}) |")
        if design.get("adr"):
            lines.append(f"| ADR | {design['adr']} |")

    return "\n".join(lines) + "\n"


def _generate_slo_section(requirements: Dict[str, Any]) -> str:
    """Generate SLO section with targets and thresholds."""
    lines: List[str] = []
    lines.append("| Metric | Target | Alert Threshold |")
    lines.append("|--------|--------|-----------------|")

    if requirements.get("availability"):
        avail = requirements["availability"]
        try:
            threshold = float(str(avail).rstrip("%")) - 0.1
            lines.append(f"| Availability | {avail}% | < {threshold}% |")
        except ValueError:
            lines.append(f"| Availability | {avail} | See alert rules |")

    if requirements.get("latencyP50"):
        lines.append(f"| Latency P50 | {requirements['latencyP50']} | > 2x target |")

    if requirements.get("latencyP99"):
        lines.append(f"| Latency P99 | {requirements['latencyP99']} | > 1.5x target |")

    if requirements.get("errorBudget"):
        lines.append(f"| Error Budget | {requirements['errorBudget']}% monthly | Exhausted |")

    if requirements.get("throughput"):
        lines.append(f"| Throughput | {requirements['throughput']} | < 80% capacity |")

    if requirements.get("rps"):
        lines.append(f"| Requests/sec | {requirements['rps']} | Sustained drop |")

    return "\n".join(lines) + "\n"


def _generate_risks_section(risks: List[Dict[str, Any]]) -> str:
    """Generate risks section with mitigations."""
    lines: List[str] = []
    lines.append("| Risk Type | Description | Priority | Mitigation |")
    lines.append("|-----------|-------------|----------|------------|")

    for risk in risks:
        risk_type = risk.get("type", "N/A")
        description = risk.get("description", "N/A")[:50]
        priority = risk.get("priority", "N/A")
        mitigation = risk.get("mitigation", _get_default_mitigation(risk_type))[:40]
        lines.append(f"| {risk_type} | {description} | {priority} | {mitigation} |")

    return "\n".join(lines) + "\n"


def _get_default_mitigation(risk_type: str) -> str:
    """Get default mitigation suggestion for a risk type."""
    defaults = {
        "availability": "Scale up replicas, check dependencies",
        "security": "Rotate credentials, review access logs",
        "data-integrity": "Check backups, verify replication",
        "compliance": "Engage compliance team immediately",
        "performance": "Profile, optimize, or scale horizontally",
        "capacity": "Add resources, enable autoscaling",
    }
    return defaults.get(risk_type, "See runbook for guidance")


def _generate_resources_section(targets: List[Dict[str, Any]]) -> str:
    """Generate Kubernetes resources section with kubectl commands."""
    lines: List[str] = []
    lines.append("### Resource Status\n")
    lines.append("```bash")
    lines.append("# Check resource status")

    for target in targets:
        ns = target.get("namespace", "default")
        kind = target.get("kind", "deployment").lower()
        name = target.get("name", "")
        if name:
            lines.append(f"kubectl get {kind} {name} -n {ns}")

    lines.append("")
    lines.append("# Describe resources for events")
    for target in targets[:2]:  # Limit to first 2 for brevity
        ns = target.get("namespace", "default")
        kind = target.get("kind", "deployment").lower()
        name = target.get("name", "")
        if name:
            lines.append(f"kubectl describe {kind} {name} -n {ns}")

    lines.append("```")
    lines.append("")

    # Log viewing
    lines.append("### View Logs\n")
    lines.append("```bash")
    if targets:
        first = targets[0]
        ns = first.get("namespace", "default")
        name = first.get("name", "app")
        lines.append(f"# Recent logs")
        lines.append(f"kubectl logs -l app={name} -n {ns} --tail=100")
        lines.append("")
        lines.append(f"# Follow logs")
        lines.append(f"kubectl logs -l app={name} -n {ns} -f")
        lines.append("")
        lines.append(f"# Previous container logs (if restarted)")
        lines.append(f"kubectl logs -l app={name} -n {ns} --previous")
    lines.append("```\n")

    return "\n".join(lines)


def _generate_dependencies_section(dependencies: List[Dict[str, Any]]) -> str:
    """Generate dependencies section."""
    lines: List[str] = []
    lines.append("| Service | Type | Health Check |")
    lines.append("|---------|------|--------------|")

    for dep in dependencies:
        name = dep.get("name", "N/A")
        dep_type = dep.get("type", "service")
        health = dep.get("healthEndpoint", "N/A")
        lines.append(f"| {name} | {dep_type} | {health} |")

    return "\n".join(lines) + "\n"


def _generate_procedures_section(spec: Dict[str, Any]) -> str:
    """Generate common procedures section."""
    targets = spec.get("targets", [])
    business = spec.get("business", {})
    criticality = business.get("criticality", "medium")

    lines: List[str] = []

    # Restart procedure
    lines.append("### Restart Service\n")
    if targets:
        target = targets[0]
        ns = target.get("namespace", "default")
        kind = target.get("kind", "deployment").lower()
        name = target.get("name", "service")
        lines.append("```bash")
        lines.append(f"# Rolling restart")
        lines.append(f"kubectl rollout restart {kind}/{name} -n {ns}")
        lines.append("")
        lines.append(f"# Wait for rollout to complete")
        lines.append(f"kubectl rollout status {kind}/{name} -n {ns} --timeout=5m")
        lines.append("```\n")
    else:
        lines.append("_No targets defined. Add targets to ProjectContext._\n")

    # Scale procedure for critical/high services
    if criticality in ["critical", "high"] and targets:
        lines.append("### Emergency Scale Up\n")
        lines.append("```bash")
        target = targets[0]
        ns = target.get("namespace", "default")
        name = target.get("name", "service")
        lines.append(f"# Scale to 5 replicas")
        lines.append(f"kubectl scale deployment/{name} --replicas=5 -n {ns}")
        lines.append("")
        lines.append(f"# Verify scaling")
        lines.append(f"kubectl get deployment/{name} -n {ns}")
        lines.append("```")
        lines.append("\n**Note**: Scale back down after incident resolution.\n")

    # Debug connectivity
    lines.append("### Debug Connectivity\n")
    lines.append("```bash")
    lines.append("# Check endpoints")
    for target in targets:
        if target.get("kind", "").lower() == "service":
            ns = target.get("namespace", "default")
            name = target.get("name", "")
            lines.append(f"kubectl get endpoints {name} -n {ns}")

    lines.append("")
    lines.append("# Test from inside cluster")
    lines.append("kubectl run debug --rm -it --image=busybox --restart=Never -- sh")
    lines.append("")
    lines.append("# Inside the debug pod:")
    if targets:
        ns = targets[0].get("namespace", "default")
        name = targets[0].get("name", "service")
        lines.append(f"# wget -qO- http://{name}.{ns}.svc.cluster.local/health")
    lines.append("```\n")

    # Resource inspection
    lines.append("### Resource Usage\n")
    lines.append("```bash")
    if targets:
        ns = targets[0].get("namespace", "default")
        name = targets[0].get("name", "service")
        lines.append(f"# Check pod resource usage")
        lines.append(f"kubectl top pods -l app={name} -n {ns}")
        lines.append("")
        lines.append(f"# Check node resource usage")
        lines.append(f"kubectl top nodes")
    lines.append("```\n")

    return "\n".join(lines)


def _generate_alert_response_section(spec: Dict[str, Any]) -> str:
    """Generate alert response guidance."""
    business = spec.get("business", {})
    criticality = business.get("criticality", "medium")

    lines: List[str] = []

    lines.append("### AvailabilityLow Alert\n")
    lines.append("1. Check pod health: `kubectl get pods -l app=<service>`")
    lines.append("2. Review recent deployments: `kubectl rollout history deployment/<name>`")
    lines.append("3. Check upstream dependencies (see Dependencies section)")
    lines.append("4. Review error logs for root cause")
    if criticality in ["critical", "high"]:
        lines.append("5. Consider emergency scale-up if load-related")
    lines.append("")

    lines.append("### LatencyHigh Alert\n")
    lines.append("1. Check resource utilization: `kubectl top pods`")
    lines.append("2. Review recent changes: commits, config updates")
    lines.append("3. Check database/cache performance")
    lines.append("4. Look for lock contention in logs")
    if criticality in ["critical", "high"]:
        lines.append("5. Consider scaling or traffic shedding")
    lines.append("")

    return "\n".join(lines)


def _generate_escalation_section(spec: Dict[str, Any]) -> str:
    """Generate escalation section with contacts."""
    business = spec.get("business", {})
    observability = spec.get("observability", {})
    owner = business.get("owner", "platform-team")

    lines: List[str] = []

    lines.append("| Level | Contact | When |")
    lines.append("|-------|---------|------|")
    lines.append("| L1 | On-call engineer | Initial response |")
    lines.append(f"| L2 | {owner} | Unresolved after 30min |")
    lines.append("| L3 | Platform team | Infrastructure issues |")

    stakeholders = business.get("stakeholders", [])
    if stakeholders:
        stakeholder_list = ", ".join(stakeholders[:2])
        lines.append(f"| Exec | {stakeholder_list} | Customer impact |")

    lines.append("")

    # Additional contact info
    if observability.get("runbook"):
        lines.append(f"**Detailed Runbook**: {observability['runbook']}\n")

    if observability.get("alertChannels"):
        channels = ", ".join(observability["alertChannels"])
        lines.append(f"**Alert Channels**: {channels}\n")

    if observability.get("dashboardUrl"):
        lines.append(f"**Dashboard**: {observability['dashboardUrl']}\n")

    return "\n".join(lines)
