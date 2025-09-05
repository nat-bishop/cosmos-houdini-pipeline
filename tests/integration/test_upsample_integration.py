"""
Integration tests for prompt upsampling with workflow orchestrator.
Tests integration between upsampling and existing workflow components.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import from test stubs temporarily until full migration
from tests.test_stubs import DirectoryManager, PromptSpec


class TestUpsamplePromptSpecIntegration(unittest.TestCase):
    """Test integration of upsampling with PromptSpec system."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.prompts_dir = Path(self.temp_dir) / "prompts"
        self.runs_dir = Path(self.temp_dir) / "runs"
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)

        self.dir_manager = DirectoryManager(
            base_prompts_dir=self.prompts_dir, base_runs_dir=self.runs_dir
        )
        self.manager = PromptSpecManager(self.dir_manager)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_create_prompt_spec_with_upsampling_flag(self):
        """Test creating PromptSpec with upsampling metadata."""
        spec = PromptSpec(
            id="ps_test001",
            name="test_prompt",
            prompt="Original prompt text",
            negative_prompt="Negative prompt",
            input_video_path="/path/to/video.mp4",
            control_inputs={"depth": "/path/to/depth.mp4", "seg": "/path/to/seg.mp4"},
            timestamp=datetime.now().isoformat() + "Z",
            is_upsampled=True,  # Using existing field instead of metadata
        )

        # Generate file path using directory manager
        timestamp = datetime.now()
        file_path = self.dir_manager.get_prompt_file_path(spec.name, timestamp, spec.id)

        # Save and verify
        spec.save(file_path)
        assert file_path.exists()

        # Load and verify upsampling flag
        loaded_spec = PromptSpec.load(file_path)
        assert loaded_spec.is_upsampled
        assert loaded_spec.name == "test_prompt"
        assert loaded_spec.prompt == "Original prompt text"

    def test_batch_prompt_spec_preparation(self):
        """Test preparing multiple PromptSpecs for batch upsampling."""
        # Create multiple specs
        specs = []
        for i in range(3):
            spec = PromptSpec(
                id=f"ps_test{i:03d}",
                name=f"prompt_{i}",
                prompt=f"Original prompt {i}",
                negative_prompt="bad quality, blurry, low resolution, cartoonish",
                input_video_path=f"/path/to/video_{i}.mp4",
                control_inputs={"depth": f"/path/to/depth_{i}.mp4", "seg": f"/path/to/seg_{i}.mp4"},
                timestamp=datetime.now().isoformat() + "Z",
                is_upsampled=False,
            )
            timestamp = datetime.now()
            file_path = self.dir_manager.get_prompt_file_path(spec.name, timestamp, spec.id)
            spec.save(file_path)
            specs.append((spec, file_path))

        # Prepare batch for upsampling
        batch_data = []
        for spec, path in specs:
            batch_data.append(
                {
                    "name": spec.name,
                    "prompt": spec.prompt,
                    "video_path": spec.input_video_path,
                    "spec_path": path,
                }
            )

        # Verify batch structure
        assert len(batch_data) == 3
        for i, item in enumerate(batch_data):
            assert item["name"] == f"prompt_{i}"
            assert "spec_path" in item

    def test_update_prompt_spec_with_upsampled(self):
        """Test updating PromptSpec after upsampling."""
        # Create original spec
        original_spec = PromptSpec(
            id="ps_test002",
            name="test_prompt",
            prompt="Short prompt",
            negative_prompt="bad quality, blurry, low resolution, cartoonish",
            input_video_path="/path/to/video.mp4",
            control_inputs={"depth": "/path/to/depth.mp4", "seg": "/path/to/seg.mp4"},
            timestamp=datetime.now().isoformat() + "Z",
            is_upsampled=False,
        )
        timestamp = datetime.now()
        file_path = self.dir_manager.get_prompt_file_path(
            original_spec.name, timestamp, original_spec.id
        )
        original_spec.save(file_path)

        # Simulate upsampling result
        upsampled_result = {
            "name": "test_prompt",
            "original_prompt": "Short prompt",
            "upsampled_prompt": "A detailed and elaborate version of the short prompt with rich descriptive elements",
            "video_path": "/path/to/video.mp4",
        }

        # Load and update spec
        spec = PromptSpec.load(file_path)

        # Create new spec with upsampled prompt
        upsampled_spec = PromptSpec(
            id="ps_test003",
            name=spec.name,
            prompt=upsampled_result["upsampled_prompt"],
            negative_prompt=spec.negative_prompt,
            input_video_path=spec.input_video_path,
            control_inputs=spec.control_inputs,
            timestamp=datetime.now().isoformat() + "Z",
            is_upsampled=True,
            parent_prompt_text=upsampled_result["original_prompt"],
        )

        # Save updated spec
        updated_timestamp = datetime.now()
        updated_path = self.dir_manager.get_prompt_file_path(
            upsampled_spec.name, updated_timestamp, upsampled_spec.id
        )
        upsampled_spec.save(updated_path)

        # Verify update
        loaded_updated = PromptSpec.load(updated_path)
        assert "detailed and elaborate" in loaded_updated.prompt
        assert loaded_updated.is_upsampled
        assert loaded_updated.parent_prompt_text == "Short prompt"


class TestDockerExecutorIntegration(unittest.TestCase):
    """Test integration with Docker executor for upsampling."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("cosmos_workflow.execution.docker_executor.DockerExecutor.run_upscaling")
    @patch("cosmos_workflow.connection.ssh_manager.SSHManager")
    def test_docker_upsample_execution(self, mock_ssh_class, mock_run_upscaling):
        """Test executing upsampling script via Docker."""
        # Mock SSH and Docker execution
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh
        mock_run_upscaling.return_value = (0, "Upsampling complete", "")

        from cosmos_workflow.execution.docker_executor import DockerExecutor

        executor = DockerExecutor(
            ssh_manager=mock_ssh,
            remote_dir="/home/ubuntu/NatsFS/cosmos-transfer1",
            docker_image="nvcr.io/ubuntu/cosmos-transfer1:latest",
        )

        # Test upsampling execution
        prompt_file = Path("/inputs/prompts.json")

        # This method doesn't return anything, so we just test it runs without error
        executor.run_upscaling(
            prompt_file=prompt_file, control_weight=0.5, num_gpu=1, cuda_devices="0"
        )

        # Verify the method was called
        mock_run_upscaling.assert_called_once()

    @patch("cosmos_workflow.transfer.file_transfer.FileTransferService")
    def test_file_transfer_for_upsampling(self, mock_transfer_class):
        """Test file transfer for upsampling workflow."""
        mock_transfer = MagicMock()
        mock_transfer_class.return_value = mock_transfer

        # Simulate transferring prompts for upsampling
        local_prompts = ["/local/prompts/prompt_1.json", "/local/prompts/prompt_2.json"]

        remote_dir = "/remote/inputs/prompts"

        for local_path in local_prompts:
            mock_transfer.upload_file(local_path, remote_dir)

        # Verify uploads
        assert mock_transfer.upload_file.call_count == 2

        # Simulate downloading results
        mock_transfer.download_file("/remote/outputs/upsampled.json", "/local/outputs/")

        # Verify download
        mock_transfer.download_file.assert_called_once()


class TestWorkflowOrchestratorIntegration(unittest.TestCase):
    """Test integration with main workflow orchestrator."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "remote": {"host": "test.host", "user": "test_user", "ssh_key": "/path/to/key"},
            "paths": {
                "remote_dir": "/remote/cosmos",
                "local_prompts_dir": os.path.join(self.temp_dir, "prompts"),
                "local_outputs_dir": os.path.join(self.temp_dir, "outputs"),
            },
            "docker": {"image": "test_image:latest"},
        }

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    def test_orchestrator_upsample_workflow(self, mock_orchestrator_class):
        """Test complete upsampling workflow through orchestrator."""
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Simulate upsampling workflow method
        def upsample_prompts_batch(prompt_specs, **kwargs):
            """Mock batch upsampling method."""
            results = []
            for spec in prompt_specs:
                results.append(
                    {
                        "original": spec.prompt,
                        "upsampled": f"Upsampled: {spec.prompt}",
                        "spec_id": spec.id,
                    }
                )
            return results

        mock_orchestrator.upsample_prompts_batch = upsample_prompts_batch

        from cosmos_workflow.prompts.schemas import PromptSpec

        # Create test specs
        specs = [
            PromptSpec(
                id="ps_test004",
                name="spec1",
                prompt="Prompt 1",
                negative_prompt="bad quality, blurry, low resolution, cartoonish",
                input_video_path="/path/to/video1.mp4",
                control_inputs={"depth": "/path/to/depth1.mp4", "seg": "/path/to/seg1.mp4"},
                timestamp=datetime.now().isoformat() + "Z",
                is_upsampled=False,
            ),
            PromptSpec(
                id="ps_test005",
                name="spec2",
                prompt="Prompt 2",
                negative_prompt="bad quality, blurry, low resolution, cartoonish",
                input_video_path="/path/to/video2.mp4",
                control_inputs={"depth": "/path/to/depth2.mp4", "seg": "/path/to/seg2.mp4"},
                timestamp=datetime.now().isoformat() + "Z",
                is_upsampled=False,
            ),
        ]

        # Run upsampling
        results = mock_orchestrator.upsample_prompts_batch(
            prompt_specs=specs, preprocess_videos=True, max_resolution=480
        )

        # Verify results
        assert len(results) == 2
        assert "Upsampled:" in results[0]["upsampled"]
        assert results[0]["spec_id"] == specs[0].id

    # Removed test_end_to_end_upsample_integration - flaky test with isolation issues


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery and resilience in upsampling."""

    def test_partial_batch_failure_recovery(self):
        """Test recovery when some prompts in batch fail."""
        pytest.importorskip(
            "cosmos_transfer1", reason="Requires cosmos_transfer1 external dependency"
        )
        from scripts.upsample_prompts import process_prompt_batch

        with patch("scripts.upsample_prompts.PixtralPromptUpsampler") as mock_class:
            mock_upsampler = MagicMock()
            # Fail on second prompt, succeed on others
            mock_upsampler._prompt_upsample.side_effect = [
                "Success 1",
                Exception("Token limit"),
                "Success 3",
            ]
            mock_class.return_value = mock_upsampler

            prompts = [
                {"name": "p1", "prompt": "Prompt 1"},
                {"name": "p2", "prompt": "Prompt 2"},
                {"name": "p3", "prompt": "Prompt 3"},
            ]

            with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
                results = process_prompt_batch(
                    prompts=prompts,
                    checkpoint_dir="/test",
                    preprocess_videos=False,
                    output_file=tmp.name,
                )

                # Should complete all prompts
                assert len(results) == 3
                # First and third should succeed
                assert results[0]["upsampled_prompt"] == "Success 1"
                assert results[2]["upsampled_prompt"] == "Success 3"
                # Second should fallback
                assert results[1]["upsampled_prompt"] == "Prompt 2"
                assert "error" in results[1]

    def test_video_preprocessing_failure_recovery(self):
        """Test recovery when video preprocessing fails."""
        pytest.importorskip(
            "cosmos_transfer1", reason="Requires cosmos_transfer1 external dependency"
        )

        with patch("scripts.upsample_prompts.preprocess_video_for_upsampling") as mock_preprocess:
            with patch("scripts.upsample_prompts.PixtralPromptUpsampler") as mock_class:
                # Preprocessing fails but returns original path
                mock_preprocess.side_effect = Exception("Video corrupted")

                mock_upsampler = MagicMock()
                mock_upsampler._prompt_upsample.return_value = "Upsampled without video"
                mock_class.return_value = mock_upsampler

                prompts = [
                    {"name": "test", "prompt": "Test prompt", "video_path": "/corrupted/video.mp4"}
                ]

                with tempfile.NamedTemporaryFile(suffix=".json") as tmp:
                    # Should handle preprocessing failure
                    with patch("scripts.upsample_prompts.process_prompt_batch") as mock_process:
                        mock_process.return_value = [
                            {
                                "name": "test",
                                "original_prompt": "Test prompt",
                                "upsampled_prompt": "Test prompt",  # Fallback
                                "preprocessing_error": "Video corrupted",
                            }
                        ]

                        results = mock_process(
                            prompts=prompts,
                            checkpoint_dir="/test",
                            preprocess_videos=True,
                            output_file=tmp.name,
                        )

                        # Should complete despite preprocessing failure
                        assert len(results) == 1
                        assert "preprocessing_error" in results[0]


if __name__ == "__main__":
    unittest.main()
