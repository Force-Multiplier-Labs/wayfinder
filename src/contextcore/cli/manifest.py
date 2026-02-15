# File: src/contextcore/generators/orchestrator.py
"""Generation orchestrator — coordinates artifact generation pipeline.

This module is the single authority for file-path resolution, directory creation,
and I/O coordination in the generation pipeline. Generator functions receive a
resolved target_path and are responsible only for content rendering and writing.

Key invariants:
    - Per-artifact failures are isolated and never abort the entire run (blocking constraint).
    - Existing files are skipped unless --force is set.
    - Dry-run mode produces results without any filesystem side effects.
    - All canonical artifact types must have registered generators (startup validation).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from contextcore.generators import ensure_generators_loaded
from contextcore.generators.models import GenerationResult
from contextcore.generators.registry import get_generator, registered_types
from contextcore.generators.types import ARTIFACT_TYPES

if TYPE_CHECKING:
    pass  # Future: import ContextManifest, ArtifactSpec for type hints


def run_generation(
    manifest,
    output_dir: Path,
    type_filter: set[str] | None,
    dry_run: bool,
    force: bool,
    progress_callback: Callable[[GenerationResult], None] | None = None,
) -> list[GenerationResult]:
    """Run the generation pipeline for all artifacts in the manifest.

    Iterates over ``manifest.artifacts``, dispatching each to the appropriate
    registered generator function. Results are collected and returned as a list,
    with per-artifact failures recorded but never aborting the run.

    Args:
        manifest: A ContextManifest instance with an ``artifacts`` attribute
                  containing ArtifactSpec objects.
        output_dir: Root directory for generated output files. Subdirectories
                    are created automatically based on each artifact's
                    ``relative_path``.
        type_filter: If not None, only generate artifacts whose ``type`` is in
                     this set. Types must use canonical casing (e.g.,
                     ``"ServiceMonitor"``).
        dry_run: If True, preview what would be generated without writing files
                 or creating directories.
        force: If True, overwrite existing files. If False, existing files are
               skipped with a ``skipped=True`` result.
        progress_callback: Optional callable invoked with each GenerationResult
                          as it is produced. Used by the CLI for ``--verbose``
                          per-artifact progress output.

    Returns:
        List of GenerationResult, one per processed artifact. Artifacts excluded
        by ``type_filter`` do not appear in the results.

    Raises:
        RuntimeError: If any canonical artifact type lacks a registered generator
                     (startup validation failure). This is raised before any
                     artifacts are processed.
    """
    # --- Phase 0: Ensure all generator modules are imported ---
    ensure_generators_loaded()

    # Startup validation: verify every canonical type has a generator.
    # This turns a missing import from a silent per-artifact failure into
    # an immediate, clear error.
    missing = set(ARTIFACT_TYPES) - registered_types()
    if missing:
        raise RuntimeError(
            f"Generator modules not registered for types: {sorted(missing)}. "
            f"Check contextcore/generators/__init__.py imports."
        )

    results: list[GenerationResult] = []

    for artifact_spec in manifest.artifacts:
        # --- Type filtering ---
        if type_filter and artifact_spec.type not in type_filter:
            continue

        # --- Registry lookup ---
        try:
            generator = get_generator(artifact_spec.type)
        except KeyError:
            result = GenerationResult(
                artifact_type=artifact_spec.type,
                artifact_name=artifact_spec.name,
                success=False,
                error=f"No generator for type '{artifact_spec.type}'",
            )
            results.append(result)
            if progress_callback:
                progress_callback(result)
            continue

        # --- Resolve target path (single source of truth) ---
        target_path = output_dir / artifact_spec.relative_path

        # --- Check for existing file — skip unless --force ---
        if target_path.exists() and not force and not dry_run:
            result = GenerationResult(
                artifact_type=artifact_spec.type,
                artifact_name=artifact_spec.name,
                success=True,
                skipped=True,
                output_path=target_path,
                message="File exists; use --force to overwrite",
            )
            results.append(result)
            if progress_callback:
                progress_callback(result)
            continue

        # --- Dry-run: report without writing ---
        if dry_run:
            result = GenerationResult(
                artifact_type=artifact_spec.type,
                artifact_name=artifact_spec.name,
                success=True,
                skipped=False,
                output_path=target_path,
                dry_run=True,
                message="Would generate",
            )
            results.append(result)
            if progress_callback:
                progress_callback(result)
            continue

        # --- Ensure parent directories exist ---
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            result = GenerationResult(
                artifact_type=artifact_spec.type,
                artifact_name=artifact_spec.name,
                success=False,
                error=f"Cannot create directory {target_path.parent}: {exc}",
            )
            results.append(result)
            if progress_callback:
                progress_callback(result)
            continue

        # --- Actual generation — per-artifact error isolation ---
        try:
            result = generator(artifact_spec, manifest, target_path)
            results.append(result)
        except Exception as exc:
            result = GenerationResult(
                artifact_type=artifact_spec.type,
                artifact_name=artifact_spec.name,
                success=False,
                error=str(exc),
            )
            results.append(result)

        if progress_callback:
            progress_callback(result)

    return results