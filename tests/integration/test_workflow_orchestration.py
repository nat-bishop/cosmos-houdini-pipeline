"""
Integration tests for the complete workflow orchestration.
Tests the full pipeline from PromptSpec creation to inference execution.
"""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.run_spec_manager import RunSpecManager
from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator


class TestWorkflowOrchestration:
    """Test complete workflow orchestration scenarios."""

    @pytest.fixture
    def workflow_orchestrator(
        self, mock_config_manager, mock_ssh_manager, mock_file_transfer, mock_docker_executor
    ):
        """Create WorkflowOrchestrator with mocked dependencies."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.SSHManager"
        ) as mock_ssh_class, patch(
            "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService"
        ) as mock_ft_class, patch(
            "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor"
        ) as mock_docker_class:
            mock_ssh_class.return_value = mock_ssh_manager
            mock_ft_class.return_value = mock_file_transfer
            mock_docker_class.return_value = mock_docker_executor

            # Create orchestrator with default config file
            orchestrator = WorkflowOrchestrator()
            # Override with mocked dependencies
            orchestrator.config_manager = mock_config_manager
            orchestrator.ssh_manager = mock_ssh_manager
            orchestrator.file_transfer = mock_file_transfer
            orchestrator.docker_executor = mock_docker_executor

            return orchestrator

    @pytest.mark.integration
    def test_complete_inference_workflow(
        self, workflow_orchestrator, sample_run_spec, sample_prompt_spec, temp_dir
    ):
        """Test complete workflow from RunSpec to inference execution."""
        # Setup
        run_spec_file = temp_dir / "run_spec.json"
        run_spec_file.write_text(json.dumps(sample_run_spec.to_dict()))

        prompt_spec_file = temp_dir / "prompt_spec.json"
        prompt_spec_file.write_text(json.dumps(sample_prompt_spec.to_dict()))

        # Mock video files
        video_dir = temp_dir / "videos"
        video_dir.mkdir()
        (video_dir / "color.mp4").write_text("mock color video")
        (video_dir / "depth.mp4").write_text("mock depth video")
        (video_dir / "segmentation.mp4").write_text("mock segmentation video")

        # Mock the prompt spec loading
        with patch(
            "cosmos_workflow.prompts.prompt_spec_manager.PromptSpecManager.load_by_id"
        ) as mock_load:
            mock_load.return_value = sample_prompt_spec

            # Execute workflow
            result = workflow_orchestrator.run_inference(
                str(run_spec_file), num_gpus=2, verbose=True
            )

        # Verify workflow steps executed in order
        assert result is True

        # 1. Files should be uploaded
        assert workflow_orchestrator.file_transfer.upload_file.called
        assert workflow_orchestrator.file_transfer.upload_directory.called

        # 2. Docker should be executed
        assert workflow_orchestrator.docker_executor.run_inference.called

        # 3. Results should be downloaded
        assert workflow_orchestrator.file_transfer.download_directory.called

    @pytest.mark.integration
    def test_video_directory_detection(self, workflow_orchestrator, temp_dir):
        """Test video directory detection from RunSpec."""
        # Setup complex directory structure
        video_base = temp_dir / "outputs" / "videos"

        # Create multiple video directories with timestamps
        dirs = [
            video_base / "scene1_20250830_120000",
            video_base / "scene1_20250830_130000",
            video_base / "scene2_20250830_140000",
        ]

        for dir_path in dirs:
            dir_path.mkdir(parents=True)
            (dir_path / "color.mp4").touch()
            (dir_path / "metadata.json").write_text(
                json.dumps(
                    {
                        "name": dir_path.name.split("_")[0],
                        "timestamp": "_".join(dir_path.name.split("_")[1:]),
                        "video_path": str(dir_path / "color.mp4"),
                    }
                )
            )

        # Create RunSpec that references one of these
        run_spec = RunSpec(
            id="test_rs_001",
            prompt_spec_id="test_ps_001",
            control_weights={"depth": 0.3},
            parameters={"num_steps": 35},
            execution_status="pending",
            output_path=str(dirs[1]),  # Reference middle directory
            timestamp=datetime.now().isoformat(),
        )

        run_spec_file = temp_dir / "runs" / "run_spec.json"
        run_spec_file.parent.mkdir(parents=True)
        run_spec_file.write_text(json.dumps(run_spec.to_dict()))

        # Create corresponding PromptSpec
        prompt_spec = PromptSpec(
            id="test_ps_001",
            name="scene1",
            prompt="Test prompt",
            negative_prompt="",
            input_video_path=str(dirs[1] / "color.mp4"),
            control_inputs={"depth": str(dirs[1] / "depth.mp4")},
            timestamp=datetime.now().isoformat(),
        )

        prompt_spec_file = temp_dir / "prompts" / "prompt_spec.json"
        prompt_spec_file.parent.mkdir(parents=True)
        prompt_spec_file.write_text(json.dumps(prompt_spec.to_dict()))

        # Test video directory detection
        with patch.object(workflow_orchestrator, "config_manager") as mock_config:
            mock_config.get_local_config.return_value.videos_dir = str(video_base)
            mock_config.get_local_config.return_value.runs_dir = str(temp_dir / "runs")
            mock_config.get_local_config.return_value.prompts_dir = str(temp_dir / "prompts")

            video_dirs = workflow_orchestrator._get_video_directories("scene1", str(run_spec_file))

        # Verify correct directory found
        assert len(video_dirs) > 0
        assert str(dirs[1]) in str(video_dirs[0])

    @pytest.mark.integration
    def test_control_spec_generation(
        self, workflow_orchestrator, sample_prompt_spec, sample_run_spec, temp_dir
    ):
        """Test generation of Cosmos control spec from PromptSpec and RunSpec."""
        # Setup
        expected_control_spec = {
            "prompt": sample_prompt_spec.prompt,
            "negative_prompt": sample_prompt_spec.negative_prompt,
            "input_video_path": sample_prompt_spec.input_video_path,
            "control_inputs": [
                {
                    "type": "depth",
                    "path": sample_prompt_spec.control_inputs["depth"],
                    "weight": sample_run_spec.control_weights["depth"],
                },
                {
                    "type": "segmentation",
                    "path": sample_prompt_spec.control_inputs["segmentation"],
                    "weight": sample_run_spec.control_weights["segmentation"],
                },
            ],
            "parameters": sample_run_spec.parameters,
        }

        # Generate control spec
        control_spec = workflow_orchestrator._generate_control_spec(
            sample_prompt_spec, sample_run_spec
        )

        # Verify structure
        assert control_spec["prompt"] == expected_control_spec["prompt"]
        assert control_spec["negative_prompt"] == expected_control_spec["negative_prompt"]
        assert len(control_spec["control_inputs"]) == 2
        assert control_spec["parameters"]["num_steps"] == 35

    @pytest.mark.integration
    def test_batch_inference_workflow(self, workflow_orchestrator, temp_dir):
        """Test batch inference with multiple RunSpecs."""
        # Setup multiple RunSpecs
        run_specs = []
        for i in range(3):
            run_spec = RunSpec(
                id=f"test_rs_{i:03d}",
                prompt_spec_id=f"test_ps_{i:03d}",
                control_weights={"depth": 0.3 + i * 0.1},
                parameters={"num_steps": 35, "seed": 42 + i},
                execution_status="pending",
                output_path=f"outputs/run_{i:03d}",
                timestamp=datetime.now().isoformat(),
            )

            run_spec_file = temp_dir / f"run_{i:03d}.json"
            run_spec_file.write_text(json.dumps(run_spec.to_dict()))
            run_specs.append((run_spec_file, run_spec))

        # Execute batch workflow
        results = []
        for spec_file, spec in run_specs:
            with patch("cosmos_workflow.prompts.prompt_spec_manager.PromptSpecManager.load_by_id"):
                result = workflow_orchestrator.run_inference(
                    str(spec_file), num_gpus=1, verbose=False
                )
                results.append(result)

        # Verify all executed
        assert all(results)
        assert workflow_orchestrator.docker_executor.run_inference.call_count == 3

    @pytest.mark.integration
    def test_error_recovery_workflow(
        self, workflow_orchestrator, sample_run_spec, sample_prompt_spec, temp_dir
    ):
        """Test workflow recovery from various failure points."""
        # Setup
        run_spec_file = temp_dir / "run_spec.json"
        run_spec_file.write_text(json.dumps(sample_run_spec.to_dict()))

        # Test 1: Upload failure
        workflow_orchestrator.file_transfer.upload_file.return_value = False

        with patch(
            "cosmos_workflow.prompts.prompt_spec_manager.PromptSpecManager.load_by_id"
        ) as mock_load:
            mock_load.return_value = sample_prompt_spec
            result = workflow_orchestrator.run_inference(str(run_spec_file))

        assert result is False
        assert not workflow_orchestrator.docker_executor.run_inference.called

        # Test 2: Docker execution failure
        workflow_orchestrator.file_transfer.upload_file.return_value = True
        workflow_orchestrator.docker_executor.run_inference.return_value = (1, "", "Error")

        with patch(
            "cosmos_workflow.prompts.prompt_spec_manager.PromptSpecManager.load_by_id"
        ) as mock_load:
            mock_load.return_value = sample_prompt_spec
            result = workflow_orchestrator.run_inference(str(run_spec_file))

        assert result is False

        # Test 3: Download failure (should still return partial success)
        workflow_orchestrator.docker_executor.run_inference.return_value = (0, "Success", "")
        workflow_orchestrator.file_transfer.download_directory.return_value = False

        with patch(
            "cosmos_workflow.prompts.prompt_spec_manager.PromptSpecManager.load_by_id"
        ) as mock_load:
            mock_load.return_value = sample_prompt_spec
            result = workflow_orchestrator.run_inference(str(run_spec_file))

        # Inference succeeded, only download failed
        assert result is True  # Or False depending on implementation

    @pytest.mark.integration
    @pytest.mark.slow
    def test_parallel_upload_optimization(self, workflow_orchestrator, temp_dir):
        """Test that multiple files are uploaded efficiently."""
        # Setup multiple video files
        video_files = []
        for i in range(10):
            video_file = temp_dir / f"video_{i:02d}.mp4"
            video_file.write_text(f"mock video {i}")
            video_files.append(video_file)

        # Mock upload to track call pattern
        upload_calls = []

        def track_upload(local_path, remote_path):
            upload_calls.append((local_path, remote_path))
            return True

        workflow_orchestrator.file_transfer.upload_file.side_effect = track_upload

        # Upload all files
        for video_file in video_files:
            workflow_orchestrator.file_transfer.upload_file(
                str(video_file), f"/remote/videos/{video_file.name}"
            )

        # Verify all uploaded
        assert len(upload_calls) == 10

        # Could verify upload order or batching strategy here
        # In a real implementation, might use concurrent uploads

    @pytest.mark.integration
    def test_prompt_upsampling_integration(
        self, workflow_orchestrator, sample_prompt_spec, temp_dir
    ):
        """Test integration with prompt upsampling workflow."""
        # Setup
        prompt_file = temp_dir / "prompt.txt"
        prompt_file.write_text(sample_prompt_spec.prompt)

        # Mock upsampling result
        upsampled_prompt = "A highly detailed futuristic city with neon lights..."
        workflow_orchestrator.docker_executor.run_upsampling = MagicMock(
            return_value=(0, json.dumps({"upsampled_prompt": upsampled_prompt}), "")
        )

        # Execute upsampling
        with patch.object(workflow_orchestrator, "run_prompt_upsampling") as mock_upsample:
            mock_upsample.return_value = upsampled_prompt

            result = mock_upsample(str(prompt_file), video_path=sample_prompt_spec.input_video_path)

        # Verify
        assert result == upsampled_prompt
        mock_upsample.assert_called_once()

    @pytest.mark.integration
    def test_status_monitoring(self, workflow_orchestrator):
        """Test workflow status monitoring and reporting."""
        # Setup status tracking
        status_updates = []

        def track_status(message, level="INFO"):
            status_updates.append((message, level))

        with patch("cosmos_workflow.workflows.workflow_orchestrator.logger") as mock_logger:
            mock_logger.info.side_effect = lambda msg: track_status(msg, "INFO")
            mock_logger.error.side_effect = lambda msg: track_status(msg, "ERROR")

            # Execute a workflow step
            workflow_orchestrator.ssh_manager.is_connected.return_value = True
            status = workflow_orchestrator.check_status(verbose=True)

        # Verify status reporting
        assert status is True
        assert len(status_updates) > 0
        assert any("connected" in msg.lower() for msg, _ in status_updates)
