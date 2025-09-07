#!/usr/bin/env python3
"""Log visualization interface for real-time log streaming and analysis."""

import html
import json
import re
from collections import deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class LogEntry:
    """Represents a single log entry."""

    timestamp: datetime
    level: str
    message: str
    source: str | None = None
    line_number: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert LogEntry to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LogEntry":
        """Create LogEntry from dictionary."""
        data = data.copy()
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class LogFilter:
    """Filter for log entries based on various criteria."""

    def __init__(
        self,
        levels: list[str] | None = None,
        search_text: str | None = None,
        regex_pattern: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ):
        """Initialize LogFilter.

        Args:
            levels: List of log levels to include
            search_text: Text to search for in messages
            regex_pattern: Regex pattern to match messages
            start_time: Filter entries after this time
            end_time: Filter entries before this time
        """
        self.levels = levels
        self.search_text = search_text.lower() if search_text else None
        self.regex_pattern = re.compile(regex_pattern) if regex_pattern else None
        self.start_time = start_time
        self.end_time = end_time

    def apply(self, entries: list[LogEntry]) -> list[LogEntry]:
        """Apply filter to list of log entries."""
        filtered = entries

        if self.levels:
            filtered = [e for e in filtered if e.level in self.levels]

        if self.search_text:
            filtered = [e for e in filtered if self.search_text in e.message.lower()]

        if self.regex_pattern:
            filtered = [e for e in filtered if self.regex_pattern.search(e.message)]

        if self.start_time:
            filtered = [e for e in filtered if e.timestamp >= self.start_time]

        if self.end_time:
            filtered = [e for e in filtered if e.timestamp <= self.end_time]

        return filtered


class LogViewer:
    """Main log viewer component for managing and displaying logs."""

    def __init__(self, max_entries: int = 1000, buffer_size: int = 50):
        """Initialize LogViewer.

        Args:
            max_entries: Maximum number of log entries to keep
            buffer_size: Buffer size for batching updates
        """
        self.max_entries = max_entries
        self.buffer_size = buffer_size
        self.entries: deque[LogEntry] = deque(maxlen=max_entries)
        self.current_filter: LogFilter | None = None
        self.update_callback: Callable[[], None] | None = None
        self.buffer_count = 0
        self.stream_callbacks: dict[str, Callable[[str], None]] = {}

    def add_log_line(self, line: str) -> None:
        """Add a log line by parsing it."""
        entry = parse_log_line(line)
        self.add_entry(entry)

    def add_entry(self, entry: LogEntry) -> None:
        """Add a LogEntry directly."""
        self.entries.append(entry)
        self.buffer_count += 1

        if self.update_callback and self.buffer_count >= self.buffer_size:
            self.update_callback()
            self.buffer_count = 0

    def set_filter(self, filter_obj: LogFilter) -> None:
        """Set the current filter."""
        self.current_filter = filter_obj

    def get_filtered_entries(self) -> list[LogEntry]:
        """Get filtered entries based on current filter."""
        entries = list(self.entries)
        if self.current_filter:
            return self.current_filter.apply(entries)
        return entries

    def clear(self) -> None:
        """Clear all log entries."""
        self.entries.clear()
        self.buffer_count = 0

    def export_json(self, filtered: bool = False) -> str:
        """Export logs to JSON format."""
        entries = self.get_filtered_entries() if filtered else list(self.entries)
        data = {"entries": [e.to_dict() for e in entries]}
        return json.dumps(data, indent=2)

    def export_text(self) -> str:
        """Export logs to plain text format."""
        lines = []
        for entry in self.entries:
            lines.append(format_log_entry(entry))
        return "\n".join(lines)

    def search(self, text: str) -> list[LogEntry]:
        """Search logs for text."""
        text_lower = text.lower()
        return [e for e in self.entries if text_lower in e.message.lower()]

    def get_formatted_html(self) -> str:
        """Get HTML formatted output with syntax highlighting."""
        html_parts = ['<div class="log-viewer">']

        for entry in self.entries:
            level_class = f"log-{entry.level.lower()}"
            html_parts.append(f'<div class="{level_class}">')
            html_parts.append(html.escape(format_log_entry(entry)))
            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def set_update_callback(self, callback: Callable[[], None]) -> None:
        """Set callback for buffered updates."""
        self.update_callback = callback

    def flush_buffer(self) -> None:
        """Flush any pending buffer updates."""
        if self.update_callback and self.buffer_count > 0:
            self.update_callback()
            self.buffer_count = 0

    def get_stream_callback(self, stream_id: str | None = None) -> Callable[[str], None]:
        """Get a callback function for streaming logs."""

        def callback(content: str) -> None:
            for line in content.strip().split("\n"):
                if line:
                    entry = parse_log_line(line)
                    if stream_id:
                        entry.source = stream_id
                    self.add_entry(entry)

        if stream_id:
            self.stream_callbacks[stream_id] = callback
        return callback

    def get_page(self, page: int = 0, page_size: int = 50) -> list[LogEntry]:
        """Get a page of log entries for virtual scrolling."""
        start = page * page_size
        end = start + page_size
        entries = list(self.entries)
        return entries[start:end]

    def get_gradio_output(self) -> str:
        """Get output formatted for Gradio display."""
        return self.export_text()


def parse_log_line(line: str) -> LogEntry:
    """Parse a log line into a LogEntry.

    Supports various log formats:
    - Standard: "2024-01-01 12:00:00 [LEVEL] message"
    - With source: "2024-01-01 12:00:00 [LEVEL] (file.py:42) message"
    - Multiline: Preserves full content
    """
    # Try standard format with optional source info
    pattern = r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\:?\d{2}) \[(\w+)\](?: \(([^:]+):(\d+)\))? (.+)"
    match = re.match(pattern, line, re.DOTALL)

    if match:
        timestamp_str, level, source, line_num, message = match.groups()
        # Handle seconds >= 60 by clamping to 59
        parts = timestamp_str.split(":")
        if len(parts) >= 3:
            seconds = int(parts[-1])
            if seconds >= 60:
                parts[-1] = "59"
                timestamp_str = ":".join(parts)

        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            timestamp = datetime.now(timezone.utc)

        line_number = int(line_num) if line_num else None
        return LogEntry(timestamp, level, message.strip(), source, line_number)

    # Fallback for unstructured lines
    return LogEntry(datetime.now(timezone.utc), "INFO", line.strip())


def format_log_entry(entry: LogEntry) -> str:
    """Format a LogEntry for display."""
    timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    source_str = (
        f" ({entry.source}:{entry.line_number})" if entry.source and entry.line_number else ""
    )
    return f"{timestamp_str} [{entry.level}]{source_str} {entry.message}"
