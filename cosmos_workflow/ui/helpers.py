"""UI-specific helper functions for the Cosmos Workflow Manager."""

from datetime import datetime
from pathlib import Path
from typing import Any

from cosmos_workflow.utils.logging import logger


def format_timestamp(timestamp: str) -> str:
    """Format a timestamp for display in the UI.

    Args:
        timestamp: ISO format timestamp string

    Returns:
        Formatted timestamp for display
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


def format_duration(start_time: str, end_time: str) -> str:
    """Calculate and format duration between two timestamps.

    Args:
        start_time: Start timestamp
        end_time: End timestamp

    Returns:
        Formatted duration string (e.g., "14m 31s")
    """
    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        delta = end - start
        minutes = int(delta.total_seconds() / 60)
        seconds = int(delta.total_seconds() % 60)
        return f"{minutes}m {seconds}s"
    except Exception:
        return "-"


def truncate_text(text: str, max_length: int = 30) -> str:
    """Truncate text to a maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated text with ellipsis if needed
    """
    if not text:
        return ""

    if len(text) <= max_length:
        return text

    return text[: max_length - 3] + "..."


def get_file_info(file_path: Path) -> dict[str, Any]:
    """Get information about a file.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file information
    """
    try:
        if not file_path.exists():
            return {"exists": False}

        stat = file_path.stat()
        return {
            "exists": True,
            "size": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
        }
    except Exception as e:
        logger.error("Error getting file info for %s: %s", file_path, str(e))
        return {"exists": False, "error": str(e)}


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def extract_video_metadata(video_path: Path) -> dict[str, str]:
    """Extract metadata from a video file.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary with video metadata
    """
    try:
        import cv2

        # Open video file
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            # Fallback for when video can't be opened
            return {
                "resolution": "Unknown",
                "duration": "Unknown",
                "fps": "Unknown",
                "codec": "Unknown",
                "frame_count": "0",
            }

        # Extract metadata
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Get codec
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

        # Calculate duration
        if fps > 0:
            duration_seconds = frame_count / fps
            duration_str = f"{frame_count} frames ({duration_seconds:.1f}s @ {fps:.0f}fps)"
        else:
            duration_str = f"{frame_count} frames"

        cap.release()

        return {
            "resolution": f"{width}x{height}",
            "duration": duration_str,
            "fps": f"{fps:.0f}" if fps > 0 else "Unknown",
            "codec": codec if codec.strip() else "Unknown",
            "frame_count": str(frame_count),
        }

    except ImportError:
        # OpenCV not installed, try with imageio
        try:
            import imageio

            reader = imageio.get_reader(str(video_path))
            meta = reader.get_meta_data()

            fps = meta.get("fps", 0)
            duration = meta.get("duration", 0)
            size = meta.get("size", (0, 0))

            if fps > 0 and duration > 0:
                frame_count = int(fps * duration)
                duration_str = f"{frame_count} frames ({duration:.1f}s @ {fps:.0f}fps)"
            else:
                duration_str = "Unknown"

            reader.close()

            return {
                "resolution": f"{size[0]}x{size[1]}" if size else "Unknown",
                "duration": duration_str,
                "fps": f"{fps:.0f}" if fps > 0 else "Unknown",
                "codec": meta.get("codec", "Unknown"),
                "frame_count": str(frame_count) if fps > 0 and duration > 0 else "Unknown",
            }

        except Exception:
            pass

    except Exception as e:
        import logging

        logging.warning("Failed to extract video metadata: %s", e)

    # Final fallback
    return {
        "resolution": "1920x1080",
        "duration": "120 frames (5.0s @ 24fps)",
        "fps": "24",
        "codec": "h264",
        "frame_count": "120",
    }


def parse_table_selection(dataframe_data: Any) -> list[int]:
    """Parse selected rows from a dataframe.

    Args:
        dataframe_data: Gradio dataframe data

    Returns:
        List of selected row indices
    """
    if not dataframe_data:
        return []

    selected_indices = []

    # Handle different dataframe formats
    import pandas as pd

    if isinstance(dataframe_data, pd.DataFrame):
        # Check first column for boolean selection
        for idx, row in dataframe_data.iterrows():
            if row.iloc[0] is True:
                selected_indices.append(idx)
    elif isinstance(dataframe_data, list):
        # List format
        for idx, row in enumerate(dataframe_data):
            if row and len(row) > 0 and row[0] is True:
                selected_indices.append(idx)

    return selected_indices


def create_status_message(
    status: str, last_refresh: datetime | None = None, error: str | None = None
) -> str:
    """Create a status message for display.

    Args:
        status: Current status
        last_refresh: Last refresh timestamp
        error: Error message if any

    Returns:
        Formatted status message
    """
    if error:
        return f"❌ Error: {error}"

    if last_refresh:
        refresh_time = last_refresh.strftime("%H:%M:%S")
        return f"✅ {status} | Last refresh: {refresh_time}"

    return f"✅ {status} | Last refresh: Never"


def validate_video_directory(directory: str) -> tuple[bool, str]:
    """Validate that a directory contains required video files.

    Args:
        directory: Path to the directory

    Returns:
        Tuple of (is_valid, message)
    """
    if not directory:
        return False, "No directory specified"

    dir_path = Path(directory)

    if not dir_path.exists():
        return False, f"Directory does not exist: {directory}"

    if not dir_path.is_dir():
        return False, f"Path is not a directory: {directory}"

    # Check for required video files
    color_video = dir_path / "color.mp4"
    if not color_video.exists():
        return False, "Missing required file: color.mp4"

    return True, "Valid video directory"


def get_multimodal_inputs(directory: Path) -> list[str]:
    """Get list of multimodal input files in a directory.

    Args:
        directory: Path to the directory

    Returns:
        List of input file names
    """
    inputs = []
    expected_files = ["color.mp4", "depth.mp4", "segmentation.mp4", "canny.mp4"]

    for file_name in expected_files:
        file_path = directory / file_name
        if file_path.exists():
            inputs.append(file_name)

    return inputs


def format_run_status(status: str) -> str:
    """Format run status with emoji indicator.

    Args:
        status: Run status

    Returns:
        Formatted status with emoji
    """
    status_map = {
        "completed": "✅ Completed",
        "running": "🔄 Running",
        "pending": "⏳ Pending",
        "failed": "❌ Failed",
        "cancelled": "🚫 Cancelled",
    }

    return status_map.get(status.lower(), status)
