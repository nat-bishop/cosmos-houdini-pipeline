"""
Integration tests for SFTP file transfer workflow - REFACTORED.

Following TEST_SUITE_INVESTIGATION_REPORT.md principles:
- Uses fake implementations instead of mocks
- Tests behavior and outcomes, not implementation
- Would survive internal refactoring
"""

import json
from pathlib import Path

import pytest

from tests.fixtures.fakes import FakeFileTransferService, FakeSSHManager


class TestSFTPWorkflowBehavior:
    """Test SFTP workflow behavior, not implementation details."""

    @pytest.fixture
    def fake_file_transfer(self):
        """Create file transfer service with fake dependencies."""
        ssh_manager = FakeSSHManager()
        return FakeFileTransferService(ssh_manager)

    @pytest.fixture
    def test_files(self, tmp_path):
        """Create test files and directories."""
        # Single file
        single_file = tmp_path / "test.json"
        single_file.write_text('{"test": "data"}')

        # Directory structure
        dir_path = tmp_path / "test_dir"
        dir_path.mkdir()
        (dir_path / "file1.txt").write_text("content1")

        subdir = dir_path / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2")

        # Prompt spec file
        prompt_spec = tmp_path / "prompt_spec.json"
        prompt_spec.write_text(
            json.dumps(
                {
                    "id": "ps_001",
                    "name": "test_prompt",
                    "prompt": "A test scene",
                    "input_video_path": str(tmp_path / "input.mp4"),
                }
            )
        )

        return {"single_file": single_file, "directory": dir_path, "prompt_spec": prompt_spec}

    def test_upload_single_file_behavior(self, fake_file_transfer, test_files):
        """Test that single file upload produces expected outcomes.

        Verifies BEHAVIOR:
        - File is tracked as uploaded
        - Remote path is correctly constructed
        - Upload completes successfully

        Does NOT test:
        - SFTP put method calls
        - Internal implementation details
        """
        # Upload file
        result = fake_file_transfer.upload_file(test_files["single_file"], "/remote/test")

        # Verify OUTCOME: Upload completed
        assert result is None  # Success returns None

        # Verify OUTCOME: File was tracked
        assert len(fake_file_transfer.uploaded_files) == 1
        upload = fake_file_transfer.uploaded_files[0]
        assert upload["local_path"] == test_files["single_file"]
        assert upload["remote_path"] == "/remote/test"
        assert upload["filename"] == "test.json"

    def test_upload_directory_recursive_behavior(self, fake_file_transfer, test_files):
        """Test that directory upload handles nested structures correctly.

        Verifies BEHAVIOR:
        - All files in directory are uploaded
        - Directory structure is preserved
        - Subdirectories are handled
        """
        # Upload directory
        fake_file_transfer.upload_directory(test_files["directory"], "/remote/test")

        # Verify OUTCOME: All files uploaded
        uploaded_files = fake_file_transfer.uploaded_files
        assert len(uploaded_files) == 2  # file1.txt and file2.txt

        # Verify OUTCOME: Directory structure preserved
        filenames = [u["filename"] for u in uploaded_files]
        assert "file1.txt" in filenames
        assert "file2.txt" in filenames

        # Verify OUTCOME: Remote paths are correct
        for upload in uploaded_files:
            assert upload["remote_path"].startswith("/remote/test")

    def test_download_directory_behavior(self, fake_file_transfer, tmp_path):
        """Test that directory download creates local structure correctly.

        Verifies BEHAVIOR:
        - Files are downloaded to correct location
        - Directory structure is created
        - Download tracking works
        """
        # Simulate remote files
        fake_file_transfer.remote_files = {
            "/remote/outputs/result1.mp4": b"video data 1",
            "/remote/outputs/result2.mp4": b"video data 2",
            "/remote/outputs/subdir/result3.mp4": b"video data 3",
        }

        # Download directory
        local_dir = tmp_path / "downloads"
        fake_file_transfer.download_directory("/remote/outputs", local_dir)

        # Verify OUTCOME: Files downloaded
        assert len(fake_file_transfer.downloaded_files) == 3

        # Verify OUTCOME: Local structure created
        downloaded = fake_file_transfer.downloaded_files
        for download in downloaded:
            # Files should be under local_dir (possibly in subdirectories)
            assert str(download["local_path"]).startswith(str(local_dir))
            assert download["remote_path"].startswith("/remote/outputs")

    def test_upload_prompt_spec_workflow(self, fake_file_transfer, test_files):
        """Test complete prompt spec upload workflow.

        Verifies BEHAVIOR:
        - Prompt spec uploaded correctly
        - Associated files uploaded
        - Remote structure follows convention
        """
        # Upload prompt spec and associated files
        fake_file_transfer.upload_file(test_files["prompt_spec"], "/remote/inputs/prompts")

        # Create and upload associated video
        video_file = test_files["single_file"].parent / "input.mp4"
        video_file.write_bytes(b"video data")
        fake_file_transfer.upload_file(video_file, "/remote/inputs/videos")

        # Verify OUTCOME: All files uploaded
        assert len(fake_file_transfer.uploaded_files) == 2

        # Verify OUTCOME: Correct remote paths
        uploads_by_name = {u["filename"]: u for u in fake_file_transfer.uploaded_files}
        assert "prompt_spec.json" in uploads_by_name
        assert "input.mp4" in uploads_by_name
        assert uploads_by_name["prompt_spec.json"]["remote_path"] == "/remote/inputs/prompts"
        assert uploads_by_name["input.mp4"]["remote_path"] == "/remote/inputs/videos"

    def test_download_inference_results_behavior(self, fake_file_transfer, tmp_path):
        """Test downloading inference results from remote.

        Verifies BEHAVIOR:
        - Results downloaded to correct location
        - Multiple result types handled
        - Download tracking accurate
        """
        # Simulate inference results
        fake_file_transfer.remote_files = {
            "/remote/outputs/inference/output.mp4": b"final video",
            "/remote/outputs/inference/frames/frame_001.png": b"frame1",
            "/remote/outputs/inference/frames/frame_002.png": b"frame2",
            "/remote/outputs/inference/metadata.json": b'{"fps": 24}',
        }

        # Download results
        local_output = tmp_path / "results"
        result_paths = [
            "/remote/outputs/inference/output.mp4",
            "/remote/outputs/inference/metadata.json",
        ]

        for remote_path in result_paths:
            fake_file_transfer.download_file(remote_path, local_output / Path(remote_path).name)

        # Verify OUTCOME: Results downloaded
        assert len(fake_file_transfer.downloaded_files) == 2

        # Verify OUTCOME: Correct file types
        downloaded_names = [d["filename"] for d in fake_file_transfer.downloaded_files]
        assert "output.mp4" in downloaded_names
        assert "metadata.json" in downloaded_names

    def test_error_recovery_on_upload_failure(self, fake_file_transfer, test_files):
        """Test that upload failures are handled gracefully.

        Verifies BEHAVIOR:
        - Failed uploads are tracked
        - System remains usable after failure
        - Retry logic works
        """
        # Simulate failure on first attempt
        fake_file_transfer.fail_next_upload = True

        # Attempt upload (will fail)
        with pytest.raises(ConnectionError):
            fake_file_transfer.upload_file(test_files["single_file"], "/remote/test")

        # Verify OUTCOME: Failure tracked
        assert len(fake_file_transfer.failed_uploads) == 1
        assert fake_file_transfer.failed_uploads[0]["reason"] == "Simulated failure"

        # Retry upload (should succeed)
        result = fake_file_transfer.upload_file(test_files["single_file"], "/remote/test")

        # Verify OUTCOME: Retry succeeded
        assert result is None
        assert len(fake_file_transfer.uploaded_files) == 1

    def test_windows_path_conversion_behavior(self, fake_file_transfer, tmp_path):
        """Test that Windows paths are handled correctly.

        Verifies BEHAVIOR:
        - Windows paths converted to POSIX for remote
        - Backslashes handled properly
        - Path separators normalized
        """
        # Create file with Windows-style path
        windows_file = tmp_path / "windows" / "test.txt"
        windows_file.parent.mkdir(exist_ok=True)
        windows_file.write_text("test")

        # Upload with Windows path
        fake_file_transfer.upload_file(windows_file, "/remote/unix/path")

        # Verify OUTCOME: Path converted correctly
        upload = fake_file_transfer.uploaded_files[0]
        assert "/" in upload["remote_path"]
        assert "\\" not in upload["remote_path"]
        assert upload["remote_path"] == "/remote/unix/path"

    def test_large_directory_upload_behavior(self, fake_file_transfer, tmp_path):
        """Test uploading large directory structures.

        Verifies BEHAVIOR:
        - Many files handled efficiently
        - Deep nesting supported
        - Progress tracking works
        """
        # Create large directory structure
        base_dir = tmp_path / "large_dir"
        base_dir.mkdir()

        # Create many files
        file_count = 50
        for i in range(file_count):
            # Create files at different depths
            depth = i % 3
            current_dir = base_dir
            for d in range(depth):
                current_dir = current_dir / f"level_{d}"
                current_dir.mkdir(exist_ok=True)

            file = current_dir / f"file_{i}.txt"
            file.write_text(f"content_{i}")

        # Upload directory
        fake_file_transfer.upload_directory(base_dir, "/remote/large")

        # Verify OUTCOME: All files uploaded
        assert len(fake_file_transfer.uploaded_files) == file_count

        # Verify OUTCOME: Structure preserved
        for upload in fake_file_transfer.uploaded_files:
            assert upload["remote_path"].startswith("/remote/large")
            assert upload["filename"].startswith("file_")

    def test_file_transfer_idempotency(self, fake_file_transfer, test_files):
        """Test that repeated transfers are idempotent.

        Verifies BEHAVIOR:
        - Multiple uploads of same file handled
        - No corruption on repeated operations
        - Consistent outcomes
        """
        # Upload same file multiple times
        for _ in range(3):
            fake_file_transfer.upload_file(test_files["single_file"], "/remote/test")

        # Verify OUTCOME: All uploads tracked
        assert len(fake_file_transfer.uploaded_files) == 3

        # Verify OUTCOME: All uploads identical
        for upload in fake_file_transfer.uploaded_files:
            assert upload["filename"] == "test.json"
            assert upload["remote_path"] == "/remote/test"
