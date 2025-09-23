#!/usr/bin/env python3
"""Check if a specific run has a thumbnail in the database."""

import json
import sys

from sqlalchemy import text

from cosmos_workflow.database import DatabaseConnection

run_id = sys.argv[1] if len(sys.argv) > 1 else "rs_f3072bb07603468cbe9dac85adeb27b7"

db = DatabaseConnection("outputs/cosmos.db")
with db.get_session() as session:
    result = session.execute(
        text("SELECT outputs FROM runs WHERE id = :id"), {"id": run_id}
    ).fetchone()

    if result:
        outputs = json.loads(result[0]) if result[0] else {}
        thumbnail_path = outputs.get("thumbnail_path")
        print(f"Run {run_id}:")
        print(f"  Thumbnail path: {thumbnail_path}")
        print(f"  Output path: {outputs.get('output_path')}")
        print(f"  Has thumbnail: {'YES' if thumbnail_path else 'NO'}")
    else:
        print(f"Run {run_id} not found")
