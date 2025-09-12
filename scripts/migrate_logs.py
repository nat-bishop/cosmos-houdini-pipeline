#!/usr/bin/env python3
"""
Migration script to update existing logs to the new unified format.

This script will:
1. Update database log_path for all existing runs
2. Rename orchestration_*.log files to rs_*.log
3. Append Docker logs (outputs/run.log) to the unified log
"""

import shutil
import sqlite3
from pathlib import Path


def migrate_logs():
    """Migrate existing logs to new unified format."""

    # Connect to database
    db_path = Path("outputs/cosmos.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all runs
    cursor.execute("SELECT id FROM runs")
    runs = cursor.fetchall()

    print(f"Found {len(runs)} runs to migrate")
    print("=" * 60)

    successful_migrations = 0
    failed_migrations = 0

    for (run_id,) in runs:
        print(f"\nProcessing run: {run_id}")
        run_dir = Path(f"outputs/run_{run_id}")

        if not run_dir.exists():
            print(f"  [WARN] Run directory not found: {run_dir}")
            failed_migrations += 1
            continue

        logs_dir = run_dir / "logs"
        outputs_dir = run_dir / "outputs"

        # New unified log path (run_id already has 'rs_' prefix)
        unified_log_path = logs_dir / f"{run_id}.log"

        # Check if already migrated
        if unified_log_path.exists():
            print(f"  [OK] Already migrated: {unified_log_path}")
            # Still update database in case it's NULL
            relative_path = f"outputs/run_{run_id}/logs/{run_id}.log"
            cursor.execute("UPDATE runs SET log_path = ? WHERE id = ?", (relative_path, run_id))
            successful_migrations += 1
            continue

        # Find orchestration log
        orchestration_log = logs_dir / f"orchestration_{run_id}.log"

        if orchestration_log.exists():
            print(f"  Found orchestration log: {orchestration_log.name}")

            # Rename orchestration log to unified log
            print(f"  Renaming to: {run_id}.log")
            shutil.move(str(orchestration_log), str(unified_log_path))

            # Check for Docker log
            docker_log = outputs_dir / "run.log"
            if docker_log.exists():
                print(f"  Found Docker log: {docker_log}")

                # Append Docker log to unified log
                with open(unified_log_path, "a") as unified:
                    unified.write("\n" + "=" * 60 + "\n")
                    unified.write("=== DOCKER EXECUTION LOGS ===\n")
                    unified.write("=" * 60 + "\n\n")
                    try:
                        with open(docker_log, encoding="utf-8", errors="ignore") as docker:
                            unified.write(docker.read())
                        print("  [OK] Appended Docker logs to unified log")
                    except Exception as e:
                        print(f"  [WARN] Failed to append Docker log: {e}")
            else:
                print(f"  No Docker log found at: {docker_log}")

        elif (outputs_dir / "run.log").exists():
            # No orchestration log, but Docker log exists
            docker_log = outputs_dir / "run.log"
            print(f"  No orchestration log, but found Docker log: {docker_log}")

            # Create logs directory if it doesn't exist
            logs_dir.mkdir(parents=True, exist_ok=True)

            # Copy Docker log as unified log
            print("  Creating unified log from Docker log")
            with open(unified_log_path, "w") as unified:
                unified.write("=== DOCKER EXECUTION LOGS ===\n")
                unified.write("=" * 60 + "\n\n")
                try:
                    with open(docker_log, encoding="utf-8", errors="ignore") as docker:
                        unified.write(docker.read())
                    print("  [OK] Created unified log from Docker log")
                except Exception as e:
                    print(f"  [WARN] Failed to create unified log: {e}")

        else:
            print("  [WARN] No logs found for this run")
            failed_migrations += 1
            continue

        # Update database with new log path
        relative_path = f"outputs/run_{run_id}/logs/rs_{run_id}.log"
        cursor.execute("UPDATE runs SET log_path = ? WHERE id = ?", (relative_path, run_id))
        print(f"  [OK] Updated database log_path: {relative_path}")
        successful_migrations += 1

    # Commit database changes
    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print("Migration complete!")
    print(f"  [OK] Successful: {successful_migrations}")
    print(f"  [WARN] Failed: {failed_migrations}")
    print(f"  Total: {len(runs)}")


def verify_migration():
    """Verify the migration was successful."""
    print("\n" + "=" * 60)
    print("Verifying migration...")

    conn = sqlite3.connect("outputs/cosmos.db")
    cursor = conn.cursor()

    # Check for NULL log_paths
    cursor.execute("SELECT COUNT(*) FROM runs WHERE log_path IS NULL")
    null_count = cursor.fetchone()[0]

    # Check for non-NULL log_paths
    cursor.execute("SELECT COUNT(*) FROM runs WHERE log_path IS NOT NULL")
    non_null_count = cursor.fetchone()[0]

    print(f"  Runs with log_path: {non_null_count}")
    print(f"  Runs without log_path: {null_count}")

    # Show a few examples
    cursor.execute("SELECT id, log_path FROM runs WHERE log_path IS NOT NULL LIMIT 3")
    examples = cursor.fetchall()

    if examples:
        print("\nExample migrated runs:")
        for run_id, log_path in examples:
            print(f"  {run_id}: {log_path}")
            # Check if file actually exists
            if Path(log_path).exists():
                print("    [OK] File exists")
            else:
                print("    [WARN] File not found")

    conn.close()


if __name__ == "__main__":
    print("Starting log migration...")
    print("This will:")
    print("1. Rename orchestration_*.log files to rs_*.log")
    print("2. Append Docker logs to the unified log")
    print("3. Update database log_path for all runs")
    print()

    response = input("Continue? (y/n): ")
    if response.lower() == "y":
        migrate_logs()
        verify_migration()
    else:
        print("Migration cancelled")
