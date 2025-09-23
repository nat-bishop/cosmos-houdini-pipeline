"""Formatting utility functions for Gradio UI display.

This module provides consistent formatting for timestamps, durations, file sizes,
and other display elements across the UI.
"""

from datetime import datetime, timezone


def format_timestamp(timestamp: str | None) -> str:
    """Format a timestamp for display in the UI.

    Args:
        timestamp: ISO format timestamp string

    Returns:
        Formatted timestamp for display (YYYY-MM-DD HH:MM:SS) or "-" if invalid
    """
    if not timestamp:
        return "-"

    try:
        # Handle ISO format with or without timezone
        if timestamp.endswith("Z"):
            timestamp = timestamp[:-1] + "+00:00"

        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        # Return first 19 chars (YYYY-MM-DD HH:MM:SS) if parsing fails
        return timestamp[:19] if len(timestamp) >= 19 else timestamp


def format_duration(start_time: str | None, end_time: str | None) -> str:
    """Calculate and format duration between two timestamps.

    Args:
        start_time: Start timestamp in ISO format
        end_time: End timestamp in ISO format

    Returns:
        Formatted duration string (e.g., "14m 31s") or "-" if invalid
    """
    if not start_time or not end_time:
        return "-"

    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        delta = end - start

        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            return "-"

        # Format based on duration length
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    except Exception:
        return "-"


def truncate_text(text: str | None, max_length: int = 30) -> str:
    """Truncate text to a maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation (default: 30)

    Returns:
        Truncated text with ellipsis if needed, or empty string if text is None
    """
    if not text:
        return ""

    text = str(text)  # Ensure we're working with a string

    if len(text) <= max_length:
        return text

    # Reserve 3 characters for ellipsis
    return text[: max_length - 3] + "..."


def format_file_size(size_bytes: int | None) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string (e.g., "1.5 MB") or "-" if invalid
    """
    if size_bytes is None or size_bytes < 0:
        return "-"

    # Handle zero bytes
    if size_bytes == 0:
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(size_bytes)
    unit_index = 0

    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    # Format with appropriate precision
    if size >= 100:
        return f"{size:.0f} {units[unit_index]}"
    elif size >= 10:
        return f"{size:.1f} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def format_run_status(status: str | None) -> str:
    """Format run status with consistent icons and styling.

    Args:
        status: Run status string (completed, failed, running, etc.)

    Returns:
        Formatted status string with icon prefix
    """
    if not status:
        return "Unknown"

    status_lower = status.lower()

    # Map status to icon and display text
    status_map = {
        "completed": "✅ Completed",
        "failed": "❌ Failed",
        "running": "🔄 Running",
        "pending": "⏳ Pending",
        "cancelled": "🚫 Cancelled",
        "cancelling": "🔄 Cancelling",
        "queued": "📋 Queued",
        "processing": "⚙️ Processing",
        "uploading": "📤 Uploading",
        "downloading": "📥 Downloading",
    }

    # Return mapped status or capitalize original
    return status_map.get(status_lower, status.capitalize())


def format_percentage(value: float | None, decimals: int = 1) -> str:
    """Format a float value as a percentage.

    Args:
        value: Value between 0 and 1 (or 0-100 if already percentage)
        decimals: Number of decimal places (default: 1)

    Returns:
        Formatted percentage string (e.g., "75.5%") or "-" if invalid
    """
    if value is None:
        return "-"

    try:
        # If value is between 0 and 1, multiply by 100
        if 0 <= value <= 1:
            percentage = value * 100
        else:
            percentage = value

        if decimals == 0:
            return f"{percentage:.0f}%"
        else:
            format_str = f"{{:.{decimals}f}}%"
            return format_str.format(percentage)
    except (TypeError, ValueError):
        return "-"


def format_number(value: int | None, use_commas: bool = True) -> str:
    """Format a number with optional comma separators.

    Args:
        value: Number to format
        use_commas: Whether to add comma separators (default: True)

    Returns:
        Formatted number string or "-" if invalid
    """
    if value is None:
        return "-"

    try:
        if use_commas:
            return f"{int(value):,}"
        else:
            return str(int(value))
    except (TypeError, ValueError):
        return "-"


def format_time_ago(timestamp: str | None) -> str:
    """Format a timestamp as relative time (e.g., "2 hours ago").

    Args:
        timestamp: ISO format timestamp string

    Returns:
        Relative time string or absolute time if too old
    """
    if not timestamp:
        return "-"

    try:
        # Parse timestamp
        if timestamp.endswith("Z"):
            timestamp = timestamp[:-1] + "+00:00"
        dt = datetime.fromisoformat(timestamp)

        # Get current time in UTC
        now = datetime.now(timezone.utc)

        # Ensure dt has timezone info
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        # Calculate difference
        delta = now - dt
        total_seconds = int(delta.total_seconds())

        # Format based on time difference
        if total_seconds < 0:
            return "in the future"
        elif total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif total_seconds < 86400:
            hours = total_seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif total_seconds < 604800:  # 7 days
            days = total_seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            # Return absolute date for older items
            return dt.strftime("%Y-%m-%d")

    except Exception:
        return format_timestamp(timestamp)  # Fallback to absolute time
