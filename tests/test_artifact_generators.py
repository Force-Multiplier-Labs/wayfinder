"""Basic generator tests for contextcore artifact generation.

This file contains ONLY test classes. All factories, assertion helpers,
and constants are imported from tests.helpers. Fixtures come from conftest.py.
"""

import pytest
from pathlib import Path

from contextcore.generators import (
    GenerationResult,
    generate_artifact,
)
from contextcore.generators.registry import get_generator, list_generators

from tests.helpers import (
    ARTIFACT_TYPES,
    ONLINE_BOUTIQUE_SERVICES,
    make_artifact_spec,
    make_context_manifest,
    make_batch_specs,
    expected_filename,
    assert_generation_result_valid,
    assert_has_derivation_rules,
    assert_file_not_overwritten,
)


# ─── Section 1: Factory & Helper Validation ────────────────────────────

class TestFactoriesAndHelpers:
    """P0 — Validate that factory functions produce valid structures."""

    def test_make_artifact_spec_returns_required_keys(self):
        spec = make_artifact_spec()
        assert "type" in spec
        assert "service" in spec
        assert "name" in spec
        assert "metadata" in spec
        assert "derivation_rules" in spec
        assert "config" in spec

    def test_make_artifact_spec_applies_overrides_without_mutation(self):
        overrides = {"config": {"port": "grpc"}}
        spec = make_artifact_spec(overrides=overrides)
        assert spec["config"]["port"] == "grpc"
        # Original overrides dict must not be mutated
        assert overrides == {"config": {"port": "grpc"}}

    def test_make_artifact_spec_no_cross_test_contamination(self):
        """Two specs created with the same overrides must be independent objects."""
        overrides = {"metadata": {"labels": {"env": "test"}}}
        spec1 = make_artifact_spec(overrides=overrides)
        spec2 = make_artifact_spec(overrides=overrides)
        spec1["metadata"]["labels"]["env"] = "mutated"
        assert spec2["metadata"]["labels"]["env"] == "test"

    def test_make_context_manifest_returns_required_keys(self):
        manifest = make_context_manifest()
        assert "project" in manifest
        assert "services" in manifest
        assert "generation" in manifest

    def test_make_batch_specs_default_produces_77_specs(self):
        specs = make_batch_specs()
        assert len(specs) == 77  # 7 types × 11 services

    @pytest.mark.parametrize("artifact_type", ARTIFACT_TYPES)
    def test_make_artifact_spec_per_type(self, artifact_type):
        spec = make_artifact_spec(artifact_type=artifact_type)
        assert spec["type"] == artifact_type
        assert spec["config"]  # must have non-empty config

    def test_expected_filename_matches_template(self):
        assert expected_filename("frontend", "ServiceMonitor") == "frontend-servicemonitor.yaml"


# ─── Section 2: Generator Signature Contract ───────────────────────────

class TestGeneratorSignatureContract:
    """[blocking] All generators must accept (artifact_spec, context_manifest, output_dir)
    and return GenerationResult."""

    @pytest.mark.parametrize("artifact_type", ARTIFACT_TYPES)
    def test_generator_returns_generation_result(self, artifact_type, output_dir, sample_manifest):
        spec = make_artifact_spec(artifact_type=artifact_type)
        generator = get_generator(artifact_type)
        result = generator(spec, sample_manifest, output_dir)
        assert_generation_result_valid(result)
        assert result.artifact_type == artifact_type

    @pytest.mark.parametrize("artifact_type", ARTIFACT_TYPES)
    def test_generated_artifact_has_derivation_rules(self, artifact_type, output_dir, sample_manifest):
        spec = make_artifact_spec(artifact_type=artifact_type)
        result = generate_artifact(spec, sample_manifest, output_dir)
        if result.success and result.output_path:
            content = Path(result.output_path).read_text()
            assert_has_derivation_rules(content)


# ─── Section 3: Registry Tests ─────────────────────────────────────────

class TestRegistry:
    def test_all_seven_types_registered(self):
        registered = list_generators()
        for artifact_type in ARTIFACT_TYPES:
            assert artifact_type in registered, f"{artifact_type} not registered"

    def test_registry_returns_callable(self):
        for artifact_type in ARTIFACT_TYPES:
            gen = get_generator(artifact_type)
            assert callable(gen)

    def test_unknown_type_raises_keyerror(self):
        with pytest.raises(KeyError):
            get_generator("NonExistentType")


# ─── Section 4: Error Handling Tests ───────────────────────────────────

class TestErrorIsolation:
    """[blocking] Per-artifact errors must not abort the entire generation run."""

    def test_invalid_spec_returns_failed_result_not_exception(self, output_dir, sample_manifest):
        """A malformed spec should return GenerationResult(success=False), not raise."""
        bad_spec = make_artifact_spec(overrides={"type": "InvalidType"})
        result = generate_artifact(bad_spec, sample_manifest, output_dir)
        assert isinstance(result, GenerationResult)
        assert result.success is False
        assert result.error is not None

    def test_batch_continues_after_single_failure(self, output_dir, sample_manifest):
        """One bad artifact in a batch must not prevent others from generating."""
        specs = [
            make_artifact_spec(artifact_type="ServiceMonitor", service_name="frontend"),
            make_artifact_spec(overrides={"type": "InvalidType"}),  # will fail
            make_artifact_spec(artifact_type="PrometheusRule", service_name="frontend"),
        ]
        results = [generate_artifact(s, sample_manifest, output_dir) for s in specs]

        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True  # Must still succeed

    def test_template_render_error_captured_not_raised(self, output_dir, sample_manifest):
        """Template errors (missing variables, syntax) are captured in result.error.

        This test unconditionally asserts failure — an empty config is expected
        to cause a template rendering error, which must be captured rather than raised.
        """
        spec = make_artifact_spec(overrides={"config": {}})  # missing required config
        result = generate_artifact(spec, sample_manifest, output_dir)
        assert isinstance(result, GenerationResult)
        # Must fail — unconditional assertion (no false-positive pass if it unexpectedly succeeds)
        assert result.success is False, (
            "Expected failure for empty config, but generation unexpectedly succeeded. "
            "If empty config is now valid, this test's premise needs updating."
        )
        assert result.error is not None
        assert len(result.error) > 0


# ─── Section 5: Overwrite/Force Tests ──────────────────────────────────

class TestOverwriteProtection:
    """[warning] Check for existing artifacts before overwriting."""

    def test_existing_file_skipped_without_force(self, populated_output_dir, sample_manifest):
        spec = make_artifact_spec()
        result = generate_artifact(spec, sample_manifest, populated_output_dir, force=False)
        assert result.skipped is True
        filename = expected_filename("frontend", "ServiceMonitor")
        assert_file_not_overwritten(populated_output_dir / filename)

    def test_existing_file_overwritten_with_force(self, populated_output_dir, sample_manifest):
        spec = make_artifact_spec()
        result = generate_artifact(spec, sample_manifest, populated_output_dir, force=True)
        assert result.success is True
        assert result.skipped is False
        filename = expected_filename("frontend", "ServiceMonitor")
        content = (populated_output_dir / filename).read_text()
        assert content != "# pre-existing file\n"


# ─── Section 6: Dry-Run Tests ──────────────────────────────────────────

class TestDryRun:
    """[warning] Dry-run mode must report success without writing files to disk."""

    @pytest.mark.parametrize("artifact_type", ARTIFACT_TYPES)
    def test_dry_run_returns_success_without_writing_file(
        self, artifact_type, output_dir, sample_manifest
    ):
        spec = make_artifact_spec(artifact_type=artifact_type)
        result = generate_artifact(spec, sample_manifest, output_dir, dry_run=True)
        assert isinstance(result, GenerationResult)
        assert result.success is True
        # No file should be written in dry-run mode
        filename = expected_filename(spec["service"], artifact_type)
        assert not (output_dir / filename).exists(), (
            f"Dry-run should not write {filename} to disk"
        )

    def test_dry_run_does_not_modify_existing_file(self, populated_output_dir, sample_manifest):
        spec = make_artifact_spec()
        result = generate_artifact(spec, sample_manifest, populated_output_dir, dry_run=True)
        assert result.success is True
        filename = expected_filename("frontend", "ServiceMonitor")
        assert_file_not_overwritten(populated_output_dir / filename)


# ─── Section 7: Type Filtering Tests (Placeholder) ────────────────────

class TestTypeFiltering:
    """[placeholder] Type filtering is an explicit project goal.

    These tests establish the pattern for validating that generation can be
    scoped to a subset of artifact types. Full implementation tests will be
    added by the type-filtering feature.
    """

    def test_single_type_filter_generates_only_matching_type(self, output_dir, sample_manifest):
        """When filtering to a single type, only that type should be generated."""
        # Placeholder: tests the concept using manual spec construction
        target_type = "ServiceMonitor"
        specs = [
            make_artifact_spec(artifact_type=at, service_name="frontend")
            for at in ARTIFACT_TYPES
        ]
        filtered_specs = [s for s in specs if s["type"] == target_type]
        assert len(filtered_specs) == 1
        result = generate_artifact(filtered_specs[0], sample_manifest, output_dir)
        assert_generation_result_valid(result)
        assert result.artifact_type == target_type

    def test_empty_filter_generates_nothing(self):
        """An empty type filter should produce zero specs."""
        specs = make_batch_specs(artifact_types=[])
        assert len(specs) == 0