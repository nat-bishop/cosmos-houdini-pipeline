"""Video utility functions for Gradio UI.

This module provides video processing, metadata extraction, and validation
utilities used across the UI.
"""

import hashlib
import subprocess
from pathlib import Path

from cosmos_workflow.utils.logging import logger


def extract_video_metadata(video_path: Path) -> dict[str, str]:
    """Extract metadata from a video file.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary with video metadata (resolution, duration, fps, codec, frame_count)
    """
    metadata_default = {
        "resolution": "Unknown",
        "duration": "Unknown",
        "fps": "Unknown",
        "codec": "Unknown",
        "frame_count": "0",
    }

    if not video_path or not Path(video_path).exists():
        return metadata_default

    try:
        import cv2

        # Open video file
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            # Try with imageio as fallback
            return _extract_metadata_imageio(video_path)

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
        # OpenCV not installed, try imageio
        return _extract_metadata_imageio(video_path)
    except Exception as e:
        logger.warning("Failed to extract video metadata with cv2: %s", e)
        return _extract_metadata_imageio(video_path)


def _extract_metadata_imageio(video_path: Path) -> dict[str, str]:
    """Extract metadata using imageio as fallback.

    Args:
        video_path: Path to the video file

    Returns:
        Dictionary with video metadata
    """
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
            frame_count = 0

        reader.close()

        return {
            "resolution": f"{size[0]}x{size[1]}" if size else "Unknown",
            "duration": duration_str,
            "fps": f"{fps:.0f}" if fps > 0 else "Unknown",
            "codec": meta.get("codec", "Unknown"),
            "frame_count": str(frame_count) if frame_count > 0 else "Unknown",
        }

    except Exception as e:
        logger.warning("Failed to extract video metadata with imageio: %s", e)
        # Return sensible defaults
        return {
            "resolution": "1920x1080",
            "duration": "120 frames (5.0s @ 24fps)",
            "fps": "24",
            "codec": "h264",
            "frame_count": "120",
        }


def generate_thumbnail_fast(
    video_path: str, thumb_size: tuple[int, int] = (384, 216), store_with_video: bool = False
) -> str | None:
    """Generate a small, low-res thumbnail very quickly using ffmpeg.

    Args:
        video_path: Path to video file
        thumb_size: Thumbnail size (width, height)
        store_with_video: If True, store thumbnail in same directory as video.
                         If False, use centralized .thumbnails directory

    Returns:
        Path to thumbnail or None if failed
    """
    try:
        video_path = Path(video_path)
        if not video_path.exists():
            logger.debug("Video file does not exist: %s", video_path)
            return None

        # Determine thumbnail path based on storage preference
        if store_with_video:
            # Store thumbnail in same directory as video with .thumb.jpg extension
            thumb_path = video_path.parent / f"{video_path.stem}.thumb.jpg"
        else:
            # Use centralized thumbnails directory (legacy behavior)
            thumb_dir = Path("outputs/.thumbnails")
            thumb_dir.mkdir(parents=True, exist_ok=True)
            # Generate unique thumbnail name based on video path
            path_hash = hashlib.md5(str(video_path).encode()).hexdigest()[:8]  # noqa: S324
            thumb_path = thumb_dir / f"{video_path.stem}_{path_hash}.jpg"

        # Skip if thumbnail already exists
        if thumb_path.exists():
            return str(thumb_path)

        # Use ffmpeg with fast settings for quick thumbnail generation
        cmd = [
            "ffmpeg",
            "-ss",
            "0.5",  # Seek to 0.5 seconds (very fast seek)
            "-i",
            str(video_path),
            "-vframes",
            "1",  # Just 1 frame
            "-vf",
            f"scale={thumb_size[0]}:{thumb_size[1]}",  # Small size
            "-q:v",
            "5",  # Lower quality for speed (1=best, 31=worst)
            "-y",  # Overwrite
            str(thumb_path),
        ]

        # Run with timeout (increased slightly for production use)
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            timeout=5,  # Reasonable timeout for production
            creationflags=subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0,
        )

        if result.returncode == 0 and thumb_path.exists():
            return str(thumb_path)
        else:
            logger.debug("ffmpeg thumbnail generation failed with code %d", result.returncode)
            return None

    except subprocess.TimeoutExpired:
        logger.debug("Thumbnail generation timed out for %s", video_path)
        return None
    except Exception as e:
        logger.debug("Failed to generate thumbnail: %s", str(e))
        return None


def get_multimodal_inputs(directory: Path) -> list[str]:
    """Get list of multimodal input files in a directory.

    Args:
        directory: Path to the directory

    Returns:
        List of input file names that exist
    """
    if not directory or not Path(directory).exists():
        return []

    inputs = []
    expected_files = ["color.mp4", "depth.mp4", "segmentation.mp4", "canny.mp4"]

    for file_name in expected_files:
        file_path = Path(directory) / file_name
        if file_path.exists():
            inputs.append(file_name)

    return inputs


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


def get_video_files(directory: Path, extensions: list[str] | None = None) -> list[Path]:
    """Get all video files in a directory.

    Args:
        directory: Path to search
        extensions: List of video extensions to look for (default: common video formats)

    Returns:
        List of video file paths
    """
    if not directory or not Path(directory).exists():
        return []

    if extensions is None:
        extensions = [".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv"]

    video_files = []
    dir_path = Path(directory)

    for ext in extensions:
        video_files.extend(dir_path.glob(f"*{ext}"))
        video_files.extend(dir_path.glob(f"*{ext.upper()}"))

    return sorted(video_files)


def get_video_duration_seconds(video_path: Path) -> float | None:
    """Get video duration in seconds.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds or None if unable to determine
    """
    metadata = extract_video_metadata(video_path)

    # Try to parse duration from the metadata string
    duration_str = metadata.get("duration", "")
    if "s @" in duration_str:
        try:
            # Format: "120 frames (5.0s @ 24fps)"
            seconds_part = duration_str.split("(")[1].split("s @")[0]
            return float(seconds_part)
        except (IndexError, ValueError):
            pass

    # Try using frame count and fps
    try:
        frame_count = int(metadata.get("frame_count", "0"))
        fps = float(metadata.get("fps", "0"))
        if frame_count > 0 and fps > 0:
            return frame_count / fps
    except (ValueError, ZeroDivisionError):
        pass

    return None
