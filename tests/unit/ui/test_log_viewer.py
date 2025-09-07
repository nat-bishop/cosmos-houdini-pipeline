#!/usr/bin/env python3
"""Tests for log visualization interface components."""

import json
from datetime import datetime
from unittest.mock import Mock, patch

from cosmos_workflow.ui.log_viewer import (
    LogEntry,
    LogFilter,
    LogViewer,
    format_log_entry,
    parse_log_line,
)


class TestLogEntry:
    """Test cases for LogEntry data class."""

    def test_log_entry_creation(self):
        """Test creating a LogEntry with all fields."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            level="INFO",
            message="Test message",
            source="test.py",
            line_number=42,
        )

        assert entry.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert entry.level == "INFO"
        assert entry.message == "Test message"
        assert entry.source == "test.py"
        assert entry.line_number == 42

    def test_log_entry_to_dict(self):
        """Test converting LogEntry to dictionary."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            level="ERROR",
            message="Error occurred",
            source="app.py",
            line_number=100,
        )

        result = entry.to_dict()

        assert result["timestamp"] == "2024-01-01T12:00:00"
        assert result["level"] == "ERROR"
        assert result["message"] == "Error occurred"
        assert result["source"] == "app.py"
        assert result["line_number"] == 100

    def test_log_entry_from_dict(self):
        """Test creating LogEntry from dictionary."""
        data = {
            "timestamp": "2024-01-01T12:00:00",
            "level": "WARNING",
            "message": "Warning message",
            "source": "module.py",
            "line_number": 25,
        }

        entry = LogEntry.from_dict(data)

        assert entry.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert entry.level == "WARNING"
        assert entry.message == "Warning message"
        assert entry.source == "module.py"
        assert entry.line_number == 25


class TestLogFilter:
    """Test cases for LogFilter functionality."""

    def test_filter_by_level(self):
        """Test filtering log entries by level."""
        entries = [
            LogEntry(datetime.now(), "INFO", "Info message", "test.py", 1),
            LogEntry(datetime.now(), "ERROR", "Error message", "test.py", 2),
            LogEntry(datetime.now(), "DEBUG", "Debug message", "test.py", 3),
            LogEntry(datetime.now(), "WARNING", "Warning message", "test.py", 4),
        ]

        filter_obj = LogFilter(levels=["ERROR", "WARNING"])
        filtered = filter_obj.apply(entries)

        assert len(filtered) == 2
        assert filtered[0].level == "ERROR"
        assert filtered[1].level == "WARNING"

    def test_filter_by_search_text(self):
        """Test filtering log entries by search text."""
        entries = [
            LogEntry(datetime.now(), "INFO", "Starting process", "test.py", 1),
            LogEntry(datetime.now(), "INFO", "Process running", "test.py", 2),
            LogEntry(datetime.now(), "INFO", "Process completed", "test.py", 3),
            LogEntry(datetime.now(), "ERROR", "Failed to connect", "test.py", 4),
        ]

        filter_obj = LogFilter(search_text="process")
        filtered = filter_obj.apply(entries)

        assert len(filtered) == 3
        assert all("process" in entry.message.lower() for entry in filtered)

    def test_filter_by_regex(self):
        """Test filtering log entries by regex pattern."""
        entries = [
            LogEntry(datetime.now(), "INFO", "Task 123 started", "test.py", 1),
            LogEntry(datetime.now(), "INFO", "Task ABC started", "test.py", 2),
            LogEntry(datetime.now(), "INFO", "Task 456 completed", "test.py", 3),
            LogEntry(datetime.now(), "ERROR", "Invalid task ID", "test.py", 4),
        ]

        filter_obj = LogFilter(regex_pattern=r"Task \d+ ")
        filtered = filter_obj.apply(entries)

        assert len(filtered) == 2
        assert "Task 123" in filtered[0].message
        assert "Task 456" in filtered[1].message

    def test_filter_by_time_range(self):
        """Test filtering log entries by time range."""
        entries = [
            LogEntry(datetime(2024, 1, 1, 11, 0, 0), "INFO", "Early", "test.py", 1),
            LogEntry(datetime(2024, 1, 1, 12, 30, 0), "INFO", "Middle", "test.py", 2),
            LogEntry(datetime(2024, 1, 1, 13, 0, 0), "INFO", "Late", "test.py", 3),
            LogEntry(datetime(2024, 1, 1, 14, 0, 0), "INFO", "Very late", "test.py", 4),
        ]

        filter_obj = LogFilter(
            start_time=datetime(2024, 1, 1, 12, 0, 0), end_time=datetime(2024, 1, 1, 13, 30, 0)
        )
        filtered = filter_obj.apply(entries)

        assert len(filtered) == 2
        assert filtered[0].message == "Middle"
        assert filtered[1].message == "Late"

    def test_combined_filters(self):
        """Test applying multiple filters simultaneously."""
        entries = [
            LogEntry(datetime(2024, 1, 1, 12, 0, 0), "INFO", "Starting task", "test.py", 1),
            LogEntry(datetime(2024, 1, 1, 12, 5, 0), "ERROR", "Task failed", "test.py", 2),
            LogEntry(datetime(2024, 1, 1, 12, 10, 0), "ERROR", "Connection lost", "test.py", 3),
            LogEntry(datetime(2024, 1, 1, 12, 15, 0), "INFO", "Task retry", "test.py", 4),
        ]

        filter_obj = LogFilter(
            levels=["ERROR"], search_text="task", start_time=datetime(2024, 1, 1, 12, 0, 0)
        )
        filtered = filter_obj.apply(entries)

        assert len(filtered) == 1
        assert filtered[0].message == "Task failed"


class TestLogViewer:
    """Test cases for LogViewer component."""

    def test_initialization(self):
        """Test LogViewer initialization."""
        viewer = LogViewer(max_entries=500, buffer_size=100)

        assert viewer.max_entries == 500
        assert viewer.buffer_size == 100
        assert len(viewer.entries) == 0
        assert viewer.current_filter is None

    def test_add_log_line(self):
        """Test adding a log line to the viewer."""
        viewer = LogViewer()
        log_line = "2024-01-01 12:00:00 [INFO] Test message"

        viewer.add_log_line(log_line)

        assert len(viewer.entries) == 1
        assert viewer.entries[0].level == "INFO"
        assert viewer.entries[0].message == "Test message"

    def test_add_log_entry(self):
        """Test adding a LogEntry directly."""
        viewer = LogViewer()
        entry = LogEntry(datetime.now(), "ERROR", "Error message", "test.py", 10)

        viewer.add_entry(entry)

        assert len(viewer.entries) == 1
        assert viewer.entries[0] == entry

    def test_max_entries_limit(self):
        """Test that viewer respects max_entries limit."""
        viewer = LogViewer(max_entries=3)

        for i in range(5):
            viewer.add_log_line(f"2024-01-01 12:00:0{i} [INFO] Message {i}")

        assert len(viewer.entries) == 3
        # Should keep the most recent entries
        assert "Message 2" in viewer.entries[0].message
        assert "Message 4" in viewer.entries[2].message

    def test_get_filtered_entries(self):
        """Test getting filtered entries."""
        viewer = LogViewer()
        viewer.add_log_line("2024-01-01 12:00:00 [INFO] Info message")
        viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")
        viewer.add_log_line("2024-01-01 12:00:02 [DEBUG] Debug message")

        filter_obj = LogFilter(levels=["ERROR"])
        viewer.set_filter(filter_obj)

        filtered = viewer.get_filtered_entries()

        assert len(filtered) == 1
        assert filtered[0].level == "ERROR"

    def test_clear_logs(self):
        """Test clearing all logs."""
        viewer = LogViewer()
        viewer.add_log_line("2024-01-01 12:00:00 [INFO] Test message")
        viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")

        viewer.clear()

        assert len(viewer.entries) == 0

    def test_export_logs_json(self):
        """Test exporting logs to JSON format."""
        viewer = LogViewer()
        viewer.add_log_line("2024-01-01 12:00:00 [INFO] Test message")
        viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")

        json_output = viewer.export_json()
        data = json.loads(json_output)

        assert len(data["entries"]) == 2
        assert data["entries"][0]["level"] == "INFO"
        assert data["entries"][1]["level"] == "ERROR"

    def test_export_logs_text(self):
        """Test exporting logs to plain text format."""
        viewer = LogViewer()
        viewer.add_log_line("2024-01-01 12:00:00 [INFO] Test message")
        viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")

        text_output = viewer.export_text()

        assert "[INFO]" in text_output
        assert "[ERROR]" in text_output
        assert "Test message" in text_output
        assert "Error message" in text_output

    def test_search_logs(self):
        """Test searching logs with text."""
        viewer = LogViewer()
        viewer.add_log_line("2024-01-01 12:00:00 [INFO] Starting process")
        viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Process failed")
        viewer.add_log_line("2024-01-01 12:00:02 [INFO] Restarting service")

        results = viewer.search("process")

        assert len(results) == 2
        assert results[0].message == "Starting process"
        assert results[1].message == "Process failed"

    def test_get_formatted_html(self):
        """Test getting HTML formatted output with syntax highlighting."""
        viewer = LogViewer()
        viewer.add_log_line("2024-01-01 12:00:00 [INFO] Info message")
        viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")
        viewer.add_log_line("2024-01-01 12:00:02 [WARNING] Warning message")

        html = viewer.get_formatted_html()

        # Check for level-specific CSS classes
        assert 'class="log-info"' in html
        assert 'class="log-error"' in html
        assert 'class="log-warning"' in html

    def test_stream_integration(self):
        """Test integration with RemoteLogStreamer."""
        viewer = LogViewer()

        # Simulate callback from streamer
        callback = viewer.get_stream_callback()
        callback("2024-01-01 12:00:00 [INFO] Line 1\n")
        callback("2024-01-01 12:00:01 [ERROR] Line 2\n")

        assert len(viewer.entries) == 2
        assert viewer.entries[0].message == "Line 1"
        assert viewer.entries[1].message == "Line 2"


class TestLogParsing:
    """Test cases for log parsing functions."""

    def test_parse_standard_log_line(self):
        """Test parsing standard log format."""
        line = "2024-01-01 12:00:00 [INFO] Starting application"
        entry = parse_log_line(line)

        assert entry.timestamp == datetime(2024, 1, 1, 12, 0, 0)
        assert entry.level == "INFO"
        assert entry.message == "Starting application"

    def test_parse_log_with_source(self):
        """Test parsing log line with source file info."""
        line = "2024-01-01 12:00:00 [ERROR] (app.py:42) Database connection failed"
        entry = parse_log_line(line)

        assert entry.level == "ERROR"
        assert entry.source == "app.py"
        assert entry.line_number == 42
        assert entry.message == "Database connection failed"

    def test_parse_multiline_log(self):
        """Test parsing multiline log entries."""
        lines = """2024-01-01 12:00:00 [ERROR] Exception occurred:
    Traceback (most recent call last):
      File "app.py", line 42, in main
        raise ValueError("Test error")
    ValueError: Test error"""

        entry = parse_log_line(lines)

        assert entry.level == "ERROR"
        assert "Exception occurred" in entry.message
        assert "ValueError: Test error" in entry.message

    def test_parse_invalid_log_line(self):
        """Test parsing invalid or unstructured log lines."""
        line = "This is not a standard log line"
        entry = parse_log_line(line)

        assert entry.level == "INFO"  # Default level
        assert entry.message == line
        assert entry.timestamp is not None

    def test_format_log_entry(self):
        """Test formatting LogEntry for display."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            level="ERROR",
            message="Test error",
            source="app.py",
            line_number=42,
        )

        formatted = format_log_entry(entry)

        assert "2024-01-01 12:00:00" in formatted
        assert "[ERROR]" in formatted
        assert "(app.py:42)" in formatted
        assert "Test error" in formatted

    def test_format_log_entry_without_source(self):
        """Test formatting LogEntry without source info."""
        entry = LogEntry(
            timestamp=datetime(2024, 1, 1, 12, 0, 0), level="INFO", message="Test message"
        )

        formatted = format_log_entry(entry)

        assert "2024-01-01 12:00:00" in formatted
        assert "[INFO]" in formatted
        assert "Test message" in formatted
        assert "app.py" not in formatted


class TestLogViewerPerformance:
    """Test cases for performance optimization."""

    def test_large_log_handling(self):
        """Test handling large number of log entries efficiently."""
        viewer = LogViewer(max_entries=1000)

        # Add 2000 entries
        for i in range(2000):
            viewer.add_log_line(f"2024-01-01 12:00:{i:02d} [INFO] Message {i}")

        # Should only keep max_entries
        assert len(viewer.entries) == 1000

        # Test filtering performance
        LogFilter(search_text="Message 1")
        filtered = viewer.get_filtered_entries()

        # Should filter efficiently
        assert all("Message 1" in entry.message for entry in filtered)

    def test_buffered_updates(self):
        """Test buffered updates for performance."""
        viewer = LogViewer(buffer_size=10)

        # Track update callbacks
        update_count = 0

        def update_callback():
            nonlocal update_count
            update_count += 1

        viewer.set_update_callback(update_callback)

        # Add 25 entries
        for i in range(25):
            viewer.add_log_line(f"2024-01-01 12:00:{i:02d} [INFO] Message {i}")

        # Should have triggered updates based on buffer size
        assert update_count == 3  # 25 entries / 10 buffer size = 2.5, rounded up to 3

    def test_virtual_scrolling_support(self):
        """Test support for virtual scrolling with large datasets."""
        viewer = LogViewer()

        # Add many entries
        for i in range(100):
            viewer.add_log_line(f"2024-01-01 12:00:{i:02d} [INFO] Message {i}")

        # Get paginated results
        page_1 = viewer.get_page(page=0, page_size=10)
        page_2 = viewer.get_page(page=1, page_size=10)

        assert len(page_1) == 10
        assert len(page_2) == 10
        assert page_1[0].message != page_2[0].message


class TestLogViewerIntegration:
    """Integration tests for LogViewer with other components."""

    @patch("cosmos_workflow.monitoring.log_streamer.RemoteLogStreamer")
    def test_integration_with_remote_streamer(self, mock_streamer_class):
        """Test integration with RemoteLogStreamer."""
        viewer = LogViewer()
        mock_streamer = Mock()
        mock_streamer_class.return_value = mock_streamer

        # Set up the viewer to receive streaming updates
        callback = viewer.get_stream_callback()

        # Simulate streaming logs
        callback("2024-01-01 12:00:00 [INFO] Starting stream\n")
        callback("2024-01-01 12:00:01 [ERROR] Stream error\n")
        callback("2024-01-01 12:00:02 [INFO] Stream recovered\n")

        assert len(viewer.entries) == 3
        assert viewer.entries[0].level == "INFO"
        assert viewer.entries[1].level == "ERROR"
        assert viewer.entries[2].level == "INFO"

    def test_concurrent_log_streams(self):
        """Test handling multiple concurrent log streams."""
        viewer = LogViewer()

        # Create callbacks for different streams
        stream1_callback = viewer.get_stream_callback(stream_id="stream1")
        stream2_callback = viewer.get_stream_callback(stream_id="stream2")

        # Simulate concurrent updates
        stream1_callback("2024-01-01 12:00:00 [INFO] Stream 1 message\n")
        stream2_callback("2024-01-01 12:00:00 [INFO] Stream 2 message\n")
        stream1_callback("2024-01-01 12:00:01 [ERROR] Stream 1 error\n")

        assert len(viewer.entries) == 3
        # Check that entries are properly tagged with stream ID
        assert any("stream1" in entry.source for entry in viewer.entries)
        assert any("stream2" in entry.source for entry in viewer.entries)

    def test_gradio_interface_integration(self):
        """Test integration with Gradio UI components."""
        viewer = LogViewer()

        # Add some test data
        viewer.add_log_line("2024-01-01 12:00:00 [INFO] Test message")
        viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")

        # Test Gradio-compatible output format
        gradio_output = viewer.get_gradio_output()

        assert isinstance(gradio_output, str)
        assert "[INFO]" in gradio_output
        assert "[ERROR]" in gradio_output

    def test_export_with_filters(self):
        """Test exporting filtered logs."""
        viewer = LogViewer()

        # Add various log entries
        viewer.add_log_line("2024-01-01 12:00:00 [INFO] Info message")
        viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")
        viewer.add_log_line("2024-01-01 12:00:02 [DEBUG] Debug message")

        # Set filter to only ERROR level
        filter_obj = LogFilter(levels=["ERROR"])
        viewer.set_filter(filter_obj)

        # Export filtered logs
        json_output = viewer.export_json(filtered=True)
        data = json.loads(json_output)

        assert len(data["entries"]) == 1
        assert data["entries"][0]["level"] == "ERROR"
