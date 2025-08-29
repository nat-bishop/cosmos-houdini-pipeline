#!/usr/bin/env python3
"""
File transfer service for Cosmos-Transfer1 workflows.
Handles uploading and downloading files between local and remote systems.
"""

import json
from pathlib import Path
from typing import Optional, List
from cosmos_workflow.connection.ssh_manager import SSHManager
import logging

logger = logging.getLogger(__name__)


class FileTransferService:
    """Handles file transfers between local and remote systems."""
    
    def __init__(self, ssh_manager: SSHManager, remote_dir: str):
        self.ssh_manager = ssh_manager
        self.remote_dir = remote_dir
    
    def upload_prompt_and_videos(self, prompt_file: Path, video_dirs: list[Path]) -> None:
        """
        Upload prompt file and video directories to remote instance.
        
        Args:
            prompt_file: Path to prompt JSON file
            video_dirs: List of video directory paths
        """
        logger.info("Creating remote directories...")
        
        # Create remote directories
        remote_prompts_dir = f"{self.remote_dir}/inputs/prompts"
        remote_videos_dir = f"{self.remote_dir}/inputs/videos"
        remote_scripts_dir = f"{self.remote_dir}/bashscripts"
        
        self.ssh_manager.execute_command_success(
            f"mkdir -p '{remote_prompts_dir}' '{remote_videos_dir}' '{remote_scripts_dir}'"
        )
        
        # Upload prompt file
        logger.info(f"Uploading prompt file: {prompt_file}")
        self._upload_file(prompt_file, remote_prompts_dir)
        
        # Upload video directories
        for video_dir in video_dirs:
            logger.info(f"Uploading video directory: {video_dir}")
            remote_video_path = f"{remote_videos_dir}/{video_dir.name}"
            self._upload_directory(video_dir, remote_video_path)
        
        # Upload bash scripts
        logger.info("Uploading bash scripts...")
        scripts_dir = Path("scripts")
        if scripts_dir.exists():
            for script_file in scripts_dir.glob("*.sh"):
                logger.info(f"Uploading script: {script_file}")
                self._upload_file(script_file, remote_scripts_dir)
            
            # Make all uploaded scripts executable
            logger.info("Making bash scripts executable...")
            self.ssh_manager.execute_command_success(f"chmod +x {remote_scripts_dir}/*.sh")
            
            # Fix permissions for Docker access (more targeted than NVIDIA's share alias)
            logger.info("Fixing permissions for Docker access...")
            self.ssh_manager.execute_command_success(f"chmod -R g+w {remote_scripts_dir}")
        else:
            logger.warning("Scripts directory not found, skipping script upload")
    
    def upload_file(self, local_path: Path, remote_path: str) -> None:
        """Upload a single file to remote."""
        self._upload_file(local_path, remote_path)
    
    def _upload_file(self, local_path: Path, remote_path: str) -> None:
        """Internal method to upload a single file."""
        if not local_path.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        
        # Ensure remote path uses forward slashes
        clean_remote_path = remote_path.replace('\\', '/')
        
        logger.info(f"Uploading {local_path} -> {clean_remote_path}")
        
        # Use scp for single file upload (more reliable than SFTP)
        try:
            import subprocess
            import os
            
            # Get SSH key path from environment or config
            ssh_key = os.getenv('SSH_KEY', os.path.expanduser('~/.ssh/LambdaSSHkey.pem'))
            remote_host = os.getenv('REMOTE_HOST', '192.222.53.15')
            remote_user = os.getenv('REMOTE_USER', 'ubuntu')
            remote_port = os.getenv('REMOTE_PORT', '22')
            
            # Build scp command
            scp_cmd = [
                'scp', '-P', remote_port, '-i', ssh_key,
                str(local_path),
                f'{remote_user}@{remote_host}:{clean_remote_path}'
            ]
            
            logger.info(f"Using scp to upload file: {' '.join(scp_cmd)}")
            
            # Execute scp command
            result = subprocess.run(scp_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"scp failed: {result.stderr}")
                raise RuntimeError(f"scp upload failed: {result.stderr}")
            
            logger.info(f"Successfully uploaded {local_path.name}")
            
        except Exception as e:
            logger.error(f"scp upload failed, falling back to SFTP: {e}")
            # Fallback to SFTP if scp fails
            with self.ssh_manager.get_sftp() as sftp:
                # Ensure remote directory exists
                remote_dir = Path(clean_remote_path).parent
                self._ensure_remote_directory(sftp, str(remote_dir))
                
                # Upload file
                sftp.put(str(local_path), clean_remote_path)
            
            logger.info(f"Successfully uploaded {local_path.name} via SFTP fallback")
    
    def _upload_directory(self, local_dir: Path, remote_dir: str) -> None:
        """Recursively upload a directory using scp (same as bash script)."""
        # Ensure remote directory uses forward slashes
        clean_remote_dir = remote_dir.replace('\\', '/')
        
        # Use scp -r for directory upload (same as bash script approach)
        # This handles permissions and directory creation automatically
        try:
            # Get SSH connection details from the SSH manager
            # We'll use the same approach as the bash script
            import subprocess
            import os
            
            # Get SSH key path from environment or config
            ssh_key = os.getenv('SSH_KEY', os.path.expanduser('~/.ssh/LambdaSSHkey.pem'))
            remote_host = os.getenv('REMOTE_HOST', '192.222.53.15')
            remote_user = os.getenv('REMOTE_USER', 'ubuntu')
            remote_port = os.getenv('REMOTE_PORT', '22')
            
            # Build scp command (same as bash script)
            scp_cmd = [
                'scp', '-r', '-P', remote_port, '-i', ssh_key,
                str(local_dir),
                f'{remote_user}@{remote_host}:{clean_remote_dir}'
            ]
            
            logger.info(f"Using scp to upload directory: {' '.join(scp_cmd)}")
            
            # Execute scp command
            result = subprocess.run(scp_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"scp failed: {result.stderr}")
                raise RuntimeError(f"scp upload failed: {result.stderr}")
            
            logger.info(f"Successfully uploaded directory using scp")
            
        except Exception as e:
            logger.error(f"scp upload failed, falling back to SFTP: {e}")
            # Fallback to SFTP if scp fails
            with self.ssh_manager.get_sftp() as sftp:
                for item in local_dir.rglob('*'):
                    if item.is_file():
                        rel_path = item.relative_to(local_dir)
                        remote_path = f"{clean_remote_dir}/{rel_path}"
                        sftp.put(str(item), remote_path)
                        logger.debug(f"Uploaded {item.name} via SFTP fallback")
    
    def _ensure_remote_directory(self, sftp, remote_dir: str) -> None:
        """Ensure remote directory exists, create if necessary."""
        # Ensure remote path uses forward slashes for all operations
        clean_remote_dir = remote_dir.replace('\\', '/')
        
        try:
            sftp.stat(clean_remote_dir)
        except FileNotFoundError:
            # Use SSH command to create directories (same as bash script approach)
            # This ensures proper ownership and permissions
            try:
                self.ssh_manager.execute_command_success(f"mkdir -p '{clean_remote_dir}'", stream_output=False)
            except Exception as e:
                logger.error(f"Failed to create remote directory {clean_remote_dir}: {e}")
                raise RuntimeError(f"Cannot create remote directory {clean_remote_dir}: {e}")
    
    def download_results(self, prompt_file: Path) -> None:
        """
        Download results from remote to local outputs directory.
        
        Args:
            prompt_file: Path to local prompt file (used to determine output names)
        """
        prompt_name = prompt_file.stem
        local_output_dir = Path(f"outputs/{prompt_name}")
        
        logger.info(f"Downloading results for {prompt_name}")
        
        # Create local output directory
        local_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download main results
        remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
        self._download_directory(remote_output_dir, local_output_dir)
        
        # Download upscaled results if they exist
        remote_upscaled_dir = f"{remote_output_dir}_upscaled"
        local_upscaled_dir = Path(f"outputs/{prompt_name}_upscaled")
        
        try:
            with self.ssh_manager.get_sftp() as sftp:
                sftp.stat(remote_upscaled_dir)
            
            # Upscaled results exist, download them
            local_upscaled_dir.mkdir(parents=True, exist_ok=True)
            self._download_directory(remote_upscaled_dir, local_upscaled_dir)
            logger.info(f"Downloaded upscaled results to {local_upscaled_dir}")
            
        except FileNotFoundError:
            logger.info("No upscaled results found")
    
    def _download_directory(self, remote_dir: str, local_dir: Path) -> None:
        """Recursively download a directory from remote."""
        logger.info(f"Downloading {remote_dir} -> {local_dir}")
        
        with self.ssh_manager.get_sftp() as sftp:
            try:
                # List all items in remote directory
                remote_items = sftp.listdir_attr(remote_dir)
                
                for item in remote_items:
                    remote_path = f"{remote_dir}/{item.filename}"
                    local_path = local_dir / item.filename
                    
                    if item.st_mode & 0o40000:  # Directory
                        # Create local directory
                        local_path.mkdir(exist_ok=True)
                        
                        # Recursively download subdirectory
                        self._download_directory(remote_path, local_path)
                    else:  # File
                        # Download file
                        sftp.get(remote_path, str(local_path))
                        logger.debug(f"Downloaded {item.filename}")
                
                logger.info(f"Successfully downloaded {remote_dir}")
                
            except Exception as e:
                logger.error(f"Failed to download {remote_dir}: {e}")
                raise RuntimeError(f"Download failed: {e}")
    
    def create_remote_directory(self, remote_path: str) -> None:
        """Create a directory on the remote system."""
        logger.info(f"Creating remote directory: {remote_path}")
        
        with self.ssh_manager.get_sftp() as sftp:
            self._ensure_remote_directory(sftp, remote_path)
    
    def file_exists_remote(self, remote_path: str) -> bool:
        """Check if a file exists on the remote system."""
        try:
            with self.ssh_manager.get_sftp() as sftp:
                sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
    
    def list_remote_directory(self, remote_dir: str) -> List[str]:
        """List contents of a remote directory."""
        try:
            with self.ssh_manager.get_sftp() as sftp:
                return sftp.listdir(remote_dir)
        except Exception as e:
            logger.error(f"Failed to list remote directory {remote_dir}: {e}")
            return []
