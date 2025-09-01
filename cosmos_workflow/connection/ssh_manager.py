#!/usr/bin/env python3
"""SSH connection management for Cosmos-Transfer1 workflows.
Handles remote connections with proper error handling and connection pooling.
"""

import logging
from contextlib import contextmanager
from typing import Any

import paramiko

logger = logging.getLogger(__name__)


class SSHManager:
    """Manages SSH connections to remote instances."""

    def __init__(self, ssh_options: dict[str, Any]):
        self.ssh_options = ssh_options
        self.ssh_client: paramiko.SSHClient | None = None
        self.sftp_client: paramiko.SFTPClient | None = None

    def connect(self) -> None:
        """Establish SSH connection to remote instance."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

            logger.info("Connecting to %s:{self.ssh_options['port']}", self.ssh_options["hostname"])
            self.ssh_client.connect(**self.ssh_options)

            logger.info("SSH connection established successfully")

        except Exception as e:
            logger.error("Failed to establish SSH connection: %s", e)
            raise ConnectionError(f"SSH connection failed: {e}")

    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.sftp_client:
            self.sftp_client.close()
            self.sftp_client = None

        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None

        logger.info("SSH connection closed")

    def is_connected(self) -> bool:
        """Check if SSH connection is active."""
        if not self.ssh_client:
            return False

        try:
            # Try to execute a simple command to test connection
            self.ssh_client.exec_command("echo 'test'", timeout=5)
            return True
        except (paramiko.SSHException, OSError, AttributeError):
            return False

    def ensure_connected(self) -> None:
        """Ensure SSH connection is active, reconnect if necessary."""
        if not self.is_connected():
            logger.info("SSH connection lost, reconnecting...")
            self.connect()

    @contextmanager
    def get_sftp(self):
        """Get SFTP client with automatic cleanup."""
        if not self.ssh_client:
            raise ConnectionError("SSH connection not established")

        try:
            self.sftp_client = self.ssh_client.open_sftp()
            yield self.sftp_client
        finally:
            if self.sftp_client:
                self.sftp_client.close()
                self.sftp_client = None

    def execute_command(
        self, command: str, timeout: int = 300, stream_output: bool = True
    ) -> tuple[int, str, str]:
        """Execute command on remote instance.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            stream_output: Whether to stream output in real-time

        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        self.ensure_connected()

        logger.info("Executing command: %s", command)

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)

            # Collect output
            stdout_lines = []
            stderr_lines = []

            if stream_output:
                # Stream stdout in real-time
                for line in stdout:
                    line = line.strip()
                    if line:
                        try:
                            print(f"  {line}")
                        except UnicodeEncodeError:
                            # Fallback for Windows encoding issues
                            print(f"  {line.encode('ascii', 'ignore').decode('ascii')}")
                        stdout_lines.append(line)

                # Collect stderr
                stderr_output = stderr.read().decode().strip()
                if stderr_output:
                    stderr_lines = stderr_output.split("\n")
                    for line in stderr_lines:
                        if line.strip():
                            try:
                                print(f"  STDERR: {line.strip()}")
                            except UnicodeEncodeError:
                                # Fallback for Windows encoding issues
                                print(
                                    f"  STDERR: {line.strip().encode('ascii', 'ignore').decode('ascii')}"
                                )
            else:
                # Collect all output at once
                stdout_output = stdout.read().decode().strip()
                if stdout_output:
                    stdout_lines = stdout_output.split("\n")

                stderr_output = stderr.read().decode().strip()
                if stderr_output:
                    stderr_lines = stderr_output.split("\n")

            # Wait for command completion
            exit_code = stdout.channel.recv_exit_status()

            logger.info("Command completed with exit code: %s", exit_code)

            return exit_code, "\n".join(stdout_lines), "\n".join(stderr_lines)

        except Exception as e:
            logger.error("Command execution failed: %s", e)
            raise RuntimeError(f"Command execution failed: {e}")

    def execute_command_success(
        self, command: str, timeout: int = 300, stream_output: bool = True
    ) -> str:
        """Execute command and raise exception on non-zero exit code.

        Args:
            command: Command to execute
            timeout: Command timeout in seconds
            stream_output: Whether to stream output in real-time

        Returns:
            Command stdout

        Raises:
            RuntimeError: If command fails
        """
        exit_code, stdout, stderr = self.execute_command(command, timeout, stream_output)

        if exit_code != 0:
            error_msg = f"Command failed with exit code {exit_code}"
            if stderr:
                error_msg += f": {stderr}"
            raise RuntimeError(error_msg)

        return stdout

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
