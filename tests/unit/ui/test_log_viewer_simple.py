#!/usr/bin/env python3
"""Tests for simplified log viewer."""

from cosmos_workflow.ui.log_viewer import LogViewer


class TestLogViewerSimple:
    """Test cases for simplified LogViewer."""

    def test_initialization(self):
        """Test LogViewer initialization."""
        viewer = LogViewer()
        assert len(viewer.entries) == 0

        viewer_small = LogViewer(max_lines=100)
        assert viewer_small.entries.maxlen == 100

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
            viewer.add_from_stream(f"Message {i}")

        assert len(viewer.entries) == 3
        # Should keep most recent (ring buffer)
        assert viewer.entries[0]["text"] == "Message 2"
        assert viewer.entries[2]["text"] == "Message 4"

    def test_get_html_with_colors(self):
        """Test HTML generation applies color coding for different log levels."""
        viewer = LogViewer()
        viewer.add_from_stream("[INFO] Information message")
        viewer.add_from_stream("[ERROR] Error occurred")
        viewer.add_from_stream("[WARNING] Warning message")
        viewer.add_from_stream("Regular message")

        html = viewer.get_html()

        # Test behavior: different log levels get different styling
        # Don't test specific colors - they may change for aesthetics
        assert "INFO" in html
        assert "ERROR" in html
        assert "WARNING" in html
        assert "color:" in html  # Some color styling is applied

    def test_filtering_by_level(self):
        """Test filtering by log level."""
        viewer = LogViewer()
        viewer.add_from_stream("[INFO] Info message")
        viewer.add_from_stream("[ERROR] Error message")
        viewer.add_from_stream("[WARNING] Warning message")
        viewer.add_from_stream("Regular message")

        # Filter to ERROR only
        html = viewer.get_html(level_filter="ERROR")
        assert "Error message" in html
        assert "Info message" not in html
        assert "Warning message" not in html

    def test_search_functionality(self):
        """Test search and highlighting."""
        viewer = LogViewer()
        viewer.add_from_stream("Starting process")
        viewer.add_from_stream("Process running")
        viewer.add_from_stream("Process failed")
        viewer.add_from_stream("Restarting service")

        html = viewer.get_html(search="process")

        # Should filter to lines with "process" (text will be highlighted)
        assert "Starting" in html  # "process" is highlighted separately
        assert "running" in html
        assert "failed" in html
        assert "Restarting service" not in html

        # Should highlight search term
        assert '<mark style="background:#ff0;color:#000">process</mark>' in html.lower()

    def test_get_stats(self):
        """Test statistics generation."""
        viewer = LogViewer()
        viewer.add_from_stream("[INFO] Info 1")
        viewer.add_from_stream("[ERROR] Error 1")
        viewer.add_from_stream("[WARNING] Warning 1")
        viewer.add_from_stream("[ERROR] Error 2")
        viewer.add_from_stream("Regular message")

        stats = viewer.get_stats()

        assert stats["total"] == 5
        assert stats["errors"] == 2
        assert stats["warnings"] == 1

    def test_clear(self):
        """Test clearing logs."""
        viewer = LogViewer()
        viewer.add_from_stream("Message 1")
        viewer.add_from_stream("Message 2")

        assert len(viewer.entries) == 2

        viewer.clear()
        assert len(viewer.entries) == 0

    def test_html_escaping(self):
        """Test that HTML is properly escaped."""
        viewer = LogViewer()
        viewer.add_from_stream("<script>alert('XSS')</script>")

        html = viewer.get_html()

        # Should escape HTML tags in the log content (not in the auto-scroll script)
        # Check that the malicious script is escaped
        assert (
            "&lt;script&gt;alert" in html
            or "&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;" in html
        )
        # The unescaped version should not appear in the log content
        assert "<script>alert('XSS')</script>" not in html

    def test_case_insensitive_search(self):
        """Test case-insensitive search."""
        viewer = LogViewer()
        viewer.add_from_stream("ERROR in module")
        viewer.add_from_stream("Error occurred")
        viewer.add_from_stream("error: failed")

        html = viewer.get_html(search="ERROR")

        # Should find all variations (with highlighting)
        assert "in module" in html
        assert "occurred" in html
        assert ": failed" in html
        # Check that all three entries are present
        assert html.count('<div style="color:#ff6b6b') == 3
