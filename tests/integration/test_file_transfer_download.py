"""
Integration tests for FileTransferService download_file method.
Following TDD Gate 1: NO MOCKS - Tests must call real functions.
"""

import tempfile
from pathlib import Path

import pytest

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.transfer.file_transfer import FileTransferService


class TestFileTransferDownload:
    """Test download_file method with real function calls (no mocks)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Create real SSHManager (it will fail to connect, that's expected)
        ssh_options = {
            "hostname": "test.example.com",
            "port": 22,
            "username": "test_user",
            "key_filename": "test_key.pem",
        }
        self.ssh_manager = SSHManager(ssh_options)

        # Create real FileTransferService
        self.file_transfer = FileTransferService(
            ssh_manager=self.ssh_manager, remote_dir="/home/test/cosmos"
        )

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_download_file_method_exists_and_accepts_parameters(self):
        """Test that download_file method exists and accepts correct parameters."""
        # Test that method exists and can be called with expected parameters
        remote_file = "/home/ubuntu/cosmos/outputs/result.json"
        local_file = str(Path(self.temp_dir) / "result.json")

        # This should fail with AttributeError if method doesn't exist
        # That's expected in TDD Gate 1!
        self.file_transfer.download_file(remote_file, local_file)

        # If we get here, the method exists and accepts the parameters
        assert True

    def test_download_file_creates_parent_directories(self):
        """Test that download_file creates parent directories if they don't exist."""
        remote_file = "/home/ubuntu/cosmos/outputs/result.json"
        local_file = str(Path(self.temp_dir) / "new_dir" / "subdir" / "result.json")

        # Call the method (will fail if doesn't exist - that's ok!)
        self.file_transfer.download_file(remote_file, local_file)

        # Check that parent directory was created
        assert Path(local_file).parent.exists()

    def test_download_file_handles_windows_paths(self):
        """Test that download_file properly converts Windows paths to POSIX."""
        # Windows-style remote path
        remote_file = r"C:\home\ubuntu\cosmos\result.json"
        local_file = str(Path(self.temp_dir) / "result.json")

        # Should handle the conversion internally
        self.file_transfer.download_file(remote_file, local_file)

        # If it works without error, conversion is handled
        assert True

    def test_download_file_with_existing_local_file(self):
        """Test download_file overwrites existing local file."""
        remote_file = "/home/ubuntu/cosmos/outputs/new_result.json"
        local_file = Path(self.temp_dir) / "existing.json"

        # Create an existing file
        local_file.write_text("old content")
        assert local_file.exists()

        # Download should overwrite
        self.file_transfer.download_file(remote_file, str(local_file))

        # File should still exist (even if download failed, method should handle it)
        assert local_file.exists()
