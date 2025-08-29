"""
Tests for the FileTransferService class.

This module tests the file transfer functionality that handles
uploading and downloading files between local and remote systems.
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
        with patch.object(self.file_transfer, '_upload_file') as mock_upload_file:
            with patch.object(self.file_transfer, '_upload_directory') as mock_upload_dir:
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
        with patch.object(self.file_transfer, '_upload_file') as mock_upload_file:
            with patch.object(self.file_transfer, '_upload_directory') as mock_upload_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Upload files
                self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                
                # Check that prompt file was uploaded - should be called with prompt_file and remote_prompts_dir
                mock_upload_file.assert_any_call(prompt_file, f"{self.remote_dir}/inputs/prompts")
    
    def test_upload_prompt_and_videos_uploads_video_directories(self):
        """Test that upload_prompt_and_videos uploads video directories."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Mock successful file uploads
        with patch.object(self.file_transfer, '_upload_file') as mock_upload_file:
            with patch.object(self.file_transfer, '_upload_directory') as mock_upload_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Upload files
                self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                
                # Check that video directory was uploaded
                mock_upload_dir.assert_called_with(video_dir, f"{self.remote_dir}/inputs/videos/test_videos")
    
    def test_upload_prompt_and_videos_uploads_bash_scripts(self):
        """Test that upload_prompt_and_videos uploads bash scripts from scripts directory."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Create mock scripts directory
        scripts_dir = Path(self.temp_dir) / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test_script.sh").write_text("#!/bin/bash\necho 'test'")
        
        with patch.object(self.file_transfer, '_upload_file') as mock_upload_file:
            with patch.object(self.file_transfer, '_upload_directory') as mock_upload_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Mock scripts directory existence
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.glob', return_value=[scripts_dir / "test_script.sh"]):
                        # Upload files
                        self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                        
                        # Check that bash script was uploaded
                        mock_upload_file.assert_any_call(
                            scripts_dir / "test_script.sh", 
                            f"{self.remote_dir}/bashscripts"
                        )
    
    def test_upload_prompt_and_videos_skips_scripts_if_directory_not_found(self):
        """Test that upload_prompt_and_videos skips script upload if scripts directory doesn't exist."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        with patch.object(self.file_transfer, '_upload_file') as mock_upload_file:
            with patch.object(self.file_transfer, '_upload_directory') as mock_upload_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Mock scripts directory not existing
                with patch('pathlib.Path.exists', return_value=False):
                    # Upload files
                    self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                    
                    # Check that no script upload was attempted
                    script_uploads = [call for call in mock_upload_file.call_args_list 
                                   if 'bashscripts' in str(call)]
                    assert len(script_uploads) == 0
    
    def test_upload_prompt_and_videos_makes_scripts_executable(self):
        """Test that upload_prompt_and_videos makes uploaded scripts executable."""
        # Mock successful directory creation
        self.mock_ssh_manager.execute_command_success.return_value = None
        
        # Create mock scripts directory
        scripts_dir = Path(self.temp_dir) / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "test_script.sh").write_text("#!/bin/bash\necho 'test'")
        
        with patch.object(self.file_transfer, '_upload_file') as mock_upload_file:
            with patch.object(self.file_transfer, '_upload_directory') as mock_upload_dir:
                # Create test prompt file
                prompt_file = Path(self.temp_dir) / "test_prompt.json"
                prompt_file.write_text('{"test": "data"}')
                
                # Create test video directory
                video_dir = Path(self.temp_dir) / "test_videos"
                video_dir.mkdir()
                
                # Mock scripts directory existence
                with patch('pathlib.Path.exists', return_value=True):
                    with patch('pathlib.Path.glob', return_value=[scripts_dir / "test_script.sh"]):
                        # Upload files
                        self.file_transfer.upload_prompt_and_videos(prompt_file, [video_dir])
                        
                        # Check that chmod commands were executed
                        chmod_calls = [call for call in self.mock_ssh_manager.execute_command_success.call_args_list 
                                     if 'chmod' in str(call)]
                        assert len(chmod_calls) == 2  # chmod +x and chmod -R g+w
    
    def test_upload_file_uses_scp_for_single_files(self):
        """Test that _upload_file uses scp for single file uploads."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            # Upload single file
            self.file_transfer._upload_file(self.test_file, f"{self.remote_dir}/test")
            
            # Check that scp was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'scp'
            assert str(self.test_file) in call_args
    
    def test_upload_directory_uses_scp_for_directory_uploads(self):
        """Test that _upload_directory uses scp for directory uploads."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            # Upload directory
            self.file_transfer._upload_directory(self.test_dir, f"{self.remote_dir}/test_dir")
            
            # Check that scp -r was called
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == 'scp'
            assert call_args[1] == '-r'
            assert str(self.test_dir) in call_args
    
    def test_upload_file_handles_windows_paths(self):
        """Test that _upload_file handles Windows path separators correctly."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            # Create a path with Windows separators
            windows_path = Path("C:\\Users\\test\\file.txt")
            
            # Mock the path to exist
            with patch.object(Path, 'exists', return_value=True):
                # Upload file
                self.file_transfer._upload_file(windows_path, f"{self.remote_dir}/test")
                
                # Check that scp was called with correct path
                mock_run.assert_called_once()
                call_args = mock_run.call_args[0][0]
                # The path should be in the command (Windows separators are preserved)
                assert str(windows_path) in call_args
    
    def test_upload_directory_handles_windows_paths(self):
        """Test that _upload_directory handles Windows path separators correctly."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            # Create a path with Windows separators
            windows_path = Path("C:\\Users\\test\\dir")
            
            # Mock the path to exist
            with patch.object(Path, 'exists', return_value=True):
                with patch.object(Path, 'is_dir', return_value=True):
                    # Upload directory
                    self.file_transfer._upload_directory(windows_path, f"{self.remote_dir}/test_dir")
                    
                    # Check that scp was called with correct path
                    mock_run.assert_called_once()
                    call_args = mock_run.call_args[0][0]
                    # The path should be in the command (Windows separators are preserved)
                    assert str(windows_path) in call_args
    
    def test_upload_file_raises_error_on_scp_failure(self):
        """Test that _upload_file falls back to SFTP when scp fails."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = b"Permission denied"
            
            # Mock SFTP context manager to succeed (simulating successful fallback)
            mock_sftp = Mock()
            
            with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
                mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
                mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
                
                # Should not raise RuntimeError, should fall back to SFTP
                self.file_transfer._upload_file(self.test_file, f"{self.remote_dir}/test")
                
                # Verify that SFTP fallback was used
                mock_get_sftp.assert_called_once()
                mock_sftp.put.assert_called_once()
    
    def test_upload_directory_raises_error_on_scp_failure(self):
        """Test that _upload_directory falls back to SFTP when scp fails."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stderr = b"Permission denied"
            
            # Mock SFTP context manager to succeed (simulating successful fallback)
            mock_sftp = Mock()
            
            with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
                mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
                mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
                
                # Should not raise RuntimeError, should fall back to SFTP
                self.file_transfer._upload_directory(self.test_dir, f"{self.remote_dir}/test_dir")
                
                # Verify that SFTP fallback was used
                mock_get_sftp.assert_called_once()
    
    def test_download_results_creates_local_directory(self):
        """Test that download_results creates local output directory."""
        with patch.object(self.file_transfer, '_download_directory') as mock_download:
            # Mock successful download
            mock_download.return_value = None
            
            # Mock SFTP context manager
            mock_sftp = Mock()
            mock_sftp.stat.side_effect = FileNotFoundError("File not found")  # No upscaled results
            
            with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
                mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
                mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
                
                # Download results
                self.file_transfer.download_results(Path("test_prompt.json"))
                
                # Check that local directory was created
                mock_download.assert_called_once()
    
    def test_download_results_uses_correct_remote_path(self):
        """Test that download_results uses correct remote path for download."""
        with patch.object(self.file_transfer, '_download_directory') as mock_download:
            # Mock successful download
            mock_download.return_value = None
            
            # Mock SFTP context manager
            mock_sftp = Mock()
            mock_sftp.stat.side_effect = FileNotFoundError("File not found")  # No upscaled results
            
            with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
                mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
                mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
                
                # Download results
                self.file_transfer.download_results(Path("test_prompt.json"))
                
                # Check that correct remote path was used
                mock_download.assert_called_once()
                call_args = mock_download.call_args
                remote_path = call_args[0][0]
                assert remote_path == f"{self.remote_dir}/outputs/test_prompt"
    
    def test_download_directory_uses_sftp_for_downloads(self):
        """Test that _download_directory uses SFTP for directory downloads."""
        # Mock SFTP context manager
        mock_sftp = Mock()
        mock_sftp.listdir_attr.return_value = []
        
        with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
            mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
            mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
            
            # Download directory
            self.file_transfer._download_directory(f"{self.remote_dir}/test_dir", self.test_dir)
            
            # Check that SFTP was used
            mock_get_sftp.assert_called_once()
            mock_sftp.listdir_attr.assert_called_once_with(f"{self.remote_dir}/test_dir")
    
    def test_download_directory_raises_error_on_sftp_failure(self):
        """Test that _download_directory raises error when SFTP fails."""
        # Mock SFTP context manager with error
        mock_sftp = Mock()
        mock_sftp.listdir_attr.side_effect = Exception("Connection failed")
        
        with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
            mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
            mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
            
            # Should raise RuntimeError
            with pytest.raises(RuntimeError, match="Download failed"):
                self.file_transfer._download_directory(f"{self.remote_dir}/test_dir", self.test_dir)
    
    def test_create_remote_directory_creates_directory_via_sftp(self):
        """Test that create_remote_directory creates directory via SFTP."""
        # Mock SFTP context manager
        mock_sftp = Mock()
        
        with patch.object(self.mock_ssh_manager, 'get_sftp') as mock_get_sftp:
            mock_get_sftp.return_value.__enter__ = Mock(return_value=mock_sftp)
            mock_get_sftp.return_value.__exit__ = Mock(return_value=None)
            
            with patch.object(self.file_transfer, '_ensure_remote_directory') as mock_ensure:
                # Create remote directory
                self.file_transfer.create_remote_directory(f"{self.remote_dir}/test/new/dir")
                
                # Check that _ensure_remote_directory was called
                mock_ensure.assert_called_once_with(mock_sftp, f"{self.remote_dir}/test/new/dir")
    
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


if __name__ == "__main__":
    pytest.main([__file__])
