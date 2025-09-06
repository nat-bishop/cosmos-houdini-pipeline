"""Behavioral tests for CLI batch inference command.

These tests define the CLI contract for the batch-inference command.
Implementation-agnostic - tests behavior, not storage mechanism.
Following TDD Gate 1: Write tests first.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli import cli


class TestBatchInferenceCommand:
    """Test the 'cosmos batch-inference' command behavior."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_with_multiple_runs(
        self, mock_get_service, mock_get_orchestrator, runner
    ):
        """Test batch inference with multiple run IDs."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data - 3 runs
        runs = [
            {
                "id": "rs_001",
                "prompt_id": "ps_001",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {
                    "weights": {"vis": 0.3, "edge": 0.2, "depth": 0.25, "seg": 0.25}
                },
            },
            {
                "id": "rs_002",
                "prompt_id": "ps_002",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {
                    "weights": {"vis": 0.5, "edge": 0.5, "depth": 0.0, "seg": 0.0}
                },
            },
            {
                "id": "rs_003",
                "prompt_id": "ps_003",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {},
            },
        ]

        prompts = [
            {
                "id": "ps_001",
                "prompt_text": "A futuristic city",
                "inputs": {"video": "/test/video1.mp4"},
            },
            {
                "id": "ps_002",
                "prompt_text": "A serene landscape",
                "inputs": {"video": "/test/video2.mp4", "depth": "/test/depth2.mp4"},
            },
            {
                "id": "ps_003",
                "prompt_text": "An abstract pattern",
                "inputs": {"video": "/test/video3.mp4"},
            },
        ]

        # Setup mock returns
        def get_run_side_effect(run_id):
            for run in runs:
                if run["id"] == run_id:
                    return run
            return None

        def get_prompt_side_effect(prompt_id):
            for prompt in prompts:
                if prompt["id"] == prompt_id:
                    return prompt
            return None

        mock_service.get_run.side_effect = get_run_side_effect
        mock_service.get_prompt.side_effect = get_prompt_side_effect

        # Mock batch execution result
        mock_orchestrator.execute_batch_runs.return_value = {
            "status": "success",
            "batch_name": "batch_20240101_120000",
            "num_runs": 3,
            "outputs": {
                "rs_001": "/output/batch_20240101_120000/rs_001/video.mp4",
                "rs_002": "/output/batch_20240101_120000/rs_002/video.mp4",
                "rs_003": "/output/batch_20240101_120000/rs_003/video.mp4",
            },
        }

        # Run command
        result = runner.invoke(cli, ["batch-inference", "rs_001", "rs_002", "rs_003"])

        # Behavioral assertions
        assert result.exit_code == 0
        assert "batch" in result.output.lower()
        assert "3 runs" in result.output.lower() or "3" in result.output

        # Should have called orchestrator with runs and prompts
        mock_orchestrator.execute_batch_runs.assert_called_once()
        call_args = mock_orchestrator.execute_batch_runs.call_args[0][0]
        assert len(call_args) == 3  # 3 run/prompt pairs

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_single_run(self, mock_get_service, mock_get_orchestrator, runner):
        """Test batch inference with single run ID (should still work)."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data - single run
        run = {
            "id": "rs_single",
            "prompt_id": "ps_single",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt = {
            "id": "ps_single",
            "prompt_text": "A single test",
            "inputs": {"video": "/test/single.mp4"},
        }

        mock_service.get_run.return_value = run
        mock_service.get_prompt.return_value = prompt
        mock_orchestrator.execute_batch_runs.return_value = {
            "status": "success",
            "batch_name": "batch_20240101_120000",
            "num_runs": 1,
            "outputs": {"rs_single": "/output/batch_20240101_120000/rs_single/video.mp4"},
        }

        # Run command with single run
        result = runner.invoke(cli, ["batch-inference", "rs_single"])

        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()

        # Should have called orchestrator
        mock_orchestrator.execute_batch_runs.assert_called_once()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_with_gpu_options(
        self, mock_get_service, mock_get_orchestrator, runner
    ):
        """Test batch inference with GPU configuration options."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        run = {
            "id": "rs_gpu",
            "prompt_id": "ps_gpu",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt = {"id": "ps_gpu", "prompt_text": "GPU test", "inputs": {"video": "/test/gpu.mp4"}}

        mock_service.get_run.return_value = run
        mock_service.get_prompt.return_value = prompt
        mock_orchestrator.execute_batch_runs.return_value = {
            "status": "success",
            "batch_name": "batch_20240101_120000",
            "num_runs": 1,
        }

        # Run command with GPU options
        result = runner.invoke(
            cli, ["batch-inference", "rs_gpu", "--num-gpu", "2", "--cuda-devices", "0,1"]
        )

        assert result.exit_code == 0

        # Should pass GPU options to orchestrator
        mock_orchestrator.execute_batch_runs.assert_called_once()
        call_kwargs = mock_orchestrator.execute_batch_runs.call_args[1]
        assert call_kwargs.get("num_gpu") == 2
        assert call_kwargs.get("cuda_devices") == "0,1"

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_with_batch_name(self, mock_get_service, mock_get_orchestrator, runner):
        """Test batch inference with custom batch name."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        run = {
            "id": "rs_named",
            "prompt_id": "ps_named",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {},
        }
        prompt = {
            "id": "ps_named",
            "prompt_text": "Named batch test",
            "inputs": {"video": "/test/named.mp4"},
        }

        mock_service.get_run.return_value = run
        mock_service.get_prompt.return_value = prompt
        mock_orchestrator.execute_batch_runs.return_value = {
            "status": "success",
            "batch_name": "my_custom_batch",
            "num_runs": 1,
        }

        # Run command with custom batch name
        result = runner.invoke(
            cli, ["batch-inference", "rs_named", "--batch-name", "my_custom_batch"]
        )

        assert result.exit_code == 0
        assert "my_custom_batch" in result.output

        # Should pass batch name to orchestrator
        call_kwargs = mock_orchestrator.execute_batch_runs.call_args[1]
        assert call_kwargs.get("batch_name") == "my_custom_batch"

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_run_not_found(self, mock_get_service, runner):
        """Test batch inference with non-existent run ID."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Setup mock to return None for non-existent run
        mock_service.get_run.return_value = None

        # Run command
        result = runner.invoke(cli, ["batch-inference", "rs_nonexistent"])

        # Should fail with error message
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_dry_run(self, mock_get_service, mock_get_orchestrator, runner):
        """Test batch inference with dry-run flag."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        runs = [
            {
                "id": "rs_dry1",
                "prompt_id": "ps_dry1",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {
                    "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
                },
            },
            {
                "id": "rs_dry2",
                "prompt_id": "ps_dry2",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {},
            },
        ]

        prompts = [
            {
                "id": "ps_dry1",
                "prompt_text": "Dry run test 1",
                "inputs": {"video": "/test/dry1.mp4"},
            },
            {
                "id": "ps_dry2",
                "prompt_text": "Dry run test 2",
                "inputs": {"video": "/test/dry2.mp4"},
            },
        ]

        def get_run_side_effect(run_id):
            for run in runs:
                if run["id"] == run_id:
                    return run
            return None

        def get_prompt_side_effect(prompt_id):
            for prompt in prompts:
                if prompt["id"] == prompt_id:
                    return prompt
            return None

        mock_service.get_run.side_effect = get_run_side_effect
        mock_service.get_prompt.side_effect = get_prompt_side_effect

        # Run command with dry-run
        result = runner.invoke(cli, ["batch-inference", "rs_dry1", "rs_dry2", "--dry-run"])

        assert result.exit_code == 0
        assert "dry run" in result.output.lower()
        assert "2 runs" in result.output.lower() or "rs_dry1" in result.output
        assert "would" in result.output.lower()

        # Should NOT execute anything in dry-run
        mock_orchestrator.execute_batch_runs.assert_not_called()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_updates_run_status(
        self, mock_get_service, mock_get_orchestrator, runner
    ):
        """Test that batch inference updates run statuses in database."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        runs = [
            {
                "id": "rs_status1",
                "prompt_id": "ps_status1",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {},
            },
            {
                "id": "rs_status2",
                "prompt_id": "ps_status2",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {},
            },
        ]

        prompts = [
            {
                "id": "ps_status1",
                "prompt_text": "Status test 1",
                "inputs": {"video": "/test/status1.mp4"},
            },
            {
                "id": "ps_status2",
                "prompt_text": "Status test 2",
                "inputs": {"video": "/test/status2.mp4"},
            },
        ]

        def get_run_side_effect(run_id):
            for run in runs:
                if run["id"] == run_id:
                    return run
            return None

        def get_prompt_side_effect(prompt_id):
            for prompt in prompts:
                if prompt["id"] == prompt_id:
                    return prompt
            return None

        mock_service.get_run.side_effect = get_run_side_effect
        mock_service.get_prompt.side_effect = get_prompt_side_effect

        mock_orchestrator.execute_batch_runs.return_value = {
            "status": "success",
            "batch_name": "batch_test",
            "num_runs": 2,
            "outputs": {
                "rs_status1": "/output/rs_status1/video.mp4",
                "rs_status2": "/output/rs_status2/video.mp4",
            },
        }

        # Run command
        result = runner.invoke(cli, ["batch-inference", "rs_status1", "rs_status2"])

        assert result.exit_code == 0

        # Should update statuses to running then completed
        expected_calls = []
        for run_id in ["rs_status1", "rs_status2"]:
            expected_calls.append(((run_id, "running"),))
            expected_calls.append(((run_id, "completed"),))

        # Check that status updates were called
        assert mock_service.update_run_status.call_count >= 2  # At least running and completed

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_handles_partial_failure(
        self, mock_get_service, mock_get_orchestrator, runner
    ):
        """Test batch inference handles partial failures gracefully."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        runs = [
            {
                "id": "rs_fail1",
                "prompt_id": "ps_fail1",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {},
            },
            {
                "id": "rs_fail2",
                "prompt_id": "ps_fail2",
                "status": "pending",
                "model_type": "transfer",
                "execution_config": {},
            },
        ]

        prompts = [
            {
                "id": "ps_fail1",
                "prompt_text": "Fail test 1",
                "inputs": {"video": "/test/fail1.mp4"},
            },
            {
                "id": "ps_fail2",
                "prompt_text": "Fail test 2",
                "inputs": {"video": "/test/fail2.mp4"},
            },
        ]

        def get_run_side_effect(run_id):
            for run in runs:
                if run["id"] == run_id:
                    return run
            return None

        def get_prompt_side_effect(prompt_id):
            for prompt in prompts:
                if prompt["id"] == prompt_id:
                    return prompt
            return None

        mock_service.get_run.side_effect = get_run_side_effect
        mock_service.get_prompt.side_effect = get_prompt_side_effect

        # Mock orchestrator to raise exception
        mock_orchestrator.execute_batch_runs.side_effect = Exception("GPU out of memory")

        # Run command
        result = runner.invoke(cli, ["batch-inference", "rs_fail1", "rs_fail2"])

        # Should fail but handle gracefully
        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()

        # Should update statuses to failed
        failed_calls = [
            call for call in mock_service.update_run_status.call_args_list if "failed" in str(call)
        ]
        assert len(failed_calls) >= 1

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_no_runs_provided(self, mock_get_service, runner):
        """Test batch inference with no run IDs provided."""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Run command with no run IDs
        result = runner.invoke(cli, ["batch-inference"])

        # Should fail with error message
        assert result.exit_code != 0
        assert "usage" in result.output.lower() or "missing" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_batch_inference_verbose_output(self, mock_get_service, mock_get_orchestrator, runner):
        """Test batch inference with verbose flag shows detailed output."""
        # Setup mocks
        mock_service = MagicMock()
        mock_orchestrator = MagicMock()

        mock_get_service.return_value = mock_service
        mock_get_orchestrator.return_value = mock_orchestrator

        # Setup test data
        run = {
            "id": "rs_verbose",
            "prompt_id": "ps_verbose",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {"weights": {"vis": 0.3, "edge": 0.2, "depth": 0.25, "seg": 0.25}},
        }
        prompt = {
            "id": "ps_verbose",
            "prompt_text": "Verbose test",
            "inputs": {"video": "/test/verbose.mp4"},
        }

        mock_service.get_run.return_value = run
        mock_service.get_prompt.return_value = prompt
        mock_orchestrator.execute_batch_runs.return_value = {
            "status": "success",
            "batch_name": "batch_verbose",
            "num_runs": 1,
            "outputs": {"rs_verbose": "/output/rs_verbose/video.mp4"},
            "jsonl_path": "/tmp/batch_verbose.jsonl",
            "upload_time": 2.5,
            "execution_time": 120.3,
        }

        # Run command with verbose flag
        result = runner.invoke(cli, ["--verbose", "batch-inference", "rs_verbose"])

        assert result.exit_code == 0
        # Verbose output should include more details
        assert "batch_verbose" in result.output or "jsonl" in result.output.lower()
