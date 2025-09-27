"""Unit tests for smart batching utility functions.

These tests define the behavioral contract for smart batching algorithms.
Tests focus on run-level batching behavior with individual weight configs.
"""

from cosmos_workflow.utils.smart_batching import (
    calculate_batch_efficiency,
    filter_batchable_jobs,
    get_control_signature,
    get_execution_signature,
    group_runs_mixed,
    group_runs_strict,
)


class MockJob:
    """Mock JobQueue object for testing."""

    def __init__(self, job_id: str, config: dict, prompt_ids: list[str] | None = None):
        self.id = job_id
        self.config = config
        self.prompt_ids = prompt_ids or [f"ps_{job_id}_1"]
        self.job_type = "inference"
        self.status = "queued"


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


class TestExecutionSignature:
    """Test execution signature extraction for params that must match."""

    def test_get_execution_signature_matches_identical_params(self):
        """Identical execution params should produce same signature."""
        config1 = {"num_steps": 25, "guidance_scale": 5.0, "seed": 1, "weights": {"edge": 0.5}}
        config2 = {"num_steps": 25, "guidance_scale": 5.0, "seed": 1, "weights": {"depth": 0.3}}

        sig1 = get_execution_signature(config1)
        sig2 = get_execution_signature(config2)
        assert sig1 == sig2  # Weights differ but exec params same

    def test_get_execution_signature_differs_with_different_params(self):
        """Different execution params should produce different signatures."""
        config1 = {"num_steps": 25, "guidance_scale": 5.0, "seed": 1}
        config2 = {"num_steps": 30, "guidance_scale": 5.0, "seed": 1}

        sig1 = get_execution_signature(config1)
        sig2 = get_execution_signature(config2)
        assert sig1 != sig2  # num_steps differs


class TestRunLevelStrictGrouping:
    """Test strict mode grouping at the run level (not job level)."""

    def test_group_runs_strict_extracts_individual_runs(self):
        """Each prompt_id should be treated as a separate run."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}, ["ps_1", "ps_2", "ps_3"]),
            MockJob("job2", {"weights": {"edge": 0.5}}, ["ps_4", "ps_5"]),
        ]

        batches = group_runs_strict(jobs, max_batch_size=4)

        # Should create batches at run level, not job level
        assert len(batches) == 2  # 5 runs total, batch_size=4 -> [4 runs, 1 run]
        assert len(batches[0]["prompt_ids"]) == 4
        assert len(batches[1]["prompt_ids"]) == 1

    def test_group_runs_strict_separates_different_controls(self):
        """Runs with different control types should not batch together."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}, ["ps_1", "ps_2"]),
            MockJob("job2", {"weights": {"depth": 0.3}}, ["ps_3", "ps_4"]),
            MockJob("job3", {"weights": {"edge": 0.5}}, ["ps_5"]),
        ]

        batches = group_runs_strict(jobs, max_batch_size=4)

        # Should create 2 batches: edge runs and depth runs
        edge_batches = [b for b in batches if "edge" in b["config"]["weights_list"][0]]
        depth_batches = [b for b in batches if "depth" in b["config"]["weights_list"][0]]

        assert len(edge_batches) == 1
        assert len(depth_batches) == 1
        assert len(edge_batches[0]["prompt_ids"]) == 3  # ps_1, ps_2, ps_5
        assert len(depth_batches[0]["prompt_ids"]) == 2  # ps_3, ps_4

    def test_group_runs_strict_creates_weights_list(self):
        """Each batch should have weights_list with entry per run."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}, ["ps_1", "ps_2"]),
            MockJob("job2", {"weights": {"edge": 0.3}}, ["ps_3"]),  # Different weight value
        ]

        batches = group_runs_strict(jobs, max_batch_size=4)

        assert len(batches) == 1
        batch = batches[0]

        # Should have weights_list with individual weights
        assert "weights_list" in batch["config"]
        assert len(batch["config"]["weights_list"]) == 3

        # First two runs have edge=0.5, third has edge=0.3
        assert batch["config"]["weights_list"][0] == {"edge": 0.5}
        assert batch["config"]["weights_list"][1] == {"edge": 0.5}
        assert batch["config"]["weights_list"][2] == {"edge": 0.3}

    def test_group_runs_strict_tracks_source_jobs(self):
        """Batches should track which original jobs they came from."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}, ["ps_1", "ps_2"]),
            MockJob("job2", {"weights": {"edge": 0.5}}, ["ps_3"]),
            MockJob("job3", {"weights": {"edge": 0.5}}, ["ps_4", "ps_5"]),
        ]

        batches = group_runs_strict(jobs, max_batch_size=3)

        # Should create 2 batches: [ps_1, ps_2, ps_3], [ps_4, ps_5]
        assert len(batches) == 2

        # First batch should reference job1 and job2
        assert set(batches[0]["source_job_ids"]) == {"job1", "job2"}

        # Second batch should reference job3
        assert set(batches[1]["source_job_ids"]) == {"job3"}


class TestRunLevelMixedGrouping:
    """Test mixed mode grouping allowing different control types."""

    def test_group_runs_mixed_combines_different_controls(self):
        """Mixed mode should allow different control types in same batch."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}, ["ps_1", "ps_2"]),
            MockJob("job2", {"weights": {"depth": 0.3}}, ["ps_3"]),
            MockJob("job3", {"weights": {"edge": 0.4, "depth": 0.2}}, ["ps_4"]),
        ]

        batches = group_runs_mixed(jobs, max_batch_size=10)

        # Should create 1 batch with all runs despite different controls
        assert len(batches) == 1
        assert len(batches[0]["prompt_ids"]) == 4

        # weights_list should have diverse configs
        weights_list = batches[0]["config"]["weights_list"]
        assert weights_list[0] == {"edge": 0.5}  # ps_1
        assert weights_list[2] == {"depth": 0.3}  # ps_3
        assert weights_list[3] == {"edge": 0.4, "depth": 0.2}  # ps_4

    def test_group_runs_mixed_separates_different_exec_params(self):
        """Even in mixed mode, different exec params cannot batch."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}, "num_steps": 25}, ["ps_1", "ps_2"]),
            MockJob("job2", {"weights": {"depth": 0.3}, "num_steps": 25}, ["ps_3"]),
            MockJob("job3", {"weights": {"edge": 0.5}, "num_steps": 30}, ["ps_4"]),  # Different steps
        ]

        batches = group_runs_mixed(jobs, max_batch_size=10)

        # Should create 2 batches due to different num_steps
        assert len(batches) == 2

        # Batch 1: num_steps=25 (ps_1, ps_2, ps_3)
        # Batch 2: num_steps=30 (ps_4)
        batch_25 = next(b for b in batches if b["config"]["num_steps"] == 25)
        batch_30 = next(b for b in batches if b["config"]["num_steps"] == 30)

        assert len(batch_25["prompt_ids"]) == 3
        assert len(batch_30["prompt_ids"]) == 1


class TestBatchEfficiencyCalculation:
    """Test efficiency metrics calculation for batches."""

    def test_calculate_efficiency_run_based(self):
        """Efficiency should be based on run count, not job count."""
        jobs = [
            MockJob("job1", {"weights": {"edge": 0.5}}, ["ps_1", "ps_2", "ps_3"]),
            MockJob("job2", {"weights": {"edge": 0.5}}, ["ps_4", "ps_5"]),
        ]

        batches = [
            {"prompt_ids": ["ps_1", "ps_2", "ps_3", "ps_4"], "config": {"weights_list": []}},
            {"prompt_ids": ["ps_5"], "config": {"weights_list": []}},
        ]

        efficiency = calculate_batch_efficiency(batches, jobs, "strict")

        assert efficiency["total_runs"] == 5  # Total prompt_ids
        assert efficiency["original_jobs"] == 2
        assert efficiency["total_batches"] == 2
        assert efficiency["speedup"] > 1.0  # Should show improvement

    def test_calculate_efficiency_mixed_mode_overhead(self):
        """Mixed mode should show overhead from control diversity."""
        jobs = [MockJob(f"job{i}", {"weights": {"edge": 0.5}}, [f"ps_{i}"]) for i in range(4)]

        # Create batch with diverse controls (simulating mixed mode)
        batches = [{
            "prompt_ids": ["ps_0", "ps_1", "ps_2", "ps_3"],
            "config": {
                "weights_list": [
                    {"edge": 0.5},
                    {"depth": 0.3},
                    {"seg": 0.2},
                    {"edge": 0.4, "depth": 0.3, "seg": 0.1}  # Many controls
                ]
            }
        }]

        efficiency = calculate_batch_efficiency(batches, jobs, "mixed")

        # Mixed mode with diverse controls should have lower speedup than strict
        assert efficiency["speedup"] < 4.0  # Less than theoretical max due to overhead


class TestFilterBatchableJobs:
    """Test filtering of jobs that can be batched."""

    def test_filter_excludes_non_batchable_types(self):
        """Enhancement and upscale jobs should be excluded."""
        jobs = [
            MockJob("job1", {}, ["ps_1"]),  # inference
            MockJob("job2", {}, ["ps_2"]),  # inference
        ]
        jobs[0].job_type = "inference"
        jobs[1].job_type = "enhancement"

        batchable = filter_batchable_jobs(jobs)

        assert len(batchable) == 1
        assert batchable[0].id == "job1"

    def test_filter_includes_batch_inference(self):
        """batch_inference jobs should be included."""
        jobs = [MockJob("job1", {}, ["ps_1", "ps_2", "ps_3"])]
        jobs[0].job_type = "batch_inference"

        batchable = filter_batchable_jobs(jobs)

        assert len(batchable) == 1
        assert batchable[0].job_type == "batch_inference"