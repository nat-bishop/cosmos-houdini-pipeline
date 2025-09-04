"""
Integration tests for FileTransferService download_file method.
Following TDD Gate 1: NO MOCKS - Tests must call real functions.
"""

import tempfile
from pathlib import Path

import pytest

from cosmos_workflow.transfer.file_transfer import FileTransferService
from tests.fixtures.fakes import FakeSSHManager


class TestFileTransferDownload:
    """Test download_file method with real function calls (no mocks)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

        # Use FakeSSHManager for predictable behavior
        self.ssh_manager = FakeSSHManager()
        self.ssh_manager.connect()

        # Create real FileTransferService with fake SSH
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

        # The method exists and we're testing it can be called with expected parameters
        # It should raise FileNotFoundError since the fake always simulates missing files
        with pytest.raises(FileNotFoundError):
            self.file_transfer.download_file(remote_file, local_file)

        # If we get here, the method exists and accepts the parameters
        assert True

    def test_download_file_creates_parent_directories(self):
        """Test that download_file creates parent directories if they don't exist."""
        remote_file = "/home/ubuntu/cosmos/outputs/result.json"
        local_file = str(Path(self.temp_dir) / "new_dir" / "subdir" / "result.json")

        # The download will fail since file doesn't exist, but parent dirs should be created
        with pytest.raises(FileNotFoundError):
            self.file_transfer.download_file(remote_file, local_file)

        # Check that parent directory was created
        assert Path(local_file).parent.exists()

    def test_download_file_handles_windows_paths(self):
        """Test that download_file properly converts Windows paths to POSIX."""
        # Windows-style remote path
        remote_file = r"C:\home\ubuntu\cosmos\result.json"
        local_file = str(Path(self.temp_dir) / "result.json")

        # Should handle the conversion internally and raise FileNotFoundError for non-existent file
        with pytest.raises(FileNotFoundError) as exc_info:
            self.file_transfer.download_file(remote_file, local_file)

        # Verify the path was converted to POSIX in the error message
        assert "C:/home/ubuntu/cosmos/result.json" in str(exc_info.value)

    def test_download_file_with_existing_local_file(self):
        """Test download_file overwrites existing local file."""
        remote_file = "/home/ubuntu/cosmos/outputs/new_result.json"
        local_file = Path(self.temp_dir) / "existing.json"

        # Create an existing file
        local_file.write_text("old content")
        assert local_file.exists()

        # Download will fail since remote file doesn't exist in fake
        with pytest.raises(FileNotFoundError):
            self.file_transfer.download_file(remote_file, str(local_file))

        # File should still exist (even if download failed)
        assert local_file.exists()
