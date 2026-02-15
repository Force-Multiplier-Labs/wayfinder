# -*- coding: utf-8 -*-
"""Tests for the artifact generator registry, individual generators, and batch orchestration.

Test class ordering follows a progressive validation strategy:
  1. TestRegistryBasics          — registry has all 7 types
  2. TestGeneratorSignature      — uniform function signature
  3. TestBasicGeneration         — each type produces valid output
  4. TestDryRunMode              — no files written, valid metadata
  5. TestTypeFiltering           — subset generation
  6. TestUnknownArtifactType     — graceful registry errors
  7. TestPerArtifactFailureIsolation — failure isolation (blocking)
  8. TestBatchOrchestrationIsolation — batch-level failure isolation (blocking)
  9. TestOverwriteProtection     — force flag (warning)
 10. TestFullMatrix              — 77 artifacts smoke test
"""

import pytest
from pathlib import Path

from contextcore.generators import (
    GenerationResult,
    generate_artifact,
    generate_artifacts_batch,
    GENERATOR_REGISTRY,
)
from tests.helpers.generators import (
    ALL_ARTIFACT_TYPES,
    ONLINE_BOUTIQUE_SERVICES,
    make_artifact_spec,
    make_context_manifest,
    assert_generation_result_valid,
    assert_file_contains_derivation_rules,
)


# ─── 1. Registry Basics ─────────────────────────────────────────────

@pytest.mark.blocking
class TestRegistryBasics:
    """Registry must contain exactly the 7 defined artifact types."""

    def test_registry_contains_all_types(self):
        """Each artifact type in ALL_ARTIFACT_TYPES must be registered."""
        for artifact_type in ALL_ARTIFACT_TYPES:
            assert artifact_type in GENERATOR_REGISTRY, (
                f"{artifact_type} missing from GENERATOR_REGISTRY"
            )

    def test_registry_has_exactly_seven_types(self):
        """Registry must not contain extra or missing types."""
        assert len(GENERATOR_REGISTRY) == 7, (
            f"Expected 7 types in registry, found {len(GENERATOR_REGISTRY)}: "
            f"{sorted(GENERATOR_REGISTRY.keys())}"
        )


# ─── 2. Generator Signature ─────────────────────────────────────────

@pytest.mark.blocking
class TestGeneratorSignature:
    """All generators must accept (artifact_spec, context_manifest, output_dir)
    and return GenerationResult."""

    def test_generator_accepts_required_args(self, artifact_type, output_dir, sample_manifest):
        """Direct registry call must accept positional args and return GenerationResult."""
        spec = make_artifact_spec(artifact_type)
        generator_fn = GENERATOR_REGISTRY[artifact_type]
        result = generator_fn(spec, sample_manifest, output_dir)
        assert isinstance(result, GenerationResult), (
            f"Generator for {artifact_type} returned {type(result).__name__}, "
            f"expected GenerationResult"
        )

    def test_generator_returns_generation_result(self, artifact_type, output_dir, sample_manifest):
        """generate_artifact orchestrator must return a valid GenerationResult."""
        spec = make_artifact_spec(artifact_type)
        result = generate_artifact(spec, sample_manifest, output_dir)
        assert_generation_result_valid(result)


# ─── 3. Basic Generation ────────────────────────────────────────────

class TestBasicGeneration:
    """Each artifact type must produce a non-empty file on disk."""

    def test_generates_file_on_disk(self, artifact_type, output_dir, sample_manifest):
        """Generator must create a non-empty file at the reported output_path."""
        spec = make_artifact_spec(artifact_type)
        result = generate_artifact(spec, sample_manifest, output_dir)

        assert result.success, (
            f"Generator for {artifact_type} failed unexpectedly: {result.error}. "
            f"If this type is not yet implemented, mark with @pytest.mark.xfail."
        )
        assert result.output_path.exists(), f"Expected file at {result.output_path}"
        assert result.output_path.stat().st_size > 0, "Generated file must not be empty"

    @pytest.mark.warning
    def test_derivation_rules_in_output(self, artifact_type, output_dir, sample_manifest):
        """Every generated artifact must include derivation_rules tracing."""
        spec = make_artifact_spec(artifact_type)
        result = generate_artifact(spec, sample_manifest, output_dir)

        assert result.success, (
            f"Cannot check derivation rules — generation failed: {result.error}"
        )
        assert_file_contains_derivation_rules(result.output_path)


# ─── 4. Dry-Run Mode ────────────────────────────────────────────────

@pytest.mark.blocking
class TestDryRunMode:
    """dry_run=True must validate and return metadata without writing files."""

    def test_dry_run_writes_no_files(self, artifact_type, output_dir, sample_manifest):
        """Dry run must report success with output_path but not create the file."""
        spec = make_artifact_spec(artifact_type)
        result = generate_artifact(spec, sample_manifest, output_dir, dry_run=True)

        assert_generation_result_valid(result)
        assert result.success, f"Dry-run should succeed for valid spec: {result.error}"
        # output_path should indicate where the file *would* be written
        assert result.output_path is not None
        # But no file should exist on disk
        assert not result.output_path.exists(), (
            f"dry_run=True must not write files, but {result.output_path} exists"
        )

    def test_dry_run_returns_correct_metadata(self, output_dir, sample_manifest):
        """Dry run must return correct artifact_type and service metadata."""
        spec = make_artifact_spec("ServiceMonitor", "frontend")
        result = generate_artifact(spec, sample_manifest, output_dir, dry_run=True)

        assert result.success
        assert result.artifact_type == "ServiceMonitor"
        assert result.service == "frontend"

    def test_dry_run_output_dir_remains_empty(self, output_dir, sample_manifest):
        """No files whatsoever should appear in output_dir during dry-run."""
        for artifact_type in ALL_ARTIFACT_TYPES:
            spec = make_artifact_spec(artifact_type)
            generate_artifact(spec, sample_manifest, output_dir, dry_run=True)

        generated_files = list(output_dir.rglob("*"))
        assert len(generated_files) == 0, (
            f"Dry-run created files: {generated_files}"
        )


# ─── 5. Type Filtering ──────────────────────────────────────────────

@pytest.mark.blocking
class TestTypeFiltering:
    """generate_artifacts_batch with type_filter should only generate matching types."""

    def test_filter_to_single_type(self, output_dir, sample_manifest):
        """Filtering to one type must generate only that type."""
        specs = [
            make_artifact_spec("ServiceMonitor", "frontend"),
            make_artifact_spec("PrometheusRule", "frontend"),
            make_artifact_spec("Dashboard", "frontend"),
        ]

        results = generate_artifacts_batch(
            specs, sample_manifest, output_dir,
            type_filter=["ServiceMonitor"],
        )

        successful = [r for r in results if r.success]
        assert all(r.artifact_type == "ServiceMonitor" for r in successful), (
            "Only ServiceMonitor artifacts should be generated"
        )

    def test_filter_to_multiple_types(self, output_dir, sample_manifest):
        """Filtering to multiple types must generate only those types."""
        specs = [
            make_artifact_spec(t, "frontend") for t in ALL_ARTIFACT_TYPES
        ]

        allowed = ["SLO", "Runbook"]
        results = generate_artifacts_batch(
            specs, sample_manifest, output_dir,
            type_filter=allowed,
        )

        successful = [r for r in results if r.success]
        assert len(successful) == 2
        assert {r.artifact_type for r in successful} == set(allowed)

    def test_filter_with_no_matches_returns_empty(self, output_dir, sample_manifest):
        """Filtering with no matches must return no successful results."""
        specs = [make_artifact_spec("ServiceMonitor", "frontend")]
        results = generate_artifacts_batch(
            specs, sample_manifest, output_dir,
            type_filter=["Dashboard"],
        )

        successful = [r for r in results if r.success]
        assert len(successful) == 0


# ─── 6. Unknown Artifact Type ───────────────────────────────────────

@pytest.mark.blocking
class TestUnknownArtifactType:
    """Graceful error handling for unregistered artifact types."""

    def test_unknown_type_returns_failed_result(self, output_dir, sample_manifest):
        """Unknown type must return a failed GenerationResult with diagnostic info."""
        spec = make_artifact_spec("ServiceMonitor", "frontend",
                                  overrides={"type": "NonExistentType"})
        result = generate_artifact(spec, sample_manifest, output_dir)

        assert isinstance(result, GenerationResult)
        assert not result.success
        assert result.error is not None
        assert (
            "NonExistentType" in result.error
            or "unknown" in result.error.lower()
            or "not found" in result.error.lower()
        )

    def test_unknown_type_does_not_raise(self, output_dir, sample_manifest):
        """Must return a result, never raise an unhandled exception."""
        spec = make_artifact_spec("ServiceMonitor", "frontend",
                                  overrides={"type": "🚫InvalidType🚫"})
        # This call must not raise
        result = generate_artifact(spec, sample_manifest, output_dir)
        assert not result.success


# ─── 7. Per-Artifact Failure Isolation ───────────────────────────────

@pytest.mark.blocking
class TestPerArtifactFailureIsolation:
    """Per-artifact errors must not abort the entire generation run."""

    def test_single_failure_does_not_abort_batch(self, output_dir, sample_manifest):
        """When one artifact spec is invalid, others still generate.

        Uses generate_artifacts_batch to test the CLI-level orchestration,
        not just individual generate_artifact calls in a loop.
        """
        specs = [
            make_artifact_spec("ServiceMonitor", "frontend"),
            make_artifact_spec("ServiceMonitor", "cartservice",
                               overrides={"type": "DELIBERATELY_INVALID_TYPE"}),
            make_artifact_spec("ServiceMonitor", "paymentservice"),
        ]

        results = generate_artifacts_batch(specs, sample_manifest, output_dir)

        # The batch must complete — we get a result for every spec
        assert len(results) == 3
        # At least the valid ones succeed
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]
        assert len(successes) >= 2, "Valid specs must succeed despite sibling failure"

        # Failed results have error details
        for f in failures:
            assert_generation_result_valid(f)
            assert f.error is not None

    def test_individual_call_returns_failure_not_exception(self, output_dir, sample_manifest):
        """A single generate_artifact call must never raise — it returns a failed result."""
        bad_spec = make_artifact_spec("ServiceMonitor", "frontend",
                                      overrides={"config": None})
        # Must not raise
        result = generate_artifact(bad_spec, sample_manifest, output_dir)
        assert isinstance(result, GenerationResult)
        if not result.success:
            assert_generation_result_valid(result)

    def test_failure_result_contains_diagnostic_info(self, output_dir, sample_manifest):
        """Failed GenerationResult must include enough info to diagnose."""
        bad_spec = make_artifact_spec("ServiceMonitor", "frontend",
                                      overrides={"type": "DELIBERATELY_INVALID_TYPE"})
        result = generate_artifact(bad_spec, sample_manifest, output_dir)

        assert not result.success, "Deliberately invalid spec must fail"
        assert result.error, "Error message required"
        assert result.artifact_type == "DELIBERATELY_INVALID_TYPE"
        assert result.service == "frontend"


# ─── 8. Batch Orchestration Isolation ────────────────────────────────

@pytest.mark.blocking
class TestBatchOrchestrationIsolation:
    """Validate that the CLI/batch layer (generate_artifacts_batch) handles
    per-artifact failures gracefully — distinct from testing individual calls."""

    def test_batch_continues_after_failure(self, output_dir, sample_manifest):
        """Batch must return one result per spec, continuing past failures."""
        specs = [
            make_artifact_spec("ServiceMonitor", "frontend"),
            make_artifact_spec("ServiceMonitor", "cartservice",
                               overrides={"type": "DELIBERATELY_INVALID_TYPE"}),
            make_artifact_spec("PrometheusRule", "frontend"),
            make_artifact_spec("Dashboard", "paymentservice"),
        ]

        results = generate_artifacts_batch(specs, sample_manifest, output_dir)

        assert len(results) == 4, "Must return one result per input spec"
        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        assert len(successes) >= 3, "Valid specs must succeed despite sibling failure"
        assert len(failures) >= 1, "Invalid spec must produce a failure result"

        for f in failures:
            assert_generation_result_valid(f)

    def test_batch_failure_order_preserved(self, output_dir, sample_manifest):
        """Results must be returned in the same order as input specs."""
        specs = [
            make_artifact_spec("Dashboard", "frontend"),
            make_artifact_spec("ServiceMonitor", "frontend",
                               overrides={"type": "INVALID"}),
            make_artifact_spec("SLO", "cartservice"),
        ]

        results = generate_artifacts_batch(specs, sample_manifest, output_dir)

        assert len(results) == 3
        assert results[0].artifact_type == "Dashboard"
        assert not results[1].success  # the invalid one
        assert results[2].artifact_type == "SLO"


# ─── 9. Overwrite Protection ────────────────────────────────────────

@pytest.mark.warning
class TestOverwriteProtection:
    """Check for existing artifacts before overwriting."""

    def test_existing_file_not_overwritten_without_force(self, output_dir, sample_manifest):
        """Without force=True, regenerating the same artifact must fail."""
        spec = make_artifact_spec("ServiceMonitor", "frontend")

        # Generate once
        result1 = generate_artifact(spec, sample_manifest, output_dir)
        assert result1.success
        original_content = result1.output_path.read_text()

        # Generate again — must fail without force
        result2 = generate_artifact(spec, sample_manifest, output_dir)
        assert not result2.success, (
            "Second generation without force=True must be rejected"
        )
        assert "exists" in result2.error.lower(), (
            f"Error message must mention file existence, got: {result2.error}"
        )
        # Verify original file is untouched
        assert result1.output_path.read_text() == original_content

    def test_existing_file_overwritten_with_force(self, output_dir, sample_manifest):
        """With force=True, regenerating the same artifact must succeed."""
        spec = make_artifact_spec("ServiceMonitor", "frontend")

        result1 = generate_artifact(spec, sample_manifest, output_dir)
        assert result1.success

        result2 = generate_artifact(spec, sample_manifest, output_dir, force=True)
        assert result2.success


# ─── 10. Full Matrix Smoke Test ─────────────────────────────────────

class TestFullMatrix:
    """Smoke test: generate all 77 artifacts (7 types × 11 services)."""

    def test_full_online_boutique_generation(self, output_dir):
        """Generate every combination of artifact type and service."""
        manifest = make_context_manifest(services=ONLINE_BOUTIQUE_SERVICES)
        specs = [
            make_artifact_spec(artifact_type, service)
            for artifact_type in ALL_ARTIFACT_TYPES
            for service in ONLINE_BOUTIQUE_SERVICES
        ]

        results = generate_artifacts_batch(specs, manifest, output_dir, force=True)

        assert len(results) == 77

        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        if failures:
            failure_summary = "\n".join(
                f"  {r.artifact_type}/{r.service}: {r.error}" for r in failures
            )
            pytest.fail(f"{len(failures)}/77 artifacts failed:\n{failure_summary}")