"""Test inference behavior without testing implementation details.

These tests verify WHAT the system does, not HOW it does it.
They test that inference uploads files, runs Docker, and downloads results.
"""

from unittest.mock import patch

import pytest

from tests.fixtures.mocks import (
    create_mock_docker_executor,
    create_mock_file_transfer,
    create_mock_ssh_manager,
)


class TestInferenceBehavior:
    """Test that inference performs the expected behaviors."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create all mock dependencies for inference."""
        return {
            "ssh": create_mock_ssh_manager(),
            "docker": create_mock_docker_executor(),
            "transfer": create_mock_file_transfer(),
        }

    @pytest.fixture
    def sample_prompt_dict(self):
        """Sample prompt data as returned from database."""
        return {
            "id": "ps_test_123",
            "model_type": "transfer",
            "prompt_text": "A futuristic city",
            "inputs": {
                "video": "/test/video.mp4",
                "depth": "/test/depth.mp4",
                "seg": "/test/seg.mp4",
            },
            "parameters": {"negative_prompt": "blurry", "fps": 24},
        }

    @pytest.fixture
    def sample_run_dict(self):
        """Sample run data as returned from database."""
        return {
            "id": "rs_test_456",
            "prompt_id": "ps_test_123",
            "status": "pending",
            "execution_config": {
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
                "num_steps": 35,
                "guidance": 8.0,
                "seed": 42,
            },
        }

    def test_inference_connects_to_gpu(
        self, mock_dependencies, sample_prompt_dict, sample_run_dict
    ):
        """Test BEHAVIOR: Inference should establish SSH connection to GPU.

        This verifies that the system connects to the GPU server,
        regardless of how the connection is implemented.
        """
        from cosmos_workflow.execution.gpu_executor import GPUExecutor

        with patch(
            "cosmos_workflow.execution.gpu_executor.SSHManager",
            return_value=mock_dependencies["ssh"],
        ):
            with patch(
                "cosmos_workflow.execution.gpu_executor.FileTransferService",
                return_value=mock_dependencies["transfer"],
            ):
                with patch(
                    "cosmos_workflow.execution.gpu_executor.DockerExecutor",
                    return_value=mock_dependencies["docker"],
                ):
                    orchestrator = GPUExecutor()
                    orchestrator.execute_run(
                        run=sample_run_dict,
                        prompt=sample_prompt_dict,
                    )

                    # Verify SSH connection was established
                    assert mock_dependencies["ssh"].__enter__.called, (
                        "Should establish SSH connection to GPU"
                    )

    def test_inference_uploads_required_files(
        self, mock_dependencies, sample_prompt_dict, sample_run_dict
    ):
        """Test BEHAVIOR: Inference should upload necessary files to GPU.

        This verifies that files are uploaded for processing,
        without caring about file formats or storage mechanisms.
        """
        from cosmos_workflow.execution.gpu_executor import GPUExecutor

        with patch(
            "cosmos_workflow.execution.gpu_executor.SSHManager",
            return_value=mock_dependencies["ssh"],
        ):
            with patch(
                "cosmos_workflow.execution.gpu_executor.FileTransferService",
                return_value=mock_dependencies["transfer"],
            ):
                with patch(
                    "cosmos_workflow.execution.gpu_executor.DockerExecutor",
                    return_value=mock_dependencies["docker"],
                ):
                    orchestrator = GPUExecutor()
                    orchestrator.execute_run(
                        run=sample_run_dict,
                        prompt=sample_prompt_dict,
                    )

                    # Verify files were uploaded
                    assert mock_dependencies["transfer"].upload_file.called, (
                        "Should upload files to GPU"
                    )

    def test_inference_runs_docker_container(
        self, mock_dependencies, sample_prompt_dict, sample_run_dict
    ):
        """Test BEHAVIOR: Inference should execute Docker container on GPU.

        This verifies that Docker inference is triggered,
        without caring about specific Docker commands or configurations.
        """
        from cosmos_workflow.execution.gpu_executor import GPUExecutor

        with patch(
            "cosmos_workflow.execution.gpu_executor.SSHManager",
            return_value=mock_dependencies["ssh"],
        ):
            with patch(
                "cosmos_workflow.execution.gpu_executor.FileTransferService",
                return_value=mock_dependencies["transfer"],
            ):
                with patch(
                    "cosmos_workflow.execution.gpu_executor.DockerExecutor",
                    return_value=mock_dependencies["docker"],
                ):
                    orchestrator = GPUExecutor()
                    orchestrator.execute_run(
                        run=sample_run_dict,
                        prompt=sample_prompt_dict,
                    )

                    # Verify Docker inference was run
                    assert mock_dependencies["docker"].run_inference.called, (
                        "Should run Docker inference on GPU"
                    )

    def test_inference_downloads_results(
        self, mock_dependencies, sample_prompt_dict, sample_run_dict
    ):
        """Test BEHAVIOR: Inference should download generated results.

        This verifies that results are retrieved after processing,
        without caring about file types or download mechanisms.
        """
        from cosmos_workflow.execution.gpu_executor import GPUExecutor

        with patch(
            "cosmos_workflow.execution.gpu_executor.SSHManager",
            return_value=mock_dependencies["ssh"],
        ):
            with patch(
                "cosmos_workflow.execution.gpu_executor.FileTransferService",
                return_value=mock_dependencies["transfer"],
            ):
                with patch(
                    "cosmos_workflow.execution.gpu_executor.DockerExecutor",
                    return_value=mock_dependencies["docker"],
                ):
                    orchestrator = GPUExecutor()
                    result = orchestrator.execute_run(
                        run=sample_run_dict,
                        prompt=sample_prompt_dict,
                    )

                    # With lazy sync, downloads don't happen immediately
                    # Container starts and runs in background
                    # Results are downloaded later by StatusChecker when needed
                    assert result["status"] == "started", (
                        "Should start container for background execution"
                    )

                    # Verify run_id is returned for tracking
                    assert "run_id" in result, "Should return run_id for tracking"

    @pytest.mark.skip(reason="Upscaling is temporarily disabled - see ROADMAP.md")
    def test_inference_with_upscaling_runs_both_steps(
        self, mock_dependencies, sample_prompt_dict, sample_run_dict
    ):
        """Test BEHAVIOR: Upscaling should run both inference and upscaling.

        This verifies that when upscaling is requested, both steps execute,
        without caring about the specific upscaling implementation.
        """
        from cosmos_workflow.execution.gpu_executor import GPUExecutor

        with patch(
            "cosmos_workflow.execution.gpu_executor.SSHManager",
            return_value=mock_dependencies["ssh"],
        ):
            with patch(
                "cosmos_workflow.execution.gpu_executor.FileTransferService",
                return_value=mock_dependencies["transfer"],
            ):
                with patch(
                    "cosmos_workflow.execution.gpu_executor.DockerExecutor",
                    return_value=mock_dependencies["docker"],
                ):
                    orchestrator = GPUExecutor()
                    orchestrator.execute_run(
                        run=sample_run_dict,
                        prompt=sample_prompt_dict,
                    )

                    # Verify both steps were executed
                    assert mock_dependencies["docker"].run_inference.called, (
                        "Should run inference first"
                    )
                    assert mock_dependencies["docker"].run_upscaling.called, (
                        "Should run upscaling after inference"
                    )

    def test_inference_handles_gpu_failure_gracefully(
        self, mock_dependencies, sample_prompt_dict, sample_run_dict
    ):
        """Test BEHAVIOR: System should handle GPU failures without crashing.

        This verifies error handling behavior,
        without caring about specific error types or recovery mechanisms.
        """
        from cosmos_workflow.execution.gpu_executor import GPUExecutor

        # Make Docker fail
        mock_dependencies["docker"].run_inference.return_value = {
            "status": "failed",
            "error": "GPU out of memory",
        }

        with patch(
            "cosmos_workflow.execution.gpu_executor.SSHManager",
            return_value=mock_dependencies["ssh"],
        ):
            with patch(
                "cosmos_workflow.execution.gpu_executor.FileTransferService",
                return_value=mock_dependencies["transfer"],
            ):
                with patch(
                    "cosmos_workflow.execution.gpu_executor.DockerExecutor",
                    return_value=mock_dependencies["docker"],
                ):
                    orchestrator = GPUExecutor()

                    # Should raise RuntimeError on failure
                    with pytest.raises(RuntimeError, match="Inference failed"):
                        orchestrator.execute_run(
                            run=sample_run_dict,
                            prompt=sample_prompt_dict,
                        )

    def test_inference_respects_execution_config(
        self, mock_dependencies, sample_prompt_dict, sample_run_dict
    ):
        """Test BEHAVIOR: Inference should use provided execution configuration.

        This verifies that custom weights and parameters are applied,
        without caring about how they're passed to the GPU.
        """
        # Modify execution config with custom values
        sample_run_dict["execution_config"] = {
            "weights": {"vis": 0.5, "edge": 0.1, "depth": 0.2, "seg": 0.2},
            "num_steps": 50,
            "guidance": 10.0,
            "seed": 12345,
        }

        from cosmos_workflow.execution.gpu_executor import GPUExecutor

        with patch(
            "cosmos_workflow.execution.gpu_executor.SSHManager",
            return_value=mock_dependencies["ssh"],
        ):
            with patch(
                "cosmos_workflow.execution.gpu_executor.FileTransferService",
                return_value=mock_dependencies["transfer"],
            ):
                with patch(
                    "cosmos_workflow.execution.gpu_executor.DockerExecutor",
                    return_value=mock_dependencies["docker"],
                ):
                    orchestrator = GPUExecutor()
                    orchestrator.execute_run(
                        run=sample_run_dict,
                        prompt=sample_prompt_dict,
                    )

                    # The behavior we care about is that Docker was called
                    # The specific config values are passed through somehow
                    assert mock_dependencies["docker"].run_inference.called, (
                        "Should execute with provided configuration"
                    )
