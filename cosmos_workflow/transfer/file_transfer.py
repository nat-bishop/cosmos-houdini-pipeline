#!/usr/bin/env python3
"""File transfer service for Cosmos-Transfer1 workflows.
Windows implementation using SFTP for file transfers.
"""

from __future__ import annotations

import logging
import stat
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cosmos_workflow.connection.ssh_manager import SSHManager

logger = logging.getLogger(__name__)


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
        """Upload prompt file, video directories, and scripts/ via SFTP.
        Creates remote directories if missing and uploads all files.
        """
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        remote_prompts_dir = f"{self.remote_dir}/inputs/prompts"
        remote_videos_dir = f"{self.remote_dir}/inputs/videos"
        remote_scripts_dir = f"{self.remote_dir}/bashscripts"

        # Ensure required remote directories exist
        self._remote_mkdirs([remote_prompts_dir, remote_videos_dir, remote_scripts_dir])

        # 1) Prompt JSON → inputs/prompts/<name>.json
        prompt_name = prompt_file.stem
        self._sftp_upload_file(prompt_file, f"{remote_prompts_dir}/{prompt_name}.json")

        # 2) Videos → inputs/videos/<dir_name>/...
        for vd in video_dirs:
            if not vd.exists():
                logger.warning("Video directory missing: %s (skipping)", vd)
                continue
            remote_video_path = f"{remote_videos_dir}/{vd.name}"
            self._remote_mkdirs([remote_video_path])
            self._sftp_upload_dir(vd, remote_video_path)

        # 3) Bash scripts (*.sh) → bashscripts/
        scripts_dir = Path("scripts")
        if scripts_dir.exists():
            self._sftp_upload_dir(scripts_dir, remote_scripts_dir)
            # Make uploaded scripts executable and writable by group (for container use)
            self.ssh_manager.execute_command_success(
                f"chmod +x {self._q(remote_scripts_dir)}/*.sh || true", stream_output=False
            )
            self.ssh_manager.execute_command_success(
                f"chmod -R g+w {self._q(remote_scripts_dir)}", stream_output=False
            )
        else:
            logger.warning("Scripts directory not found; skipping script upload.")

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
        else:
            logger.info("No remote outputs found at %s", remote_out)

        # Upscaled outputs (optional)
        remote_up = f"{remote_out}_upscaled"
        local_up = Path(f"outputs/{prompt_name}_upscaled")
        if self.file_exists_remote(remote_up):
            local_up.mkdir(parents=True, exist_ok=True)
            self._sftp_download_dir(remote_up, local_up)
        else:
            logger.info("No upscaled results found.")

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
            logger.info("Uploading file: %s -> {remote_abs_file}", local_file)
            sftp.put(str(local_file), remote_abs_file)
            logger.debug("Successfully uploaded %s", local_file.name)

    def _sftp_upload_dir(self, local_dir: Path, remote_abs_dir: str) -> None:
        """Upload a directory to a remote absolute directory via SFTP.
        Copies all files in the directory recursively.
        """
        remote_abs_dir = remote_abs_dir.replace("\\", "/")
        with self.ssh_manager.get_sftp() as sftp:
            logger.info("Uploading directory: %s -> {remote_abs_dir}", local_dir)

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
