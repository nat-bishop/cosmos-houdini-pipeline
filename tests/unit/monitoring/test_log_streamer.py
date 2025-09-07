#!/usr/bin/env python3
"""Tests for RemoteLogStreamer with seek-based position tracking."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.monitoring.log_streamer import RemoteLogStreamer


class TestRemoteLogStreamer:
    """Test cases for RemoteLogStreamer."""

    def test_initialization(self):
        """Test that RemoteLogStreamer initializes correctly."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        assert streamer.ssh_manager == ssh_manager
        assert streamer.position == 0
        assert streamer.buffer_size == 8192  # Default buffer size

    def test_initialization_with_custom_buffer(self):
        """Test initialization with custom buffer size."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager, buffer_size=16384)

        assert streamer.buffer_size == 16384

    def test_stream_remote_log_creates_local_file(self):
        """Test that streaming creates the local log file with parent directories."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        # Mock file doesn't exist initially, then exists
        ssh_manager.execute_command.side_effect = [
            (1, "", ""),  # File doesn't exist
            (0, "100", ""),  # File size check
            (0, "log line 1\nlog line 2", ""),  # Read content
            (0, "100", ""),  # File size unchanged (stop condition)
        ]

        local_path = Path(".claude/workspace/test_log.log")
        streamer.stream_remote_log("/remote/log.log", local_path, poll_interval=0.01, timeout=0.1)

        # Verify local directory creation was attempted
        assert local_path.parent == Path(".claude/workspace")

    def test_stream_reads_incrementally_using_tail(self):
        """Test that streaming uses tail -c +position for efficient reading."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        # Simulate log file growing over time
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "50", ""),  # Initial size 50 bytes
            (0, "First log entry\nSecond entry\n", ""),  # First read (30 bytes)
            (0, "80", ""),  # Size grown to 80 bytes
            (0, "Third log entry\nFourth entry\n", ""),  # Second read (30 bytes)
            (0, "80", ""),  # Size unchanged (stop)
        ]

        local_path = Path(".claude/workspace/test_stream.log")
        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            streamer.stream_remote_log(
                "/remote/app.log", local_path, poll_interval=0.01, timeout=0.1
            )

        # Verify tail commands use correct position
        calls = ssh_manager.execute_command.call_args_list

        # First read from position 1 (start of file)
        assert "tail -c +1 /remote/app.log" in calls[2][0][0]
        # Second read from position 31 (after first 30 bytes)
        assert "tail -c +31 /remote/app.log" in calls[4][0][0]

    def test_stream_handles_no_new_content(self):
        """Test that streaming handles periods with no new content gracefully."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "100", ""),  # Initial size
            (0, "Initial content\n", ""),  # Read content
            (0, "100", ""),  # Size unchanged
            (0, "", ""),  # No new content (empty read)
            (0, "100", ""),  # Size still unchanged (stop)
        ]

        local_path = Path(".claude/workspace/no_new.log")
        content_written = []

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.write.side_effect = lambda x: content_written.append(x)
            mock_open.return_value.__enter__.return_value = mock_file

            streamer.stream_remote_log(
                "/remote/stable.log", local_path, poll_interval=0.01, timeout=0.1
            )

        # Verify only non-empty content was written
        assert len(content_written) == 1
        assert content_written[0] == "Initial content\n"

    def test_stream_stops_on_completion_marker(self):
        """Test that streaming stops when it detects a completion marker."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "200", ""),  # Initial size
            (0, "Processing...\n", ""),  # First read
            (0, "250", ""),  # Size grown
            (0, "More processing...\n[COSMOS_COMPLETE]\n", ""),  # Completion marker
        ]

        local_path = Path(".claude/workspace/complete.log")
        content_written = []

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.write.side_effect = lambda x: content_written.append(x)
            mock_open.return_value.__enter__.return_value = mock_file

            streamer.stream_remote_log(
                "/remote/job.log",
                local_path,
                poll_interval=0.01,
                timeout=10.0,  # Long timeout but should stop early
                completion_marker="[COSMOS_COMPLETE]",
            )

        # Verify both chunks were written and stopped after marker
        assert len(content_written) == 2
        assert "[COSMOS_COMPLETE]" in content_written[1]

        # Should not continue polling after marker found
        assert ssh_manager.execute_command.call_count == 5  # Not more

    def test_stream_handles_file_not_found_initially(self):
        """Test graceful handling when remote file doesn't exist initially."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.side_effect = [
            (1, "", "No such file"),  # File doesn't exist
            (1, "", "No such file"),  # Still doesn't exist
            (0, "", ""),  # Now it exists
            (0, "50", ""),  # Has content
            (0, "Log started\n", ""),  # Read content
            (0, "50", ""),  # Size unchanged (stop)
        ]

        local_path = Path(".claude/workspace/delayed.log")
        content_written = []

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.write.side_effect = lambda x: content_written.append(x)
            mock_open.return_value.__enter__.return_value = mock_file

            streamer.stream_remote_log(
                "/remote/delayed.log",
                local_path,
                poll_interval=0.01,
                timeout=0.5,
                wait_for_file=True,
            )

        # Verify content was eventually captured
        assert len(content_written) == 1
        assert content_written[0] == "Log started\n"

    def test_stream_respects_timeout(self):
        """Test that streaming respects the timeout parameter."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        # Simulate file that never stops growing
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
        ] + [(0, str(i * 100), "") for i in range(1, 100)]  # Keep growing

        local_path = Path(".claude/workspace/timeout.log")
        start_time = time.time()

        with patch("builtins.open", create=True):
            with pytest.raises(TimeoutError, match="Log streaming timed out after"):
                streamer.stream_remote_log(
                    "/remote/endless.log", local_path, poll_interval=0.01, timeout=0.1
                )

        elapsed = time.time() - start_time
        assert elapsed < 0.3  # Should timeout quickly

    def test_stream_captures_final_content(self):
        """Test that final content is fully captured even if size stops changing."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "1000", ""),  # Large file
            (0, "A" * 500, ""),  # First chunk
            (0, "1000", ""),  # Size unchanged but more to read
            (0, "B" * 500, ""),  # Second chunk
            (0, "1000", ""),  # Size unchanged (stop)
        ]

        local_path = Path(".claude/workspace/final.log")
        content_written = []

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.write.side_effect = lambda x: content_written.append(x)
            mock_open.return_value.__enter__.return_value = mock_file

            streamer.stream_remote_log(
                "/remote/large.log", local_path, poll_interval=0.01, timeout=0.1
            )

        # Verify all content was captured
        total_content = "".join(content_written)
        assert len(total_content) == 1000
        assert "A" * 500 in total_content
        assert "B" * 500 in total_content

    def test_stream_handles_ssh_errors_gracefully(self):
        """Test graceful error handling for SSH failures."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "100", ""),  # Initial size
            RuntimeError("SSH connection lost"),  # Connection failure
        ]

        local_path = Path(".claude/workspace/error.log")

        with patch("builtins.open", create=True):
            with pytest.raises(RuntimeError, match="Failed to stream log"):
                streamer.stream_remote_log(
                    "/remote/error.log", local_path, poll_interval=0.01, timeout=1.0
                )

    def test_get_remote_file_size(self):
        """Test getting remote file size using stat."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.return_value = (0, "12345", "")

        size = streamer._get_remote_file_size("/remote/file.log")

        assert size == 12345
        ssh_manager.execute_command.assert_called_with("stat -c %s /remote/file.log", timeout=10)

    def test_get_remote_file_size_handles_missing_file(self):
        """Test that missing files return size of 0."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.return_value = (1, "", "No such file")

        size = streamer._get_remote_file_size("/remote/missing.log")

        assert size == 0

    def test_read_remote_chunk(self):
        """Test reading a chunk from remote file."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.return_value = (0, "Hello World", "")

        content = streamer._read_remote_chunk("/remote/file.log", 1, 100)

        assert content == "Hello World"
        ssh_manager.execute_command.assert_called_with(
            "tail -c +1 /remote/file.log | head -c 100", timeout=30
        )

    def test_read_remote_chunk_from_middle(self):
        """Test reading a chunk from middle of file."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.return_value = (0, "Middle content", "")

        content = streamer._read_remote_chunk("/remote/file.log", 5001, 1000)

        assert content == "Middle content"
        ssh_manager.execute_command.assert_called_with(
            "tail -c +5001 /remote/file.log | head -c 1000", timeout=30
        )

    def test_concurrent_streaming_prevents_duplicate_content(self):
        """Test that position tracking prevents duplicate content in concurrent scenarios."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        # Simulate rapid file growth
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "30", ""),  # Initial 30 bytes
            (0, "Line 1\nLine 2\nLine 3\n", ""),  # Read all 30 bytes
            (0, "60", ""),  # Grown to 60 bytes
            (0, "Line 4\nLine 5\nLine 6\n", ""),  # Read next 30 bytes
            (0, "60", ""),  # Size stable (stop)
        ]

        local_path = Path(".claude/workspace/concurrent.log")
        content_written = []

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_file.write.side_effect = lambda x: content_written.append(x)
            mock_open.return_value.__enter__.return_value = mock_file

            streamer.stream_remote_log(
                "/remote/growing.log", local_path, poll_interval=0.01, timeout=0.1
            )

        # Verify no duplicate lines
        full_content = "".join(content_written)
        lines = full_content.strip().split("\n")
        assert lines == ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5", "Line 6"]
        assert len(lines) == len(set(lines))  # No duplicates

    def test_stream_with_callback(self):
        """Test streaming with a callback function for real-time processing."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "50", ""),  # Initial size
            (0, "Progress: 10%\n", ""),  # First update
            (0, "100", ""),  # Size grown
            (0, "Progress: 50%\nProgress: 100%\n", ""),  # More updates
            (0, "100", ""),  # Size stable (stop)
        ]

        local_path = Path(".claude/workspace/callback.log")
        callback_data = []

        def progress_callback(chunk):
            """Extract progress from log chunks."""
            for line in chunk.split("\n"):
                if "Progress:" in line:
                    callback_data.append(line.strip())

        with patch("builtins.open", create=True):
            streamer.stream_remote_log(
                "/remote/progress.log",
                local_path,
                poll_interval=0.01,
                timeout=0.1,
                callback=progress_callback,
            )

        # Verify callback received all progress updates
        assert callback_data == ["Progress: 10%", "Progress: 50%", "Progress: 100%"]

    def test_stream_handles_binary_content_safely(self):
        """Test that binary content in logs is handled safely."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        # Include some non-UTF8 bytes
        binary_content = b"Text \xc3\x28 more text\n"
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "100", ""),  # Size
            (
                0,
                binary_content.decode("utf-8", errors="replace"),
                "",
            ),  # Content with replacement char
            (0, "100", ""),  # Size stable
        ]

        local_path = Path(".claude/workspace/binary.log")

        with patch("builtins.open", create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            streamer.stream_remote_log(
                "/remote/binary.log", local_path, poll_interval=0.01, timeout=0.1
            )

        # Should complete without raising encoding errors
        assert mock_file.write.called

    def test_stream_creates_parent_directories(self):
        """Test that parent directories are created for the local log file."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "10", ""),  # Small file
            (0, "Test log\n", ""),  # Content
            (0, "10", ""),  # Size stable
        ]

        local_path = Path(".claude/workspace/deep/nested/path/test.log")

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("builtins.open", create=True):
                streamer.stream_remote_log(
                    "/remote/test.log", local_path, poll_interval=0.01, timeout=0.1
                )

            # Verify directories were created
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)
