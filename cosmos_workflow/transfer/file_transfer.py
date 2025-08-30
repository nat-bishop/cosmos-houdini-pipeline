#!/usr/bin/env python3
"""
File transfer service for Cosmos-Transfer1 workflows.
Simplified rsync implementation (SSH), with minimal knobs.
"""

from __future__ import annotations
import os
import subprocess
from pathlib import Path
from typing import List, Optional
import logging

from cosmos_workflow.connection.ssh_manager import SSHManager

logger = logging.getLogger(__name__)


class FileTransferService:
    """Handles file transfers between local and remote systems via rsync/SSH."""

    def __init__(self, ssh_manager: SSHManager, remote_dir: str):
        self.ssh_manager = ssh_manager
        # Use POSIX separators on remote
        self.remote_dir = remote_dir.replace("\\", "/")

        # Read SSH connection details from env (keeps your current pattern)
        self._remote_host = os.getenv("REMOTE_HOST", "127.0.0.1")
        self._remote_user = os.getenv("REMOTE_USER", "ubuntu")
        self._remote_port = os.getenv("REMOTE_PORT", "22")
        self._ssh_key = os.getenv("SSH_KEY", os.path.expanduser("~/.ssh/id_rsa"))

        # Build the ssh transport for rsync
        self._ssh_cmd = f'ssh -i "{self._ssh_key}" -p {self._remote_port} -o StrictHostKeyChecking=no'

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def upload_prompt_and_videos(self, prompt_file: Path, video_dirs: list[Path]) -> None:
        """
        Upload prompt file, video directories, and scripts/ via rsync.
        Creates remote directories if missing and only sends changed files.
        """
        if not prompt_file.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        remote_prompts_dir = f"{self.remote_dir}/inputs/prompts"
        remote_videos_dir  = f"{self.remote_dir}/inputs/videos"
        remote_scripts_dir = f"{self.remote_dir}/bashscripts"

        # Ensure required remote directories exist
        self._remote_mkdirs([remote_prompts_dir, remote_videos_dir, remote_scripts_dir])

        # 1) Prompt JSON → inputs/prompts/<name>.json
        prompt_name = prompt_file.stem
        self._rsync_file(prompt_file, f"{remote_prompts_dir}/{prompt_name}.json")

        # 2) Videos → inputs/videos/<dir_name>/...
        for vd in video_dirs:
            if not vd.exists():
                logger.warning(f"Video directory missing: {vd} (skipping)")
                continue
            self._remote_mkdirs([f"{remote_videos_dir}/{vd.name}"])
            self._rsync_dir(vd, f"{remote_videos_dir}/{vd.name}")

        # 3) Bash scripts (*.sh) → bashscripts/
        scripts_dir = Path("scripts")
        if scripts_dir.exists():
            self._rsync_dir(scripts_dir, remote_scripts_dir)
            # Make uploaded scripts executable and writable by group (for container use)
            self.ssh_manager.execute_command_success(
                f"chmod +x {self._q(remote_scripts_dir)}/*.sh || true", stream_output=False
            )
            self.ssh_manager.execute_command_success(
                f"chmod -R g+w {self._q(remote_scripts_dir)}", stream_output=False
            )
        else:
            logger.warning("Scripts directory not found; skipping script upload.")

    def upload_file(self, local_path: Path, remote_dir: str) -> None:
        """Upload a single file to a remote directory via rsync."""
        if not local_path.exists():
            raise FileNotFoundError(local_path)
        remote_dir = remote_dir.replace("\\", "/")
        self._remote_mkdirs([remote_dir])
        self._rsync_file(local_path, f"{remote_dir}/{local_path.name}")

    def download_results(self, prompt_file: Path) -> None:
        """
        Download results from remote:
          remote: <remote>/outputs/<prompt_name>[ _upscaled]
          local : outputs/<prompt_name>[ _upscaled]
        """
        prompt_name = prompt_file.stem

        # Main outputs
        remote_out = f"{self.remote_dir}/outputs/{prompt_name}"
        local_out = Path(f"outputs/{prompt_name}")
        local_out.mkdir(parents=True, exist_ok=True)
        if self.file_exists_remote(remote_out):
            self._rsync_pull(remote_out + "/", str(local_out))
        else:
            logger.info(f"No remote outputs found at {remote_out}")

        # Upscaled outputs (optional)
        remote_up = f"{remote_out}_upscaled"
        local_up = Path(f"outputs/{prompt_name}_upscaled")
        if self.file_exists_remote(remote_up):
            local_up.mkdir(parents=True, exist_ok=True)
            self._rsync_pull(remote_up + "/", str(local_up))
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

    def list_remote_directory(self, remote_dir: str) -> List[str]:
        """List contents of a remote directory."""
        try:
            with self.ssh_manager.get_sftp() as sftp:
                return sftp.listdir(remote_dir)
        except Exception as e:
            logger.error(f"Failed to list remote directory {remote_dir}: {e}")
            return []

    # ------------------------------------------------------------------ #
    # Rsync helpers
    # ------------------------------------------------------------------ #

    def _rsync_file(self, local_file: Path, remote_abs_file: str) -> None:
        """
        Rsync a single file to a specific remote absolute path.
        """
        remote_abs_file = remote_abs_file.replace("\\", "/")
        remote_spec = f"{self._remote_user}@{self._remote_host}:{remote_abs_file}"
        cmd = [
            "rsync",
            "-az",                       # archive-ish and compress
            "--progress",                # progress text (optional)
            "-e", self._ssh_cmd,         # use our SSH transport
            str(local_file),
            remote_spec,
        ]
        self._run(cmd, f"rsync file: {local_file} → {remote_abs_file}")

    def _rsync_dir(self, local_dir: Path, remote_abs_dir: str) -> None:
        """
        Rsync a directory to a remote absolute directory.
        Trailing slash on the source means "copy contents", not the directory itself.
        """
        src = str(local_dir)
        if not src.endswith(os.sep):
            src = src + os.sep  # ensure trailing sep to copy contents
        remote_abs_dir = remote_abs_dir.replace("\\", "/")
        remote_spec = f"{self._remote_user}@{self._remote_host}:{remote_abs_dir}"
        cmd = [
            "rsync",
            "-az",                       # archive-ish and compress
            "--delete-after",            # optional: clean up stale files after transfer (safer than --delete)
            "--progress",
            "-e", self._ssh_cmd,
            src,
            remote_spec,
        ]
        self._run(cmd, f"rsync dir: {local_dir} → {remote_abs_dir}")

    def _rsync_pull(self, remote_abs_dir_or_file: str, local_dir: str) -> None:
        """
        Pull a remote directory (with trailing slash) or file to a local directory.
        """
        remote_abs = remote_abs_dir_or_file.replace("\\", "/")
        remote_spec = f"{self._remote_user}@{self._remote_host}:{remote_abs}"
        cmd = [
            "rsync",
            "-az",
            "--progress",
            "-e", self._ssh_cmd,
            remote_spec,
            local_dir,
        ]
        self._run(cmd, f"rsync pull: {remote_abs} → {local_dir}")

    # ------------------------------------------------------------------ #
    # Misc helpers
    # ------------------------------------------------------------------ #

    def _remote_mkdirs(self, abs_paths: list[str]) -> None:
        if not abs_paths:
            return
        # quote each path and create via one shell
        join = " ".join(self._q(p) for p in abs_paths)
        self.ssh_manager.execute_command_success(f"mkdir -p {join}", stream_output=False)

    def _run(self, cmd: list[str], label: str) -> None:
        logger.info(f"{label}\n  $ {' '.join(cmd)}")
        proc = subprocess.run(cmd, text=True, capture_output=True)
        if proc.returncode != 0:
            logger.error(proc.stdout)
            logger.error(proc.stderr)
            raise RuntimeError(f"{label} failed with exit {proc.returncode}")
        if proc.stdout:
            logger.debug(proc.stdout.strip())
        if proc.stderr:
            # rsync sends progress to stderr; only log at debug to avoid noisy info logs
            logger.debug(proc.stderr.strip())

    @staticmethod
    def _q(path: str) -> str:
        return "'" + path.replace("'", "'\\''") + "'"
