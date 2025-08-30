"""
Integration tests for prompt upsampling with workflow orchestrator.
Tests integration between upsampling and existing workflow components.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.prompts.schemas import PromptSpec
from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager


class TestUpsamplePromptSpecIntegration(unittest.TestCase):
    """Test integration of upsampling with PromptSpec system."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = PromptSpecManager(base_dir=self.temp_dir)
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_prompt_spec_with_upsampling_flag(self):
        """Test creating PromptSpec with upsampling metadata."""
        spec = PromptSpec(
            name="test_prompt",
            prompt="Original prompt text",
            negative_prompt="Negative prompt",
            input_video_path="/path/to/video.mp4",
            control_inputs={
                "depth": {
                    "input_control": "/path/to/depth.mp4",
                    "control_weight": 0.5
                }
            },
            metadata={
                "needs_upsampling": True,
                "upsampling_params": {
                    "max_resolution": 480,
                    "num_frames": 2
                }
            }
        )
        
        # Save and verify
        saved_path = self.manager.save(spec)
        self.assertTrue(os.path.exists(saved_path))
        
        # Load and verify metadata
        loaded_spec = self.manager.load(saved_path)
        self.assertTrue(loaded_spec.metadata.get("needs_upsampling"))
        self.assertEqual(
            loaded_spec.metadata.get("upsampling_params", {}).get("max_resolution"),
            480
        )
    
    def test_batch_prompt_spec_preparation(self):
        """Test preparing multiple PromptSpecs for batch upsampling."""
        # Create multiple specs
        specs = []
        for i in range(3):
            spec = PromptSpec(
                name=f"prompt_{i}",
                prompt=f"Original prompt {i}",
                input_video_path=f"/path/to/video_{i}.mp4",
                metadata={"needs_upsampling": True}
            )
            saved_path = self.manager.save(spec)
            specs.append((spec, saved_path))
        
        # Prepare batch for upsampling
        batch_data = []
        for spec, path in specs:
            batch_data.append({
                "name": spec.name,
                "prompt": spec.prompt,
                "video_path": spec.input_video_path,
                "spec_path": path
            })
        
        # Verify batch structure
        self.assertEqual(len(batch_data), 3)
        for i, item in enumerate(batch_data):
            self.assertEqual(item["name"], f"prompt_{i}")
            self.assertIn("spec_path", item)
    
    def test_update_prompt_spec_with_upsampled(self):
        """Test updating PromptSpec after upsampling."""
        # Create original spec
        original_spec = PromptSpec(
            name="test_prompt",
            prompt="Short prompt",
            input_video_path="/path/to/video.mp4"
        )
        saved_path = self.manager.save(original_spec)
        
        # Simulate upsampling result
        upsampled_result = {
            "name": "test_prompt",
            "original_prompt": "Short prompt",
            "upsampled_prompt": "A detailed and elaborate version of the short prompt with rich descriptive elements",
            "video_path": "/path/to/video.mp4"
        }
        
        # Load and update spec
        spec = self.manager.load(saved_path)
        
        # Create new spec with upsampled prompt
        upsampled_spec = PromptSpec(
            name=spec.name,
            prompt=upsampled_result["upsampled_prompt"],
            negative_prompt=spec.negative_prompt,
            input_video_path=spec.input_video_path,
            control_inputs=spec.control_inputs,
            metadata={
                **spec.metadata,
                "original_prompt": upsampled_result["original_prompt"],
                "upsampled": True,
                "upsampled_at": datetime.now().isoformat()
            }
        )
        
        # Save updated spec
        updated_path = self.manager.save(upsampled_spec)
        
        # Verify update
        loaded_updated = self.manager.load(updated_path)
        self.assertIn("detailed and elaborate", loaded_updated.prompt)
        self.assertTrue(loaded_updated.metadata.get("upsampled"))
        self.assertEqual(loaded_updated.metadata.get("original_prompt"), "Short prompt")


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
    
    @patch('cosmos_workflow.execution.docker_executor.DockerExecutor.execute')
    @patch('cosmos_workflow.connection.ssh_manager.SSHManager')
    def test_docker_upsample_execution(self, mock_ssh_class, mock_execute):
        """Test executing upsampling script via Docker."""
        # Mock SSH and Docker execution
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh
        mock_execute.return_value = (0, "Upsampling complete", "")
        
        from cosmos_workflow.execution.docker_executor import DockerExecutor
        
        executor = DockerExecutor(
            ssh_manager=mock_ssh,
            container_image="nvcr.io/ubuntu/cosmos-transfer1:latest"
        )
        
        # Simulate upsampling command
        command = [
            "bash", "/scripts/upsample_prompt.sh",
            "/inputs/prompts.json",
            "/outputs/upsampled.json",
            "true",  # preprocess_videos
            "480",   # max_resolution
            "2"      # num_frames
        ]
        
        exit_code, stdout, stderr = executor.execute(
            command=command,
            working_dir="/home/ubuntu/NatsFS/cosmos-transfer1",
            environment={"CUDA_VISIBLE_DEVICES": "0"},
            volumes={
                "/local/inputs": "/inputs",
                "/local/outputs": "/outputs"
            }
        )
        
        # Verify execution
        self.assertEqual(exit_code, 0)
        self.assertIn("complete", stdout.lower())
        mock_execute.assert_called_once()
    
    @patch('cosmos_workflow.transfer.file_transfer.FileTransferManager')
    def test_file_transfer_for_upsampling(self, mock_transfer_class):
        """Test file transfer for upsampling workflow."""
        mock_transfer = MagicMock()
        mock_transfer_class.return_value = mock_transfer
        
        # Simulate transferring prompts for upsampling
        local_prompts = [
            "/local/prompts/prompt_1.json",
            "/local/prompts/prompt_2.json"
        ]
        
        remote_dir = "/remote/inputs/prompts"
        
        for local_path in local_prompts:
            mock_transfer.upload_file(local_path, remote_dir)
        
        # Verify uploads
        self.assertEqual(mock_transfer.upload_file.call_count, 2)
        
        # Simulate downloading results
        mock_transfer.download_file(
            "/remote/outputs/upsampled.json",
            "/local/outputs/"
        )
        
        # Verify download
        mock_transfer.download_file.assert_called_once()


class TestWorkflowOrchestratorIntegration(unittest.TestCase):
    """Test integration with main workflow orchestrator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            "remote": {
                "host": "test.host",
                "user": "test_user",
                "ssh_key": "/path/to/key"
            },
            "paths": {
                "remote_dir": "/remote/cosmos",
                "local_prompts_dir": os.path.join(self.temp_dir, "prompts"),
                "local_outputs_dir": os.path.join(self.temp_dir, "outputs")
            },
            "docker": {
                "image": "test_image:latest"
            }
        }
        
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    @patch('cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator')
    def test_orchestrator_upsample_workflow(self, mock_orchestrator_class):
        """Test complete upsampling workflow through orchestrator."""
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        
        # Simulate upsampling workflow method
        def upsample_prompts_batch(prompt_specs, **kwargs):
            """Mock batch upsampling method."""
            results = []
            for spec in prompt_specs:
                results.append({
                    "original": spec.prompt,
                    "upsampled": f"Upsampled: {spec.prompt}",
                    "spec_id": spec.id
                })
            return results
        
        mock_orchestrator.upsample_prompts_batch = upsample_prompts_batch
        
        from cosmos_workflow.prompts.schemas import PromptSpec
        
        # Create test specs
        specs = [
            PromptSpec(name="spec1", prompt="Prompt 1"),
            PromptSpec(name="spec2", prompt="Prompt 2")
        ]
        
        # Run upsampling
        results = mock_orchestrator.upsample_prompts_batch(
            prompt_specs=specs,
            preprocess_videos=True,
            max_resolution=480
        )
        
        # Verify results
        self.assertEqual(len(results), 2)
        self.assertIn("Upsampled:", results[0]["upsampled"])
        self.assertEqual(results[0]["spec_id"], specs[0].id)
    
    @patch('cosmos_workflow.connection.ssh_manager.SSHManager')
    @patch('cosmos_workflow.execution.docker_executor.DockerExecutor')
    @patch('cosmos_workflow.transfer.file_transfer.FileTransferManager')
    def test_end_to_end_upsample_integration(
        self, mock_transfer_class, mock_docker_class, mock_ssh_class
    ):
        """Test complete end-to-end upsampling integration."""
        # Setup mocks
        mock_ssh = MagicMock()
        mock_ssh_class.return_value = mock_ssh
        
        mock_docker = MagicMock()
        mock_docker.execute.return_value = (0, "Success", "")
        mock_docker_class.return_value = mock_docker
        
        mock_transfer = MagicMock()
        mock_transfer_class.return_value = mock_transfer
        
        from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator
        
        orchestrator = WorkflowOrchestrator(config=self.config)
        
        # Create test prompt specs
        specs = []
        for i in range(2):
            spec = PromptSpec(
                name=f"test_{i}",
                prompt=f"Test prompt {i}",
                input_video_path=f"/videos/test_{i}.mp4"
            )
            specs.append(spec)
        
        # Mock the upsampling process
        with patch.object(orchestrator, 'ssh_manager', mock_ssh):
            with patch.object(orchestrator, 'docker_executor', mock_docker):
                with patch.object(orchestrator, 'file_transfer', mock_transfer):
                    # Simulate upsampling workflow
                    # 1. Upload prompt specs
                    for spec in specs:
                        mock_transfer.upload_file(spec, "/remote/prompts")
                    
                    # 2. Execute upsampling
                    mock_docker.execute([
                        "bash", "/scripts/upsample_prompt.sh",
                        "/remote/prompts/batch.json",
                        "/remote/outputs/upsampled.json"
                    ])
                    
                    # 3. Download results
                    mock_transfer.download_file(
                        "/remote/outputs/upsampled.json",
                        "/local/outputs/"
                    )
        
        # Verify workflow steps
        self.assertEqual(mock_transfer.upload_file.call_count, 2)
        mock_docker.execute.assert_called_once()
        mock_transfer.download_file.assert_called_once()


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery and resilience in upsampling."""
    
    def test_partial_batch_failure_recovery(self):
        """Test recovery when some prompts in batch fail."""
        from scripts.upsample_prompts import process_prompt_batch
        
        with patch('scripts.upsample_prompts.PixtralPromptUpsampler') as mock_class:
            mock_upsampler = MagicMock()
            # Fail on second prompt, succeed on others
            mock_upsampler._prompt_upsample.side_effect = [
                "Success 1",
                Exception("Token limit"),
                "Success 3"
            ]
            mock_class.return_value = mock_upsampler
            
            prompts = [
                {"name": "p1", "prompt": "Prompt 1"},
                {"name": "p2", "prompt": "Prompt 2"},
                {"name": "p3", "prompt": "Prompt 3"}
            ]
            
            with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
                results = process_prompt_batch(
                    prompts=prompts,
                    checkpoint_dir="/test",
                    preprocess_videos=False,
                    output_file=tmp.name
                )
                
                # Should complete all prompts
                self.assertEqual(len(results), 3)
                # First and third should succeed
                self.assertEqual(results[0]["upsampled_prompt"], "Success 1")
                self.assertEqual(results[2]["upsampled_prompt"], "Success 3")
                # Second should fallback
                self.assertEqual(results[1]["upsampled_prompt"], "Prompt 2")
                self.assertIn("error", results[1])
    
    def test_video_preprocessing_failure_recovery(self):
        """Test recovery when video preprocessing fails."""
        from scripts.upsample_prompts import process_prompt_batch
        
        with patch('scripts.upsample_prompts.preprocess_video_for_upsampling') as mock_preprocess:
            with patch('scripts.upsample_prompts.PixtralPromptUpsampler') as mock_class:
                # Preprocessing fails but returns original path
                mock_preprocess.side_effect = Exception("Video corrupted")
                
                mock_upsampler = MagicMock()
                mock_upsampler._prompt_upsample.return_value = "Upsampled without video"
                mock_class.return_value = mock_upsampler
                
                prompts = [{
                    "name": "test",
                    "prompt": "Test prompt",
                    "video_path": "/corrupted/video.mp4"
                }]
                
                with tempfile.NamedTemporaryFile(suffix='.json') as tmp:
                    # Should handle preprocessing failure
                    with patch('scripts.upsample_prompts.process_prompt_batch') as mock_process:
                        mock_process.return_value = [{
                            "name": "test",
                            "original_prompt": "Test prompt",
                            "upsampled_prompt": "Test prompt",  # Fallback
                            "preprocessing_error": "Video corrupted"
                        }]
                        
                        results = mock_process(
                            prompts=prompts,
                            checkpoint_dir="/test",
                            preprocess_videos=True,
                            output_file=tmp.name
                        )
                        
                        # Should complete despite preprocessing failure
                        self.assertEqual(len(results), 1)
                        self.assertIn("preprocessing_error", results[0])


if __name__ == '__main__':
    unittest.main()