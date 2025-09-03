"""
Tests for the SSHManager class.

This module tests the SSH connection management functionality
that handles connections to remote instances using paramiko.
"""

from unittest.mock import Mock, patch

import paramiko
import pytest

from cosmos_workflow.connection.ssh_manager import SSHManager


class TestSSHManager:
    """Test suite for SSHManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Mock SSH connection parameters
        self.ssh_options = {
            "hostname": "192.168.1.100",
            "username": "ubuntu",
            "key_filename": "./test_ssh_key",
            "port": 22,
        }

        # Initialize SSHManager with mock options
        self.ssh_manager = SSHManager(self.ssh_options)

    def test_init_with_valid_options(self):
        """Test SSHManager initialization with valid connection options."""
        assert self.ssh_manager.ssh_options == self.ssh_options
        assert self.ssh_manager.ssh_client is None
        assert self.ssh_manager.sftp_client is None

    def test_connect_establishes_ssh_connection(self):
        """Test that connect method establishes SSH connection successfully."""
        # Mock paramiko SSHClient
        mock_client = Mock()
        mock_client.connect.return_value = None

        with patch("paramiko.SSHClient", return_value=mock_client):
            self.ssh_manager.connect()

            # Check that client was created and connected
            assert self.ssh_manager.ssh_client is not None
            mock_client.connect.assert_called_once_with(**self.ssh_options)

    def test_connect_handles_connection_errors(self):
        """Test that connect method handles SSH connection errors gracefully."""
        # Mock paramiko SSHClient that raises an exception
        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Connection failed")

        with patch("paramiko.SSHClient", return_value=mock_client):
            with pytest.raises(ConnectionError, match="SSH connection failed: Connection failed"):
                self.ssh_manager.connect()

    def test_disconnect_closes_connections(self):
        """Test that disconnect method properly closes SSH and SFTP connections."""
        # Mock existing connections
        mock_client = Mock()
        mock_sftp = Mock()
        self.ssh_manager.ssh_client = mock_client
        self.ssh_manager.sftp_client = mock_sftp

        # Disconnect
        self.ssh_manager.disconnect()

        # Check that connections were closed
        mock_sftp.close.assert_called_once()
        mock_client.close.assert_called_once()
        assert self.ssh_manager.ssh_client is None
        assert self.ssh_manager.sftp_client is None

    def test_disconnect_handles_none_connections(self):
        """Test that disconnect method handles None connections gracefully."""
        # Should not raise any exceptions
        self.ssh_manager.disconnect()

        # Connections should remain None
        assert self.ssh_manager.ssh_client is None
        assert self.ssh_manager.sftp_client is None

    def test_is_connected_with_active_connection(self):
        """Test is_connected returns True with active connection."""
        # Mock SSH client with successful exec_command
        mock_client = Mock()
        mock_client.exec_command.return_value = (Mock(), Mock(), Mock())
        self.ssh_manager.ssh_client = mock_client

        assert self.ssh_manager.is_connected() is True
        mock_client.exec_command.assert_called_once_with("echo 'test'", timeout=5)

    def test_is_connected_with_no_client(self):
        """Test is_connected returns False with no client."""
        assert self.ssh_manager.is_connected() is False

    def test_is_connected_with_failed_command(self):
        """Test is_connected returns False when command execution fails."""
        # Mock SSH client with failed exec_command
        mock_client = Mock()
        mock_client.exec_command.side_effect = paramiko.SSHException("Connection lost")
        self.ssh_manager.ssh_client = mock_client

        assert self.ssh_manager.is_connected() is False

    def test_ensure_connected_reconnects_when_needed(self):
        """Test that ensure_connected reconnects when connection is lost."""
        # Mock is_connected to return False, then True after connect
        with patch.object(self.ssh_manager, "is_connected", side_effect=[False, True]):
            with patch.object(self.ssh_manager, "connect") as mock_connect:
                self.ssh_manager.ensure_connected()
                mock_connect.assert_called_once()

    def test_ensure_connected_does_nothing_when_connected(self):
        """Test that ensure_connected does nothing when already connected."""
        with patch.object(self.ssh_manager, "is_connected", return_value=True):
            with patch.object(self.ssh_manager, "connect") as mock_connect:
                self.ssh_manager.ensure_connected()
                mock_connect.assert_not_called()

    def test_get_sftp_creates_sftp_session(self):
        """Test that get_sftp creates SFTP session when connected."""
        # Mock SSH client
        mock_client = Mock()
        mock_sftp = Mock()
        mock_client.open_sftp.return_value = mock_sftp

        self.ssh_manager.ssh_client = mock_client

        # Get SFTP
        with self.ssh_manager.get_sftp() as sftp:
            assert sftp == mock_sftp
            mock_client.open_sftp.assert_called_once()

    def test_get_sftp_without_connection(self):
        """Test that get_sftp raises error when not connected."""
        with pytest.raises(ConnectionError, match="SSH connection not established"):
            with self.ssh_manager.get_sftp():
                pass

    def test_get_sftp_cleanup_on_exit(self):
        """Test that get_sftp properly cleans up SFTP session."""
        # Mock SSH client
        mock_client = Mock()
        mock_sftp = Mock()
        mock_client.open_sftp.return_value = mock_sftp

        self.ssh_manager.ssh_client = mock_client

        # Use get_sftp context manager
        with self.ssh_manager.get_sftp() as sftp:
            assert sftp == mock_sftp

        # Check that SFTP was closed
        mock_sftp.close.assert_called_once()
        assert self.ssh_manager.sftp_client is None

    def test_execute_command_ensures_connection(self):
        """Test that execute_command ensures connection before execution."""
        with patch.object(self.ssh_manager, "ensure_connected") as mock_ensure:
            # Mock the actual command execution
            mock_client = Mock()

            # Mock stdout and stderr objects
            mock_stdout = Mock()
            mock_stderr = Mock()
            mock_stdout.channel.recv_exit_status.return_value = 0
            mock_stdout.__iter__ = lambda x: iter(["Command output"])  # String instead of bytes
            mock_stderr.read.return_value = b""

            # Mock exec_command to return tuple
            mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

            self.ssh_manager.ssh_client = mock_client

            # Execute command
            self.ssh_manager.execute_command("ls -la")

            # Check that ensure_connected was called
            mock_ensure.assert_called_once()

    def test_execute_command_successful_execution(self):
        """Test successful command execution."""
        # Mock SSH client and channel
        mock_client = Mock()

        # Mock stdout and stderr objects
        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.__iter__ = lambda x: iter(["Command output"])  # String instead of bytes
        mock_stderr.read.return_value = b""

        # Mock exec_command to return tuple
        mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

        self.ssh_manager.ssh_client = mock_client

        # Execute command
        exit_code, stdout, stderr = self.ssh_manager.execute_command("ls -la")

        # Check result
        assert stdout == "Command output"
        assert stderr == ""
        assert exit_code == 0

    def test_execute_command_with_error(self):
        """Test command execution that returns an error."""
        # Mock SSH client and channel with error
        mock_client = Mock()

        # Mock stdout and stderr objects
        mock_stdout = Mock()
        mock_stderr = Mock()
        mock_stdout.channel.recv_exit_status.return_value = 1
        mock_stdout.__iter__ = lambda x: iter([])  # No stdout
        mock_stderr.read.return_value = b"Permission denied"

        # Mock exec_command to return tuple
        mock_client.exec_command.return_value = (Mock(), mock_stdout, mock_stderr)

        self.ssh_manager.ssh_client = mock_client

        # Execute command
        exit_code, stdout, stderr = self.ssh_manager.execute_command("rm /root/file")

        # Check result
        assert stdout == ""
        assert stderr == "Permission denied"
        assert exit_code == 1

    def test_context_manager_enter_exit(self):
        """Test SSHManager context manager functionality."""
        # Mock connect and disconnect methods
        with patch.object(self.ssh_manager, "connect") as mock_connect:
            with patch.object(self.ssh_manager, "disconnect") as mock_disconnect:
                with self.ssh_manager:
                    mock_connect.assert_called_once()

                mock_disconnect.assert_called_once()

    def test_context_manager_exit_with_exception(self):
        """Test SSHManager context manager exit method even with exceptions."""
        # Mock connect and disconnect methods
        with patch.object(self.ssh_manager, "connect"):
            with patch.object(self.ssh_manager, "disconnect") as mock_disconnect:
                try:
                    with self.ssh_manager:
                        raise Exception("Test exception")
                except Exception:
                    pass  # Exception was raised

                # Should still disconnect
                mock_disconnect.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
