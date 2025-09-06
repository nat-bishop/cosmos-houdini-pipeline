"""Test batch inference functions in nvidia_format module.

Tests the conversion of multiple runs/prompts to JSONL format
and file writing utilities for batch processing.
"""

import json
import tempfile
from pathlib import Path

from cosmos_workflow.utils import nvidia_format


class TestBatchInferenceJsonl:
    """Test to_cosmos_batch_inference_jsonl function."""

    def test_converts_multiple_runs_to_jsonl_format(self):
        """Test converting multiple run/prompt pairs to JSONL format."""
        # Arrange
        runs_and_prompts = [
            (
                {
                    "id": "rs_001",
                    "execution_config": {
                        "weights": {"vis": 0.3, "edge": 0.2, "depth": 0.25, "seg": 0.25}
                    },
                },
                {
                    "id": "ps_001",
                    "prompt_text": "A futuristic city",
                    "inputs": {"video": "inputs/videos/city/color.mp4"},
                },
            ),
            (
                {
                    "id": "rs_002",
                    "execution_config": {
                        "weights": {"vis": 0.5, "edge": 0.5, "depth": 0.0, "seg": 0.0}
                    },
                },
                {
                    "id": "ps_002",
                    "prompt_text": "A serene landscape",
                    "inputs": {
                        "video": "inputs/videos/landscape/color.mp4",
                        "depth": "inputs/videos/landscape/depth.mp4",
                    },
                },
            ),
        ]

        # Act
        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        # Assert
        assert len(result) == 2

        # First entry
        first = result[0]
        assert first["visual_input"] == "inputs/videos/city/color.mp4"
        assert first["prompt"] == "A futuristic city"
        assert "control_overrides" in first
        assert first["control_overrides"]["vis"]["control_weight"] == 0.3
        assert first["control_overrides"]["edge"]["control_weight"] == 0.2
        assert first["_run_id"] == "rs_001"
        assert first["_prompt_id"] == "ps_001"

        # Second entry with depth
        second = result[1]
        assert second["visual_input"] == "inputs/videos/landscape/color.mp4"
        assert second["prompt"] == "A serene landscape"
        assert second["control_overrides"]["vis"]["control_weight"] == 0.5
        # Depth weight is 0, should not be included
        assert "depth" not in second["control_overrides"]
        assert "seg" not in second["control_overrides"]

    def test_handles_windows_to_unix_path_conversion(self):
        """Test that Windows paths are converted to Unix paths."""
        runs_and_prompts = [
            (
                {"id": "rs_001", "execution_config": {"weights": {"vis": 0.25}}},
                {
                    "id": "ps_001",
                    "prompt_text": "Test prompt",
                    "inputs": {
                        "video": "C:\\Users\\test\\videos\\color.mp4",
                        "depth": "D:\\data\\depth\\video.mp4",
                    },
                },
            )
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        assert result[0]["visual_input"] == "C:/Users/test/videos/color.mp4"
        # Depth with 0 weight won't be included by default

    def test_handles_optional_depth_and_seg_videos(self):
        """Test handling of optional depth and segmentation videos."""
        runs_and_prompts = [
            (
                {
                    "id": "rs_001",
                    "execution_config": {
                        "weights": {"vis": 0.2, "edge": 0.2, "depth": 0.3, "seg": 0.3}
                    },
                },
                {
                    "id": "ps_001",
                    "prompt_text": "Test with all videos",
                    "inputs": {
                        "video": "inputs/color.mp4",
                        "depth": "inputs/depth.mp4",
                        "seg": "inputs/seg.mp4",
                    },
                },
            ),
            (
                {
                    "id": "rs_002",
                    "execution_config": {
                        "weights": {"vis": 0.5, "edge": 0.5, "depth": 0.0, "seg": 0.0}
                    },
                },
                {
                    "id": "ps_002",
                    "prompt_text": "Test with only color",
                    "inputs": {"video": "inputs/color_only.mp4"},
                },
            ),
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        # First has all controls
        first = result[0]
        assert "depth" in first["control_overrides"]
        assert first["control_overrides"]["depth"]["input_control"] == "inputs/depth.mp4"
        assert first["control_overrides"]["depth"]["control_weight"] == 0.3
        assert "seg" in first["control_overrides"]
        assert first["control_overrides"]["seg"]["input_control"] == "inputs/seg.mp4"

        # Second has only vis and edge (non-zero weights)
        second = result[1]
        assert "vis" in second["control_overrides"]
        assert "edge" in second["control_overrides"]
        assert "depth" not in second["control_overrides"]  # Zero weight
        assert "seg" not in second["control_overrides"]  # Zero weight

    def test_auto_generates_depth_seg_when_no_input_provided(self):
        """Test that depth/seg are auto-generated (null) when weight > 0 but no input."""
        runs_and_prompts = [
            (
                {
                    "id": "rs_001",
                    "execution_config": {
                        "weights": {"vis": 0.2, "edge": 0.2, "depth": 0.3, "seg": 0.3}
                    },
                },
                {
                    "id": "ps_001",
                    "prompt_text": "Auto-generate controls",
                    "inputs": {"video": "inputs/color.mp4"},  # No depth or seg provided
                },
            )
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        # Should have depth and seg with null input_control for auto-generation
        assert result[0]["control_overrides"]["depth"]["input_control"] is None
        assert result[0]["control_overrides"]["depth"]["control_weight"] == 0.3
        assert result[0]["control_overrides"]["seg"]["input_control"] is None
        assert result[0]["control_overrides"]["seg"]["control_weight"] == 0.3

    def test_excludes_zero_weight_controls(self):
        """Test that controls with zero weight are excluded."""
        runs_and_prompts = [
            (
                {
                    "id": "rs_001",
                    "execution_config": {
                        "weights": {"vis": 0.0, "edge": 0.5, "depth": 0.0, "seg": 0.5}
                    },
                },
                {
                    "id": "ps_001",
                    "prompt_text": "Selective controls",
                    "inputs": {"video": "inputs/color.mp4"},
                },
            )
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        # Only edge and seg should be included
        assert "vis" not in result[0]["control_overrides"]
        assert "edge" in result[0]["control_overrides"]
        assert "depth" not in result[0]["control_overrides"]
        assert "seg" in result[0]["control_overrides"]

    def test_handles_empty_batch(self):
        """Test handling of empty batch."""
        result = nvidia_format.to_cosmos_batch_inference_jsonl([])
        assert result == []

    def test_handles_single_item_batch(self):
        """Test handling of single item batch."""
        runs_and_prompts = [
            (
                {"id": "rs_001", "execution_config": {"weights": {"vis": 1.0}}},
                {
                    "id": "ps_001",
                    "prompt_text": "Single item",
                    "inputs": {"video": "input.mp4"},
                },
            )
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        assert len(result) == 1
        assert result[0]["prompt"] == "Single item"

    def test_preserves_metadata_fields(self):
        """Test that metadata fields are preserved for tracking."""
        runs_and_prompts = [
            (
                {"id": "rs_abc123", "execution_config": {"weights": {}}},
                {"id": "ps_xyz789", "prompt_text": "Test", "inputs": {"video": "test.mp4"}},
            )
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        assert result[0]["_run_id"] == "rs_abc123"
        assert result[0]["_prompt_id"] == "ps_xyz789"

    def test_handles_very_long_prompts(self):
        """Test handling of very long prompts (>1000 chars)."""
        long_prompt = "A " * 600  # 1200 characters
        runs_and_prompts = [
            (
                {"id": "rs_001", "execution_config": {"weights": {"vis": 0.5}}},
                {
                    "id": "ps_001",
                    "prompt_text": long_prompt,
                    "inputs": {"video": "input.mp4"},
                },
            )
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        assert result[0]["prompt"] == long_prompt
        assert len(result[0]["prompt"]) > 1000

    def test_handles_unicode_in_prompts(self):
        """Test handling of Unicode characters in prompts."""
        unicode_prompt = "A beautiful 日本 landscape with 🌸 cherry blossoms"
        runs_and_prompts = [
            (
                {"id": "rs_001", "execution_config": {"weights": {"vis": 0.5}}},
                {
                    "id": "ps_001",
                    "prompt_text": unicode_prompt,
                    "inputs": {"video": "input.mp4"},
                },
            )
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        assert result[0]["prompt"] == unicode_prompt

    def test_handles_missing_execution_config(self):
        """Test handling when execution_config is missing or incomplete."""
        runs_and_prompts = [
            (
                {"id": "rs_001"},  # No execution_config
                {
                    "id": "ps_001",
                    "prompt_text": "Test",
                    "inputs": {"video": "input.mp4"},
                },
            ),
            (
                {"id": "rs_002", "execution_config": {}},  # Empty execution_config
                {
                    "id": "ps_002",
                    "prompt_text": "Test 2",
                    "inputs": {"video": "input2.mp4"},
                },
            ),
        ]

        result = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        # Should handle gracefully without crashing
        assert len(result) == 2
        assert result[0]["prompt"] == "Test"
        assert result[1]["prompt"] == "Test 2"


class TestWriteBatchJsonl:
    """Test write_batch_jsonl function."""

    def test_writes_valid_jsonl_file(self):
        """Test that a valid JSONL file is written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "batch.jsonl"

            batch_data = [
                {
                    "visual_input": "video1.mp4",
                    "prompt": "First prompt",
                    "control_overrides": {"vis": {"control_weight": 0.5}},
                    "_run_id": "rs_001",
                },
                {
                    "visual_input": "video2.mp4",
                    "prompt": "Second prompt",
                    "_run_id": "rs_002",
                },
            ]

            result_path = nvidia_format.write_batch_jsonl(batch_data, output_path)

            # Verify file was created
            assert result_path.exists()
            assert result_path == output_path

            # Verify content is valid JSONL
            with open(result_path) as f:
                lines = f.readlines()

            assert len(lines) == 2

            # Each line should be valid JSON
            first_line = json.loads(lines[0])
            assert first_line["visual_input"] == "video1.mp4"
            assert first_line["prompt"] == "First prompt"
            assert "_run_id" not in first_line  # Metadata should be stripped

            second_line = json.loads(lines[1])
            assert second_line["visual_input"] == "video2.mp4"
            assert "_run_id" not in second_line

    def test_creates_parent_directories(self):
        """Test that parent directories are created if they don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "nested" / "dirs" / "batch.jsonl"

            batch_data = [{"visual_input": "test.mp4", "prompt": "Test"}]

            result_path = nvidia_format.write_batch_jsonl(batch_data, output_path)

            assert result_path.exists()
            assert result_path.parent.exists()

    def test_overwrites_existing_file(self):
        """Test that existing files are overwritten."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "batch.jsonl"

            # Write initial file
            output_path.write_text("old content\n")

            batch_data = [{"visual_input": "new.mp4", "prompt": "New content"}]

            nvidia_format.write_batch_jsonl(batch_data, output_path)

            # Verify old content is gone
            with open(output_path) as f:
                content = f.read()

            assert "old content" not in content
            assert "New content" in content

    def test_strips_internal_metadata_fields(self):
        """Test that fields starting with underscore are removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "batch.jsonl"

            batch_data = [
                {
                    "visual_input": "video.mp4",
                    "prompt": "Test",
                    "_run_id": "should_be_removed",
                    "_prompt_id": "also_removed",
                    "_internal": "not_in_output",
                    "normal_field": "should_remain",
                }
            ]

            nvidia_format.write_batch_jsonl(batch_data, output_path)

            with open(output_path) as f:
                line = json.loads(f.readline())

            assert "_run_id" not in line
            assert "_prompt_id" not in line
            assert "_internal" not in line
            assert "normal_field" in line
            assert line["normal_field"] == "should_remain"

    def test_handles_empty_batch(self):
        """Test writing empty batch creates empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "empty.jsonl"

            nvidia_format.write_batch_jsonl([], output_path)

            assert output_path.exists()
            assert output_path.stat().st_size == 0

    def test_handles_special_characters_in_json(self):
        """Test that special characters are properly escaped in JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "special.jsonl"

            batch_data = [
                {
                    "visual_input": "path/with spaces/video.mp4",
                    "prompt": 'Prompt with "quotes" and \nnewlines\tand tabs',
                }
            ]

            nvidia_format.write_batch_jsonl(batch_data, output_path)

            # Should be able to read back as valid JSON
            with open(output_path) as f:
                line = json.loads(f.readline())

            assert line["visual_input"] == "path/with spaces/video.mp4"
            assert '"quotes"' in line["prompt"]
            assert "\n" in line["prompt"]
            assert "\t" in line["prompt"]
