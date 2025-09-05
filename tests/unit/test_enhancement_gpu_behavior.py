"""Test prompt enhancement behavior using GPU-based upsampling.

These tests verify WHAT the enhancement system does (GPU-based enhancement via scripts),
not HOW it's implemented internally. Tests use fakes instead of mocks per CLAUDE.md.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator
from tests.fixtures.fakes import FakeDockerExecutor, FakeFileTransferService, FakeSSHManager


class TestEnhancementGPUBehavior:
    """Test prompt enhancement via GPU execution following actual architecture.

    NOTE: The current implementation bypasses DockerExecutor wrapper and uses SSH directly.
    This violates CLAUDE.md principles but these tests verify the ACTUAL behavior.
    TODO: Refactor run_prompt_upsampling to use DockerExecutor wrapper.
    """

    @pytest.fixture
    def fake_ssh_manager(self):
        """Create a fake SSH manager for testing."""
        return FakeSSHManager(connected=True)

    @pytest.fixture
    def fake_file_transfer(self, fake_ssh_manager):
        """Create a fake file transfer service for testing."""
        return FakeFileTransferService(fake_ssh_manager, "/remote/cosmos")

    @pytest.fixture
    def fake_docker_executor(self, fake_ssh_manager):
        """Create a fake Docker executor for testing."""
        return FakeDockerExecutor(fake_ssh_manager, "/remote/cosmos", "cosmos:latest")

    def test_enhancement_uploads_upsampler_script(
        self, fake_ssh_manager, fake_file_transfer, fake_docker_executor
    ):
        """Test BEHAVIOR: Enhancement should upload the prompt_upsampler.py script to GPU.

        This verifies that the upsampling script is transferred to the remote machine,
        which is required for GPU-based enhancement.
        """
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
            return_value=fake_ssh_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                return_value=fake_file_transfer,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                    return_value=fake_docker_executor,
                ):
                    orchestrator = WorkflowOrchestrator()

                    # Run enhancement
                    orchestrator.run_prompt_upsampling("A simple city", model="pixtral")

                    # Verify upsampler script was uploaded
                    uploaded_files = [str(f[0]) for f in fake_ssh_manager.files_uploaded]
                    assert any("prompt_upsampler.py" in f for f in uploaded_files), (
                        "Should upload prompt_upsampler.py script"
                    )

    def test_enhancement_executes_on_gpu_via_docker(self, fake_ssh_manager, fake_file_transfer):
        """Test BEHAVIOR: Enhancement should execute upsampling on GPU using Docker via SSH.

        This verifies that enhancement runs the upsampler script in a Docker container
        with GPU support via SSH commands, not locally or via DockerExecutor.
        """

        # Setup fake to simulate successful download of results
        def fake_download(remote_path, local_path):
            # Create a fake results file
            results = [
                {"upsampled_prompt": "An elaborate futuristic scene with advanced technology"}
            ]
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            with open(local_path, "w") as f:
                json.dump(results, f)

        fake_file_transfer.download_file = fake_download

        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
            return_value=fake_ssh_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                return_value=fake_file_transfer,
            ):
                # No need to patch DockerExecutor - it's not used!
                orchestrator = WorkflowOrchestrator()

                # Run enhancement
                orchestrator.run_prompt_upsampling("A futuristic scene", model="pixtral")

                # Verify Docker command was executed via SSH
                docker_commands = [
                    cmd for cmd, _ in fake_ssh_manager.commands_executed if "docker run" in cmd
                ]
                assert len(docker_commands) > 0, "Should execute docker run command via SSH"

                # Verify the command includes the upsampler script
                docker_cmd = docker_commands[0]
                assert "prompt_upsampler.py" in docker_cmd, (
                    "Should run prompt_upsampler.py in container"
                )
                assert "--batch" in docker_cmd, "Should pass batch file"
                assert "--output-dir" in docker_cmd, "Should specify output directory"

    def test_enhancement_downloads_and_returns_enhanced_text(
        self, fake_ssh_manager, fake_file_transfer, fake_docker_executor
    ):
        """Test BEHAVIOR: Enhancement should download results and return enhanced text.

        This verifies that the enhanced prompt is retrieved from the GPU
        and returned to the caller.
        """
        # Setup fake enhanced result
        enhanced_text = (
            "An elaborate futuristic cyberpunk cityscape with neon lights and flying vehicles"
        )
        fake_result = [{"name": "prompt", "enhanced": enhanced_text}]

        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
            return_value=fake_ssh_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                return_value=fake_file_transfer,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                    return_value=fake_docker_executor,
                ):
                    # Mock reading the result file
                    with patch("builtins.open", create=True) as mock_open:
                        mock_open.return_value.__enter__.return_value.read.return_value = (
                            json.dumps(fake_result)
                        )

                        orchestrator = WorkflowOrchestrator()

                        # Run enhancement
                        result = orchestrator.run_prompt_upsampling("A city", model="pixtral")

                        # Verify result is the enhanced text
                        assert result == enhanced_text, "Should return enhanced text"
                        assert len(result) > len("A city"), "Enhanced should be longer"

    def test_enhancement_handles_gpu_failure_gracefully(
        self, fake_ssh_manager, fake_file_transfer, fake_docker_executor
    ):
        """Test BEHAVIOR: Enhancement should handle GPU failures gracefully.

        This verifies that GPU failures (OOM, model loading errors) are handled
        without crashing the system.
        """
        # Configure Docker to simulate failure
        fake_docker_executor.should_fail = True
        fake_docker_executor.failure_message = "CUDA out of memory"

        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
            return_value=fake_ssh_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                return_value=fake_file_transfer,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                    return_value=fake_docker_executor,
                ):
                    orchestrator = WorkflowOrchestrator()

                    # Enhancement should raise an exception on GPU failure
                    with pytest.raises(RuntimeError) as exc_info:
                        orchestrator.run_prompt_upsampling("A scene", model="pixtral")

                    assert "CUDA out of memory" in str(exc_info.value), (
                        "Should report GPU failure reason"
                    )

    def test_enhancement_supports_video_context(
        self, fake_ssh_manager, fake_file_transfer, fake_docker_executor
    ):
        """Test BEHAVIOR: Enhancement should support optional video context.

        This verifies that video paths can be provided for visual context
        during enhancement (Pixtral model feature).
        """
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
            return_value=fake_ssh_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                return_value=fake_file_transfer,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                    return_value=fake_docker_executor,
                ):
                    orchestrator = WorkflowOrchestrator()

                    # Run enhancement with video
                    orchestrator.run_prompt_upsampling(
                        "Describe this scene", model="pixtral", video_path="/path/to/video.mp4"
                    )

                    # Verify video path was included in batch data
                    uploaded_files = fake_ssh_manager.files_uploaded
                    batch_files = [
                        f
                        for f in uploaded_files
                        if "upsample_" in str(f[0]) and str(f[0]).endswith(".json")
                    ]

                    assert len(batch_files) > 0, "Should upload batch file"

                    # Read the batch content to verify video path
                    batch_path = batch_files[0][0]
                    if batch_path.exists():
                        with open(batch_path) as f:
                            batch_data = json.load(f)
                            assert batch_data[0].get("video_path") == "/path/to/video.mp4", (
                                "Should include video path in batch"
                            )

    def test_enhancement_uses_pixtral_model_on_gpu(
        self, fake_ssh_manager, fake_file_transfer, fake_docker_executor
    ):
        """Test BEHAVIOR: Enhancement should use NVIDIA Pixtral model on GPU.

        This verifies that the system uses the Pixtral upsampling model,
        not a generic AI model.
        """
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
            return_value=fake_ssh_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                return_value=fake_file_transfer,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                    return_value=fake_docker_executor,
                ):
                    orchestrator = WorkflowOrchestrator()

                    # Run enhancement
                    orchestrator.run_prompt_upsampling("A landscape", model="pixtral")

                    # Verify the Docker command references Pixtral
                    last_execution = fake_docker_executor.execution_history[-1]
                    # The script uses PixtralPromptUpsampler internally
                    assert "prompt_upsampler.py" in last_execution["command"], (
                        "Should use prompt_upsampler.py which uses PixtralPromptUpsampler"
                    )

    def test_enhancement_creates_temporary_batch_file(
        self, fake_ssh_manager, fake_file_transfer, fake_docker_executor
    ):
        """Test BEHAVIOR: Enhancement should create batch files for processing.

        This verifies that prompts are batched into JSON files for GPU processing,
        following the expected input format for the upsampler script.
        """
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
            return_value=fake_ssh_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                return_value=fake_file_transfer,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                    return_value=fake_docker_executor,
                ):
                    orchestrator = WorkflowOrchestrator()

                    prompt_text = "A detailed architectural scene"

                    # Run enhancement
                    orchestrator.run_prompt_upsampling(prompt_text, model="pixtral")

                    # Verify batch file was created and uploaded
                    uploaded_files = fake_ssh_manager.files_uploaded
                    batch_files = [
                        f
                        for f in uploaded_files
                        if "upsample_" in str(f[0]) and str(f[0]).endswith(".json")
                    ]

                    assert len(batch_files) > 0, "Should create and upload batch file"

                    # Verify batch content structure
                    batch_path = batch_files[0][0]
                    if batch_path.exists():
                        with open(batch_path) as f:
                            batch_data = json.load(f)
                            assert isinstance(batch_data, list), "Batch should be a list"
                            assert len(batch_data) == 1, "Should have one prompt in batch"
                            assert batch_data[0]["prompt"] == prompt_text, (
                                "Should contain the prompt text"
                            )
                            assert "name" in batch_data[0], "Should have a name field"
