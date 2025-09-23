#!/usr/bin/env python3
"""Get statistics about thumbnail generation."""

import json
from pathlib import Path

from sqlalchemy import text

from cosmos_workflow.database import DatabaseConnection

db = DatabaseConnection("outputs/cosmos.db")

with db.get_session() as session:
    # Get all completed runs
    runs = session.execute(
        text("SELECT id, outputs FROM runs WHERE status = 'completed'")
    ).fetchall()

    total_runs = len(runs)
    has_thumbnail_in_db = 0
    thumbnail_exists = 0
    missing_thumbnails = []

    for run_id, outputs_json in runs:
        outputs = json.loads(outputs_json) if outputs_json else {}

        # Check if thumbnail path is in database
        if outputs.get("thumbnail_path"):
            has_thumbnail_in_db += 1

            # Check if file actually exists
            thumb_path = Path(outputs["thumbnail_path"])
            if thumb_path.exists():
                thumbnail_exists += 1
            else:
                missing_thumbnails.append((run_id, outputs["thumbnail_path"]))

    print("=== Thumbnail Generation Statistics ===")
    print(f"Total completed runs: {total_runs}")
    print(
        f"Runs with thumbnail path in DB: {has_thumbnail_in_db} ({has_thumbnail_in_db * 100 / total_runs:.1f}%)"
    )
    print(
        f"Thumbnails that exist on disk: {thumbnail_exists} ({thumbnail_exists * 100 / total_runs:.1f}%)"
    )

    if missing_thumbnails:
        print(f"\nWarning: {len(missing_thumbnails)} thumbnails in DB but missing on disk:")
        for run_id, path in missing_thumbnails[:5]:
            print(f"  - {run_id}: {path}")
        if len(missing_thumbnails) > 5:
            print(f"  ... and {len(missing_thumbnails) - 5} more")

    # Check for thumbnails that exist but aren't in DB
    orphaned = 0
    for _run_id, outputs_json in runs:
        outputs = json.loads(outputs_json) if outputs_json else {}

        if "thumbnail_path" not in outputs or not outputs["thumbnail_path"]:
            # Check if output exists
            output_path = outputs.get("output_path")
            if output_path:
                video_path = Path(output_path)
                if video_path.exists():
                    expected_thumb = video_path.parent / f"{video_path.stem}.thumb.jpg"
                    if expected_thumb.exists():
                        orphaned += 1

    if orphaned > 0:
        print(f"\nNote: {orphaned} thumbnails exist on disk but aren't recorded in DB")
        print("(These may have been created by the script but not committed to DB)")

    print("\n=== Summary ===")
    if thumbnail_exists == total_runs:
        print("SUCCESS: All completed runs have thumbnails!")
    elif thumbnail_exists >= total_runs * 0.95:
        print(f"MOSTLY COMPLETE: {thumbnail_exists}/{total_runs} runs have thumbnails")
    else:
        print(f"PARTIAL: {thumbnail_exists}/{total_runs} runs have thumbnails")
