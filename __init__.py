"""contextcore generator infrastructure.

Provides the core generator skeleton: data models, registry, Jinja2 environment
setup, path resolution, atomic file writes, and orchestration functions.

This module is the coordination surface between the CLI
(``contextcore manifest generate``) and the individual generators in
``artifact_generators.py``.  It owns the contract; generators are plugged in
via registration.
"""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from jinja2 import Environment, FileSystemLoader, StrictUndefined

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────
# Input Contracts (TypedDict definitions)
# ──────────────────────────────────────────────────────────────────


class ArtifactSpec(TypedDict, total=False):
    """Expected shape of an artifact spec dict from the manifest.

    Required keys (in practice):
        type: One of SUPPORTED_ARTIFACT_TYPES (e.g., "ServiceMonitor").
        service: Service name this artifact targets (e.g., "cartservice").

    Optional keys:
        metadata: Type-specific configuration consumed by templates.
        output_filename: Override for the generated filename (without directory).

    ``total=False`` is used for gradual adoption — callers may provide
    partial dicts and the orchestration layer defaults missing keys to
    ``"unknown"``.
    """

    type: str
    service: str
    metadata: dict
    output_filename: str


# ──────────────────────────────────────────────────────────────────
# Data Models
# ──────────────────────────────────────────────────────────────────


@dataclass
class GeneratedFile:
    """Represents a single file produced by a generator."""

    path: Path
    content: str
    artifact_type: str
    service_name: str
    derivation_rules: dict = field(default_factory=dict)
    overwritten: bool = False


@dataclass
class GenerationResult:
    """Per-artifact outcome — success or failure with context."""

    artifact_type: str
    service_name: str
    success: bool
    file: Optional[GeneratedFile] = None
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


# ──────────────────────────────────────────────────────────────────
# Type Aliases
# ──────────────────────────────────────────────────────────────────

# Generators receive the artifact spec, the full context manifest,
# and the resolved output path.  They return a GenerationResult
# containing the rendered content.  The orchestrator handles file I/O.
GeneratorFn = Callable[[ArtifactSpec, dict, Path], GenerationResult]


# ──────────────────────────────────────────────────────────────────
# Generator Registry
# ──────────────────────────────────────────────────────────────────

SUPPORTED_ARTIFACT_TYPES = (
    "ServiceMonitor",
    "PrometheusRule",
    "LokiRule",
    "SLO",
    "NotificationPolicy",
    "Runbook",
    "Dashboard",
)

# Registry: artifact_type_string -> generator function
_GENERATOR_REGISTRY: dict[str, GeneratorFn] = {}

_generators_loaded: bool = False


def register_generator(artifact_type: str, fn: GeneratorFn) -> None:
    """Register a generator function for an artifact type.

    Args:
        artifact_type: One of ``SUPPORTED_ARTIFACT_TYPES``.
        fn: Generator function with signature
            ``(spec, context_manifest, output_path) -> GenerationResult``.

    Raises:
        ValueError: If *artifact_type* is not in ``SUPPORTED_ARTIFACT_TYPES``.
    """
    if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
        raise ValueError(
            f"Unknown artifact type '{artifact_type}'. "
            f"Supported: {SUPPORTED_ARTIFACT_TYPES}"
        )
    _GENERATOR_REGISTRY[artifact_type] = fn
    logger.debug("Registered generator for artifact type '%s'", artifact_type)


def get_generator(artifact_type: str) -> Optional[GeneratorFn]:
    """Look up a registered generator.  Returns ``None`` if not registered."""
    return _GENERATOR_REGISTRY.get(artifact_type)


def registered_types() -> list[str]:
    """Return list of currently registered artifact types."""
    return list(_GENERATOR_REGISTRY.keys())


def load_generators() -> None:
    """Explicitly import ``artifact_generators`` to populate the registry.

    This function is idempotent — subsequent calls are no-ops.
    It **must** be called before ``generate_all()`` or
    ``generate_artifact()`` are expected to find registered generators.
    ``generate_all()`` calls this automatically as a safety net, but
    callers (e.g., the CLI entrypoint) should call it explicitly during
    setup for clarity and faster failure.
    """
    global _generators_loaded
    if _generators_loaded:
        return
    logger.debug("Loading generators from artifact_generators module")
    # Import triggers module-level register_generator() calls
    import contextcore.generators.artifact_generators  # noqa: F401

    _generators_loaded = True
    logger.info("Generators loaded. Registered types: %s", registered_types())


# ──────────────────────────────────────────────────────────────────
# Jinja2 Environment (Lazy Singleton)
# ──────────────────────────────────────────────────────────────────

_TEMPLATES_DIR = Path(__file__).parent / "templates"

# Module-level singleton — lazy init.
# Known limitation: not thread-safe (no lock around lazy init).
# Acceptable for single-threaded CLI usage.
_jinja_env: Optional[Environment] = None


def create_jinja_env(templates_dir: Optional[Path] = None) -> Environment:
    """Create a configured Jinja2 environment.

    Args:
        templates_dir: Directory containing ``.j2`` templates.
            Defaults to ``src/contextcore/generators/templates/``.
    """
    target_dir = templates_dir or _TEMPLATES_DIR
    return Environment(
        loader=FileSystemLoader(str(target_dir)),
        undefined=StrictUndefined,  # fail loudly on missing vars
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def get_jinja_env() -> Environment:
    """Return the module-level Jinja2 environment (lazy singleton)."""
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = create_jinja_env()
    return _jinja_env


def reset_jinja_env(templates_dir: Optional[Path] = None) -> None:
    """Reset the Jinja2 singleton, optionally with a new templates directory.

    Primarily intended for testing scenarios where *templates_dir* needs
    to change between tests.  If *templates_dir* is provided, the singleton
    is immediately re-created with that directory; otherwise it is set to
    ``None`` and will be lazily re-created on next access.
    """
    global _jinja_env
    if templates_dir is not None:
        _jinja_env = create_jinja_env(templates_dir)
    else:
        _jinja_env = None


# ──────────────────────────────────────────────────────────────────
# Path Resolution
# ──────────────────────────────────────────────────────────────────

# Default filename patterns per artifact type
_FILENAME_PATTERNS: dict[str, str] = {
    "ServiceMonitor": "{service}_service_monitor.yaml",
    "PrometheusRule": "{service}_prometheus_rule.yaml",
    "LokiRule": "{service}_loki_rule.yaml",
    "SLO": "{service}_slo.yaml",
    "NotificationPolicy": "{service}_notification_policy.yaml",
    "Runbook": "{service}_runbook.md",
    "Dashboard": "{service}_dashboard.json",
}


def resolve_output_path(
    artifact_spec: ArtifactSpec,
    output_dir: Path,
) -> Path:
    """Resolve the output file path for an artifact spec.

    The orchestrator calls this **before** invoking the generator, ensuring
    path computation is centralised and consistent.

    Resolution order:
        1. If *artifact_spec* contains ``output_filename``, use it directly.
        2. Otherwise, use the default pattern from ``_FILENAME_PATTERNS``.
        3. Falls back to ``{service}_{type}.yaml`` if no pattern is defined.
    """
    artifact_type = artifact_spec.get("type", "unknown")
    service_name = artifact_spec.get("service", "unknown")

    filename = artifact_spec.get("output_filename")
    if not filename:
        pattern = _FILENAME_PATTERNS.get(artifact_type, "{service}_{type}.yaml")
        filename = pattern.format(service=service_name, type=artifact_type.lower())

    return output_dir / filename


# ──────────────────────────────────────────────────────────────────
# Atomic File Write
# ──────────────────────────────────────────────────────────────────


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* atomically via temp-file-then-rename.

    This avoids partial/corrupted files on failure (disk full, permission
    errors mid-write, etc.).  The temp file is created in the same directory
    as the target to ensure the rename is atomic (same filesystem).
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path_str = tempfile.mkstemp(
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp_path = Path(tmp_path_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        tmp_path.replace(path)  # atomic on POSIX; best-effort on Windows
    except BaseException:
        # Clean up temp file on any failure
        tmp_path.unlink(missing_ok=True)
        raise


# ──────────────────────────────────────────────────────────────────
# Orchestration
# ──────────────────────────────────────────────────────────────────


def generate_artifact(
    artifact_spec: ArtifactSpec,
    context_manifest: dict,
    output_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> GenerationResult:
    """Generate a single artifact.

    Wraps the registered generator with pre-invocation file-existence
    checks, dry-run support, atomic writes, and error containment.

    Path resolution happens here (not in the generator) so that:
    - File-existence can be checked **before** invoking the generator
    - Generators don't duplicate path logic
    - The orchestrator has full control over I/O

    Error containment: any ``Exception`` is caught and returned as a
    ``GenerationResult(success=False)``.  ``BaseException`` subclasses
    that are **not** ``Exception`` (``KeyboardInterrupt``, ``SystemExit``,
    ``GeneratorExit``) are **not** caught and propagate normally.
    """
    artifact_type = artifact_spec.get("type", "unknown")
    service_name = artifact_spec.get("service", "unknown")

    # Look up generator — fast path for unregistered types
    generator = get_generator(artifact_type)
    if generator is None:
        logger.warning(
            "No generator registered for type '%s' (service: %s)",
            artifact_type,
            service_name,
        )
        return GenerationResult(
            artifact_type=artifact_type,
            service_name=service_name,
            success=False,
            error=f"No generator registered for type '{artifact_type}'",
        )

    try:
        # Resolve output path BEFORE invoking the generator
        output_path = resolve_output_path(artifact_spec, output_dir)

        # Pre-invocation file-existence check — skip expensive rendering
        # if the file already exists and --force is not set.
        # NOTE: There is an inherent TOCTOU race between this check and
        # the eventual write.  For CLI usage with ~77 artifacts this is
        # negligible risk, but callers should be aware in concurrent contexts.
        file_exists_before = output_path.exists()

        if file_exists_before and not force:
            logger.info(
                "Skipping %s/%s — file exists: %s (use --force to overwrite)",
                artifact_type,
                service_name,
                output_path,
            )
            return GenerationResult(
                artifact_type=artifact_type,
                service_name=service_name,
                success=True,
                skipped=True,
                skip_reason=f"File exists: {output_path}. Use --force to overwrite.",
            )

        # Invoke the generator — it produces content, we handle I/O
        result = generator(artifact_spec, context_manifest, output_path)

        # Tag overwrite if file existed and --force was used
        if result.success and result.file and file_exists_before:
            result.file.overwritten = True

        # Dry-run: don't write, just return the result
        if dry_run:
            logger.info(
                "Dry-run: would write %s/%s -> %s",
                artifact_type,
                service_name,
                output_path,
            )
        elif result.success and result.file:
            _atomic_write(result.file.path, result.file.content)
            logger.info(
                "Generated %s/%s -> %s%s",
                artifact_type,
                service_name,
                result.file.path,
                " (overwritten)" if result.file.overwritten else "",
            )

        if not result.success:
            logger.error(
                "Generator failed for %s/%s: %s",
                artifact_type,
                service_name,
                result.error,
            )

        return result

    except Exception as exc:
        # [blocking] Per-artifact failure — never abort the run.
        #
        # Catches all Exception subclasses, including:
        # - jinja2.TemplateNotFound, jinja2.TemplateSyntaxError
        # - jinja2.UndefinedError (from StrictUndefined)
        # - PermissionError, OSError (file I/O)
        # - RuntimeError, ValueError (generator bugs)
        # - MemoryError (inherits from Exception in Python 3)
        #
        # NOT caught (BaseException only):
        # - KeyboardInterrupt, SystemExit, GeneratorExit
        logger.error(
            "Exception in generator for %s/%s: %s: %s",
            artifact_type,
            service_name,
            type(exc).__name__,
            exc,
            exc_info=True,
        )
        return GenerationResult(
            artifact_type=artifact_type,
            service_name=service_name,
            success=False,
            error=f"{type(exc).__name__}: {exc}",
        )


def generate_all(
    artifact_specs: list[ArtifactSpec],
    context_manifest: dict,
    output_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
    type_filter: Optional[set[str]] = None,
) -> list[GenerationResult]:
    """Orchestrate generation across all artifact specs.

    Args:
        artifact_specs: List of artifact spec dicts from the manifest.
        context_manifest: The full context manifest dict.
        output_dir: Root output directory.
        dry_run: If True, compute results but don't write files.
        force: If True, overwrite existing files.
        type_filter: If provided, only generate artifacts of these types.

    Returns:
        List of ``GenerationResult`` — one per artifact spec, regardless
        of success/failure.
    """
    # Ensure generators are loaded before consulting the registry.
    # This is a safety net — callers should call load_generators()
    # explicitly during setup for clarity and faster failure.
    load_generators()

    results: list[GenerationResult] = []

    for spec in artifact_specs:
        artifact_type = spec.get("type", "unknown")

        # Type filtering
        if type_filter and artifact_type not in type_filter:
            results.append(
                GenerationResult(
                    artifact_type=artifact_type,
                    service_name=spec.get("service", "unknown"),
                    success=True,
                    skipped=True,
                    skip_reason=f"Filtered out (type_filter={type_filter})",
                )
            )
            continue

        result = generate_artifact(
            spec,
            context_manifest,
            output_dir,
            dry_run=dry_run,
            force=force,
        )
        results.append(result)

    logger.info(
        "Generation complete: %d succeeded, %d failed, %d skipped out of %d total",
        sum(1 for r in results if r.success and not r.skipped),
        sum(1 for r in results if not r.success),
        sum(1 for r in results if r.skipped),
        len(results),
    )

    return results


# ──────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────

__all__ = [
    # Data models
    "GeneratedFile",
    "GenerationResult",
    # Type aliases / contracts
    "GeneratorFn",
    "ArtifactSpec",
    # Registry
    "register_generator",
    "get_generator",
    "registered_types",
    "load_generators",
    "SUPPORTED_ARTIFACT_TYPES",
    # Jinja2
    "create_jinja_env",
    "get_jinja_env",
    "reset_jinja_env",
    # Orchestration
    "generate_artifact",
    "generate_all",
    # Path resolution
    "resolve_output_path",
]