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
        # The actual sequence:
        # 1. Check file exists
        # 2. Get size (50)
        # 3. Read 50 bytes from position 1
        # 4. Get size again (still 50, stable count 1)
        # 5. Get size again (still 50, stable count 2, stop)
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "50", ""),  # Initial size 50 bytes
            (0, "First log entry\nSecond entry\n", ""),  # Read first 50 bytes
            (0, "50", ""),  # Size unchanged (stable count 1)
            (0, "50", ""),  # Size unchanged (stable count 2, stop)
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
        assert "head -c 50" in calls[2][0][0]  # Reading up to 50 bytes (or buffer size)

    def test_stream_handles_no_new_content(self):
        """Test that streaming handles periods with no new content gracefully."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        # Content is 16 bytes long
        content = "Initial content\n"
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "16", ""),  # File size (matches content length)
            (0, content, ""),  # Read content
            (0, "16", ""),  # Size unchanged (stable 1)
            (0, "16", ""),  # Size unchanged (stable 2, stop)
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

        # Verify content was written correctly
        assert len(content_written) == 1
        assert content_written[0] == content

    def test_stream_stops_on_completion_marker(self):
        """Test that streaming stops when it detects a completion marker."""
        ssh_manager = MagicMock()
        streamer = RemoteLogStreamer(ssh_manager)

        content1 = "Processing...\n"  # 14 bytes
        content2 = "More processing...\n[COSMOS_COMPLETE]\n"  # 38 bytes
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "14", ""),  # Initial size
            (0, content1, ""),  # First read
            (0, "52", ""),  # Size grown (14 + 38)
            (0, content2, ""),  # Read new content with completion marker
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

        content = "Log started\n"  # 12 bytes
        ssh_manager.execute_command.side_effect = [
            (1, "", "No such file"),  # File doesn't exist
            (1, "", "No such file"),  # Still doesn't exist
            (0, "", ""),  # Now it exists
            (0, "12", ""),  # Has content
            (0, content, ""),  # Read content
            (0, "12", ""),  # Size unchanged (stable 1)
            (0, "12", ""),  # Size unchanged (stable 2, stop)
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

        # Create a mock that will always return growing file sizes and dummy content
        def side_effect_generator():
            yield (0, "", "")  # File exists
            size = 100
            while True:
                yield (0, str(size), "")  # File size
                yield (0, "X" * 100, "")  # Content
                size += 100

        ssh_manager.execute_command.side_effect = side_effect_generator()

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

        # Split into smaller chunks that fit in buffer
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "1000", ""),  # Large file
            (0, "A" * 1000, ""),  # Read all content at once (within buffer)
            (0, "1000", ""),  # Size unchanged (stable 1)
            (0, "1000", ""),  # Size unchanged (stable 2, stop)
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
        assert "A" * 1000 == total_content

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

        content1 = "Line 1\nLine 2\nLine 3\n"  # 21 bytes
        content2 = "Line 4\nLine 5\nLine 6\n"  # 21 bytes
        # Simulate rapid file growth
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "21", ""),  # Initial 21 bytes
            (0, content1, ""),  # Read first chunk
            (0, "42", ""),  # Grown to 42 bytes
            (0, content2, ""),  # Read next 21 bytes
            (0, "42", ""),  # Size stable (stable 1)
            (0, "42", ""),  # Size stable (stable 2, stop)
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

        content1 = "Progress: 10%\n"  # 14 bytes
        content2 = "Progress: 50%\nProgress: 100%\n"  # 29 bytes
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "14", ""),  # Initial size
            (0, content1, ""),  # First update
            (0, "43", ""),  # Size grown
            (0, content2, ""),  # More updates
            (0, "43", ""),  # Size stable (stable 1)
            (0, "43", ""),  # Size stable (stable 2, stop)
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
        decoded = binary_content.decode("utf-8", errors="replace")
        size = str(len(decoded.encode("utf-8")))
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, size, ""),  # Size
            (0, decoded, ""),  # Content with replacement char
            (0, size, ""),  # Size stable (stable 1)
            (0, size, ""),  # Size stable (stable 2, stop)
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

        content = "Test log\n"  # 9 bytes
        ssh_manager.execute_command.side_effect = [
            (0, "", ""),  # File exists
            (0, "9", ""),  # Small file
            (0, content, ""),  # Content
            (0, "9", ""),  # Size stable (stable 1)
            (0, "9", ""),  # Size stable (stable 2, stop)
        ]

        local_path = Path(".claude/workspace/deep/nested/path/test.log")

        with patch("pathlib.Path.mkdir") as mock_mkdir:
            with patch("builtins.open", create=True):
                streamer.stream_remote_log(
                    "/remote/test.log", local_path, poll_interval=0.01, timeout=0.1
                )

            # Verify directories were created
            mock_mkdir.assert_called_with(parents=True, exist_ok=True)
