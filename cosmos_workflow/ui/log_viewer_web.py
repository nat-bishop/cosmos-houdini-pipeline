#!/usr/bin/env python3
"""Web-based log viewer integration for Gradio interface."""

import csv
import html
import io
import re
from typing import Any

import gradio as gr

from cosmos_workflow.ui.log_viewer import LogFilter, LogViewer


class LogViewerWeb:
    """Web-based log viewer component for Gradio integration."""

    def __init__(self):
        """Initialize LogViewerWeb."""
        self.log_viewer = LogViewer()
        self.active_streams: dict[str, dict[str, Any]] = {}
        self.theme = "dark"
        self.auto_refresh_enabled = False
        self.auto_refresh_interval = 2.0
        self.selected_index = 0
        self.cache: dict[str, Any] = {}
        self.viewport_size = "desktop"

    def add_stream(self, run_id: str, log_path: str) -> str:
        """Add a new log stream.

        Args:
            run_id: Run ID for the stream
            log_path: Path to the log file

        Returns:
            Stream ID
        """
        stream_id = f"stream_{run_id}"
        self.active_streams[stream_id] = {"run_id": run_id, "log_path": log_path, "active": True}
        return stream_id

    def remove_stream(self, stream_id: str) -> None:
        """Remove a log stream."""
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]

    def get_active_streams(self) -> list[dict[str, Any]]:
        """Get list of active streams."""
        return list(self.active_streams.values())

    def render_html(self) -> str:
        """Render HTML output for display."""
        theme_class = f"theme-{self.theme}"
        html_parts = [
            f'<div class="log-viewer-web {theme_class}" aria-label="Log viewer" aria-live="polite" role="log">'
        ]

        for entry in self.log_viewer.entries:
            level_class = f"log-{entry.level.lower()}"
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            message = html.escape(entry.message)

            html_parts.append(f'<div class="log-entry {level_class}">')
            html_parts.append(f'<span class="timestamp">{timestamp}</span>')
            html_parts.append(f'<span class="level">[{entry.level}]</span>')
            html_parts.append(f'<span class="message">{message}</span>')
            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def set_theme(self, theme: str) -> None:
        """Set the UI theme."""
        self.theme = theme

    def enable_auto_refresh(self, interval: float = 2.0) -> None:
        """Enable auto-refresh with specified interval."""
        self.auto_refresh_enabled = True
        self.auto_refresh_interval = interval

    def disable_auto_refresh(self) -> None:
        """Disable auto-refresh."""
        self.auto_refresh_enabled = False

    def get_keyboard_shortcuts(self) -> dict[str, str]:
        """Get keyboard shortcuts configuration."""
        return {
            "search": "Ctrl+F",
            "filter": "Ctrl+Shift+F",
            "export": "Ctrl+E",
            "clear": "Ctrl+L",
            "refresh": "F5",
        }

    def render_page(self, page: int = 0, page_size: int = 50) -> str:
        """Render a specific page of logs."""
        entries = self.log_viewer.get_page(page, page_size)
        html_parts = []

        for entry in entries:
            level_class = f"log-{entry.level.lower()}"
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            message = html.escape(entry.message)

            html_parts.append(f'<div class="log-entry {level_class}">')
            html_parts.append(f'<span class="timestamp">{timestamp}</span>')
            html_parts.append(f'<span class="level">[{entry.level}]</span>')
            html_parts.append(f'<span class="message">{message}</span>')
            html_parts.append("</div>")

        return "\n".join(html_parts)

    def get_viewport_config(self) -> dict[str, int]:
        """Get viewport configuration for virtual scrolling."""
        return {
            "total_items": len(self.log_viewer.entries),
            "viewport_size": 50,
            "buffer_size": 10,
        }

    def incremental_search(self, query: str, previous_query: str | None = None) -> list:
        """Perform incremental search."""
        if previous_query and query.startswith(previous_query):
            # Optimize by searching within previous results if cached
            if "search_results" in self.cache:
                results = [
                    e for e in self.cache["search_results"] if query.lower() in e.message.lower()
                ]
            else:
                results = self.log_viewer.search(query)
        else:
            results = self.log_viewer.search(query)

        self.cache["search_results"] = results
        return results

    def apply_filter(self, levels: list[str] | None = None) -> None:
        """Apply filter and cache results."""
        filter_obj = LogFilter(levels=levels)
        self.log_viewer.set_filter(filter_obj)
        self.cache["filtered_html"] = self.render_html()

    def get_filtered_html(self) -> str:
        """Get cached filtered HTML or generate new."""
        if "filtered_html" in self.cache:
            return self.cache["filtered_html"]
        return self.render_html()

    def set_viewport_size(self, size: str) -> None:
        """Set viewport size for responsive design."""
        self.viewport_size = size

    def get_layout_config(self) -> dict[str, Any]:
        """Get layout configuration based on viewport size."""
        configs = {
            "mobile": {
                "columns": 1,
                "font_size": "14px",
                "compact_mode": True,
                "sidebar_visible": False,
            },
            "tablet": {
                "columns": 2,
                "font_size": "16px",
                "compact_mode": False,
                "sidebar_visible": False,
            },
            "desktop": {
                "columns": 3,
                "font_size": "16px",
                "compact_mode": False,
                "sidebar_visible": True,
            },
        }
        return configs.get(self.viewport_size, configs["desktop"])

    def handle_keyboard_event(self, key: str) -> None:
        """Handle keyboard navigation events."""
        if key == "ArrowDown":
            self.selected_index = min(
                self.selected_index + 1, max(0, len(self.log_viewer.entries) - 1)
            )
        elif key == "ArrowUp":
            self.selected_index = max(self.selected_index - 1, 0)
        elif key == "Home":
            self.selected_index = 0
        elif key == "End":
            self.selected_index = max(0, len(self.log_viewer.entries) - 1)

    def get_screen_reader_announcement(self) -> str:
        """Get screen reader announcement for latest log entry."""
        if self.log_viewer.entries:
            latest = self.log_viewer.entries[-1]
            return f"New log entry: {latest.level} - {latest.message}"
        return ""

    def get_level_filter_options(self) -> list[str]:
        """Get log level filter options."""
        return ["ALL", "INFO", "ERROR", "WARNING", "DEBUG"]

    def get_export_format_options(self) -> list[str]:
        """Get export format options."""
        return ["JSON", "TEXT", "CSV"]

    def setup_auto_refresh_timer(self) -> None:
        """Setup Gradio timer for auto-refresh."""
        gr.Timer(value=self.auto_refresh_interval, active=True)


def get_log_level_style(level: str) -> str:
    """Get CSS style for log level."""
    styles = {
        "INFO": "color: #28a745",  # Green
        "ERROR": "color: #dc3545",  # Red
        "WARNING": "color: #ffc107",  # Yellow
        "DEBUG": "color: #6c757d",  # Gray
    }
    return styles.get(level, "color: #333")


def format_log_html(log_text: str, highlight: str | None = None) -> str:
    """Format log text as HTML with optional highlighting."""
    # Escape HTML characters
    log_text = html.escape(log_text)

    # Parse timestamp, level, and message
    pattern = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[(\w+)\] (.+)"
    match = re.match(pattern, log_text, re.DOTALL)

    if match:
        timestamp, level, message = match.groups()

        # Apply highlighting if requested
        if highlight:
            message = message.replace(highlight, f'<mark class="highlight">{highlight}</mark>')

        # Check for multiline content (tracebacks)
        if "\n" in message and "Traceback" in message:
            message = f'<pre class="log-traceback">{message}</pre>'

        html_output = f'<span class="log-timestamp">{timestamp}</span> '
        html_output += f'<span class="log-level log-{level.lower()}">[{level}]</span> '
        html_output += f'<span class="log-message">{message}</span>'
        return html_output

    return log_text


def handle_log_search(viewer: LogViewerWeb, search_text: str) -> str:
    """Handle search input from Gradio."""
    results = viewer.log_viewer.search(search_text)
    html_parts = []

    for entry in results:
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        html_parts.append(f"{timestamp} [{entry.level}] {entry.message}")

    return "\n".join(html_parts)


def handle_log_filter_update(viewer: LogViewerWeb, levels: list[str], search_text: str) -> str:
    """Handle filter updates from Gradio."""
    # Convert "ALL" to None for no level filtering
    if "ALL" in levels:
        levels = None

    filter_obj = LogFilter(levels=levels, search_text=search_text if search_text else None)
    viewer.log_viewer.set_filter(filter_obj)

    # Return filtered text output
    filtered_entries = viewer.log_viewer.get_filtered_entries()
    lines = []
    for entry in filtered_entries:
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"{timestamp} [{entry.level}] {entry.message}")

    return "\n".join(lines)


def handle_log_export(viewer: LogViewerWeb, format: str = "json") -> str:
    """Handle export requests from Gradio."""
    format_upper = format.upper()

    if format_upper == "JSON":
        return viewer.log_viewer.export_json()
    elif format_upper == "TEXT":
        return viewer.log_viewer.export_text()
    elif format_upper == "CSV":
        # Create CSV export
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "level", "message", "source", "line_number"])

        for entry in viewer.log_viewer.entries:
            writer.writerow(
                [
                    entry.timestamp.isoformat(),
                    entry.level,
                    entry.message,
                    entry.source or "",
                    entry.line_number or "",
                ]
            )

        return output.getvalue()

    return ""


def create_log_viewer_interface() -> gr.Blocks:
    """Create Gradio interface for log viewer."""
    viewer = LogViewerWeb()

    interface = gr.Blocks(title="Log Viewer", theme=gr.themes.Soft())
    with interface:
        gr.Markdown("## Log Visualization Interface")

        with gr.Row():
            # Left panel - controls
            with gr.Column(scale=1):
                gr.Markdown("### Filters")

                level_filter = gr.CheckboxGroup(
                    choices=viewer.get_level_filter_options(),
                    value=["ALL"],
                    label="Log Levels",
                )

                search_box = gr.Textbox(label="Search", placeholder="Enter search text...")

                export_format = gr.Dropdown(
                    choices=viewer.get_export_format_options(),
                    value="JSON",
                    label="Export Format",
                )

                export_btn = gr.Button("Export Logs", variant="primary")

                gr.Markdown("### Settings")

                theme_selector = gr.Radio(choices=["dark", "light"], value="dark", label="Theme")

                gr.Checkbox(label="Auto-refresh", value=False)

            # Right panel - log display
            with gr.Column(scale=3):
                log_display = gr.Textbox(
                    label="Logs",
                    lines=30,
                    max_lines=50,
                    interactive=False,
                    elem_classes=["log-display"],
                )

                with gr.Row():
                    clear_btn = gr.Button("Clear Logs", variant="secondary")
                    refresh_btn = gr.Button("Refresh", variant="secondary")

        # Event handlers
        def update_logs(levels, search_text):
            return handle_log_filter_update(viewer, levels, search_text)

        def export_logs(format):
            return handle_log_export(viewer, format)

        def clear_logs():
            viewer.log_viewer.clear()
            return ""

        def set_theme(theme):
            viewer.set_theme(theme)
            return gr.update()

        # Wire up events
        level_filter.change(fn=update_logs, inputs=[level_filter, search_box], outputs=log_display)

        search_box.change(fn=update_logs, inputs=[level_filter, search_box], outputs=log_display)

        export_btn.click(fn=export_logs, inputs=[export_format], outputs=gr.Textbox(visible=False))

        clear_btn.click(fn=clear_logs, outputs=log_display)

        refresh_btn.click(fn=update_logs, inputs=[level_filter, search_box], outputs=log_display)

        theme_selector.change(fn=set_theme, inputs=[theme_selector], outputs=log_display)

    return interface
