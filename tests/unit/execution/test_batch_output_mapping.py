"""Test batch output mapping for NVIDIA format."""

from cosmos_workflow.execution.gpu_executor import GPUExecutor


class TestBatchOutputMapping:
    """Test output file mapping to runs."""

    def test_nvidia_sequential_naming(self):
        """Test mapping of NVIDIA sequential output files (video_000.mp4, etc.)."""
        # Create mock runs and prompts
        runs_and_prompts = [
            ({"id": "run_001"}, {"prompt_text": "prompt1"}),
            ({"id": "run_002"}, {"prompt_text": "prompt2"}),
            ({"id": "run_003"}, {"prompt_text": "prompt3"}),
        ]

        # Mock batch result with NVIDIA naming
        batch_result = {
            "output_files": [
                "/workspace/outputs/batch_123/video_000.mp4",
                "/workspace/outputs/batch_123/video_001.mp4",
                "/workspace/outputs/batch_123/video_002.mp4",
            ]
        }

        # Call the static method
        mapping = GPUExecutor._split_batch_outputs(runs_and_prompts, batch_result)

        # Verify correct mapping
        assert len(mapping) == 3
        assert mapping["run_001"]["remote_path"].endswith("video_000.mp4")
        assert mapping["run_001"]["status"] == "found"
        assert mapping["run_002"]["remote_path"].endswith("video_001.mp4")
        assert mapping["run_002"]["status"] == "found"
        assert mapping["run_003"]["remote_path"].endswith("video_002.mp4")
        assert mapping["run_003"]["status"] == "found"

    def test_fallback_sequential_matching(self):
        """Test fallback to sequential matching when pattern doesn't match."""
        runs_and_prompts = [
            ({"id": "run_001"}, {"prompt_text": "prompt1"}),
            ({"id": "run_002"}, {"prompt_text": "prompt2"}),
        ]

        # Output files with non-standard naming
        batch_result = {
            "output_files": [
                "/workspace/outputs/batch_123/output_a.mp4",
                "/workspace/outputs/batch_123/output_b.mp4",
            ]
        }

        mapping = GPUExecutor._split_batch_outputs(runs_and_prompts, batch_result)

        # Should use fallback sequential matching
        assert mapping["run_001"]["remote_path"].endswith("output_a.mp4")
        assert mapping["run_001"]["status"] == "assumed"
        assert mapping["run_002"]["remote_path"].endswith("output_b.mp4")
        assert mapping["run_002"]["status"] == "assumed"

    def test_missing_outputs(self):
        """Test handling when some outputs are missing."""
        runs_and_prompts = [
            ({"id": "run_001"}, {"prompt_text": "prompt1"}),
            ({"id": "run_002"}, {"prompt_text": "prompt2"}),
            ({"id": "run_003"}, {"prompt_text": "prompt3"}),
        ]

        # Only 2 output files for 3 runs
        batch_result = {
            "output_files": [
                "/workspace/outputs/batch_123/video_000.mp4",
                "/workspace/outputs/batch_123/video_001.mp4",
            ]
        }

        mapping = GPUExecutor._split_batch_outputs(runs_and_prompts, batch_result)

        # First two should match, third should be missing
        assert mapping["run_001"]["status"] == "found"
        assert mapping["run_002"]["status"] == "found"
        assert mapping["run_003"]["status"] == "missing"
        assert mapping["run_003"]["remote_path"] is None

    def test_run_id_in_filename(self):
        """Test matching when run_id is in the filename."""
        runs_and_prompts = [
            ({"id": "run_abc123"}, {"prompt_text": "prompt1"}),
            ({"id": "run_def456"}, {"prompt_text": "prompt2"}),
        ]

        # Output files with run_id in name
        batch_result = {
            "output_files": [
                "/workspace/outputs/batch_123/video_run_def456.mp4",
                "/workspace/outputs/batch_123/video_run_abc123.mp4",
            ]
        }

        mapping = GPUExecutor._split_batch_outputs(runs_and_prompts, batch_result)

        # Should match by run_id even if out of order
        assert mapping["run_abc123"]["remote_path"].endswith("video_run_abc123.mp4")
        assert mapping["run_abc123"]["status"] == "found"
        assert mapping["run_def456"]["remote_path"].endswith("video_run_def456.mp4")
        assert mapping["run_def456"]["status"] == "found"

    def test_mixed_naming_patterns(self):
        """Test handling mixed naming patterns."""
        runs_and_prompts = [
            ({"id": "run_001"}, {"prompt_text": "prompt1"}),
            ({"id": "run_002"}, {"prompt_text": "prompt2"}),
            ({"id": "run_003"}, {"prompt_text": "prompt3"}),
        ]

        # Mix of NVIDIA and custom naming
        batch_result = {
            "output_files": [
                "/workspace/outputs/batch_123/video_000.mp4",  # NVIDIA format
                "/workspace/outputs/batch_123/custom_output.mp4",  # Custom
                "/workspace/outputs/batch_123/video_run_003.mp4",  # Has run_id
            ]
        }

        mapping = GPUExecutor._split_batch_outputs(runs_and_prompts, batch_result)

        # First should match NVIDIA pattern
        assert mapping["run_001"]["remote_path"].endswith("video_000.mp4")
        assert mapping["run_001"]["status"] == "found"

        # Third should match by run_id
        assert mapping["run_003"]["remote_path"].endswith("video_run_003.mp4")
        assert mapping["run_003"]["status"] == "found"

        # Second gets the remaining file via fallback
        assert mapping["run_002"]["remote_path"].endswith("custom_output.mp4")
        assert mapping["run_002"]["status"] == "assumed"
