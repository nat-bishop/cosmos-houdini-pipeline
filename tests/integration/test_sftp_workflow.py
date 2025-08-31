"""
Integration tests for SFTP file transfer workflow.
Tests the complete upload/download cycle with mocked SSH/SFTP connections.
"""
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import pytest

from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec


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
    def test_upload_single_file(self, file_transfer_manager, mock_ssh_manager, 
                                mock_sftp_client, temp_dir):
        """Test uploading a single file via SFTP."""
        # Setup
        test_file = temp_dir / "test.json"
        test_file.write_text('{"test": "data"}')
        remote_path = "/remote/test/test.json"
        
        mock_ssh_manager.ssh_client.open_sftp.return_value = mock_sftp_client
        
        # Execute
        result = file_transfer_manager.upload_file(str(test_file), remote_path)
        
        # Verify
        assert result is True
        mock_sftp_client.put.assert_called_once()
        call_args = mock_sftp_client.put.call_args
        assert str(test_file) in str(call_args[0][0])
        assert remote_path in str(call_args[0][1])
    
    @pytest.mark.integration
    def test_upload_directory_recursive(self, file_transfer_manager, mock_ssh_manager,
                                       mock_sftp_client, temp_dir):
        """Test uploading a directory recursively via SFTP."""
        # Setup directory structure
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        
        subdir = source_dir / "subdir"
        subdir.mkdir()
        (subdir / "file2.txt").write_text("content2")
        
        remote_dir = "/remote/test/source"
        
        mock_ssh_manager.ssh_client.open_sftp.return_value = mock_sftp_client
        mock_sftp_client.stat.side_effect = FileNotFoundError()  # Directory doesn't exist
        
        # Execute
        result = file_transfer_manager.upload_directory(str(source_dir), remote_dir)
        
        # Verify
        assert result is True
        assert mock_sftp_client.mkdir.call_count >= 2  # Main dir and subdir
        assert mock_sftp_client.put.call_count == 2  # Two files
    
    @pytest.mark.integration
    def test_download_directory(self, file_transfer_manager, mock_ssh_manager,
                               mock_sftp_client, temp_dir):
        """Test downloading a directory via SFTP."""
        # Setup
        remote_dir = "/remote/outputs/test_run"
        local_dir = temp_dir / "downloads"
        
        # Mock remote directory listing
        mock_sftp_client.listdir.side_effect = [
            ["output.mp4", "metadata.json", "logs"],  # Main directory
            ["inference.log", "error.log"]  # logs subdirectory
        ]
        
        # Mock file attributes (distinguish files from directories)
        def mock_stat(path):
            if "logs" in path and not path.endswith(".log"):
                return Mock(st_mode=16877)  # Directory
            return Mock(st_mode=33188)  # File
        
        mock_sftp_client.stat.side_effect = mock_stat
        mock_ssh_manager.ssh_client.open_sftp.return_value = mock_sftp_client
        
        # Execute
        result = file_transfer_manager.download_directory(remote_dir, str(local_dir))
        
        # Verify
        assert result is True
        assert mock_sftp_client.get.call_count >= 3  # At least 3 files
    
    @pytest.mark.integration
    def test_upload_prompt_spec_workflow(self, file_transfer_manager, mock_ssh_manager,
                                        mock_sftp_client, sample_prompt_spec, temp_dir):
        """Test complete workflow of uploading a PromptSpec and its videos."""
        # Setup
        spec_file = temp_dir / "prompt_spec.json"
        spec_file.write_text(json.dumps(sample_prompt_spec.to_dict()))
        
        # Create mock video files
        for video_type in ["color", "depth", "segmentation"]:
            video_file = temp_dir / f"{video_type}.mp4"
            video_file.write_text(f"mock {video_type} video data")
        
        mock_ssh_manager.ssh_client.open_sftp.return_value = mock_sftp_client
        mock_sftp_client.stat.side_effect = FileNotFoundError()  # Dirs don't exist
        
        # Execute workflow
        # 1. Upload spec file
        spec_uploaded = file_transfer_manager.upload_file(
            str(spec_file), 
            "/remote/test/inputs/prompt_spec.json"
        )
        
        # 2. Upload video files
        videos_uploaded = True
        for video_type in ["color", "depth", "segmentation"]:
            result = file_transfer_manager.upload_file(
                str(temp_dir / f"{video_type}.mp4"),
                f"/remote/test/inputs/videos/{video_type}.mp4"
            )
            videos_uploaded = videos_uploaded and result
        
        # Verify
        assert spec_uploaded is True
        assert videos_uploaded is True
        assert mock_sftp_client.put.call_count == 4  # 1 spec + 3 videos
    
    @pytest.mark.integration
    def test_download_inference_results(self, file_transfer_manager, mock_ssh_manager,
                                       mock_sftp_client, temp_dir):
        """Test downloading inference results including video and logs."""
        # Setup
        remote_output_dir = "/remote/test/outputs/run_001"
        local_output_dir = temp_dir / "outputs" / "run_001"
        
        # Mock remote directory structure
        mock_sftp_client.listdir.side_effect = [
            ["output.mp4", "output_upscaled.mp4", "metadata.json", "logs"],
            ["inference.log", "docker.log", "gpu_stats.txt"]
        ]
        
        def mock_stat(path):
            if "logs" in path and not any(ext in path for ext in [".log", ".txt"]):
                return Mock(st_mode=16877)  # Directory
            return Mock(st_mode=33188)  # File
        
        mock_sftp_client.stat.side_effect = mock_stat
        mock_ssh_manager.ssh_client.open_sftp.return_value = mock_sftp_client
        
        # Execute
        result = file_transfer_manager.download_directory(
            remote_output_dir, 
            str(local_output_dir)
        )
        
        # Verify
        assert result is True
        # Should download: 2 videos + 1 metadata + 3 log files = 6 files
        assert mock_sftp_client.get.call_count >= 5
    
    @pytest.mark.integration
    def test_error_recovery_on_upload_failure(self, file_transfer_manager, 
                                             mock_ssh_manager, mock_sftp_client, temp_dir):
        """Test error recovery when upload fails partway through."""
        # Setup
        source_dir = temp_dir / "source"
        source_dir.mkdir()
        
        for i in range(5):
            (source_dir / f"file{i}.txt").write_text(f"content{i}")
        
        # Simulate failure on third file
        mock_sftp_client.put.side_effect = [
            None,  # file0 succeeds
            None,  # file1 succeeds
            Exception("Connection lost"),  # file2 fails
            None,  # file3 would succeed
            None   # file4 would succeed
        ]
        
        mock_ssh_manager.ssh_client.open_sftp.return_value = mock_sftp_client
        
        # Execute
        result = file_transfer_manager.upload_directory(
            str(source_dir), 
            "/remote/test/source"
        )
        
        # Verify
        assert result is False  # Should return False on failure
        assert mock_sftp_client.put.call_count == 3  # Stopped after failure
    
    @pytest.mark.integration
    def test_windows_path_conversion(self, file_transfer_manager, mock_ssh_manager,
                                    mock_sftp_client, temp_dir):
        """Test that Windows paths are correctly converted for remote Linux."""
        # Setup Windows-style path
        windows_path = temp_dir / "test\\subdir\\file.txt"
        windows_path.parent.mkdir(parents=True, exist_ok=True)
        windows_path.write_text("test content")
        
        remote_path = "/remote/test/subdir/file.txt"
        
        mock_ssh_manager.ssh_client.open_sftp.return_value = mock_sftp_client
        
        # Execute
        result = file_transfer_manager.upload_file(str(windows_path), remote_path)
        
        # Verify
        assert result is True
        mock_sftp_client.put.assert_called_once()
        
        # Check that remote path uses forward slashes
        call_args = mock_sftp_client.put.call_args
        assert "/" in str(call_args[0][1])
        assert "\\" not in str(call_args[0][1])
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_directory_upload(self, file_transfer_manager, mock_ssh_manager,
                                   mock_sftp_client, temp_dir):
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
        
        mock_ssh_manager.ssh_client.open_sftp.return_value = mock_sftp_client
        mock_sftp_client.stat.side_effect = FileNotFoundError()  # Dirs don't exist
        
        # Execute
        result = file_transfer_manager.upload_directory(
            str(base_dir), 
            "/remote/test/large_dataset"
        )
        
        # Verify
        assert result is True
        assert mock_sftp_client.mkdir.call_count >= 11  # Base + 10 subdirs
        assert mock_sftp_client.put.call_count == 100  # 10x10 files