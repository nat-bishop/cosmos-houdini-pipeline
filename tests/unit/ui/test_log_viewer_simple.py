#!/usr/bin/env python3
"""Tests for simplified log viewer."""

import json

from cosmos_workflow.ui.log_viewer import LogViewer


class TestLogViewerSimple:
    """Test cases for simplified LogViewer."""

    def test_initialization(self):
        """Test LogViewer initialization."""
        viewer = LogViewer()
        assert len(viewer.entries) == 0

        viewer_small = LogViewer(max_lines=100)
        assert viewer_small.entries.maxlen == 100

    def test_add_line(self):
        """Test adding single log lines."""
        viewer = LogViewer()

        viewer.add_line("Test log message")
        assert len(viewer.entries) == 1
        assert viewer.entries[0]["text"] == "Test log message"
        assert ":" in viewer.entries[0]["time"]  # Has time format HH:MM:SS

    def test_add_from_stream(self):
        """Test adding from stream callback."""
        viewer = LogViewer()

        content = "Line 1\nLine 2\nLine 3\n"
        viewer.add_from_stream(content)

        assert len(viewer.entries) == 3
        assert viewer.entries[0]["text"] == "Line 1"
        assert viewer.entries[2]["text"] == "Line 3"

    def test_max_lines_limit(self):
        """Test that viewer respects max_lines limit."""
        viewer = LogViewer(max_lines=3)

        for i in range(5):
            viewer.add_line(f"Message {i}")

        assert len(viewer.entries) == 3
        # Should keep most recent (ring buffer)
        assert viewer.entries[0]["text"] == "Message 2"
        assert viewer.entries[2]["text"] == "Message 4"

    def test_get_html_with_colors(self):
        """Test HTML generation with color coding."""
        viewer = LogViewer()
        viewer.add_line("[INFO] Information message")
        viewer.add_line("[ERROR] Error occurred")
        viewer.add_line("[WARNING] Warning message")
        viewer.add_line("Regular message")

        html = viewer.get_html()

        # Check colors are applied
        assert "#4dabf7" in html  # Blue for INFO
        assert "#ff6b6b" in html  # Red for ERROR
        assert "#ffd93d" in html  # Yellow for WARNING
        assert "#fff" in html  # White for regular

    def test_filtering_by_level(self):
        """Test filtering by log level."""
        viewer = LogViewer()
        viewer.add_line("[INFO] Info message")
        viewer.add_line("[ERROR] Error message")
        viewer.add_line("[WARNING] Warning message")
        viewer.add_line("Regular message")

        # Filter to ERROR only
        html = viewer.get_html(level_filter="ERROR")
        assert "Error message" in html
        assert "Info message" not in html
        assert "Warning message" not in html

    def test_search_functionality(self):
        """Test search and highlighting."""
        viewer = LogViewer()
        viewer.add_line("Starting process")
        viewer.add_line("Process running")
        viewer.add_line("Process failed")
        viewer.add_line("Restarting service")

        html = viewer.get_html(search="process")

        # Should filter to lines with "process" (text will be highlighted)
        assert "Starting" in html  # "process" is highlighted separately
        assert "running" in html
        assert "failed" in html
        assert "Restarting service" not in html

        # Should highlight search term
        assert '<mark style="background:#ff0;color:#000">process</mark>' in html.lower()

    def test_has_errors(self):
        """Test error detection."""
        viewer = LogViewer()
        viewer.add_line("[INFO] All good")
        assert viewer.has_errors() is False

        viewer.add_line("[ERROR] Something failed")
        assert viewer.has_errors() is True

    def test_get_last_error(self):
        """Test getting last error."""
        viewer = LogViewer()
        viewer.add_line("[INFO] Starting")
        viewer.add_line("[ERROR] First error")
        viewer.add_line("[INFO] Continuing")
        viewer.add_line("[ERROR] Second error")

        last_error = viewer.get_last_error()
        assert last_error == "[ERROR] Second error"

    def test_get_stats(self):
        """Test statistics generation."""
        viewer = LogViewer()
        viewer.add_line("[INFO] Info 1")
        viewer.add_line("[ERROR] Error 1")
        viewer.add_line("[WARNING] Warning 1")
        viewer.add_line("[ERROR] Error 2")
        viewer.add_line("Regular message")

        stats = viewer.get_stats()

        assert stats["total"] == 5
        assert stats["errors"] == 2
        assert stats["warnings"] == 1

    def test_clear(self):
        """Test clearing logs."""
        viewer = LogViewer()
        viewer.add_line("Message 1")
        viewer.add_line("Message 2")

        assert len(viewer.entries) == 2

        viewer.clear()
        assert len(viewer.entries) == 0

    def test_export_json(self):
        """Test JSON export."""
        viewer = LogViewer()
        viewer.add_line("[INFO] Test message")
        viewer.add_line("[ERROR] Error message")

        json_str = viewer.export_json()
        data = json.loads(json_str)

        assert len(data) == 2
        assert data[0]["text"] == "[INFO] Test message"
        assert data[1]["text"] == "[ERROR] Error message"

    def test_html_escaping(self):
        """Test that HTML is properly escaped."""
        viewer = LogViewer()
        viewer.add_line("<script>alert('XSS')</script>")

        html = viewer.get_html()

        # Should escape HTML tags
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_case_insensitive_search(self):
        """Test case-insensitive search."""
        viewer = LogViewer()
        viewer.add_line("ERROR in module")
        viewer.add_line("Error occurred")
        viewer.add_line("error: failed")

        html = viewer.get_html(search="ERROR")

        # Should find all variations (with highlighting)
        assert "in module" in html
        assert "occurred" in html
        assert ": failed" in html
        # Check that all three entries are present
        assert html.count('<div style="color:#ff6b6b') == 3
