"""Test batch execution functionality in GPUExecutor.

Tests the orchestration of batch inference runs without using actual GPU resources.
Uses fakes and mocks to verify behavior of batch processing."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from cosmos_workflow.execution.gpu_executor import GPUExecutor
from tests.fixtures.fakes import FakeFileTransferService, FakeSSHManager


class TestGPUExecutorBatchExecution:
    """Test suite for batch execution in GPUExecutor."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
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

        # Replace services with mocks/fakes
        self.orchestrator.ssh_manager = self.fake_ssh
        self.orchestrator.file_transfer = self.fake_file_transfer
        self.orchestrator.docker_executor = self.mock_docker_executor
        self.orchestrator.config_manager = self.mock_config_manager

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

    def test_execute_batch_runs_successful(self):
        """Test successful batch execution with multiple runs."""
        # Mock batch inference result
        self.mock_docker_executor.run_batch_inference.return_value = {
            "batch_name": "batch_test",
            "output_dir": "/remote/outputs/batch_test",
            "output_files": [
                "/remote/outputs/batch_test/video_000.mp4",
                "/remote/outputs/batch_test/video_001.mp4",
            ],
        }

        # Mock output splitting
        with patch.object(self.orchestrator, "_split_batch_outputs") as mock_split:
            mock_split.return_value = {
                "rs_001": {
                    "remote_path": "/remote/outputs/batch_test/video_000.mp4",
                    "batch_index": 0,
                    "status": "found",
                },
                "rs_002": {
                    "remote_path": "/remote/outputs/batch_test/video_001.mp4",
                    "batch_index": 1,
                    "status": "found",
                },
            }

            # Mock nvidia_format functions
            with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
                mock_nv.to_cosmos_batch_inference_jsonl.return_value = [
                    {"visual_input": "video1.mp4", "prompt": "First"},
                    {"visual_input": "video2.mp4", "prompt": "Second"},
                ]
                mock_nv.write_batch_jsonl.return_value = Path("/tmp/batch.jsonl")

                # Execute batch
                result = self.orchestrator.execute_batch_runs(
                    self.test_runs_and_prompts,
                    batch_name="batch_test",
                )

                # Verify success
                assert result["status"] == "success"
                assert result["batch_name"] == "batch_test"
                assert result["num_runs"] == 2
                assert "output_mapping" in result
                assert len(result["output_mapping"]) == 2

                # Verify JSONL was created
                mock_nv.to_cosmos_batch_inference_jsonl.assert_called_once_with(
                    self.test_runs_and_prompts
                )

                # Verify batch inference was called
                self.mock_docker_executor.run_batch_inference.assert_called_once()
                call_args = self.mock_docker_executor.run_batch_inference.call_args
                assert call_args[0][0] == "batch_test"  # batch_name
                assert call_args[0][1] == "batch_test.jsonl"  # jsonl_file

    def test_execute_batch_runs_auto_generates_batch_name(self):
        """Test that batch name is auto-generated when not provided."""
        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            mock_nv.to_cosmos_batch_inference_jsonl.return_value = []
            mock_nv.write_batch_jsonl.return_value = Path("/tmp/batch.jsonl")

            self.mock_docker_executor.run_batch_inference.return_value = {
                "batch_name": "auto_name",
                "output_dir": "/remote/outputs/auto",
                "output_files": [],
            }

            with patch.object(self.orchestrator, "_split_batch_outputs") as mock_split:
                mock_split.return_value = {}

                # Execute without batch_name
                result = self.orchestrator.execute_batch_runs(self.test_runs_and_prompts)

                # Should have auto-generated name
                assert result["batch_name"].startswith("batch_")
                assert len(result["batch_name"]) > 10  # Has timestamp

    def test_execute_batch_runs_uploads_all_video_files(self):
        """Test that all referenced video files are uploaded."""
        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            mock_nv.to_cosmos_batch_inference_jsonl.return_value = []
            mock_nv.write_batch_jsonl.return_value = Path("/tmp/batch.jsonl")

            self.mock_docker_executor.run_batch_inference.return_value = {"output_files": []}

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

                with patch.object(self.orchestrator, "_split_batch_outputs"):
                    # Execute batch
                    self.orchestrator.execute_batch_runs(test_runs)

                    # Check uploaded files
                    uploaded = self.fake_file_transfer.uploaded_files
                    assert len(uploaded) >= 4  # JSONL + 3 videos

                    # Check video files were uploaded
                    uploaded_names = [f["local_path"].name for f in uploaded]
                    assert "video1.mp4" in uploaded_names
                    assert "video2.mp4" in uploaded_names
                    assert "depth2.mp4" in uploaded_names

    def test_execute_batch_runs_handles_batch_failure(self):
        """Test handling of batch execution failure."""
        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            mock_nv.to_cosmos_batch_inference_jsonl.return_value = []
            mock_nv.write_batch_jsonl.return_value = Path("/tmp/batch.jsonl")

            # Mock batch inference failure
            self.mock_docker_executor.run_batch_inference.side_effect = Exception(
                "GPU out of memory"
            )

            # Execute batch
            result = self.orchestrator.execute_batch_runs(
                self.test_runs_and_prompts,
                batch_name="failed_batch",
            )

            # Should return failure status
            assert result["status"] == "failed"
            assert result["batch_name"] == "failed_batch"
            assert "GPU out of memory" in result["error"]

    def test_execute_batch_runs_empty_batch(self):
        """Test handling of empty batch."""
        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            mock_nv.to_cosmos_batch_inference_jsonl.return_value = []
            mock_nv.write_batch_jsonl.return_value = Path("/tmp/empty.jsonl")

            self.mock_docker_executor.run_batch_inference.return_value = {"output_files": []}

            with patch.object(self.orchestrator, "_split_batch_outputs") as mock_split:
                mock_split.return_value = {}

                # Execute empty batch
                result = self.orchestrator.execute_batch_runs([])

                # Should handle gracefully
                assert result["status"] == "success"
                assert result["num_runs"] == 0

    def test_split_batch_outputs_exact_matching(self):
        """Test output splitting with exact run_id matching."""
        batch_result = {
            "output_files": [
                "/outputs/batch/rs_001_output.mp4",
                "/outputs/batch/rs_002_result.mp4",
                "/outputs/batch/rs_003_video.mp4",
            ]
        }

        runs_and_prompts = [
            ({"id": "rs_001"}, {"id": "ps_001"}),
            ({"id": "rs_002"}, {"id": "ps_002"}),
            ({"id": "rs_003"}, {"id": "ps_003"}),
        ]

        # Split outputs
        mapping = self.orchestrator._split_batch_outputs(runs_and_prompts, batch_result)

        # Should match by run_id in filename
        assert mapping["rs_001"]["remote_path"] == "/outputs/batch/rs_001_output.mp4"
        assert mapping["rs_001"]["status"] == "found"
        assert mapping["rs_002"]["remote_path"] == "/outputs/batch/rs_002_result.mp4"
        assert mapping["rs_002"]["status"] == "found"
        assert mapping["rs_003"]["remote_path"] == "/outputs/batch/rs_003_video.mp4"
        assert mapping["rs_003"]["status"] == "found"

    def test_split_batch_outputs_index_matching(self):
        """Test output splitting with index-based matching."""
        batch_result = {
            "output_files": [
                "/outputs/batch/video_000_output.mp4",
                "/outputs/batch/video_001_output.mp4",
                "/outputs/batch/video_002_output.mp4",
            ]
        }

        runs_and_prompts = [
            ({"id": "rs_abc"}, {"id": "ps_001"}),
            ({"id": "rs_def"}, {"id": "ps_002"}),
            ({"id": "rs_ghi"}, {"id": "ps_003"}),
        ]

        # Split outputs
        mapping = self.orchestrator._split_batch_outputs(runs_and_prompts, batch_result)

        # Should match by index in filename
        assert mapping["rs_abc"]["remote_path"] == "/outputs/batch/video_000_output.mp4"
        assert mapping["rs_abc"]["batch_index"] == 0
        assert mapping["rs_def"]["remote_path"] == "/outputs/batch/video_001_output.mp4"
        assert mapping["rs_def"]["batch_index"] == 1
        assert mapping["rs_ghi"]["remote_path"] == "/outputs/batch/video_002_output.mp4"
        assert mapping["rs_ghi"]["batch_index"] == 2

    def test_split_batch_outputs_sequential_fallback(self):
        """Test sequential matching when no pattern matches."""
        batch_result = {
            "output_files": [
                "/outputs/batch/output1.mp4",
                "/outputs/batch/output2.mp4",
                "/outputs/batch/output3.mp4",
            ]
        }

        runs_and_prompts = [
            ({"id": "rs_aaa"}, {"id": "ps_001"}),
            ({"id": "rs_bbb"}, {"id": "ps_002"}),
            ({"id": "rs_ccc"}, {"id": "ps_003"}),
        ]

        # Split outputs
        mapping = self.orchestrator._split_batch_outputs(runs_and_prompts, batch_result)

        # Should fall back to sequential matching
        assert mapping["rs_aaa"]["remote_path"] == "/outputs/batch/output1.mp4"
        assert mapping["rs_aaa"]["status"] == "assumed"
        assert mapping["rs_bbb"]["remote_path"] == "/outputs/batch/output2.mp4"
        assert mapping["rs_bbb"]["status"] == "assumed"
        assert mapping["rs_ccc"]["remote_path"] == "/outputs/batch/output3.mp4"
        assert mapping["rs_ccc"]["status"] == "assumed"

    def test_split_batch_outputs_missing_outputs(self):
        """Test handling when some outputs are missing."""
        batch_result = {
            "output_files": [
                "/outputs/batch/video_000.mp4",
                "/outputs/batch/video_001.mp4",
                # video_002 is missing
            ]
        }

        runs_and_prompts = [
            ({"id": "rs_001"}, {"id": "ps_001"}),
            ({"id": "rs_002"}, {"id": "ps_002"}),
            ({"id": "rs_003"}, {"id": "ps_003"}),  # This one will be missing
        ]

        # Split outputs
        mapping = self.orchestrator._split_batch_outputs(runs_and_prompts, batch_result)

        # First two should be matched
        assert mapping["rs_001"]["status"] in ["found", "assumed"]
        assert mapping["rs_002"]["status"] in ["found", "assumed"]

        # Third should be marked as missing
        assert mapping["rs_003"]["remote_path"] is None
        assert mapping["rs_003"]["status"] == "missing"

    def test_split_batch_outputs_no_outputs(self):
        """Test handling when there are no output files."""
        batch_result = {"output_files": []}

        runs_and_prompts = [
            ({"id": "rs_001"}, {"id": "ps_001"}),
            ({"id": "rs_002"}, {"id": "ps_002"}),
        ]

        # Split outputs
        mapping = self.orchestrator._split_batch_outputs(runs_and_prompts, batch_result)

        # All should be marked as missing
        assert mapping["rs_001"]["remote_path"] is None
        assert mapping["rs_001"]["status"] == "missing"
        assert mapping["rs_002"]["remote_path"] is None
        assert mapping["rs_002"]["status"] == "missing"

    def test_execute_batch_runs_downloads_outputs_to_individual_folders(self):
        """Test that outputs are downloaded to individual run folders."""
        # Mock batch inference result
        self.mock_docker_executor.run_batch_inference.return_value = {
            "batch_name": "batch_test",
            "output_dir": "/remote/outputs/batch_test",
            "output_files": [
                "/remote/outputs/batch_test/video_000.mp4",
                "/remote/outputs/batch_test/video_001.mp4",
            ],
        }

        with patch.object(self.orchestrator, "_split_batch_outputs") as mock_split:
            mock_split.return_value = {
                "rs_001": {
                    "remote_path": "/remote/outputs/batch_test/video_000.mp4",
                    "batch_index": 0,
                    "status": "found",
                },
                "rs_002": {
                    "remote_path": "/remote/outputs/batch_test/video_001.mp4",
                    "batch_index": 1,
                    "status": "found",
                },
            }

            with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
                mock_nv.to_cosmos_batch_inference_jsonl.return_value = []
                mock_nv.write_batch_jsonl.return_value = Path("/tmp/batch.jsonl")

                # Execute batch
                result = self.orchestrator.execute_batch_runs(self.test_runs_and_prompts)

                # Check download calls
                downloaded = self.fake_file_transfer.downloaded_files

                # Should download to individual run folders
                downloaded_paths = [str(f["local_path"]).replace("\\", "/") for f in downloaded]
                assert any("outputs/run_rs_001/output.mp4" in p for p in downloaded_paths)
                assert any("outputs/run_rs_002/output.mp4" in p for p in downloaded_paths)

                # Check output mapping has local paths
                output_mapping = result["output_mapping"]
                assert "local_path" in output_mapping["rs_001"]
                assert "local_path" in output_mapping["rs_002"]

    def test_execute_batch_runs_with_mixed_video_inputs(self):
        """Test batch execution with different video input combinations."""
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
            batch_data = []
            mock_nv.to_cosmos_batch_inference_jsonl.return_value = batch_data
            mock_nv.write_batch_jsonl.return_value = Path("/tmp/batch.jsonl")

            self.mock_docker_executor.run_batch_inference.return_value = {"output_files": []}

            with patch.object(self.orchestrator, "_split_batch_outputs") as mock_split:
                mock_split.return_value = {}

                # Execute batch with mixed inputs
                result = self.orchestrator.execute_batch_runs(test_runs)

                # Should handle all input combinations
                assert result["status"] == "success"
                assert result["num_runs"] == 3

    def test_execute_batch_runs_uploads_batch_script(self):
        """Test that batch_inference.sh script is uploaded if it exists."""
        with patch("cosmos_workflow.execution.gpu_executor.nvidia_format") as mock_nv:
            mock_nv.to_cosmos_batch_inference_jsonl.return_value = []
            mock_nv.write_batch_jsonl.return_value = Path("/tmp/batch.jsonl")

            self.mock_docker_executor.run_batch_inference.return_value = {"output_files": []}

            with patch.object(self.orchestrator, "_split_batch_outputs"):
                # Mock Path.exists to return True for batch_inference.sh
                with patch.object(Path, "exists") as mock_exists:
                    mock_exists.return_value = True

                    # Execute batch
                    self.orchestrator.execute_batch_runs(self.test_runs_and_prompts)

                    # Check that script upload was attempted
                    uploaded_files = self.fake_file_transfer.uploaded_files
                    script_uploaded = any(
                        "batch_inference.sh" in str(f["local_path"]) for f in uploaded_files
                    )

                    # Script should be uploaded since we mocked it exists
                    assert script_uploaded
