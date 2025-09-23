"""Display data builders for runs UI components.

This module contains functions for building gallery data, table data,
and statistics for the runs display.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from cosmos_workflow.ui.utils import video as video_utils
from cosmos_workflow.utils.logging import logger

# Thread pool for parallel thumbnail generation
THUMBNAIL_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def build_gallery_data(runs: list, limit: int = 50) -> list:
    """Build gallery data with thumbnails for completed runs.

    Args:
        runs: List of run dictionaries
        limit: Maximum number of thumbnails to generate

    Returns:
        List of (thumbnail_path, label) tuples for gallery
    """
    gallery_data = []
    video_paths = []

    # Collect video paths from completed runs
    for run in runs:
        if run.get("status") != "completed":
            continue

        outputs = run.get("outputs", {})
        output_video = None

        # New structure: outputs.output_path
        if isinstance(outputs, dict) and "output_path" in outputs:
            output_path = outputs["output_path"]
            if output_path and output_path.endswith(".mp4"):
                output_video = Path(output_path)
                if output_video.exists():
                    video_paths.append((output_video, run))
        # Old structure: outputs.files array
        elif isinstance(outputs, dict) and "files" in outputs:
            files = outputs.get("files", [])
            for file_path in files:
                if file_path.endswith("output.mp4"):
                    output_video = Path(file_path)
                    if output_video.exists():
                        video_paths.append((output_video, run))
                        break

    # Generate thumbnails in parallel
    if video_paths:
        logger.info("Generating thumbnails for {} videos", min(len(video_paths), limit))
        futures = []
        for video_path, run in video_paths[:limit]:
            future = THUMBNAIL_EXECUTOR.submit(video_utils.generate_thumbnail_fast, video_path)
            futures.append((future, run))

        # Collect results
        for future, run in futures:
            try:
                thumb_path = future.result(timeout=3)
                if thumb_path:
                    # Include rating and run ID in label
                    full_id = run.get("id", "")
                    rating = run.get("rating")
                    star_display = "★" * rating + "☆" * (5 - rating) if rating else "☆☆☆☆☆"
                    label = f"{star_display}||{full_id}"
                    gallery_data.append((thumb_path, label))
            except Exception as e:
                logger.debug("Failed to generate thumbnail: {}", str(e))

    return gallery_data


def build_runs_table_data(runs: list) -> list:
    """Build table data from runs list.

    Args:
        runs: List of run dictionaries

    Returns:
        List of table rows
    """
    table_data = []

    for run in runs:
        run_id = run.get("id", "")
        status = run.get("status", "unknown")
        model_type = run.get("model_type", "transfer")

        # Calculate duration
        duration = "N/A"
        if run.get("created_at") and run.get("completed_at"):
            try:
                created_str = run["created_at"]
                if "Z" in created_str or "+" in created_str or "-" in created_str[-6:]:
                    start = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                else:
                    start = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)

                completed_str = run["completed_at"]
                if "Z" in completed_str or "+" in completed_str or "-" in completed_str[-6:]:
                    end = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
                else:
                    end = datetime.fromisoformat(completed_str).replace(tzinfo=timezone.utc)

                duration_delta = end - start
                duration = str(duration_delta).split(".")[0]
            except (ValueError, TypeError) as e:
                # Unable to parse dates, leave duration as-is
                logger.debug("Unable to parse dates for duration calculation: %s", e)

        created = run.get("created_at", "")[:19] if run.get("created_at") else ""
        rating = run.get("rating")
        rating_display = str(rating) if rating else "-"

        table_data.append([run_id, status, model_type, duration, rating_display, created])

    return table_data


def calculate_runs_statistics(runs: list, total_count: int) -> str:
    """Calculate statistics for runs display.

    Args:
        runs: List of displayed runs
        total_count: Total count before limiting

    Returns:
        Formatted statistics string
    """
    completed_count = sum(1 for r in runs if r.get("status") == "completed")
    running_count = sum(1 for r in runs if r.get("status") == "running")
    failed_count = sum(1 for r in runs if r.get("status") == "failed")

    stats = f"""
    **Total Matching:** {total_count} (showing {len(runs)})
    **Completed:** {completed_count}
    **Running:** {running_count}
    **Failed:** {failed_count}
    """

    return stats


# Maintain backward compatibility with underscore-prefixed names
_build_gallery_data = build_gallery_data
_build_runs_table_data = build_runs_table_data
_calculate_runs_statistics = calculate_runs_statistics

__all__ = [
    "THUMBNAIL_EXECUTOR",
    "build_gallery_data",
    "build_runs_table_data",
    "calculate_runs_statistics",
]
