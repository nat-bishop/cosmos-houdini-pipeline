"""Display data builders for runs UI components.

This module contains functions for building gallery data, table data,
and statistics for the runs display.
"""

from datetime import datetime, timezone
from pathlib import Path

from cosmos_workflow.utils.logging import logger


def build_gallery_data(runs: list, limit: int = 50) -> list:
    """Build gallery data using pre-generated thumbnails for completed runs.

    This function first checks for thumbnail_path in the database (fastest),
    then looks for thumbnails in the filesystem as fallback. Thumbnails are
    generated once when outputs are downloaded, never on-demand.

    Args:
        runs: List of run dictionaries from database
        limit: Maximum number of thumbnails to display

    Returns:
        List of (thumbnail_path, label) tuples for gallery
    """
    gallery_data = []
    processed_count = 0

    # Look for pre-generated thumbnails for completed runs
    for run in runs:
        if processed_count >= limit:
            break

        if run.get("status") != "completed":
            continue

        outputs = run.get("outputs", {})
        thumb_path = None
        output_video = None

        # FIRST: Check if thumbnail_path is stored in database (fastest)
        if isinstance(outputs, dict) and "thumbnail_path" in outputs:
            thumb_path_str = outputs["thumbnail_path"]
            if thumb_path_str:
                thumb_path = Path(thumb_path_str)
                if not thumb_path.exists():
                    logger.warning(
                        "Thumbnail path stored in database but file missing: {} for run {}",
                        thumb_path_str,
                        run.get("id", "unknown"),
                    )
                    thumb_path = None

        # If no thumbnail in database, try filesystem locations as fallback
        if not thumb_path:
            # Get output video path
            if isinstance(outputs, dict) and "output_path" in outputs:
                output_path = outputs["output_path"]
                if output_path and output_path.endswith(".mp4"):
                    output_video = Path(output_path)
            # Old structure: outputs.files array
            elif isinstance(outputs, dict) and "files" in outputs:
                files = outputs.get("files", [])
                for file_path in files:
                    if file_path.endswith("output.mp4"):
                        output_video = Path(file_path)
                        break

            if output_video and output_video.exists():
                # Look for pre-generated thumbnail in same directory
                thumb_path = output_video.parent / f"{output_video.stem}.thumb.jpg"

                # Also check legacy centralized thumbnail location as fallback
                if not thumb_path.exists():
                    import hashlib

                    path_hash = hashlib.md5(str(output_video).encode()).hexdigest()[:8]  # noqa: S324
                    legacy_thumb_path = (
                        Path("outputs/.thumbnails") / f"{output_video.stem}_{path_hash}.jpg"
                    )
                    if legacy_thumb_path.exists():
                        thumb_path = legacy_thumb_path
                    else:
                        thumb_path = None

                if not thumb_path or not thumb_path.exists():
                    # Log warning that thumbnail is missing
                    logger.warning(
                        "Thumbnail not found for completed run {} with output video at {}. "
                        "Thumbnail should have been generated when output was downloaded.",
                        run.get("id", "unknown"),
                        output_video,
                    )
                    continue
            else:
                # No output video found, skip this run
                continue

        # Add to gallery if we have a valid thumbnail
        if thumb_path and thumb_path.exists():
            # Include rating and run ID in label
            full_id = run.get("id", "")
            rating = run.get("rating")
            star_display = "★" * rating + "☆" * (5 - rating) if rating else "☆☆☆☆☆"
            label = f"{star_display}||{full_id}"
            gallery_data.append((str(thumb_path), label))
            processed_count += 1

    if processed_count > 0:
        logger.info("Loaded {} pre-generated thumbnails for gallery display", processed_count)

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
    "build_gallery_data",
    "build_runs_table_data",
    "calculate_runs_statistics",
]
