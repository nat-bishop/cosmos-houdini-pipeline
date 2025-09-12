"""Tests for batch inference format generation."""

import json
from unittest.mock import MagicMock, patch

from cosmos_workflow.execution.gpu_executor import GPUExecutor
from cosmos_workflow.utils import nvidia_format


class TestBatchFormat:
    """Test batch inference JSONL format generation."""

    def test_batch_jsonl_format(self):
        """Test that batch inference uses JSONL format with control_overrides."""
        # Prepare test data
        runs_and_prompts = [
            (
                {
                    "id": "rs_001",
                    "execution_config": {
                        "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
                    },
                },
                {
                    "id": "ps_001",
                    "prompt_text": "A futuristic city",
                    "inputs": {"video": "test1.mp4"},
                },
            ),
            (
                {
                    "id": "rs_002",
                    "execution_config": {
                        "weights": {"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2}
                    },
                },
                {
                    "id": "ps_002",
                    "prompt_text": "An alien landscape",
                    "inputs": {"video": "test2.mp4", "depth": "depth2.mp4"},
                },
            ),
        ]

        # Generate JSONL
        batch_lines = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        # Verify we get correct number of lines
        assert len(batch_lines) == 2

        # Check first line structure
        line1 = batch_lines[0]
        assert "visual_input" in line1
        assert "prompt" in line1
        assert "control_overrides" in line1
        assert line1["visual_input"] == "inputs/videos/test1.mp4"
        assert line1["prompt"] == "A futuristic city"

        # Check control_overrides structure
        controls = line1["control_overrides"]
        assert "vis" in controls
        assert "edge" in controls
        assert controls["vis"]["control_weight"] == 0.25

        # Check second line has depth input
        line2 = batch_lines[1]
        assert "depth" in line2["control_overrides"]
        assert line2["control_overrides"]["depth"]["input_control"] == "inputs/videos/depth2.mp4"

    def test_batch_jsonl_write(self, tmp_path):
        """Test writing batch data as JSONL file."""
        batch_data = [
            {"visual_input": "video1.mp4", "prompt": "test1", "_run_id": "rs_001"},
            {"visual_input": "video2.mp4", "prompt": "test2", "_run_id": "rs_002"},
        ]

        output_file = tmp_path / "batch.jsonl"
        nvidia_format.write_batch_jsonl(batch_data, output_file)

        # Verify file exists and is JSONL format
        assert output_file.exists()

        # Read and verify JSONL format (one JSON per line)
        lines = output_file.read_text().strip().split("\n")
        assert len(lines) == 2

        # Parse each line as separate JSON
        for line in lines:
            data = json.loads(line)
            assert "visual_input" in data
            assert "prompt" in data
            # Metadata fields should be stripped
            assert "_run_id" not in data

    @patch("cosmos_workflow.execution.gpu_executor.nvidia_format")
    def test_gpu_executor_uses_jsonl(self, mock_nvidia_format, tmp_path):
        """Test that GPUExecutor creates JSONL files for batch inference."""
        # Setup mocks
        mock_nvidia_format.to_cosmos_batch_inference_jsonl.return_value = [
            {"visual_input": "test.mp4", "prompt": "test"}
        ]
        mock_nvidia_format.write_batch_jsonl.return_value = tmp_path / "batch.jsonl"

        # Create executor with mocked services
        executor = GPUExecutor()
        executor._services_initialized = True
        executor.ssh_manager = MagicMock()
        executor.ssh_manager.__enter__ = MagicMock(return_value=executor.ssh_manager)
        executor.ssh_manager.__exit__ = MagicMock(return_value=None)
        executor.file_transfer = MagicMock()
        executor.remote_executor = MagicMock()
        executor.docker_executor = MagicMock()
        executor.docker_executor.run_batch_inference.return_value = {
            "status": "started",
            "batch_name": "test_batch",
        }
        executor.config_manager = MagicMock()
        executor.config_manager.get_remote_config.return_value = MagicMock(remote_dir="/workspace")

        # Test data
        runs_and_prompts = [
            ({"id": "rs_001", "execution_config": {}}, {"id": "ps_001", "prompt_text": "test"})
        ]

        # Execute batch
        executor.execute_batch_runs(runs_and_prompts)

        # Verify JSONL functions were called
        mock_nvidia_format.to_cosmos_batch_inference_jsonl.assert_called_once_with(runs_and_prompts)
        mock_nvidia_format.write_batch_jsonl.assert_called_once()

        # Verify the file has .jsonl extension
        call_args = mock_nvidia_format.write_batch_jsonl.call_args
        batch_file = call_args[0][1]
        assert batch_file.name == "batch.jsonl"

    def test_control_overrides_structure(self):
        """Test control_overrides structure matches NVIDIA spec."""
        runs_and_prompts = [
            (
                {
                    "id": "rs_001",
                    "execution_config": {
                        "weights": {"vis": 0.0, "edge": 0.0, "depth": 0.5, "seg": 0.5}
                    },
                },
                {
                    "id": "ps_001",
                    "prompt_text": "test",
                    "inputs": {"video": "test.mp4", "seg": "seg.mp4"},
                },
            )
        ]

        batch_lines = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)
        line = batch_lines[0]

        # Verify only non-zero weights are included
        controls = line["control_overrides"]
        assert "vis" not in controls  # 0.0 weight
        assert "edge" not in controls  # 0.0 weight
        assert "depth" in controls  # 0.5 weight
        assert "seg" in controls  # 0.5 weight

        # Verify seg has input_control from provided file
        assert controls["seg"]["input_control"] == "inputs/videos/seg.mp4"
        assert controls["seg"]["control_weight"] == 0.5

        # Verify depth has null input_control (auto-generate)
        assert controls["depth"]["input_control"] is None
        assert controls["depth"]["control_weight"] == 0.5
