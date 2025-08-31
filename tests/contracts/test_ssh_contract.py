"""
Contract tests for SSH boundary.

These tests verify the CONTRACT at the SSH boundary without mocking internals.
They can run against either real SSH (with localhost) or fake implementations.

Following TEST_SUITE_INVESTIGATION_REPORT.md recommendations for boundary testing.
"""

from pathlib import Path

import pytest

from tests.fixtures.fakes import FakeSSHManager


class TestSSHContract:
    """Test the SSH contract at system boundary.

    These tests verify what the SSH interface promises,
    not how it's implemented internally.
    """

    @pytest.fixture
    def ssh_manager(self):
        """Get SSH manager - can be real or fake."""
        # For testing, use fake. In CI, could use real localhost SSH
        return FakeSSHManager()

    def test_connection_lifecycle(self, ssh_manager):
        """Test SSH connection lifecycle contract.

        Contract:
        - Can connect and disconnect
        - Can check connection status
        - Status reflects actual state
        """
        # Initially may or may not be connected
        ssh_manager.is_connected()

        # Connect should succeed
        result = ssh_manager.connect()
        assert result is True
        assert ssh_manager.is_connected() is True

        # Disconnect should work
        ssh_manager.disconnect()
        assert ssh_manager.is_connected() is False

        # Can reconnect
        ssh_manager.connect()
        assert ssh_manager.is_connected() is True

    def test_command_execution_contract(self, ssh_manager):
        """Test command execution contract.

        Contract:
        - Commands return (exit_code, stdout, stderr) tuple
        - Exit code 0 means success
        - Output is captured
        """
        ssh_manager.connect()

        # Test successful command
        exit_code, stdout, stderr = ssh_manager.execute_command("echo hello")
        assert exit_code == 0
        assert "hello" in stdout

        # Test command with error (simulated)
        ssh_manager.command_responses["invalid_cmd"] = (127, "", "command not found")
        exit_code, stdout, stderr = ssh_manager.execute_command("invalid_cmd")
        assert exit_code != 0
        assert "not found" in stderr

    def test_execute_success_contract(self, ssh_manager):
        """Test execute_command_success contract.

        Contract:
        - Returns stdout on success
        - Raises exception on failure
        """
        ssh_manager.connect()

        # Successful command
        output = ssh_manager.execute_command_success("echo test")
        assert "test" in output

        # Failed command should raise
        ssh_manager.command_responses["fail_cmd"] = (1, "", "error")
        with pytest.raises(RuntimeError):
            ssh_manager.execute_command_success("fail_cmd")

    def test_timeout_contract(self, ssh_manager):
        """Test timeout handling contract.

        Contract:
        - Commands accept timeout parameter
        - Timeout is respected
        """
        ssh_manager.connect()

        # Command with timeout
        exit_code, stdout, stderr = ssh_manager.execute_command("echo quick", timeout=5)
        assert exit_code == 0

        # Verify timeout was passed through
        last_command = ssh_manager.commands_executed[-1]
        assert last_command[1].get("timeout") == 5

    def test_idempotency_contract(self, ssh_manager):
        """Test that operations are idempotent.

        Contract:
        - Multiple connects don't break things
        - Multiple disconnects are safe
        """
        # Multiple connects
        for _ in range(3):
            ssh_manager.connect()
        assert ssh_manager.is_connected() is True

        # Multiple disconnects
        for _ in range(3):
            ssh_manager.disconnect()
        assert ssh_manager.is_connected() is False


class TestFileTransferContract:
    """Test file transfer contract at boundary."""

    @pytest.fixture
    def file_transfer(self):
        """Get file transfer service."""
        from tests.fixtures.fakes import FakeFileTransferService

        return FakeFileTransferService()

    @pytest.fixture
    def test_files(self, tmp_path):
        """Create test files."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        # Create test directory
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content1")
        (test_dir / "file2.txt").write_text("content2")

        return {"file": test_file, "dir": test_dir}

    def test_file_upload_contract(self, file_transfer, test_files):
        """Test file upload contract.

        Contract:
        - Can upload files
        - Validates file exists
        - Tracks uploads
        """
        # Upload existing file
        file_transfer.upload_file(test_files["file"], "/remote/dest")

        # Verify upload was tracked
        expected_remote = f"/remote/dest/{test_files['file'].name}"
        assert expected_remote in file_transfer.uploaded_files

        # Upload non-existent file should fail
        fake_file = Path("non_existent.txt")
        with pytest.raises(FileNotFoundError):
            file_transfer.upload_file(fake_file, "/remote/dest")

    def test_file_existence_check_contract(self, file_transfer, test_files):
        """Test remote file existence checking.

        Contract:
        - Can check if remote files exist
        - Returns boolean
        """
        # Upload a file
        file_transfer.upload_file(test_files["file"], "/remote")

        # Check existence
        assert file_transfer.file_exists_remote("/remote/test.txt") is True
        assert file_transfer.file_exists_remote("/remote/missing.txt") is False

    def test_directory_listing_contract(self, file_transfer, test_files):
        """Test remote directory listing.

        Contract:
        - Can list remote directory contents
        - Returns list of filenames
        """
        # Upload multiple files
        for i in range(3):
            file = test_files["dir"].parent / f"file_{i}.txt"
            file.write_text(f"content {i}")
            file_transfer.upload_file(file, "/remote/test")

        # List directory
        files = file_transfer.list_remote_directory("/remote/test")
        assert len(files) == 3
        assert all(f"file_{i}.txt" in files for i in range(3))

    def test_prompt_and_video_upload_contract(self, file_transfer, tmp_path):
        """Test specialized prompt and video upload.

        Contract:
        - Uploads prompt to correct location
        - Uploads video directories
        """
        # Create prompt file
        prompt = tmp_path / "prompt.json"
        prompt.write_text('{"prompt": "test"}')

        # Create video directories
        video_dir = tmp_path / "videos"
        video_dir.mkdir()
        (video_dir / "color.mp4").write_text("video")

        # Upload
        file_transfer.upload_prompt_and_videos(prompt, [video_dir])

        # Verify prompt uploaded to correct location
        assert any("inputs/prompts" in path for path in file_transfer.uploaded_files)

        # Verify video directory tracked
        assert any("inputs/videos" in path for path in file_transfer.uploaded_dirs)


class TestDockerExecutorContract:
    """Test Docker executor contract at boundary."""

    @pytest.fixture
    def docker_executor(self):
        """Get Docker executor."""
        from tests.fixtures.fakes import FakeDockerExecutor

        return FakeDockerExecutor()

    def test_inference_execution_contract(self, docker_executor, tmp_path):
        """Test inference execution contract.

        Contract:
        - Accepts prompt file and GPU config
        - Tracks execution
        - Produces results
        """
        # Create prompt
        prompt = tmp_path / "test.json"
        prompt.write_text('{"name": "test"}')

        # Run inference
        docker_executor.run_inference(prompt, num_gpu=2, cuda_devices="0,1")

        # Verify execution tracked
        assert len(docker_executor.containers_run) == 1
        container = docker_executor.containers_run[0]
        assert container[0] == "inference"
        assert container[1]["num_gpu"] == 2

        # Verify results produced
        assert "test" in docker_executor.inference_results

    def test_upscaling_prerequisites_contract(self, docker_executor, tmp_path):
        """Test upscaling prerequisites contract.

        Contract:
        - Requires completed inference
        - Validates input exists
        - Creates separate output
        """
        prompt = tmp_path / "test.json"
        prompt.write_text('{"name": "test"}')

        # Should fail without inference
        with pytest.raises(FileNotFoundError):
            docker_executor.run_upscaling(prompt)

        # Run inference first
        docker_executor.run_inference(prompt)

        # Now should succeed
        docker_executor.run_upscaling(prompt, control_weight=0.7)

        # Verify separate execution
        assert len(docker_executor.containers_run) == 2
        assert docker_executor.containers_run[1][0] == "upscaling"

    def test_status_reporting_contract(self, docker_executor):
        """Test status reporting contract.

        Contract:
        - Reports Docker status
        - Includes running state
        - Tracks container count
        """
        # Get status
        status = docker_executor.get_docker_status()

        # Verify required fields
        assert "docker_running" in status
        assert "containers_run" in status

        # Run some containers
        prompt = Path("test.json")
        prompt.write_text('{"name": "test"}')
        docker_executor.run_inference(prompt)

        # Status should update
        status = docker_executor.get_docker_status()
        assert status["containers_run"] == 1
