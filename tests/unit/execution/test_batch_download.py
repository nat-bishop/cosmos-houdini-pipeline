"""Test batch output download and renaming logic."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call

from cosmos_workflow.execution.gpu_executor import GPUExecutor


class TestBatchDownload:
    """Test downloading batch outputs to individual run directories."""

    def test_download_batch_output_for_run(self):
        """Test downloading and renaming batch output to run directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mocks
            mock_ssh = MagicMock()
            mock_remote_config = MagicMock()
            mock_remote_config.remote_dir = "/workspace"
            mock_config = MagicMock()
            mock_config.get_remote_config.return_value = mock_remote_config
            mock_file_transfer = MagicMock()

            # Create GPUExecutor instance
            executor = GPUExecutor(mock_ssh, mock_config)
            executor.file_transfer = mock_file_transfer
            executor.config_manager = mock_config

            # Change working directory to temp for testing
            import os

            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                # Test the download
                executor._download_batch_output_for_run(
                    run_id="run_123",
                    remote_batch_output="/workspace/outputs/batch_20241206/video_000.mp4",
                    batch_name="batch_20241206",
                )

                # Verify directories were created
                assert Path("outputs/run_123").exists()
                assert Path("outputs/run_123/outputs").exists()
                assert Path("outputs/run_123/logs").exists()

                # Verify download calls
                calls = mock_file_transfer.download_file.call_args_list

                # First call should be for the video file
                assert calls[0] == call(
                    "/workspace/outputs/batch_20241206/video_000.mp4",
                    str(Path("outputs/run_123/outputs/output.mp4")),
                )

                # Second call should be for the batch log (batch_run.log from batch output)
                assert calls[1] == call(
                    "/workspace/outputs/batch_20241206/batch_run.log",
                    str(Path("outputs/run_123/logs/batch.log")),
                )

                # Verify run.log was created with reference to batch
                run_log = Path("outputs/run_123/logs/run.log")
                assert run_log.exists()
                assert "batch_20241206" in run_log.read_text()

            finally:
                os.chdir(original_cwd)

    def test_download_handles_missing_batch_log(self):
        """Test that missing batch log doesn't fail the download."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mocks
            mock_ssh = MagicMock()
            mock_remote_config = MagicMock()
            mock_remote_config.remote_dir = "/workspace"
            mock_config = MagicMock()
            mock_config.get_remote_config.return_value = mock_remote_config
            mock_file_transfer = MagicMock()

            # Create GPUExecutor instance
            executor = GPUExecutor(mock_ssh, mock_config)
            executor.file_transfer = mock_file_transfer
            executor.config_manager = mock_config

            # Make batch log download fail
            def download_side_effect(remote, local):
                if "batch.log" in remote:
                    raise Exception("File not found")
                return None

            mock_file_transfer.download_file.side_effect = download_side_effect

            # Change working directory to temp for testing
            import os

            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                # This should not raise an exception
                executor._download_batch_output_for_run(
                    run_id="run_456",
                    remote_batch_output="/workspace/outputs/batch_xyz/video_001.mp4",
                    batch_name="batch_xyz",
                )

                # Verify main file download was attempted
                assert mock_file_transfer.download_file.call_count >= 1

                # Verify directories were still created
                assert Path("outputs/run_456").exists()

                # Verify run.log was still created even without batch log
                run_log = Path("outputs/run_456/logs/run.log")
                assert run_log.exists()
                assert "batch_xyz" in run_log.read_text()

            finally:
                os.chdir(original_cwd)

    def test_download_creates_error_file_on_failure(self):
        """Test that download failure creates an error marker file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mocks
            mock_ssh = MagicMock()
            mock_remote_config = MagicMock()
            mock_remote_config.remote_dir = "/workspace"
            mock_config = MagicMock()
            mock_config.get_remote_config.return_value = mock_remote_config
            mock_file_transfer = MagicMock()

            # Create GPUExecutor instance
            executor = GPUExecutor(mock_ssh, mock_config)
            executor.file_transfer = mock_file_transfer
            executor.config_manager = mock_config

            # Make main download fail
            mock_file_transfer.download_file.side_effect = Exception("Network error")

            # Change working directory to temp for testing
            import os

            original_cwd = os.getcwd()
            os.chdir(tmpdir)

            try:
                # Run the download (should not raise)
                executor._download_batch_output_for_run(
                    run_id="run_789",
                    remote_batch_output="/workspace/outputs/batch_abc/video_002.mp4",
                    batch_name="batch_abc",
                )

                # Verify error file was created
                error_file = Path("outputs/run_789/outputs/download_error.txt")
                assert error_file.exists()

                # Check error message content
                error_content = error_file.read_text()
                assert "Failed to download output" in error_content
                assert "Network error" in error_content

            finally:
                os.chdir(original_cwd)
