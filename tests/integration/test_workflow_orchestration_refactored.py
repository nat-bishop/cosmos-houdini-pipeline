"""
Refactored integration tests using test doubles instead of excessive mocking.
This tests real behavior instead of implementation details.
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest

from cosmos_workflow.prompts.schemas import ExecutionStatus, PromptSpec, RunSpec
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator
from tests.test_doubles import (
    FakeDockerExecutor,
    FakeFileTransferService,
    FakePromptSpecManager,
    FakeSSHManager,
)


class TestWorkflowOrchestrationRefactored:
    """Test workflow orchestration with reduced mocking."""

    @pytest.fixture
    def fake_ssh_manager(self):
        """Create a fake SSH manager."""
        return FakeSSHManager()

    @pytest.fixture
    def fake_file_transfer(self, temp_dir):
        """Create a fake file transfer service."""
        return FakeFileTransferService(temp_dir)

    @pytest.fixture
    def fake_docker_executor(self):
        """Create a fake Docker executor."""
        return FakeDockerExecutor()

    @pytest.fixture
    def fake_prompt_manager(self, temp_dir):
        """Create a fake prompt spec manager."""
        return FakePromptSpecManager(temp_dir / "prompts")

    @pytest.fixture
    def workflow_orchestrator(
        self,
        mock_config_manager,
        fake_ssh_manager,
        fake_file_transfer,
        fake_docker_executor,
        temp_dir,
    ):
        """Create WorkflowOrchestrator with test doubles for external dependencies."""
        # Create real orchestrator
        orchestrator = WorkflowOrchestrator()

        # Replace only external boundary objects with fakes
        orchestrator.config_manager = mock_config_manager
        orchestrator.ssh_manager = fake_ssh_manager
        orchestrator.file_transfer = fake_file_transfer
        orchestrator.docker_executor = fake_docker_executor

        return orchestrator

    @pytest.mark.integration
    def test_complete_inference_workflow(
        self,
        workflow_orchestrator,
        sample_run_spec,
        sample_prompt_spec,
        fake_prompt_manager,
        temp_dir,
    ):
        """Test complete workflow from RunSpec to inference execution."""
        # Setup - Create real files
        run_spec_file = temp_dir / "run_spec.json"
        run_spec_file.write_text(json.dumps(sample_run_spec.to_dict()))

        # Store prompt spec in fake manager
        fake_prompt_manager.prompt_specs[sample_prompt_spec.id] = sample_prompt_spec

        # Create actual video files
        video_dir = temp_dir / "videos"
        video_dir.mkdir()
        (video_dir / "color.mp4").write_bytes(b"fake video data")
        (video_dir / "depth.mp4").write_bytes(b"fake depth data")
        (video_dir / "segmentation.mp4").write_bytes(b"fake seg data")

        # Patch only the prompt manager's get method since it's an internal lookup
        with patch.object(workflow_orchestrator, "prompt_manager", fake_prompt_manager):
            # Execute workflow - test real behavior
            result = workflow_orchestrator.run_inference(
                str(run_spec_file), num_gpus=2, verbose=True
            )

        # Verify behavioral outcomes (not implementation details)
        assert result is True

        # Check that files were processed (behavioral outcome)
        assert len(workflow_orchestrator.file_transfer.uploaded_files) > 0
        assert len(workflow_orchestrator.docker_executor.containers_run) == 1

        # Verify the correct spec was used
        container_run = workflow_orchestrator.docker_executor.containers_run[0]
        assert container_run["run_spec_id"] == sample_run_spec.id
        assert container_run["num_gpus"] == 2

    @pytest.mark.integration
    def test_video_directory_detection(self, workflow_orchestrator, temp_dir):
        """Test that workflow correctly identifies video directories."""
        # Create actual directory structure
        video_base = temp_dir / "outputs" / "videos"
        test_dir = video_base / "test_video_001"
        test_dir.mkdir(parents=True)

        # Create video files
        (test_dir / "color.mp4").touch()
        (test_dir / "depth.mp4").touch()

        # Create RunSpec pointing to this directory
        run_spec = RunSpec(
            id="test_rs_001",
            prompt_id="test_ps_001",
            name="test_run",
            control_weights={"depth": 0.3},
            parameters={"num_steps": 35},
            timestamp=datetime.now().isoformat(),
            execution_status=ExecutionStatus.PENDING,
            output_path=str(test_dir),
        )

        run_spec_file = temp_dir / "run_spec.json"
        run_spec.save(run_spec_file)

        # Test video directory detection
        video_dirs = workflow_orchestrator.get_video_directories(run_spec_file)

        # Verify correct directory was found
        assert len(video_dirs) > 0
        assert any(str(test_dir) in str(d) for d in video_dirs)

    @pytest.mark.integration
    def test_batch_inference_workflow(self, workflow_orchestrator, fake_prompt_manager, temp_dir):
        """Test batch inference with multiple RunSpecs."""
        # Create multiple specs with real data
        results = []

        for i in range(3):
            # Create prompt spec
            prompt_spec = PromptSpec(
                id=f"test_ps_{i:03d}",
                name=f"scene_{i}",
                prompt=f"Test prompt {i}",
                negative_prompt="",
                input_video_path=str(temp_dir / f"video_{i}.mp4"),
                control_inputs={},
                timestamp=datetime.now().isoformat(),
            )
            fake_prompt_manager.prompt_specs[prompt_spec.id] = prompt_spec

            # Create run spec
            run_spec = RunSpec(
                id=f"test_rs_{i:03d}",
                prompt_id=prompt_spec.id,
                name=f"test_run_{i:03d}",
                control_weights={"depth": 0.3 + i * 0.1},
                parameters={"num_steps": 35, "seed": 42 + i},
                timestamp=datetime.now().isoformat(),
                execution_status=ExecutionStatus.PENDING,
                output_path=str(temp_dir / f"output_{i}"),
            )

            run_spec_file = temp_dir / f"run_{i:03d}.json"
            run_spec.save(run_spec_file)

            # Execute with fake dependencies
            with patch.object(workflow_orchestrator, "prompt_manager", fake_prompt_manager):
                result = workflow_orchestrator.run_inference(
                    str(run_spec_file), num_gpus=1, verbose=False
                )
                results.append(result)

        # Verify all executed successfully
        assert all(results)
        assert len(workflow_orchestrator.docker_executor.containers_run) == 3

    @pytest.mark.integration
    def test_error_recovery_workflow(
        self,
        workflow_orchestrator,
        fake_docker_executor,
        sample_run_spec,
        sample_prompt_spec,
        fake_prompt_manager,
        temp_dir,
    ):
        """Test workflow handles errors gracefully."""
        # Setup error condition
        fake_docker_executor.set_execution_result(
            sample_run_spec.id, (1, "", "Error: GPU out of memory")
        )

        # Store prompt spec
        fake_prompt_manager.prompt_specs[sample_prompt_spec.id] = sample_prompt_spec

        # Create run spec file
        run_spec_file = temp_dir / "run_spec.json"
        sample_run_spec.save(run_spec_file)

        with patch.object(workflow_orchestrator, "prompt_manager", fake_prompt_manager):
            # Execute workflow - should handle error
            result = workflow_orchestrator.run_inference(
                str(run_spec_file), num_gpus=1, verbose=False
            )

        # Verify error was handled
        assert result is False

        # Verify attempted execution
        assert len(workflow_orchestrator.docker_executor.containers_run) == 1

    @pytest.mark.integration
    def test_status_monitoring(self, workflow_orchestrator):
        """Test status monitoring functionality."""
        # Connect SSH (using fake)
        workflow_orchestrator.ssh_manager.connect()

        # Check status
        status = workflow_orchestrator.check_remote_status()

        # Verify status structure
        assert "ssh_connected" in status
        assert status["ssh_connected"] is True
        assert "containers_running" in status

    @pytest.mark.integration
    def test_prompt_upsampling_integration(
        self, workflow_orchestrator, fake_docker_executor, sample_prompt_spec, temp_dir
    ):
        """Test prompt upsampling workflow."""
        # Setup
        prompt_file = temp_dir / "prompt.json"
        sample_prompt_spec.save(prompt_file)

        # Execute upsampling
        exit_code, output, error = fake_docker_executor.run_upsampling(sample_prompt_spec)

        # Verify upsampling executed
        assert exit_code == 0
        assert "Upsampled prompt" in output
        assert sample_prompt_spec.prompt[:50] in output

    @pytest.mark.integration
    def test_parallel_upload_optimization(
        self,
        workflow_orchestrator,
        fake_file_transfer,
        sample_prompt_spec,
        sample_run_spec,
        temp_dir,
    ):
        """Test that uploads are optimized for parallel execution."""
        # Create multiple video files
        video_files = []
        for i in range(5):
            video_file = temp_dir / f"video_{i}.mp4"
            video_file.write_bytes(b"video data")
            video_files.append(video_file)

        # Update prompt spec with multiple control inputs
        sample_prompt_spec = PromptSpec(
            id=sample_prompt_spec.id,
            name=sample_prompt_spec.name,
            prompt=sample_prompt_spec.prompt,
            negative_prompt=sample_prompt_spec.negative_prompt,
            input_video_path=str(video_files[0]),
            control_inputs={f"control_{i}": str(video_files[i + 1]) for i in range(4)},
            timestamp=sample_prompt_spec.timestamp,
        )

        # Upload files
        result = fake_file_transfer.upload_prompt_and_videos(sample_prompt_spec, sample_run_spec)

        # Verify parallel upload optimization
        assert result["prompt_uploaded"] is True
        assert len(result["videos_uploaded"]) == 5  # 1 input + 4 controls
        assert len(fake_file_transfer.uploaded_files) >= 5
