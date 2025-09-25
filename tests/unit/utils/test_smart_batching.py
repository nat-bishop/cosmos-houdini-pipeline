"""Unit tests for smart batching utility functions.

These tests define the behavioral contract for smart batching algorithms.
Tests focus on user-observable outcomes, not implementation details.
"""

from cosmos_workflow.utils.smart_batching import (
    calculate_batch_efficiency,
    filter_batchable_jobs,
    get_control_signature,
    get_safe_batch_size,
    group_jobs_mixed,
    group_jobs_strict,
)


class TestControlSignatureExtraction:
    """Test extraction of control signatures from job configurations."""

    def test_get_control_signature_single_control(self):
        """Single active control should return tuple with that control."""
        config = {"weights": {"edge": 0.5}}
        signature = get_control_signature(config)
        assert signature == ("edge",)

    def test_get_control_signature_multiple_controls(self):
        """Multiple active controls should return sorted tuple."""
        config = {"weights": {"depth": 0.3, "edge": 0.5, "normal": 0.2}}
        signature = get_control_signature(config)
        assert signature == ("depth", "edge", "normal")

    def test_get_control_signature_no_controls(self):
        """No weights should return empty tuple."""
        config = {}
        signature = get_control_signature(config)
        assert signature == ()

    def test_get_control_signature_zero_weights(self):
        """Zero-weighted controls should be excluded."""
        config = {"weights": {"edge": 0.5, "depth": 0.0, "normal": 0.0}}
        signature = get_control_signature(config)
        assert signature == ("edge",)


class TestStrictGrouping:
    """Test strict mode grouping (identical controls only)."""

    def test_group_jobs_strict_identical_controls(self):
        """Jobs with identical controls should group together."""
        # Create mock job objects with control signatures
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}),
            MockJob("job2", {"weights": {"edge": 0.5}}),
            MockJob("job3", {"weights": {"edge": 0.5}}),
        ]

        batches = group_jobs_strict(jobs, max_batch_size=4)

        assert len(batches) == 1
        assert len(batches[0]["jobs"]) == 3
        assert batches[0]["signature"] == ("edge",)

    def test_group_jobs_strict_mixed_controls(self):
        """Jobs with different controls should create separate groups."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}),
            MockJob("job2", {"weights": {"depth": 0.5}}),
            MockJob("job3", {"weights": {"edge": 0.5}}),
        ]

        batches = group_jobs_strict(jobs, max_batch_size=4)

        assert len(batches) == 2
        # Find edge batch and depth batch
        edge_batch = next(b for b in batches if b["signature"] == ("edge",))
        depth_batch = next(b for b in batches if b["signature"] == ("depth",))
        assert len(edge_batch["jobs"]) == 2
        assert len(depth_batch["jobs"]) == 1

    def test_group_jobs_strict_respects_batch_limits(self):
        """Batches should not exceed max_batch_size."""
        jobs = [MockJob(f"job{i}", {"weights": {"edge": 0.5}}) for i in range(10)]

        batches = group_jobs_strict(jobs, max_batch_size=3)

        # Should create 4 batches: 3, 3, 3, 1
        assert len(batches) == 4
        assert all(len(b["jobs"]) <= 3 for b in batches)
        assert sum(len(b["jobs"]) for b in batches) == 10

    def test_group_jobs_strict_with_different_prompt_counts(self):
        """Jobs can have different prompt counts but same controls."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}, prompt_count=1),
            MockJob("job2", {"weights": {"edge": 0.5}}, prompt_count=5),
            MockJob("job3", {"weights": {"edge": 0.5}}, prompt_count=2),
        ]

        batches = group_jobs_strict(jobs, max_batch_size=4)

        assert len(batches) == 1
        assert len(batches[0]["jobs"]) == 3


class TestMixedGrouping:
    """Test mixed mode grouping (master batch approach)."""

    def test_group_jobs_mixed_optimizes_control_overhead(self):
        """Mixed mode should minimize total control overhead."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}),
            MockJob("job2", {"weights": {"edge": 0.5, "depth": 0.3}}),
            MockJob("job3", {"weights": {"depth": 0.3}}),
        ]

        batches = group_jobs_mixed(jobs, max_batch_size=4)

        # Should create one batch with master controls
        assert len(batches) == 1
        assert set(batches[0]["master_controls"]) == {"edge", "depth"}
        assert len(batches[0]["jobs"]) == 3

    def test_group_jobs_mixed_creates_master_batch(self):
        """Master batch should be union of all job controls."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}),
            MockJob("job2", {"weights": {"depth": 0.3}}),
            MockJob("job3", {"weights": {"normal": 0.4}}),
        ]

        batches = group_jobs_mixed(jobs, max_batch_size=4)

        assert len(batches) == 1
        assert set(batches[0]["master_controls"]) == {"edge", "depth", "normal"}

    def test_group_jobs_mixed_respects_batch_limits(self):
        """Mixed mode should respect batch size limits."""
        jobs = [
            MockJob(
                f"job{i}",
                {
                    "weights": {
                        "edge": 0.5 if i % 2 == 0 else 0,
                        "depth": 0.5 if i % 2 == 1 else 0.5,
                    }
                },
            )
            for i in range(10)
        ]

        batches = group_jobs_mixed(jobs, max_batch_size=3)

        assert all(len(b["jobs"]) <= 3 for b in batches)
        assert sum(len(b["jobs"]) for b in batches) == 10

    def test_group_jobs_mixed_master_control_selection(self):
        """Verify union algorithm for master control selection."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}),
            MockJob("job2", {"weights": {"depth": 0.3}}),
            MockJob("job3", {"weights": {"edge": 0.5, "depth": 0.3}}),
        ]

        batches = group_jobs_mixed(jobs, max_batch_size=4)

        # Master should be union: edge U depth U (edge, depth) = (edge, depth)
        assert len(batches) == 1
        assert set(batches[0]["master_controls"]) == {"edge", "depth"}


class TestBatchSizing:
    """Test conservative batch sizing based on control count."""

    def test_safe_batch_size_single_control(self):
        """Single control should allow max 8."""
        assert get_safe_batch_size(1) == 8
        assert get_safe_batch_size(1, user_max=16) == 8
        assert get_safe_batch_size(1, user_max=4) == 4

    def test_safe_batch_size_two_controls(self):
        """Two controls should allow max 4."""
        assert get_safe_batch_size(2) == 4
        assert get_safe_batch_size(2, user_max=16) == 4
        assert get_safe_batch_size(2, user_max=2) == 2

    def test_safe_batch_size_three_plus_controls(self):
        """Three or more controls should allow max 2."""
        assert get_safe_batch_size(3) == 2
        assert get_safe_batch_size(5) == 2
        assert get_safe_batch_size(10) == 2

    def test_safe_batch_size_respects_user_override(self):
        """User max should be respected if lower than safe limit."""
        assert get_safe_batch_size(1, user_max=5) == 5
        assert get_safe_batch_size(2, user_max=3) == 3
        assert get_safe_batch_size(3, user_max=1) == 1


class TestBatchEfficiency:
    """Test batch efficiency calculations."""

    def test_calculate_batch_efficiency_basic(self):
        """Calculate basic efficiency metrics."""
        original_jobs = [MockJob(f"job{i}", {"weights": {"edge": 0.5}}) for i in range(6)]

        batches = [
            {"jobs": original_jobs[:3], "signature": ("edge",)},
            {"jobs": original_jobs[3:], "signature": ("edge",)},
        ]

        metrics = calculate_batch_efficiency(batches, original_jobs)

        assert metrics["job_count_before"] == 6
        assert metrics["job_count_after"] == 2
        assert metrics["estimated_speedup"] == 3.0  # 6 jobs -> 2 batches
        assert metrics["control_reduction"] > 0

    def test_calculate_batch_efficiency_mixed_controls(self):
        """Efficiency should account for control overhead."""
        original_jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}),
            MockJob("job2", {"weights": {"depth": 0.5}}),
            MockJob("job3", {"weights": {"normal": 0.5}}),
        ]

        # One batch with 3 controls vs 3 individual jobs
        batches = [
            {"jobs": original_jobs, "master_controls": ["edge", "depth", "normal"]},
        ]

        metrics = calculate_batch_efficiency(batches, original_jobs)

        assert metrics["job_count_before"] == 3
        assert metrics["job_count_after"] == 1
        # Speedup less than 3x due to control overhead
        assert 1.5 <= metrics["estimated_speedup"] <= 2.5


class TestJobFiltering:
    """Test filtering of batchable jobs."""

    def test_filter_batchable_jobs_includes_inference(self):
        """Inference and batch_inference jobs should be batchable."""
        jobs = [
            MockJob("job1", job_type="inference"),
            MockJob("job2", job_type="batch_inference"),
            MockJob("job3", job_type="inference"),
        ]

        batchable = filter_batchable_jobs(jobs)

        assert len(batchable) == 3
        assert all(j in batchable for j in jobs)

    def test_filter_batchable_jobs_excludes_enhance_upscale(self):
        """Enhancement and upscale jobs should not be batchable."""
        jobs = [
            MockJob("job1", job_type="inference"),
            MockJob("job2", job_type="enhancement"),
            MockJob("job3", job_type="upscale"),
            MockJob("job4", job_type="batch_inference"),
        ]

        batchable = filter_batchable_jobs(jobs)

        assert len(batchable) == 2
        assert all(j.job_type in ["inference", "batch_inference"] for j in batchable)


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_job_list(self):
        """Empty job list should return empty batches."""
        assert group_jobs_strict([], max_batch_size=4) == []
        assert group_jobs_mixed([], max_batch_size=4) == []

    def test_single_job(self):
        """Single job should create single batch."""
        jobs = [MockJob("job1", {"weights": {"edge": 0.5}})]

        strict_batches = group_jobs_strict(jobs, max_batch_size=4)
        mixed_batches = group_jobs_mixed(jobs, max_batch_size=4)

        assert len(strict_batches) == 1
        assert len(mixed_batches) == 1
        assert len(strict_batches[0]["jobs"]) == 1
        assert len(mixed_batches[0]["jobs"]) == 1

    def test_non_batchable_jobs_excluded(self):
        """Non-batchable jobs should be filtered out."""
        jobs = [
            MockJob("job1", job_type="enhancement"),
            MockJob("job2", job_type="upscale"),
        ]

        batchable = filter_batchable_jobs(jobs)
        assert len(batchable) == 0

    def test_all_jobs_different_controls(self):
        """All different controls in strict mode creates separate batches."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}),
            MockJob("job2", {"weights": {"depth": 0.5}}),
            MockJob("job3", {"weights": {"normal": 0.5}}),
        ]

        batches = group_jobs_strict(jobs, max_batch_size=4)

        assert len(batches) == 3
        assert all(len(b["jobs"]) == 1 for b in batches)

    def test_mixed_batchable_and_non_batchable_jobs(self):
        """Mixed job types should filter correctly."""
        jobs = [
            MockJob("job1", job_type="inference"),
            MockJob("job2", job_type="enhancement"),
            MockJob("job3", job_type="batch_inference"),
            MockJob("job4", job_type="upscale"),
        ]

        batchable = filter_batchable_jobs(jobs)

        assert len(batchable) == 2
        assert "job1" in [j.id for j in batchable]
        assert "job3" in [j.id for j in batchable]


# Mock JobQueue class for testing
class MockJob:
    """Mock job object for testing."""

    def __init__(self, job_id, config=None, job_type="inference", prompt_count=1):
        self.id = job_id
        self.config = config or {}
        self.job_type = job_type
        self.prompt_ids = ["prompt"] * prompt_count
