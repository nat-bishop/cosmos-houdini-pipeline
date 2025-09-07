#!/usr/bin/env python3
"""File transfer service for Cosmos-Transfer1 workflows.
Windows implementation using SFTP for file transfers.
"""

from __future__ import annotations

import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from cosmos_workflow.utils.logging import logger

if TYPE_CHECKING:
    from cosmos_workflow.connection.ssh_manager import SSHManager


class FileTransferService:
    """Handles file transfers between local and remote systems via rsync/SSH."""

    def __init__(self, ssh_manager: SSHManager, remote_dir: str):
        self.ssh_manager = ssh_manager
        # Use POSIX separators on remote
        self.remote_dir = remote_dir.replace("\\", "/")

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def upload_prompt_and_videos(self, prompt_file: Path, video_dirs: list[Path]) -> None:
        """Upload prompt file and video directories via SFTP.

        DEPRECATED: This method is no longer used. The orchestrator now handles
        format conversion and uses upload_file() directly.
        """
        logger.warning("upload_prompt_and_videos is deprecated and will be removed")

        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        remote_prompts_dir = f"{self.remote_dir}/inputs/prompts"
        remote_videos_dir = f"{self.remote_dir}/inputs/videos"

        # Upload prompt file as-is
        self.upload_file(prompt_file, remote_prompts_dir)

        # Upload video directories
        for vd in video_dirs:
            if vd.exists():
                self.upload_directory(vd, f"{remote_videos_dir}/{vd.name}")

    def upload_file(self, local_path: Path | str, remote_dir: str) -> bool:
        """Upload a single file to a remote directory via SFTP."""
        local_path = Path(local_path) if isinstance(local_path, str) else local_path
        if not local_path.exists():
            raise FileNotFoundError(local_path)
        remote_dir = remote_dir.replace("\\", "/")
        self._remote_mkdirs([remote_dir])
        self._sftp_upload_file(local_path, f"{remote_dir}/{local_path.name}")
        return True

    def upload_directory(self, local_dir: Path | str, remote_dir: str) -> bool:
        """Upload a directory recursively to remote via SFTP."""
        local_dir = Path(local_dir) if isinstance(local_dir, str) else local_dir
        if not local_dir.exists():
            raise FileNotFoundError(local_dir)
        remote_dir = remote_dir.replace("\\", "/")
        self._remote_mkdirs([remote_dir])
        self._sftp_upload_dir(local_dir, remote_dir)
        return True

    def download_file(self, remote_file: str, local_file: Path | str) -> bool:
        """Download a single file from remote via SFTP.

        Args:
            remote_file: Remote file path to download
            local_file: Local file path to save to

        Returns:
            True if download successful

        Raises:
            FileNotFoundError: If remote file doesn't exist
            PermissionError: If access denied to remote file
            RuntimeError: If download fails
        """
        # Convert to Path if string
        local_path = Path(local_file) if isinstance(local_file, str) else local_file
        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert Windows paths to POSIX for remote
        remote_file = remote_file.replace("\\", "/")

        # Download file via SFTP with error handling
        try:
            with self.ssh_manager.get_sftp() as sftp:
                # Check if remote file exists
                try:
                    sftp.stat(remote_file)
                except FileNotFoundError as e:
                    logger.error("Remote file not found: %s", remote_file)
                    raise FileNotFoundError(f"Remote file not found: {remote_file}") from e

                logger.info("Downloading file: %s -> %s", remote_file, str(local_path))
                sftp.get(remote_file, str(local_path))
                logger.debug("Successfully downloaded %s", local_path.name)

        except PermissionError:
            logger.error("Permission denied accessing remote file: %s", remote_file)
            raise
        except FileNotFoundError:
            raise  # Re-raise the FileNotFoundError we caught above
        except Exception as e:
            logger.error("Failed to download file %s: %s", remote_file, e)
            raise RuntimeError(f"Download failed: {e}") from e

        return True

    def download_directory(self, remote_dir: str, local_dir: Path | str) -> bool:
        """Download a directory recursively from remote via SFTP."""
        local_dir = Path(local_dir) if isinstance(local_dir, str) else local_dir
        local_dir.mkdir(parents=True, exist_ok=True)
        remote_dir = remote_dir.replace("\\", "/")
        self._sftp_download_dir(remote_dir, local_dir)
        return True

    def download_results(self, prompt_file: Path) -> None:
        """Download results from remote:
        remote: <remote>/outputs/<prompt_name>[ _upscaled]
        local : outputs/<prompt_name>[ _upscaled].
        """
        prompt_name = prompt_file.stem

        # Main outputs
        remote_out = f"{self.remote_dir}/outputs/{prompt_name}"
        local_out = Path(f"outputs/{prompt_name}")
        local_out.mkdir(parents=True, exist_ok=True)
        if self.file_exists_remote(remote_out):
            self._sftp_download_dir(remote_out, local_out)
            # Create manifest of downloaded files
            self._create_manifest(local_out)
        else:
            logger.info("No remote outputs found at %s", remote_out)

        # Upscaled outputs (optional)
        remote_up = f"{remote_out}_upscaled"
        local_up = Path(f"outputs/{prompt_name}_upscaled")
        if self.file_exists_remote(remote_up):
            local_up.mkdir(parents=True, exist_ok=True)
            self._sftp_download_dir(remote_up, local_up)
            # Create manifest for upscaled outputs
            self._create_manifest(local_up)
        else:
            logger.info("No upscaled results found.")

    def _create_manifest(self, directory: Path) -> None:
        """Create a manifest file listing all files in the directory.

        Args:
            directory: Directory to create manifest for
        """
        manifest_path = directory / "manifest.txt"
        try:
            with open(manifest_path, "w") as f:
                f.write(f"# Manifest for {directory.name}\n")
                f.write(f"# Generated at {datetime.now(timezone.utc).isoformat()}\n")
                f.write("# Format: filename\tsize_bytes\tmodified_timestamp\n\n")

                for file_path in sorted(directory.iterdir()):
                    if file_path.name != "manifest.txt" and file_path.is_file():
                        stat = file_path.stat()
                        f.write(f"{file_path.name}\t{stat.st_size}\t{stat.st_mtime}\n")

                logger.debug("Created manifest at %s", manifest_path)
        except Exception as e:
            logger.warning("Failed to create manifest: %s", e)

    def create_remote_directory(self, remote_path: str) -> None:
        """Create a directory on the remote system."""
        self._remote_mkdirs([remote_path.replace("\\", "/")])

    def file_exists_remote(self, remote_path: str) -> bool:
        """Check if a path exists on the remote system."""
        try:
            with self.ssh_manager.get_sftp() as sftp:
                sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False

    def list_remote_directory(self, remote_dir: str) -> list[str]:
        """List contents of a remote directory."""
        try:
            with self.ssh_manager.get_sftp() as sftp:
                return sftp.listdir(remote_dir)
        except Exception as e:
            logger.error("Failed to list remote directory %s: %s", remote_dir, e)
            return []

    # ------------------------------------------------------------------ #
    # SFTP helpers
    # ------------------------------------------------------------------ #

    def _sftp_upload_file(self, local_file: Path, remote_abs_file: str) -> None:
        """Upload a single file via SFTP to a specific remote absolute path."""
        remote_abs_file = remote_abs_file.replace("\\", "/")
        with self.ssh_manager.get_sftp() as sftp:
            logger.info("Uploading file: %s -> %s", local_file, remote_abs_file)
            sftp.put(str(local_file), remote_abs_file)
            logger.debug("Successfully uploaded %s", local_file.name)

    def _sftp_upload_dir(self, local_dir: Path, remote_abs_dir: str) -> None:
        """Upload a directory to a remote absolute directory via SFTP.
        Copies all files in the directory recursively.
        """
        remote_abs_dir = remote_abs_dir.replace("\\", "/")
        with self.ssh_manager.get_sftp() as sftp:
            logger.info("Uploading directory: %s -> %s", local_dir, remote_abs_dir)

            for item in local_dir.iterdir():
                if item.is_file():
                    remote_path = f"{remote_abs_dir}/{item.name}"
                    sftp.put(str(item), remote_path)
                    logger.debug("Uploaded %s", item.name)
                elif item.is_dir():
                    # Recursively handle subdirectories
                    remote_subdir = f"{remote_abs_dir}/{item.name}"
                    self._remote_mkdirs([remote_subdir])
                    self._sftp_upload_dir(item, remote_subdir)

    def _sftp_download_dir(self, remote_abs_dir: str, local_dir: Path) -> None:
        """Download a remote directory to a local directory via SFTP."""
        remote_abs_dir = remote_abs_dir.replace("\\", "/")
        with self.ssh_manager.get_sftp() as sftp:
            logger.info("Downloading directory: %s -> {local_dir}", remote_abs_dir)

            # List remote directory contents
            try:
                items = sftp.listdir_attr(remote_abs_dir)
            except Exception as e:
                logger.error("Failed to list directory %s: %s", remote_abs_dir, e)
                return

            for item in items:
                remote_path = f"{remote_abs_dir}/{item.filename}"
                local_path = local_dir / item.filename

                if stat.S_ISDIR(item.st_mode):
                    # Recursively download subdirectories
                    local_path.mkdir(parents=True, exist_ok=True)
                    self._sftp_download_dir(remote_path, local_path)
                else:
                    # Download file
                    sftp.get(remote_path, str(local_path))
                    logger.debug("Downloaded %s", item.filename)

    # ------------------------------------------------------------------ #
    # Misc helpers
    # ------------------------------------------------------------------ #

    def _remote_mkdirs(self, abs_paths: list[str]) -> None:
        """Create directories on remote system."""
        if not abs_paths:
            return
        # quote each path and create via one shell
        join = " ".join(self._q(p) for p in abs_paths)
        self.ssh_manager.execute_command_success(f"mkdir -p {join}", stream_output=False)

    @staticmethod
    def _q(path: str) -> str:
        """Quote a path for shell safety."""
        return "'" + path.replace("'", "'\\''") + "'"
