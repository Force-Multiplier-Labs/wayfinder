"""contextcore generator infrastructure.

This module provides the core infrastructure for generating observability artifacts
(ServiceMonitor, PrometheusRule, LokiRule, SLO, NotificationPolicy, Runbook, Dashboard).

It includes:
  - Data models (ArtifactSpec, GeneratedFile, GenerationResult)
  - Registry functions (register_generator, get_generator, etc.)
  - Jinja2 environment management (create_jinja_env, get_jinja_env, reset_jinja_env)
  - Orchestration (generate_artifact, generate_all)
  - Path resolution and atomic file writes

Generators are plain functions registered by artifact type string via
``register_generator()``.  The ``load_generators()`` function explicitly
imports ``artifact_generators.py`` to populate the registry — there are no
import-time side-effects from this module itself.

Thread-safety note:
    The lazy Jinja2 singleton (``_jinja_env``) is **not** protected by a lock.
    This is acceptable for single-threaded CLI usage but must be addressed if the
    module is ever used from multiple threads.
"""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import jinja2

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # type: ignore[assignment]

# ── Legacy re-exports (backward compatibility) ───────────────────────────────
# These imports allow downstream code that does
#   ``from contextcore.generators import generate_runbook``
# to keep working even though the canonical location is a sub-module.
try:
    from contextcore.generators.runbook import generate_runbook  # noqa: F401
except ImportError:
    generate_runbook = None  # type: ignore[assignment,misc]

try:
    from contextcore.generators.slo_tests import (  # noqa: F401
        TestType,
        GeneratedTest,
        SLOTestGenerator,
        parse_duration,
        parse_throughput,
    )
except ImportError:
    TestType = None  # type: ignore[assignment,misc]
    GeneratedTest = None  # type: ignore[assignment,misc]
    SLOTestGenerator = None  # type: ignore[assignment,misc]
    parse_duration = None  # type: ignore[assignment,misc]
    parse_throughput = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Input Contracts (TypedDict definitions)
# ─────────────────────────────────────────────────────────────────────────────


class ArtifactSpec(TypedDict, total=False):
    """Expected shape of an artifact spec dict from the manifest.

    Required keys (in practice — ``total=False`` for gradual adoption):
        type: One of :data:`SUPPORTED_ARTIFACT_TYPES` (e.g. ``"ServiceMonitor"``).
        service: Service name this artifact targets (e.g. ``"cartservice"``).

    Optional keys:
        metadata: Type-specific configuration consumed by templates.
        output_filename: Override for the generated filename (without directory).
    """

    type: str
    service: str
    metadata: dict
    output_filename: str


# ─────────────────────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class GeneratedFile:
    """Represents a single file produced by a generator.

    Attributes:
        path: Resolved output path (computed by the orchestrator via
              :func:`resolve_output_path`).
        content: Rendered file content (from Jinja2 template).
        artifact_type: One of the 7 supported artifact types.
        service_name: Service this artifact belongs to.
        derivation_rules: Maps output config values back to manifest fields
                          for traceability.
        overwritten: Set to ``True`` when an existing file was overwritten
                     with ``--force``.
    """

    path: Path
    content: str
    artifact_type: str
    service_name: str
    derivation_rules: dict = field(default_factory=dict)
    overwritten: bool = False


@dataclass
class GenerationResult:
    """Per-artifact outcome — success or failure with context.

    Attributes:
        artifact_type: Artifact type attempted.
        service_name: Target service name.
        success: Whether generation succeeded.
        file: The generated file (if successful).
        error: Error message (if failed).
        skipped: Whether generation was skipped (filtered/exists).
        skip_reason: Reason for skip.
    """

    artifact_type: str
    service_name: str
    success: bool
    file: Optional[GeneratedFile] = None
    error: Optional[str] = None
    skipped: bool = False
    skip_reason: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Type Aliases
# ─────────────────────────────────────────────────────────────────────────────

GeneratorFn = Callable[[ArtifactSpec, dict, Path], GenerationResult]
"""Signature for a generator function.

Every generator accepts ``(artifact_spec, context_manifest, output_path)``
and returns a :class:`GenerationResult`.  The orchestrator handles all
file I/O; generators are responsible only for content generation.
"""

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

SUPPORTED_ARTIFACT_TYPES: tuple[str, ...] = (
    "ServiceMonitor",
    "PrometheusRule",
    "LokiRule",
    "SLO",
    "NotificationPolicy",
    "Runbook",
    "Dashboard",
)
"""All artifact types recognised by the generator framework."""

_TEMPLATES_DIR: Path = Path(__file__).parent / "templates"
"""Root directory for Jinja2 templates (sibling ``templates/`` package)."""

_FILENAME_PATTERNS: dict[str, str] = {
    "ServiceMonitor": "{service}_service_monitor.yaml",
    "PrometheusRule": "{service}_prometheus_rule.yaml",
    "LokiRule": "{service}_loki_rule.yaml",
    "SLO": "{service}_slo.yaml",
    "NotificationPolicy": "{service}_notification_policy.yaml",
    "Runbook": "{service}_runbook.md",
    "Dashboard": "{service}_dashboard.json",
}
"""Default filename patterns per artifact type.  ``{service}`` is replaced at
resolution time by :func:`resolve_output_path`."""

# ─────────────────────────────────────────────────────────────────────────────
# Module-level Mutable State
# ─────────────────────────────────────────────────────────────────────────────

_GENERATOR_REGISTRY: dict[str, GeneratorFn] = {}
"""Registry mapping artifact type string → generator function."""

_generators_loaded: bool = False
"""Idempotency guard for :func:`load_generators`."""

_jinja_env: Optional[jinja2.Environment] = None
"""Lazy-initialised Jinja2 environment singleton.  ``None`` until first
:func:`get_jinja_env` call (or until :func:`reset_jinja_env` sets it)."""

# ─────────────────────────────────────────────────────────────────────────────
# Generator Registry
# ─────────────────────────────────────────────────────────────────────────────


def register_generator(artifact_type: str, fn: GeneratorFn) -> None:
    """Register a generator function for *artifact_type*.

    Args:
        artifact_type: Must be one of :data:`SUPPORTED_ARTIFACT_TYPES`.
        fn: Generator function matching the :data:`GeneratorFn` signature.

    Raises:
        ValueError: If *artifact_type* is not in :data:`SUPPORTED_ARTIFACT_TYPES`.
    """
    if artifact_type not in SUPPORTED_ARTIFACT_TYPES:
        raise ValueError(
            f"Unknown artifact type {artifact_type!r}. "
            f"Supported: {SUPPORTED_ARTIFACT_TYPES}"
        )
    _GENERATOR_REGISTRY[artifact_type] = fn
    logger.debug("Registered generator for artifact type %r", artifact_type)


def get_generator(artifact_type: str) -> Optional[GeneratorFn]:
    """Look up a registered generator.  Returns ``None`` if not registered."""
    return _GENERATOR_REGISTRY.get(artifact_type)


def registered_types() -> list[str]:
    """Return a list of currently registered artifact type strings."""
    return list(_GENERATOR_REGISTRY.keys())


def load_generators() -> None:
    """Explicitly import ``artifact_generators`` to populate the registry.

    This function is **idempotent** — subsequent calls are no-ops.

    It **must** be called before :func:`generate_all` or
    :func:`generate_artifact` are expected to find registered generators.
    :func:`generate_all` calls this automatically as a safety net, but
    callers (e.g. the CLI entry-point) should call it explicitly during
    setup for clarity and faster failure.
    """
    global _generators_loaded
    if _generators_loaded:
        return
    logger.debug("Loading generators from artifact_generators module")
    try:
        # Import triggers module-level register_generator() calls
        import contextcore.generators.artifact_generators  # noqa: F401
    except ImportError:
        logger.warning(
            "Could not import contextcore.generators.artifact_generators — "
            "no built-in generators will be available"
        )
    _generators_loaded = True
    logger.info("Generators loaded. Registered types: %s", registered_types())


# ─────────────────────────────────────────────────────────────────────────────
# Jinja2 Environment
# ─────────────────────────────────────────────────────────────────────────────


def create_jinja_env(templates_dir: Optional[Path] = None) -> jinja2.Environment:
    """Create a configured Jinja2 environment.

    Args:
        templates_dir: Directory to load templates from.
                       Defaults to the ``templates/`` sub-package.

    Returns:
        A :class:`jinja2.Environment` with :class:`jinja2.StrictUndefined`.
    """
    target_dir = templates_dir or _TEMPLATES_DIR
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(target_dir)),
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def get_jinja_env() -> jinja2.Environment:
    """Return the module-level Jinja2 environment (lazy singleton).

    The environment is created on first access using :func:`create_jinja_env`
    with the default templates directory.

    .. warning::
       Not thread-safe.  See module docstring.
    """
    global _jinja_env
    if _jinja_env is None:
        _jinja_env = create_jinja_env()
    return _jinja_env


def reset_jinja_env(templates_dir: Optional[Path] = None) -> None:
    """Reset the Jinja2 singleton.

    Args:
        templates_dir: If provided, the singleton is immediately re-created
                       pointing at this directory.  If ``None``, the singleton
                       is cleared and will be lazily re-created on next access.

    Primarily intended for testing.
    """
    global _jinja_env
    if templates_dir is not None:
        _jinja_env = create_jinja_env(templates_dir)
    else:
        _jinja_env = None


# ─────────────────────────────────────────────────────────────────────────────
# Path Resolution
# ─────────────────────────────────────────────────────────────────────────────


def resolve_output_path(
    artifact_spec: ArtifactSpec,
    output_dir: Path,
) -> Path:
    """Resolve the output file path for an artifact spec.

    Resolution order:
      1. If *artifact_spec* contains ``"output_filename"``, use it directly.
      2. Otherwise use the default pattern from :data:`_FILENAME_PATTERNS`.
      3. Falls back to ``"{service}_{type}.yaml"`` if no pattern is defined.

    Args:
        artifact_spec: Specification dict.
        output_dir: Root output directory.

    Returns:
        Fully-resolved :class:`~pathlib.Path`.
    """
    artifact_type = artifact_spec.get("type", "unknown")
    service_name = artifact_spec.get("service", "unknown")

    filename = artifact_spec.get("output_filename")
    if not filename:
        pattern = _FILENAME_PATTERNS.get(
            artifact_type, "{service}_{type}.yaml"
        )
        filename = pattern.format(service=service_name, type=artifact_type.lower())

    return output_dir / filename


# ─────────────────────────────────────────────────────────────────────────────
# Atomic File Write
# ─────────────────────────────────────────────────────────────────────────────


def _atomic_write(path: Path, content: str) -> None:
    """Write *content* to *path* atomically via temp-file-then-rename.

    The temp file is created in the same directory as *path* so that the
    rename is atomic on POSIX (same filesystem).  Parent directories are
    created as needed.

    On any failure the temp file is cleaned up and the exception is
    re-raised — the target *path* is never left in a partial state.
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


# ─────────────────────────────────────────────────────────────────────────────
# Orchestration
# ─────────────────────────────────────────────────────────────────────────────


def generate_artifact(
    artifact_spec: ArtifactSpec,
    context_manifest: dict,
    output_dir: Path,
    *,
    dry_run: bool = False,
    force: bool = False,
) -> GenerationResult:
    """Generate a single artifact.

    Wraps the registered generator with pre-invocation file-existence checks,
    dry-run support, atomic writes, and error containment.

    Path resolution happens here (not in the generator) so that:
    - File-existence can be checked **before** invoking the generator.
    - Generators don't duplicate path logic.
    - The orchestrator has full control over I/O.

    Args:
        artifact_spec: Specification of the artifact to generate.
        context_manifest: The full context manifest dict.
        output_dir: Root output directory.
        dry_run: If ``True``, compute results but don't write files.
        force: If ``True``, overwrite existing files.

    Returns:
        A :class:`GenerationResult` — always, never raises (except
        ``BaseException`` subclasses that are not ``Exception``).
    """
    artifact_type = artifact_spec.get("type", "unknown")
    service_name = artifact_spec.get("service", "unknown")

    # 1. Look up generator
    generator = get_generator(artifact_type)
    if generator is None:
        logger.warning(
            "No generator registered for type %r (service: %s)",
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
        # 2. Resolve output path BEFORE invoking the generator
        output_path = resolve_output_path(artifact_spec, output_dir)

        # 3. Pre-invocation file-existence check — skip expensive rendering
        #    if the file already exists and --force is not set.
        #    NOTE: inherent TOCTOU race; acceptable for CLI usage.
        if output_path.exists() and not force:
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

        # 4. Invoke the generator — it produces content, we handle I/O
        result = generator(artifact_spec, context_manifest, output_path)

        # 5. Tag overwrite if file existed and --force was used
        if result.success and result.file and output_path.exists():
            result.file.overwritten = True

        # 6. Dry-run: don't write, just return the result
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
        # Per-artifact failure — never abort the run.
        #
        # Catches all Exception subclasses including:
        #   jinja2.TemplateNotFound, TemplateSyntaxError, UndefinedError,
        #   PermissionError, OSError, RuntimeError, ValueError, MemoryError.
        #
        # NOT caught (BaseException only):
        #   KeyboardInterrupt, SystemExit, GeneratorExit.
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
        dry_run: If ``True``, compute results but don't write files.
        force: If ``True``, overwrite existing files.
        type_filter: If provided, only generate artifacts of these types.

    Returns:
        List of :class:`GenerationResult` — one per artifact spec,
        regardless of success/failure.
    """
    # Safety net — callers should call load_generators() explicitly.
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


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

__all__ = [
    # Legacy exports (backward compatibility)
    "generate_runbook",
    "TestType",
    "GeneratedTest",
    "SLOTestGenerator",
    "parse_duration",
    "parse_throughput",
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