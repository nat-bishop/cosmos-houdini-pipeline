#!/usr/bin/env python3
"""Simple log viewer for GPU inference runs."""

import html
from collections import deque
from datetime import datetime, timezone


class LogViewer:
    """Simple log viewer for GPU inference."""

    def __init__(self, max_lines=2000):
        """Initialize with a ring buffer for automatic old log cleanup."""
        self.entries = deque(maxlen=max_lines)

    def add_from_stream(self, content: str):
        """Add lines from container log streaming callback."""
        for line in content.strip().split("\n"):
            if line:
                self.entries.append(
                    {"time": datetime.now(timezone.utc).strftime("%H:%M:%S"), "text": line.strip()}
                )

    def get_html(self, level_filter=None, search=None) -> str:
        """Get colored HTML with optional filtering.

        Args:
            level_filter: Filter by log level (ERROR, WARNING, INFO) or ALL/None
            search: Search text to filter/highlight

        Returns:
            HTML string with colored and filtered logs
        """
        # Add a unique ID and auto-scroll script
        html_lines = [
            '<div id="log-container" style="font-family:monospace; '
            "padding:10px; overflow-y:auto; max-height:600px; "
            "background:var(--body-background-fill); color:var(--body-text-color); "
            'border:1px solid var(--border-color-primary);">'
        ]

        for entry in self.entries:
            text = entry["text"]

            # Simple filtering
            if level_filter and level_filter != "ALL":
                # Check if the level appears in the text
                if f"[{level_filter}]" not in text and level_filter not in text:
                    continue
            if search and search.lower() not in text.lower():
                continue

            # Color based on content - semantic colors for log levels
            color = "inherit"  # Default to inherit theme color
            if "ERROR" in text or "Error" in text or "error" in text.lower():
                color = "#ff6b6b"  # Red for errors
            elif "WARNING" in text or "Warning" in text or "warning" in text.lower():
                color = "#ffa500"  # Orange for warnings
            elif "SUCCESS" in text or "complete" in text.lower() or "✓" in text:
                color = "#6bcf7f"  # Green for success
            elif "INFO" in text or "[INFO]" in text:
                color = "#4dabf7"  # Blue for info
            elif "DEBUG" in text or "[DEBUG]" in text:
                color = "#868e96"  # Gray for debug

            # Escape HTML for safety
            safe_text = html.escape(text)

            # Highlight search term if provided
            if search:
                # Case-insensitive highlight
                import re

                pattern = re.compile(re.escape(search), re.IGNORECASE)
                safe_text = pattern.sub(
                    lambda m: f'<mark style="background:#ff0;color:#000">{html.escape(m.group())}</mark>',
                    safe_text,
                )

            html_lines.append(
                f'<div style="color:{color};margin:2px 0">'
                f'<span style="color:#868e96">{entry["time"]}</span> {safe_text}'
                f"</div>"
            )

        html_lines.append("</div>")
        # Add auto-scroll script that runs after content loads
        html_lines.append(
            """<script>
            setTimeout(function() {
                var logContainer = document.getElementById('log-container');
                if (logContainer) {
                    logContainer.scrollTop = logContainer.scrollHeight;
                }
            }, 100);
            </script>"""
        )
        return "\n".join(html_lines)

    def clear(self):
        """Clear all logs."""
        self.entries.clear()

    def get_stats(self) -> dict:
        """Get quick statistics about the logs."""
        total = len(self.entries)
        errors = sum(1 for e in self.entries if "ERROR" in e["text"] or "Error" in e["text"])
        warnings = sum(1 for e in self.entries if "WARNING" in e["text"] or "Warning" in e["text"])
        return {"total": total, "errors": errors, "warnings": warnings}
