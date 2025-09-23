#!/usr/bin/env python3
"""Generate thumbnails for all existing runs that don't have them.

This script will:
1. Query all completed runs from the database
2. Check if they have thumbnails
3. Generate thumbnails for videos that don't have them
4. Update the database with thumbnail paths
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text

from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.ui.utils.video import generate_thumbnail_fast
from cosmos_workflow.utils.logging import logger


def generate_missing_thumbnails():
    """Generate thumbnails for all runs that don't have them."""
    # Connect to database
    db_path = Path("outputs/cosmos.db")
    if not db_path.exists():
        logger.error("Database not found at {}", db_path)
        return

    db = DatabaseConnection(str(db_path))

    # Get all completed runs
    with db.get_session() as session:
        # Query all runs with status 'completed'
        runs = session.execute(
            text("SELECT id, outputs FROM runs WHERE status = 'completed'")
        ).fetchall()

        logger.info("Found {} completed runs to process", len(runs))

        updated_count = 0
        generated_count = 0

        for run_id, outputs_json in runs:
            try:
                # Parse the outputs JSON
                outputs = json.loads(outputs_json) if outputs_json else {}

                # Check if thumbnail already exists in database
                if outputs.get("thumbnail_path"):
                    thumb_path = Path(outputs["thumbnail_path"])
                    if thumb_path.exists():
                        logger.debug("Run {} already has thumbnail at {}", run_id, thumb_path)
                        continue
                    else:
                        logger.warning(
                            "Run {} has thumbnail path but file missing: {}", run_id, thumb_path
                        )

                # Check if output video exists
                output_path = outputs.get("output_path")
                if not output_path:
                    logger.debug("Run {} has no output_path", run_id)
                    continue

                video_path = Path(output_path)
                if not video_path.exists():
                    logger.warning("Run {} output video not found: {}", run_id, video_path)
                    continue

                # Check if thumbnail already exists on disk (but not in database)
                expected_thumb = video_path.parent / f"{video_path.stem}.thumb.jpg"

                if expected_thumb.exists():
                    # Thumbnail exists but not in database, just update database
                    logger.info("Found existing thumbnail for run {}, updating database", run_id)
                    thumbnail_path = str(expected_thumb)
                else:
                    # Generate thumbnail
                    logger.info("Generating thumbnail for run {} from {}", run_id, video_path)
                    thumbnail_path = generate_thumbnail_fast(str(video_path))

                    if thumbnail_path:
                        generated_count += 1
                        logger.info("Generated thumbnail: {}", thumbnail_path)
                    else:
                        logger.error("Failed to generate thumbnail for run {}", run_id)
                        continue

                # Update database with thumbnail path
                outputs["thumbnail_path"] = thumbnail_path

                # If completed_at is missing, add it
                if "completed_at" not in outputs:
                    outputs["completed_at"] = datetime.now(timezone.utc).isoformat()

                # Update the database
                session.execute(
                    text("UPDATE runs SET outputs = :outputs WHERE id = :id"),
                    {"outputs": json.dumps(outputs), "id": run_id},
                )
                updated_count += 1
                logger.info("Updated database for run {}", run_id)

            except Exception as e:
                logger.error("Error processing run {}: {}", run_id, e)
                continue

        # Commit all updates
        session.commit()

        logger.info(
            "Thumbnail generation complete:\n"
            "  - Generated {} new thumbnails\n"
            "  - Updated {} database entries\n"
            "  - Total runs processed: {}",
            generated_count,
            updated_count,
            len(runs),
        )


def verify_thumbnails():
    """Verify all completed runs have thumbnails."""
    db_path = Path("outputs/cosmos.db")
    db = DatabaseConnection(str(db_path))

    with db.get_session() as session:
        runs = session.execute(
            text("SELECT id, outputs FROM runs WHERE status = 'completed'")
        ).fetchall()

        missing_count = 0
        valid_count = 0

        for run_id, outputs_json in runs:
            outputs = json.loads(outputs_json) if outputs_json else {}

            if outputs.get("thumbnail_path"):
                thumb_path = Path(outputs["thumbnail_path"])
                if thumb_path.exists():
                    valid_count += 1
                else:
                    logger.warning("Run {} has invalid thumbnail path: {}", run_id, thumb_path)
                    missing_count += 1
            else:
                output_path = outputs.get("output_path")
                if output_path and Path(output_path).exists():
                    logger.warning("Run {} missing thumbnail (has video)", run_id)
                    missing_count += 1

        logger.info(
            "Thumbnail verification:\n"
            "  - Valid thumbnails: {}\n"
            "  - Missing/invalid: {}\n"
            "  - Total completed runs: {}",
            valid_count,
            missing_count,
            len(runs),
        )

        return missing_count == 0


if __name__ == "__main__":
    logger.info("Starting thumbnail generation for existing runs...")
    generate_missing_thumbnails()

    logger.info("\nVerifying thumbnails...")
    if verify_thumbnails():
        logger.info("✅ All completed runs have valid thumbnails!")
    else:
        logger.warning("⚠️ Some runs still missing thumbnails, check logs above")
