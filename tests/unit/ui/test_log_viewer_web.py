#!/usr/bin/env python3
"""Tests for web-based log viewer integration components."""

import json
from unittest.mock import patch

from cosmos_workflow.ui.log_viewer_web import (
    LogViewerWeb,
    create_log_viewer_interface,
    format_log_html,
    get_log_level_style,
    handle_log_export,
    handle_log_filter_update,
    handle_log_search,
)


class TestLogViewerWeb:
    """Test cases for web-based log viewer component."""

    def test_initialization(self):
        """Test LogViewerWeb initialization."""
        viewer = LogViewerWeb()

        assert viewer.log_viewer is not None
        assert viewer.active_streams == {}
        assert viewer.theme == "dark"  # Default theme

    def test_add_stream(self):
        """Test adding a new log stream."""
        viewer = LogViewerWeb()

        stream_id = viewer.add_stream("run_123", "/logs/run_123.log")

        assert stream_id in viewer.active_streams
        assert viewer.active_streams[stream_id]["run_id"] == "run_123"
        assert viewer.active_streams[stream_id]["log_path"] == "/logs/run_123.log"

    def test_remove_stream(self):
        """Test removing a log stream."""
        viewer = LogViewerWeb()
        stream_id = viewer.add_stream("run_123", "/logs/run_123.log")

        viewer.remove_stream(stream_id)

        assert stream_id not in viewer.active_streams

    def test_get_active_streams(self):
        """Test getting list of active streams."""
        viewer = LogViewerWeb()
        viewer.add_stream("run_123", "/logs/run_123.log")
        viewer.add_stream("run_456", "/logs/run_456.log")

        streams = viewer.get_active_streams()

        assert len(streams) == 2
        assert any(s["run_id"] == "run_123" for s in streams)
        assert any(s["run_id"] == "run_456" for s in streams)

    def test_render_html_output(self):
        """Test rendering HTML output for display."""
        viewer = LogViewerWeb()
        viewer.log_viewer.add_log_line("2024-01-01 12:00:00 [INFO] Test message")
        viewer.log_viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")

        html = viewer.render_html()

        assert "<div" in html
        assert "log-info" in html
        assert "log-error" in html
        assert "Test message" in html
        assert "Error message" in html

    def test_theme_switching(self):
        """Test switching between dark and light themes."""
        viewer = LogViewerWeb()

        viewer.set_theme("light")
        assert viewer.theme == "light"

        html = viewer.render_html()
        assert "theme-light" in html

        viewer.set_theme("dark")
        assert viewer.theme == "dark"

        html = viewer.render_html()
        assert "theme-dark" in html

    def test_auto_refresh_capability(self):
        """Test auto-refresh functionality."""
        viewer = LogViewerWeb()

        viewer.enable_auto_refresh(interval=2.0)
        assert viewer.auto_refresh_enabled is True
        assert viewer.auto_refresh_interval == 2.0

        viewer.disable_auto_refresh()
        assert viewer.auto_refresh_enabled is False

    def test_keyboard_shortcuts_config(self):
        """Test keyboard shortcuts configuration."""
        viewer = LogViewerWeb()

        shortcuts = viewer.get_keyboard_shortcuts()

        assert "search" in shortcuts
        assert "filter" in shortcuts
        assert "export" in shortcuts
        assert "clear" in shortcuts
        assert "refresh" in shortcuts


class TestLogFormatting:
    """Test cases for log formatting functions."""

    def test_get_log_level_style(self):
        """Test getting CSS style for different log levels."""
        assert "color: #28a745" in get_log_level_style("INFO")  # Green
        assert "color: #dc3545" in get_log_level_style("ERROR")  # Red
        assert "color: #ffc107" in get_log_level_style("WARNING")  # Yellow
        assert "color: #6c757d" in get_log_level_style("DEBUG")  # Gray

    def test_format_log_html_basic(self):
        """Test formatting a basic log entry as HTML."""
        log_text = "2024-01-01 12:00:00 [INFO] Test message"
        html = format_log_html(log_text)

        assert '<span class="log-timestamp">' in html
        assert '<span class="log-level log-info">' in html
        assert '<span class="log-message">' in html
        assert "Test message" in html

    def test_format_log_html_with_highlighting(self):
        """Test formatting with search term highlighting."""
        log_text = "2024-01-01 12:00:00 [ERROR] Database connection failed"
        html = format_log_html(log_text, highlight="connection")

        assert '<mark class="highlight">' in html
        assert "connection" in html

    def test_format_log_html_multiline(self):
        """Test formatting multiline log entries."""
        log_text = """2024-01-01 12:00:00 [ERROR] Exception occurred:
    Traceback (most recent call last):
      File "app.py", line 42
    ValueError: Test error"""

        html = format_log_html(log_text)

        assert '<pre class="log-traceback">' in html
        assert "Traceback" in html
        assert "ValueError" in html

    def test_format_log_html_escape_special_chars(self):
        """Test that special HTML characters are properly escaped."""
        log_text = '2024-01-01 12:00:00 [INFO] Message with <script>alert("XSS")</script>'
        html = format_log_html(log_text)

        assert "<script>" not in html
        assert "&lt;script&gt;" in html


class TestGradioIntegration:
    """Test cases for Gradio UI integration."""

    def test_create_log_viewer_interface(self):
        """Test creating the Gradio interface for log viewer."""
        with patch("cosmos_workflow.ui.log_viewer_web.gr") as mock_gr:
            mock_blocks = mock_gr.Blocks.return_value
            mock_blocks.__enter__ = lambda self: self
            mock_blocks.__exit__ = lambda self, *args: None

            interface = create_log_viewer_interface()

            mock_gr.Blocks.assert_called_once()
            assert interface is not None

    def test_handle_log_search(self):
        """Test handling search input from Gradio."""
        viewer = LogViewerWeb()
        viewer.log_viewer.add_log_line("2024-01-01 12:00:00 [INFO] Starting process")
        viewer.log_viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Process failed")
        viewer.log_viewer.add_log_line("2024-01-01 12:00:02 [INFO] Restarting")

        results = handle_log_search(viewer, "process")

        assert "Starting process" in results
        assert "Process failed" in results
        assert "Restarting" not in results

    def test_handle_log_filter_update(self):
        """Test handling filter updates from Gradio."""
        viewer = LogViewerWeb()
        viewer.log_viewer.add_log_line("2024-01-01 12:00:00 [INFO] Info message")
        viewer.log_viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")
        viewer.log_viewer.add_log_line("2024-01-01 12:00:02 [DEBUG] Debug message")

        # Filter to show only ERROR and INFO
        result = handle_log_filter_update(viewer, levels=["ERROR", "INFO"], search_text="")

        assert "[INFO]" in result
        assert "[ERROR]" in result
        assert "[DEBUG]" not in result

    def test_handle_log_export(self):
        """Test handling export requests from Gradio."""
        viewer = LogViewerWeb()
        viewer.log_viewer.add_log_line("2024-01-01 12:00:00 [INFO] Test message")
        viewer.log_viewer.add_log_line("2024-01-01 12:00:01 [ERROR] Error message")

        # Test JSON export
        json_result = handle_log_export(viewer, format="json")
        data = json.loads(json_result)
        assert len(data["entries"]) == 2

        # Test text export
        text_result = handle_log_export(viewer, format="text")
        assert "[INFO]" in text_result
        assert "[ERROR]" in text_result

        # Test CSV export
        csv_result = handle_log_export(viewer, format="csv")
        assert "timestamp,level,message" in csv_result

    def test_gradio_dropdown_options(self):
        """Test that Gradio dropdown options are properly configured."""
        viewer = LogViewerWeb()

        # Test log level dropdown options
        level_options = viewer.get_level_filter_options()
        assert "ALL" in level_options
        assert "INFO" in level_options
        assert "ERROR" in level_options
        assert "WARNING" in level_options
        assert "DEBUG" in level_options

        # Test export format dropdown options
        export_options = viewer.get_export_format_options()
        assert "JSON" in export_options
        assert "TEXT" in export_options
        assert "CSV" in export_options

    def test_gradio_timer_integration(self):
        """Test integration with Gradio timer for auto-refresh."""
        viewer = LogViewerWeb()

        with patch("gradio.Timer") as mock_timer:
            viewer.setup_auto_refresh_timer()

            mock_timer.assert_called_once()
            call_args = mock_timer.call_args
            assert call_args[1]["value"] == 2.0  # Default refresh interval
            assert call_args[1]["active"] is True


class TestPerformanceOptimization:
    """Test cases for performance optimization features."""

    def test_lazy_loading(self):
        """Test lazy loading of log entries."""
        viewer = LogViewerWeb()

        # Add many entries
        for i in range(1000):
            viewer.log_viewer.add_log_line(f"2024-01-01 12:00:{i:02d} [INFO] Message {i}")

        # Request first page
        page_html = viewer.render_page(page=0, page_size=50)

        # Should only render requested page
        assert page_html.count('<div class="log-entry log-info">') == 50

    def test_virtual_scrolling(self):
        """Test virtual scrolling implementation."""
        viewer = LogViewerWeb()

        # Add many entries
        for i in range(500):
            viewer.log_viewer.add_log_line(f"2024-01-01 12:00:{i:02d} [INFO] Message {i}")

        # Get viewport configuration
        viewport = viewer.get_viewport_config()

        assert viewport["total_items"] == 500
        assert viewport["viewport_size"] == 50  # Default viewport size
        assert viewport["buffer_size"] == 10  # Buffer above and below viewport

    def test_incremental_search(self):
        """Test incremental search performance."""
        viewer = LogViewerWeb()

        # Add many entries
        for i in range(100):
            viewer.log_viewer.add_log_line(f"2024-01-01 12:00:{i:02d} [INFO] Message {i}")

        # Perform incremental search
        results1 = viewer.incremental_search("Message 1")
        results2 = viewer.incremental_search("Message 10", previous_query="Message 1")

        # Second search should be optimized based on previous results
        assert len(results2) < len(results1)

    def test_caching_filtered_results(self):
        """Test caching of filtered results for performance."""
        viewer = LogViewerWeb()

        # Add entries
        for i in range(100):
            level = "INFO" if i % 2 == 0 else "ERROR"
            viewer.log_viewer.add_log_line(f"2024-01-01 12:00:{i:02d} [{level}] Message {i}")

        # Apply filter
        viewer.apply_filter(levels=["ERROR"])

        # First call should cache results
        result1 = viewer.get_filtered_html()

        # Second call should use cache
        with patch.object(viewer.log_viewer, "get_filtered_entries") as mock_filter:
            result2 = viewer.get_filtered_html()
            mock_filter.assert_not_called()  # Should use cache

        assert result1 == result2


class TestResponsiveDesign:
    """Test cases for responsive design features."""

    def test_mobile_layout(self):
        """Test mobile-responsive layout."""
        viewer = LogViewerWeb()
        viewer.set_viewport_size("mobile")

        config = viewer.get_layout_config()

        assert config["columns"] == 1
        assert config["font_size"] == "14px"
        assert config["compact_mode"] is True

    def test_tablet_layout(self):
        """Test tablet-responsive layout."""
        viewer = LogViewerWeb()
        viewer.set_viewport_size("tablet")

        config = viewer.get_layout_config()

        assert config["columns"] == 2
        assert config["font_size"] == "16px"
        assert config["compact_mode"] is False

    def test_desktop_layout(self):
        """Test desktop layout."""
        viewer = LogViewerWeb()
        viewer.set_viewport_size("desktop")

        config = viewer.get_layout_config()

        assert config["columns"] == 3
        assert config["font_size"] == "16px"
        assert config["sidebar_visible"] is True


class TestAccessibility:
    """Test cases for accessibility features."""

    def test_aria_labels(self):
        """Test that ARIA labels are properly set."""
        viewer = LogViewerWeb()
        html = viewer.render_html()

        assert 'aria-label="Log viewer"' in html
        assert 'aria-live="polite"' in html
        assert 'role="log"' in html

    def test_keyboard_navigation(self):
        """Test keyboard navigation support."""
        viewer = LogViewerWeb()

        # Add some entries first
        viewer.log_viewer.add_log_line("2024-01-01 12:00:00 [INFO] Entry 0")
        viewer.log_viewer.add_log_line("2024-01-01 12:00:01 [INFO] Entry 1")
        viewer.log_viewer.add_log_line("2024-01-01 12:00:02 [INFO] Entry 2")

        # Test navigation actions
        viewer.handle_keyboard_event("ArrowDown")
        assert viewer.selected_index == 1

        viewer.handle_keyboard_event("ArrowUp")
        assert viewer.selected_index == 0

        viewer.handle_keyboard_event("Home")
        assert viewer.selected_index == 0

        viewer.handle_keyboard_event("End")
        assert viewer.selected_index == len(viewer.log_viewer.entries) - 1

    def test_screen_reader_support(self):
        """Test screen reader compatibility."""
        viewer = LogViewerWeb()
        viewer.log_viewer.add_log_line("2024-01-01 12:00:00 [ERROR] Critical error occurred")

        announcement = viewer.get_screen_reader_announcement()

        assert "New log entry" in announcement
        assert "ERROR" in announcement
        assert "Critical error occurred" in announcement
