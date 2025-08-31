"""
Tests for the FileTransferService class.

This module tests the file transfer functionality that handles
uploading and downloading files between local and remote systems via rsync.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import os
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.connection.ssh_manager import SSHManager


class TestFileTransferService:
    """Test suite for FileTransferService class."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock SSH manager
        self.mock_ssh_manager = Mock(spec=SSHManager)
        
        # Test configuration
        self.remote_dir = "/home/ubuntu/cosmos-transfer1"
        
        # Initialize FileTransferService
        self.file_transfer = FileTransferService(
            ssh_manager=self.mock_ssh_manager,
            remote_dir=self.remote_dir
        )
        
        # Create temporary test files
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test_file.txt"
        self.test_file.write_text("Test content")
        
        self.test_dir = Path(self.temp_dir) / "test_dir"
        self.test_dir.mkdir()
        (self.test_dir / "file1.txt").write_text("File 1 content")
        (self.test_dir / "file2.txt").write_text("File 2 content")
    
    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        import shutil
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_init_with_valid_parameters(self):
        """Test FileTransferService initialization with valid parameters."""
        assert self.file_transfer.ssh_manager == self.mock_ssh_manager
        assert self.file_transfer.remote_dir == self.remote_dir
    
    def test_upload_prompt_and_videos_creates_remote_directories(self):
        """Test that upload_prompt_and_videos creates necessary remote directories."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Mock successful file uploads
        with patch.object(self.file_transfer, '_rsync_file') as mock_rsync_file:
            with patch.object(self.file_transfer, '_rsync_dir') as mock_rsync_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Upload files
                self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                
                # Check that directories were created (first call should be mkdir)
                mkdir_calls = [call for call in self.mock_ssh_manager.execute_command_success.call_args_list 
                             if 'mkdir -p' in str(call)]
                assert len(mkdir_calls) >= 1
    
    def test_upload_prompt_and_videos_uploads_prompt_file(self):
        """Test that upload_prompt_and_videos uploads the prompt file."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Mock successful file uploads
        with patch.object(self.file_transfer, '_rsync_file') as mock_rsync_file:
            with patch.object(self.file_transfer, '_rsync_dir') as mock_rsync_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Upload files
                self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                
                # Check that prompt file was uploaded - should be called with prompt_file and remote_prompts_dir
                mock_rsync_file.assert_any_call(prompt_file, f"{self.remote_dir}/inputs/prompts/test_prompt.json")
    
    def test_upload_prompt_and_videos_uploads_video_directories(self):
        """Test that upload_prompt_and_videos uploads video directories."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Mock successful file uploads
        with patch.object(self.file_transfer, '_rsync_file') as mock_rsync_file:
            with patch.object(self.file_transfer, '_rsync_dir') as mock_rsync_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Upload files
                self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                
                # Check that video directory was uploaded
                mock_rsync_dir.assert_any_call(video_dir, f"{self.remote_dir}/inputs/videos/test_videos")
    
    def test_upload_prompt_and_videos_uploads_bash_scripts(self):
        """Test that upload_prompt_and_videos uploads bash scripts from scripts directory."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Create mock scripts directory in temp directory
        scripts_dir = Path(self.temp_dir) / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test_script.sh").write_text("#!/bin/bash\necho 'test'")
        
        with patch.object(self.file_transfer, '_rsync_file') as mock_rsync_file:
            with patch.object(self.file_transfer, '_rsync_dir') as mock_rsync_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Mock scripts directory existence by patching the Path import in file_transfer module
                with patch('cosmos_workflow.transfer.file_transfer.Path') as mock_path:
                    # Make Path("scripts") return our temp scripts directory
                    def mock_path_side_effect(path_arg):
                        if path_arg == "scripts":
                            return scripts_dir
                        return Path(path_arg)
                    
                    mock_path.side_effect = mock_path_side_effect
                    
                    # Upload files
                    self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                    
                    # Check that bash script directory was uploaded
                    mock_rsync_dir.assert_any_call(scripts_dir, f"{self.remote_dir}/bashscripts")
    
    def test_upload_prompt_and_videos_skips_scripts_if_directory_not_found(self):
        """Test that upload_prompt_and_videos skips script upload if scripts directory doesn't exist."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        with patch.object(self.file_transfer, '_rsync_file') as mock_rsync_file:
            with patch.object(self.file_transfer, '_rsync_dir') as mock_rsync_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Mock scripts directory not existing by patching Path import in file_transfer module
                with patch('cosmos_workflow.transfer.file_transfer.Path') as mock_path:
                    # Make Path("scripts") return a non-existent path
                    def mock_path_side_effect(path_arg):
                        if path_arg == "scripts":
                            return Path("/nonexistent/scripts")
                        return Path(path_arg)
                    
                    mock_path.side_effect = mock_path_side_effect
                    
                    # Upload files
                    self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                    
                    # Check that no script upload was attempted
                    script_uploads = [call for call in mock_rsync_dir.call_args_list 
                                   if 'bashscripts' in str(call)]
                    assert len(script_uploads) == 0
    
    def test_upload_prompt_and_videos_makes_scripts_executable(self):
        """Test that upload_prompt_and_videos makes uploaded scripts executable."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Create mock scripts directory in temp directory
        scripts_dir = Path(self.temp_dir) / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test_script.sh").write_text("#!/bin/bash\necho 'test'")
        
        with patch.object(self.file_transfer, '_rsync_file') as mock_rsync_file:
            with patch.object(self.file_transfer, '_rsync_dir') as mock_rsync_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Mock scripts directory existence by patching Path import in file_transfer module
                with patch('cosmos_workflow.transfer.file_transfer.Path') as mock_path:
                    # Make Path("scripts") return our temp scripts directory
                    def mock_path_side_effect(path_arg):
                        if path_arg == "scripts":
                            return scripts_dir
                        return Path(path_arg)
                    
                    mock_path.side_effect = mock_path_side_effect
                    
                    # Upload files
                    self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                    
                    # Check that chmod commands were executed
                    chmod_calls = [call for call in self.mock_ssh_manager.execute_command_success.call_args_list 
                                 if 'chmod' in str(call)]
                    assert len(chmod_calls) == 2  # chmod +x and chmod -R g+w
    
    def test_upload_file_uses_rsync_for_single_files(self):
        """Test that upload_file uses rsync for single file uploads."""
        with patch.object(self.file_transfer, '_rsync_file') as mock_rsync_file:
            # Upload single file
            self.file_transfer.upload_file(self.test_file, f"{self.remote_dir}/test")
            
            # Check that rsync was called
            mock_rsync_file.assert_called_once_with(self.test_file, f"{self.remote_dir}/test/test_file.txt")
    
    def test_upload_file_creates_remote_directory(self):
        """Test that upload_file creates remote directory before upload."""
        with patch.object(self.file_transfer, '_rsync_file') as mock_rsync_file:
            # Mock successful directory creation
            self.mock_ssh_manager.execute_command_success.return_value = None
            
            # Upload single file
            self.file_transfer.upload_file(self.test_file, f"{self.remote_dir}/test")
            
            # Check that directory was created
            mkdir_calls = [call for call in self.mock_ssh_manager.execute_command_success.call_args_list 
                         if 'mkdir -p' in str(call)]
            assert len(mkdir_calls) == 1
    
    def test_upload_file_raises_error_when_file_not_found(self):
        """Test that upload_file raises error when local file doesn't exist."""
        non_existent_file = Path("/nonexistent/file.txt")
        
        with pytest.raises(FileNotFoundError):
            self.file_transfer.upload_file(non_existent_file, f"{self.remote_dir}/test")
    
    def test_download_results_creates_local_directory(self):
        """Test that download_results creates local output directory."""
        with patch.object(self.file_transfer, '_rsync_pull') as mock_rsync_pull:
            # Mock successful download
            mock_rsync_pull.return_value = None
            
            # Mock SFTP context manager to find main outputs
            mock_sftp = Mock()
            mock_sftp.stat.return_value = Mock()  # Main outputs exist
            mock_sftp.stat.side_effect = lambda x: Mock() if "upscaled" not in x else FileNotFoundError("File not found")
            
            with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
                mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
                mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
                
                # Download results
                self.file_transfer.download_results(Path("test_prompt.json"))
                
                # Check that local directory was created and rsync was called
                # Note: The actual implementation calls rsync twice (main + upscaled)
                assert mock_rsync_pull.call_count >= 1
    
    def test_download_results_uses_correct_remote_path(self):
        """Test that download_results uses correct remote path for download."""
        with patch.object(self.file_transfer, '_rsync_pull') as mock_rsync_pull:
            # Mock successful download
            mock_rsync_pull.return_value = None
            
            # Mock SFTP context manager to find main outputs
            mock_sftp = Mock()
            mock_sftp.stat.return_value = Mock()  # Main outputs exist
            mock_sftp.stat.side_effect = lambda x: Mock() if "upscaled" not in x else FileNotFoundError("File not found")
            
            with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
                mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
                mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
                
                # Download results
                self.file_transfer.download_results(Path("test_prompt.json"))
                
                # Check that correct remote path was used
                # Note: The actual implementation calls rsync twice (main + upscaled)
                assert mock_rsync_pull.call_count >= 1
                call_args = mock_rsync_pull.call_args_list[0]
                remote_path = call_args[0][0]
                assert remote_path == f"{self.remote_dir}/outputs/test_prompt/"
    
    def test_download_results_handles_upscaled_outputs(self):
        """Test that download_results handles upscaled outputs correctly."""
        with patch.object(self.file_transfer, '_rsync_pull') as mock_rsync_pull:
            # Mock successful downloads
            mock_rsync_pull.return_value = None
            
            # Mock SFTP context manager to find upscaled results
            mock_sftp = Mock()
            mock_sftp.stat.return_value = Mock()  # Upscaled results exist
            
            with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
                mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
                mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
                
                # Download results
                self.file_transfer.download_results(Path("test_prompt.json"))
                
                # Check that both main and upscaled results were downloaded
                assert mock_rsync_pull.call_count == 2
    
    def test_create_remote_directory_creates_directory_via_ssh(self):
        """Test that create_remote_directory creates directory via SSH."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Create remote directory
        self.file_transfer.create_remote_directory(f"{self.remote_dir}/test/new/dir")
        
        # Check that mkdir command was executed
        self.mock_ssh_manager.execute_command_success.assert_called_once()
        call_args = self.mock_ssh_manager.execute_command_success.call_args
        cmd = call_args[0][0]
        assert "mkdir -p" in cmd
        assert f"{self.remote_dir}/test/new/dir" in cmd
    
    def test_file_exists_remote_returns_true_for_existing_file(self):
        """Test that file_exists_remote returns True for existing files."""
        # Mock SFTP context manager
        mock_sftp = Mock()
        mock_sftp.stat.return_value = Mock()  # File exists
        
        with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
            mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
            mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
            
            # Check if file exists
            result = self.file_transfer.file_exists_remote(f"{self.remote_dir}/test_file.txt")
            
            # Should return True
            assert result is True
            mock_sftp.stat.assert_called_once_with(f"{self.remote_dir}/test_file.txt")
    
    def test_file_exists_remote_returns_false_for_nonexistent_file(self):
        """Test that file_exists_remote returns False for non-existent files."""
        # Mock SFTP context manager with FileNotFoundError
        mock_sftp = Mock()
        mock_sftp.stat.side_effect = FileNotFoundError("File not found")
        
        with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
            mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
            mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
            
            # Check if file exists
            result = self.file_transfer.file_exists_remote(f"{self.remote_dir}/nonexistent.txt")
            
            # Should return False
            assert result is False
    
    def test_list_remote_directory_returns_file_list(self):
        """Test that list_remote_directory returns list of files."""
        # Mock SFTP context manager
        mock_sftp = Mock()
        mock_sftp.listdir.return_value = ["file1.txt", "file2.txt", "subdir"]
        
        with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
            mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
            mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
            
            # List remote directory
            result = self.file_transfer.list_remote_directory(f"{self.remote_dir}/test_dir")
            
            # Should return list of files
            assert result == ["file1.txt", "file2.txt", "subdir"]
            mock_sftp.listdir.assert_called_once_with(f"{self.remote_dir}/test_dir")
    
    def test_list_remote_directory_returns_empty_list_on_error(self):
        """Test that list_remote_directory returns empty list on error."""
        # Mock SFTP context manager with error
        mock_sftp = Mock()
        mock_sftp.listdir.side_effect = Exception("Connection failed")
        
        with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
            mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
            mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
            
            # List remote directory
            result = self.file_transfer.list_remote_directory(f"{self.remote_dir}/test_dir")
            
            # Should return empty list
            assert result == []
    
    def test_rsync_file_executes_correct_command(self):
        """Test that _rsync_file executes the correct rsync command."""
        with patch.object(self.file_transfer, '_run') as mock_run:
            # Mock successful rsync execution
            mock_run.return_value = None
            
            # Upload file
            self.file_transfer._rsync_file(self.test_file, f"{self.remote_dir}/test/test_file.txt")
            
            # Check that _run was called with correct rsync command
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            label = call_args[0][1]
            
            assert cmd[0] == "rsync"
            assert "-az" in cmd
            assert "--progress" in cmd
            assert "-e" in cmd
            assert str(self.test_file) in cmd
            assert "test_file.txt" in cmd[-1]  # Remote path
            assert "rsync file:" in label
    
    def test_rsync_dir_executes_correct_command(self):
        """Test that _rsync_dir executes the correct rsync command."""
        with patch.object(self.file_transfer, '_run') as mock_run:
            # Mock successful rsync execution
            mock_run.return_value = None
            
            # Upload directory
            self.file_transfer._rsync_dir(self.test_dir, f"{self.remote_dir}/test_dir")
            
            # Check that _run was called with correct rsync command
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            label = call_args[0][1]
            
            assert cmd[0] == "rsync"
            assert "-az" in cmd
            assert "--delete-after" in cmd
            assert "--progress" in cmd
            assert "-e" in cmd
            assert str(self.test_dir) + os.sep in cmd  # Source with trailing slash
            assert "test_dir" in cmd[-1]  # Remote path
            assert "rsync dir:" in label
    
    def test_rsync_pull_executes_correct_command(self):
        """Test that _rsync_pull executes the correct rsync command."""
        with patch.object(self.file_transfer, '_run') as mock_run:
            # Mock successful rsync execution
            mock_run.return_value = None
            
            # Download directory
            self.file_transfer._rsync_pull(f"{self.remote_dir}/test_dir/", str(self.test_dir))
            
            # Check that _run was called with correct rsync command
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            cmd = call_args[0][0]
            label = call_args[0][1]
            
            assert cmd[0] == "rsync"
            assert "-az" in cmd
            assert "--progress" in cmd
            assert "-e" in cmd
            # Check that the remote spec contains the correct path
            remote_spec = cmd[-2]  # Second to last argument should be remote spec
            assert f"{self.remote_dir}/test_dir/" in remote_spec
            assert str(self.test_dir) in cmd[-1]  # Last argument should be local destination
            assert "rsync pull:" in label
    
    def test_remote_mkdirs_creates_multiple_directories(self):
        """Test that _remote_mkdirs creates multiple directories in one command."""
        with patch.object(self.file_transfer, '_q') as mock_q:
            mock_q.return_value = "'/test/path'"
            
            # Mock successful command execution
            self.mock_ssh_manager.execute_command_success.return_value = None
            
            # Create directories
            self.file_transfer._remote_mkdirs(["/test/path1", "/test/path2"])
            
            # Check that mkdir command was executed
            self.mock_ssh_manager.execute_command_success.assert_called_once()
            call_args = self.mock_ssh_manager.execute_command_success.call_args
            cmd = call_args[0][0]
            
            assert "mkdir -p" in cmd
            assert "'/test/path'" in cmd  # Should be quoted
    
    def test_remote_mkdirs_handles_empty_list(self):
        """Test that _remote_mkdirs handles empty list gracefully."""
        # Should not raise any exceptions
        self.file_transfer._remote_mkdirs([])
        
        # Should not call SSH manager
        self.mock_ssh_manager.execute_command_success.assert_not_called()
    
    def test_run_executes_command_and_handles_success(self):
        """Test that _run executes command and handles success."""
        with patch('subprocess.run') as mock_subprocess:
            # Mock successful command execution
            mock_proc = Mock()
            mock_proc.returncode = 0
            mock_proc.stdout = "Success output"
            mock_proc.stderr = "Progress info"
            mock_subprocess.return_value = mock_proc
            
            # Execute command
            self.file_transfer._run(["echo", "test"], "Test command")
            
            # Check that subprocess.run was called
            mock_subprocess.assert_called_once()
            call_args = mock_subprocess.call_args
            cmd = call_args[0][0]
            assert cmd == ["echo", "test"]
    
    def test_run_raises_error_on_failure(self):
        """Test that _run raises error when command fails."""
        with patch('subprocess.run') as mock_subprocess:
            # Mock failed command execution
            mock_proc = Mock()
            mock_proc.returncode = 1
            mock_proc.stdout = "Error output"
            mock_proc.stderr = "Error details"
            mock_subprocess.return_value = mock_proc
            
            # Should raise RuntimeError
            with pytest.raises(RuntimeError, match="Test command failed with exit 1"):
                self.file_transfer._run(["false"], "Test command")
    
    def test_quote_escapes_single_quotes(self):
        """Test that _q properly escapes single quotes in paths."""
        result = self.file_transfer._q("/path/with'quote")
        assert result == "'/path/with'\\''quote'"
    
    def test_quote_handles_paths_without_quotes(self):
        """Test that _q handles paths without quotes."""
        result = self.file_transfer._q("/simple/path")
        assert result == "'/simple/path'"


if __name__ == "__main__":
    pytest.main([__file__])
