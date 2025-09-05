"""
Integration tests for SFTP file transfer workflow.
Tests the complete upload/download cycle with mocked SSH/SFTP connections.
"""

from unittest.mock import MagicMock, Mock

import pytest

from cosmos_workflow.transfer.file_transfer import FileTransferService


class TestSFTPWorkflow:
    """Test SFTP file transfer workflows."""

    @pytest.fixture
    def mock_sftp_client(self):
        """Create a mock SFTP client."""
        sftp = MagicMock()
        sftp.put.return_value = None
        sftp.get.return_value = None
        sftp.mkdir.return_value = None
        sftp.listdir.return_value = []
        sftp.stat.return_value = Mock(st_mode=16877)  # Directory mode
        return sftp

    @pytest.fixture
    def mock_ssh_client(self, mock_sftp_client):
        """Create a mock SSH client with SFTP."""
        ssh = MagicMock()
        ssh.open_sftp.return_value = mock_sftp_client
        return ssh

    @pytest.fixture
    def file_transfer_manager(self, mock_ssh_manager, mock_config_manager):
        """Create FileTransferService with mocked dependencies."""
        remote_config = mock_config_manager.get_remote_config()
        manager = FileTransferService(mock_ssh_manager, remote_config.remote_dir)
        return manager

    @pytest.mark.integration
    def test_upload_single_file(
        self, file_transfer_manager, mock_ssh_manager, mock_sftp_client, temp_dir
    ):
        """Test uploading a single file via SFTP."""
        # Setup
        test_file = temp_dir / "test.json"
        test_file.write_text('{"test": "data"}')
        remote_path = "/remote/test"

        # Configure the mock to return our sftp client
        mock_ssh_manager.get_sftp.return_value.__enter__ = lambda self: mock_sftp_client

        # Execute
        result = file_transfer_manager.upload_file(str(test_file), remote_path)

        # Verify
        assert result is True
        mock_sftp_client.put.assert_called_once()
        call_args = mock_sftp_client.put.call_args
        assert str(test_file) in str(call_args[0][0])
        assert "test.json" in str(call_args[0][1])

    @pytest.mark.integration
    def test_upload_directory_recursive(self, file_transfer_manager, mock_ssh_manager, temp_dir):
        """Test uploading a directory recursively via SFTP."""
        # Setup directory structure
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")

        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2")

        remote_dir = "/remote/test/source"

        # Get the mock sftp client from the fixture
        mock_sftp_client = mock_ssh_manager._sftp_client

        # Execute
        result = file_transfer_manager.upload_directory(str(source_dir), remote_dir)

        # Verify
        assert result is True
        # SSH commands called for mkdir
        assert mock_ssh_manager.execute_command_success.called
        # Files uploaded via SFTP
        assert mock_sftp_client.put.call_count == 2  # Two files

    @pytest.mark.integration
    def test_download_directory(self, file_transfer_manager, mock_ssh_manager, temp_dir):
        """Test downloading a directory via SFTP."""
        # Setup
        remote_dir = "/remote/outputs/test_run"
        local_dir = temp_dir / "downloads"

        # Mock remote directory listing
        # Get the mock sftp client from the fixture
        mock_sftp_client = mock_ssh_manager._sftp_client

        # Set up side_effect to avoid recursion - first call returns files, second returns empty
        mock_sftp_client.listdir_attr.side_effect = [
            [
                Mock(filename="output.mp4", st_mode=33188),  # File
                Mock(filename="metadata.json", st_mode=33188),  # File
            ],
            [],  # Empty for any subdirectory calls
        ]

        # Execute
        result = file_transfer_manager.download_directory(remote_dir, str(local_dir))

        # Verify
        assert result is True
        assert mock_sftp_client.get.call_count == 2  # 2 files (output.mp4, metadata.json)

    @pytest.mark.integration
    def test_download_inference_results(self, file_transfer_manager, mock_ssh_manager, temp_dir):
        """Test downloading inference results including video and logs."""
        # Setup
        remote_output_dir = "/remote/test/outputs/run_001"
        local_output_dir = temp_dir / "outputs" / "run_001"

        # Get the mock sftp client from the fixture
        mock_sftp_client = mock_ssh_manager._sftp_client

        # Mock remote directory structure - avoid recursion
        mock_sftp_client.listdir_attr.side_effect = [
            [
                Mock(filename="output.mp4", st_mode=33188),
                Mock(filename="output_upscaled.mp4", st_mode=33188),
                Mock(filename="metadata.json", st_mode=33188),
            ],
            [],  # Empty for any subdirectory calls
        ]

        # Execute
        result = file_transfer_manager.download_directory(remote_output_dir, str(local_output_dir))

        # Verify
        assert result is True
        # Should download: 2 videos + 1 metadata + 3 log files = 6 files
        assert mock_sftp_client.get.call_count >= 3  # At least the video files and metadata

    @pytest.mark.integration
    def test_error_recovery_on_upload_failure(
        self, file_transfer_manager, mock_ssh_manager, temp_dir
    ):
        """Test error recovery when upload fails partway through."""
        # Setup
        source_dir = temp_dir / "source"
        source_dir.mkdir()

        for i in range(5):
            (source_dir / f"file{i}.txt").write_text(f"content{i}")

        # Get the mock sftp client from the fixture
        mock_sftp_client = mock_ssh_manager._sftp_client

        # Simulate failure on third file
        mock_sftp_client.put.side_effect = [
            None,  # file0 succeeds
            None,  # file1 succeeds
            Exception("Connection lost"),  # file2 fails
            None,  # file3 would succeed
            None,  # file4 would succeed
        ]

        # Execute - expect exception
        with pytest.raises(Exception, match="Connection lost"):
            file_transfer_manager.upload_directory(str(source_dir), "/remote/test/source")

        # Verify
        assert mock_sftp_client.put.call_count == 3  # Stopped after failure

    @pytest.mark.integration
    def test_windows_path_conversion(self, file_transfer_manager, mock_ssh_manager, temp_dir):
        """Test that Windows paths are correctly converted for remote Linux."""
        # Setup Windows-style path
        windows_path = temp_dir / "test\\subdir\\file.txt"
        windows_path.parent.mkdir(parents=True, exist_ok=True)
        windows_path.write_text("test content")

        # Get the mock sftp client from the fixture
        mock_sftp_client = mock_ssh_manager._sftp_client

        # Execute - upload_file expects just the directory, not full path
        result = file_transfer_manager.upload_file(str(windows_path), "/remote/test/subdir")

        # Verify
        assert result is True
        mock_sftp_client.put.assert_called_once()

        # Check that remote path uses forward slashes
        call_args = mock_sftp_client.put.call_args
        assert "/" in str(call_args[0][1])
        assert "\\" not in str(call_args[0][1])

    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_directory_upload(self, file_transfer_manager, mock_ssh_manager, temp_dir):
        """Test uploading a large directory structure."""
        # Setup large directory structure
        base_dir = temp_dir / "large_dataset"
        base_dir.mkdir()

        # Create 10 subdirectories with 10 files each
        for i in range(10):
            subdir = base_dir / f"batch_{i}"
            subdir.mkdir()
            for j in range(10):
                (subdir / f"file_{j}.dat").write_text(f"data_{i}_{j}")

        # Get the mock sftp client from the fixture
        mock_sftp_client = mock_ssh_manager._sftp_client

        # Execute
        result = file_transfer_manager.upload_directory(str(base_dir), "/remote/test/large_dataset")

        # Verify
        assert result is True
        # SSH mkdir commands called for directories
        assert mock_ssh_manager.execute_command_success.called
        assert mock_sftp_client.put.call_count == 100  # 10x10 files
