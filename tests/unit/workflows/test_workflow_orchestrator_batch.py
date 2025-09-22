"""Test batch execution functionality in GPUExecutor.

Tests the orchestration of batch inference runs without using actual GPU resources.
Uses fakes and mocks to verify behavior of batch processing."""

import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from cosmos_workflow.execution.gpu_executor import GPUExecutor
from tests.fixtures.fakes import FakeFileTransferService, FakeSSHManager


class TestGPUExecutorBatchExecution:
    """Test suite for batch execution in GPUExecutor."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temp directory for test outputs
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        # Create orchestrator with test config
        with patch("cosmos_workflow.execution.gpu_executor.ConfigManager"):
            self.orchestrator = GPUExecutor()

        # Create fake SSH and file transfer
        self.fake_ssh = FakeSSHManager()
        self.fake_ssh.is_connected = True  # Set connected state after creation
        self.fake_file_transfer = FakeFileTransferService(self.fake_ssh)

        # Mock docker executor
        self.mock_docker_executor = Mock()

        # Mock config manager
        self.mock_config_manager = Mock()
        self.mock_config_manager.get_remote_config.return_value = Mock(
            remote_dir="/remote/cosmos-transfer1", docker_image="cosmos-transfer1:latest"
        )

        # Mock data repository service
        self.mock_service = Mock()
        self.mock_service.update_run = Mock()
        self.mock_service.update_run_status = Mock()

        # Replace services with mocks/fakes
        self.orchestrator.ssh_manager = self.fake_ssh
        self.orchestrator.file_transfer = self.fake_file_transfer
        self.orchestrator.docker_executor = self.mock_docker_executor
        self.orchestrator.config_manager = self.mock_config_manager
        self.orchestrator.service = self.mock_service
        # Mark services as initialized to prevent them from being recreated
        self.orchestrator._services_initialized = True

        # Create test data
        self.test_runs_and_prompts = [
            (
                {
                    "id": "rs_001",
                    "execution_config": {
                        "weights": {"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2}
                    },
                },
                {
                    "id": "ps_001",
                    "prompt_text": "First prompt",
                    "inputs": {"video": "inputs/videos/first/color.mp4"},
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
                    "prompt_text": "Second prompt",
                    "inputs": {
                        "video": "inputs/videos/second/color.mp4",
                        "depth": "inputs/videos/second/depth.mp4",
                    },
                },
            ),
        ]

    def _setup_nvidia_format_mock(self, mock_nv):
        """Helper to setup nvidia_format mock with write_batch_jsonl and write_cosmos_json."""

        def mock_write_batch_jsonl(data, path):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text("mocked jsonl content")
            return Path(path)

        def mock_write_cosmos_json(data, path):
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text("mocked json content")
            return Path(path)

        mock_nv.write_batch_jsonl = mock_write_batch_jsonl
        mock_nv.write_cosmos_json = mock_write_cosmos_json
        mock_nv.to_cosmos_batch_inference_jsonl.return_value = [{"test": "data"}]
        mock_nv.create_batch_base_controlnet_spec.return_value = {
            "prompt": "",
            "input_video_path": "",
        }
        return mock_nv

    def teardown_method(self):
        """Clean up after each test method."""
        # Restore original directory
        os.chdir(self.original_cwd)
        # Remove temp directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_execute_batch_runs_successful(self):
        """Test successful batch execution with multiple runs."""
        # Create outputs directory in temp dir
        Path("outputs").mkdir(exist_ok=True)

        # Mock batch inference result with files in video_X subdirectories
        self.mock_docker_executor.run_batch_inference.return_value = {
            "batch_name": "batch_test",
            "output_dir": "/remote/outputs/batch_test",
            "status": "completed",
            "output_files": [
                "/remote/outputs/batch_test/video_0/output.mp4",
                "/remote/outputs/batch_test/video_1/output.mp4",
            ],
        }

        # Mock nvidia_format functions
        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            self._setup_nvidia_format_mock(mock_nv)

            # Mock to_cosmos_inference_json to return a valid dict for each call
            mock_nv.to_cosmos_inference_json.side_effect = [
                {
                    "visual_input": "video1.mp4",
                    "prompt": "First prompt",
                    "name": "rs_001",
                    "weights": {"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2},
                },
                {
                    "visual_input": "video2.mp4",
                    "prompt": "Second prompt",
                    "name": "rs_002",
                    "weights": {"vis": 0.5, "edge": 0.5, "depth": 0.0, "seg": 0.0},
                },
            ]

            # Execute batch
            result = self.orchestrator.execute_batch_runs(self.test_runs_and_prompts)

            # Verify success
            assert result["status"] == "success"
            assert "batch_name" in result

            # Note: to_cosmos_inference_json is not called in batch mode
            # It's only used for individual inference, not batch

            # Verify batch inference was called
            self.mock_docker_executor.run_batch_inference.assert_called_once()
            call_kwargs = self.mock_docker_executor.run_batch_inference.call_args.kwargs
            assert call_kwargs["batch_name"].startswith("batch_")
            assert call_kwargs["batch_jsonl_file"] == "batch.jsonl"

    def test_execute_batch_runs_auto_generates_batch_name(self):
        """Test that batch name is auto-generated when not provided."""
        # Create outputs directory in temp dir
        Path("outputs").mkdir(exist_ok=True)

        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            self._setup_nvidia_format_mock(mock_nv)
            # Mock to_cosmos_inference_json to return a valid dict for each call
            mock_nv.to_cosmos_inference_json.side_effect = [
                {
                    "visual_input": "video1.mp4",
                    "prompt": "First prompt",
                    "name": "rs_001",
                    "weights": {"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2},
                },
                {
                    "visual_input": "video2.mp4",
                    "prompt": "Second prompt",
                    "name": "rs_002",
                    "weights": {"vis": 0.5, "edge": 0.5, "depth": 0.0, "seg": 0.0},
                },
            ]

            self.mock_docker_executor.run_batch_inference.return_value = {
                "batch_name": "auto_name",
                "output_dir": "/remote/outputs/auto",
                "status": "completed",
                "output_files": [],
            }

            # Execute without batch_name
            result = self.orchestrator.execute_batch_runs(self.test_runs_and_prompts)

            # Should have auto-generated name
            assert result["batch_name"].startswith("batch_")
            assert len(result["batch_name"]) > 10  # Has timestamp
            assert result["status"] == "success"

    def test_execute_batch_runs_uploads_all_video_files(self):
        """Test that all referenced video files are uploaded."""
        # Create outputs directory in temp dir
        Path("outputs").mkdir(exist_ok=True)

        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            self._setup_nvidia_format_mock(mock_nv)
            # Mock to_cosmos_inference_json to return a valid dict for each call
            mock_nv.to_cosmos_inference_json.side_effect = [
                {"visual_input": "video1.mp4", "prompt": "First", "name": "rs_001", "weights": {}},
                {"visual_input": "video2.mp4", "prompt": "Second", "name": "rs_002", "weights": {}},
            ]

            self.mock_docker_executor.run_batch_inference.return_value = {
                "status": "completed",
                "output_files": [],
            }

            # Create temporary video files
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create video files
                video1 = Path(tmpdir) / "video1.mp4"
                video2 = Path(tmpdir) / "video2.mp4"
                depth2 = Path(tmpdir) / "depth2.mp4"
                video1.write_text("video1")
                video2.write_text("video2")
                depth2.write_text("depth")

                # Update test data with temp paths
                test_runs = [
                    (
                        {"id": "rs_001", "execution_config": {}},
                        {
                            "id": "ps_001",
                            "prompt_text": "First",
                            "inputs": {"video": str(video1)},
                        },
                    ),
                    (
                        {"id": "rs_002", "execution_config": {}},
                        {
                            "id": "ps_002",
                            "prompt_text": "Second",
                            "inputs": {"video": str(video2), "depth": str(depth2)},
                        },
                    ),
                ]

                # Execute batch
                self.orchestrator.execute_batch_runs(test_runs)

                # Check uploaded files
                uploaded = self.fake_file_transfer.uploaded_files
                assert (
                    len(uploaded) >= 3
                )  # batch.jsonl + 2 video files (only 'video' key is uploaded)

                # Check video files were uploaded (only video key, not depth)
                uploaded_names = [Path(f["local"]).name for f in uploaded]
                assert "batch.jsonl" in uploaded_names
                assert "video1.mp4" in uploaded_names
                assert "video2.mp4" in uploaded_names
                # Note: depth2.mp4 is NOT uploaded as the code only uploads 'video' key files

    def test_execute_batch_runs_handles_batch_failure(self):
        """Test handling of batch execution failure."""
        # Create outputs directory in temp dir
        Path("outputs").mkdir(exist_ok=True)

        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            self._setup_nvidia_format_mock(mock_nv)
            # Mock to_cosmos_inference_json to return a valid dict for each call
            mock_nv.to_cosmos_inference_json.side_effect = [
                {
                    "visual_input": "video1.mp4",
                    "prompt": "First prompt",
                    "name": "rs_001",
                    "weights": {"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2},
                },
                {
                    "visual_input": "video2.mp4",
                    "prompt": "Second prompt",
                    "name": "rs_002",
                    "weights": {"vis": 0.5, "edge": 0.5, "depth": 0.0, "seg": 0.0},
                },
            ]

            # Mock batch inference failure
            self.mock_docker_executor.run_batch_inference.side_effect = Exception(
                "GPU out of memory"
            )

            # Execute batch
            result = self.orchestrator.execute_batch_runs(self.test_runs_and_prompts)

            # Should return failure status
            assert result["status"] == "failed"
            assert "GPU out of memory" in result["error"]

    def test_execute_batch_runs_empty_batch(self):
        """Test handling of empty batch."""
        # Execute empty batch - should return immediately without patching anything
        result = self.orchestrator.execute_batch_runs([])

        # Should handle gracefully
        assert result["status"] == "success"
        assert "batch_name" in result
        assert result["batch_name"] == "empty_batch"
        assert result["output_mapping"] == {}

    def test_execute_batch_runs_downloads_outputs_to_individual_folders(self):
        """Test that outputs are downloaded to individual run folders."""
        # Create outputs directory in temp dir
        Path("outputs").mkdir(exist_ok=True)

        # Mock batch inference result with files in video_0 and video_1 subdirs
        self.mock_docker_executor.run_batch_inference.return_value = {
            "batch_name": "batch_test",
            "output_dir": "/remote/outputs/batch_test",
            "status": "completed",
            "output_files": [
                "/remote/outputs/batch_test/video_0/output.mp4",
                "/remote/outputs/batch_test/video_1/output.mp4",
            ],
        }

        # Mock service.update_run to track updates
        run_updates = {}

        def track_updates(run_id, **kwargs):
            if "outputs" in kwargs:
                run_updates[run_id] = kwargs["outputs"]

        # Create mock service if not present
        if not hasattr(self.orchestrator, "service"):
            self.orchestrator.service = Mock()

        self.orchestrator.service.update_run = Mock(side_effect=track_updates)
        self.orchestrator.service.update_run_status = Mock()

        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            self._setup_nvidia_format_mock(mock_nv)

            # Execute batch
            result = self.orchestrator.execute_batch_runs(self.test_runs_and_prompts)

            # Check download calls - files should be downloaded to batch_test/video_X subdirs
            downloaded = self.fake_file_transfer.downloaded_files

            # Should download output files to batch directory
            downloaded_paths = [str(f["local"]).replace("\\", "/") for f in downloaded]

            # The downloads should have happened for the outputs (2 videos + 1 log)
            assert len(downloaded) == 3, (
                f"Expected 3 downloads, got {len(downloaded)}. Downloaded: {downloaded}"
            )

            # Check that downloads went to batch directory with video_X subdirs
            assert any("batch_" in p and "video_0" in p for p in downloaded_paths), (
                f"video_0 not in paths: {downloaded_paths}"
            )
            assert any("batch_" in p and "video_1" in p for p in downloaded_paths), (
                f"video_1 not in paths: {downloaded_paths}"
            )

            # Check result structure (no output_mapping in current implementation)
            assert result["status"] == "success"
            assert "batch_name" in result
            # batch_name is auto-generated, not the one from docker result
            assert result["batch_name"].startswith("batch_rs_")

            # Check that runs were updated with output paths
            assert "rs_001" in run_updates
            assert "rs_002" in run_updates
            assert "output_path" in run_updates["rs_001"]
            assert "output_path" in run_updates["rs_002"]

    def test_execute_batch_runs_with_mixed_video_inputs(self):
        """Test batch execution with different video input combinations."""
        # Create outputs directory in temp dir
        Path("outputs").mkdir(exist_ok=True)

        test_runs = [
            (
                {"id": "rs_001", "execution_config": {"weights": {"vis": 1.0}}},
                {
                    "id": "ps_001",
                    "prompt_text": "Only color",
                    "inputs": {"video": "color1.mp4"},
                },
            ),
            (
                {"id": "rs_002", "execution_config": {"weights": {"depth": 0.5}}},
                {
                    "id": "ps_002",
                    "prompt_text": "With depth",
                    "inputs": {"video": "color2.mp4", "depth": "depth2.mp4"},
                },
            ),
            (
                {"id": "rs_003", "execution_config": {"weights": {"seg": 0.5}}},
                {
                    "id": "ps_003",
                    "prompt_text": "With all",
                    "inputs": {
                        "video": "color3.mp4",
                        "depth": "depth3.mp4",
                        "seg": "seg3.mp4",
                    },
                },
            ),
        ]

        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            self._setup_nvidia_format_mock(mock_nv)
            # Mock to_cosmos_inference_json to return a valid dict for each call
            mock_nv.to_cosmos_inference_json.side_effect = [
                {
                    "visual_input": "color1.mp4",
                    "prompt": "Only color",
                    "name": "rs_001",
                    "weights": {"vis": 1.0},
                },
                {
                    "visual_input": "color2.mp4",
                    "prompt": "With depth",
                    "name": "rs_002",
                    "weights": {"depth": 0.5},
                },
                {
                    "visual_input": "color3.mp4",
                    "prompt": "With all",
                    "name": "rs_003",
                    "weights": {"seg": 0.5},
                },
            ]

            self.mock_docker_executor.run_batch_inference.return_value = {
                "status": "completed",
                "output_files": [],
            }

            # Execute batch with mixed inputs
            result = self.orchestrator.execute_batch_runs(test_runs)

            # Should handle all input combinations
            assert result["status"] == "success"
            assert "batch_name" in result

    def test_execute_batch_runs_uploads_batch_json(self):
        """Test that batch.jsonl file is uploaded."""
        # Create outputs directory in temp dir
        Path("outputs").mkdir(exist_ok=True)

        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            self._setup_nvidia_format_mock(mock_nv)

            self.mock_docker_executor.run_batch_inference.return_value = {
                "status": "completed",
                "output_files": [],
            }

            # Track calls to upload_file
            upload_calls = []

            def track_upload(local_path, remote_dir):
                upload_calls.append((str(local_path), remote_dir))
                # Don't call original since file may not exist
                return True

            self.fake_file_transfer.upload_file = track_upload

            # Execute batch
            self.orchestrator.execute_batch_runs(self.test_runs_and_prompts)

            # Check that batch.jsonl was uploaded
            batch_json_uploaded = any("batch.jsonl" in str(call[0]) for call in upload_calls)

            # batch.jsonl should be uploaded
            assert batch_json_uploaded, f"batch.jsonl not found in upload calls: {upload_calls}"
