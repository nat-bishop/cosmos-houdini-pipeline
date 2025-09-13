#!/usr/bin/env python3
"""Event handlers for Runs tab functionality."""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.utils.logging import logger

# Thread pool for parallel thumbnail generation
THUMBNAIL_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def generate_thumbnail_fast(video_path, thumb_size=(384, 216)):
    """Generate a small, low-res thumbnail very quickly.

    Args:
        video_path: Path to video file
        thumb_size: Thumbnail size (width, height)

    Returns:
        Path to thumbnail or None if failed
    """
    try:
        video_path = Path(video_path)
        if not video_path.exists():
            return None

        # Create thumbnails directory
        thumb_dir = Path("outputs/.thumbnails")
        thumb_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique thumbnail name based on video path
        import hashlib

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

        # Run with timeout
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            timeout=2,  # Very short timeout
            creationflags=subprocess.CREATE_NO_WINDOW
            if hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0,
        )

        if result.returncode == 0 and thumb_path.exists():
            return str(thumb_path)

    except (subprocess.TimeoutExpired, Exception):  # noqa: S110
        pass

    return None


def load_runs_data(status_filter, date_filter, search_text, limit):
    """Load runs data for table with filtering and populate video grid."""
    try:
        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()

        if not ops:
            logger.warning("CosmosAPI not initialized")
            return [], [], "No data available"

        # Query runs with status filter
        all_runs = ops.list_runs(
            status=None if status_filter == "all" else status_filter, limit=int(limit)
        )

        # Enrich runs with prompt text
        for run in all_runs:
            if not run.get("prompt_text") and run.get("prompt_id"):
                prompt = ops.get_prompt(run["prompt_id"])
                if prompt:
                    run["prompt_text"] = prompt.get("prompt_text", "")

        # Apply date filter
        now = datetime.now(timezone.utc)
        filtered_runs = []

        for run in all_runs:
            # Parse run creation date
            try:
                created_str = run.get("created_at", "")
                if created_str:
                    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                else:
                    created = now
            except Exception:
                created = now

            # Apply date filter
            if date_filter == "today":
                if created.date() == now.date():
                    filtered_runs.append(run)
            elif date_filter == "yesterday":
                yesterday = now - timedelta(days=1)
                if created.date() == yesterday.date():
                    filtered_runs.append(run)
            elif date_filter == "last_7_days":
                seven_days_ago = now - timedelta(days=7)
                if created >= seven_days_ago:
                    filtered_runs.append(run)
            elif date_filter == "last_30_days":
                thirty_days_ago = now - timedelta(days=30)
                if created >= thirty_days_ago:
                    filtered_runs.append(run)
            else:  # all
                filtered_runs.append(run)

        # Apply text search
        if search_text:
            search_lower = search_text.lower()
            filtered_runs = [
                run
                for run in filtered_runs
                if search_lower in run.get("id", "").lower()
                or search_lower in run.get("prompt_text", "").lower()
            ]

        # Build gallery data with thumbnails (only completed runs)
        gallery_data = []
        video_paths = []

        # First collect all video paths
        for run in filtered_runs:
            if run.get("status") == "completed":
                # Extract output video from files array
                outputs = run.get("outputs", {})
                files = outputs.get("files", []) if isinstance(outputs, dict) else []

                # Find the output.mp4 file
                output_video = None
                for file_path in files:
                    if file_path.endswith("output.mp4"):
                        # Normalize path for Windows
                        output_video = Path(file_path)
                        if output_video.exists():
                            break

                if output_video:
                    video_paths.append((output_video, run))

        # Generate thumbnails in parallel for speed
        if video_paths:
            futures = []
            for video_path, run in video_paths[:50]:  # Limit to 50 for performance
                future = THUMBNAIL_EXECUTOR.submit(generate_thumbnail_fast, video_path)
                futures.append((future, run))

            # Collect results
            for future, run in futures:
                try:
                    thumb_path = future.result(timeout=3)
                    if thumb_path:
                        prompt_text = run.get("prompt_text", "")
                        # Include full run ID for selection handler, show shortened version visually
                        full_id = run.get("id", "")
                        label = f"{full_id}||{prompt_text[:30]}..."
                        gallery_data.append((thumb_path, label))
                except Exception:  # noqa: S110
                    pass  # Skip failed thumbnails

        # Build table data
        table_data = []
        for run in filtered_runs:
            run_id = run.get("id", "")
            status = run.get("status", "unknown")
            prompt_text = run.get("prompt_text", "")[:50]

            # Calculate duration
            duration = "N/A"
            if run.get("created_at") and run.get("completed_at"):
                try:
                    start = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(run["completed_at"].replace("Z", "+00:00"))
                    duration_delta = end - start
                    duration = str(duration_delta).split(".")[0]
                except Exception:  # noqa: S110
                    pass

            created = run.get("created_at", "")[:19] if run.get("created_at") else ""
            completed = run.get("completed_at", "")[:19] if run.get("completed_at") else ""

            # No checkbox, just data
            table_data.append([run_id, status, prompt_text, duration, created, completed])

        # Build statistics
        stats = f"""
        **Total Runs:** {len(filtered_runs)}
        **Completed:** {sum(1 for r in filtered_runs if r.get("status") == "completed")}
        **Running:** {sum(1 for r in filtered_runs if r.get("status") == "running")}
        **Failed:** {sum(1 for r in filtered_runs if r.get("status") == "failed")}
        """

        # Return gallery data, table data and stats
        return gallery_data, table_data, stats

    except Exception as e:
        import traceback

        logger.error("Error loading runs data: {}\n{}", str(e), traceback.format_exc())
        return [], [], "Error loading data"


def on_runs_gallery_select(evt: gr.SelectData):
    """Handle selection of a run from the gallery."""
    try:
        logger.info("on_runs_gallery_select called - evt: {}", evt)

        if evt is None:
            logger.warning("No evt, hiding details")
            return [gr.update(visible=False)] + [gr.update()] * 16

        # The label contains the run ID in format "full_run_id||prompt text..."
        label = evt.value.get("caption", "") if isinstance(evt.value, dict) else ""
        if not label:
            logger.warning("No label in gallery selection")
            return [gr.update(visible=False)] + [gr.update()] * 16

        # Extract full run ID from label (before the || separator)
        if "||" in label:
            full_run_id = label.split("||")[0].strip()
            if full_run_id and full_run_id.startswith("rs_"):
                # Create a fake table data and event to reuse the existing handler
                fake_table_data = [[full_run_id]]
                fake_evt = type("obj", (object,), {"index": 0})()
                return on_runs_table_select(fake_table_data, fake_evt)

        # Fallback to old format handling if || separator not found
        if "rs_" in label:
            # Find the run ID pattern - handle "rs_xxxxx..." format
            import re

            # Try full ID first, then shortened with dots, then just prefix
            match = (
                re.search(r"(rs_[a-f0-9]{32})", label)
                or re.search(r"(rs_[a-f0-9]+)\.\.\.", label)
                or re.search(r"(rs_[a-f0-9]{5,8})", label)
            )
            if match:
                run_id_prefix = match.group(1)
                # If it's a shortened ID, we need to find the full one
                from cosmos_workflow.api.cosmos_api import CosmosAPI

                ops = CosmosAPI()

                # Get all runs and find the matching one
                runs = ops.list_runs(limit=100)
                full_run_id = None
                for run in runs:
                    if run["id"].startswith(run_id_prefix):
                        full_run_id = run["id"]
                        break

                if full_run_id:
                    # Create a fake table data and event to reuse the existing handler
                    fake_table_data = [[full_run_id]]
                    fake_evt = type("obj", (object,), {"index": 0})()
                    return on_runs_table_select(fake_table_data, fake_evt)

        logger.warning("Could not extract run ID from label: {}", label)
        return [gr.update(visible=False)] + [gr.update()] * 16

    except Exception as e:
        logger.error("Error selecting from gallery: {}", str(e))
        return [gr.update(visible=False)] + [gr.update()] * 16


def on_runs_table_select(table_data, evt: gr.SelectData):
    """Handle selection of a run from the table."""
    try:
        logger.info(
            "on_runs_table_select called - evt: {}, table_data type: {}", evt, type(table_data)
        )

        if evt is None or table_data is None:
            logger.warning("No evt or table_data, hiding details")
            return [gr.update(visible=False)] + [gr.update()] * 16

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()

        # Get selected row
        logger.info("Event index: {}, type: {}", evt.index, type(evt.index))
        row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index
        logger.info("Selected row index: {}", row_idx)

        # Extract run ID from table
        import pandas as pd

        if isinstance(table_data, pd.DataFrame):
            run_id = table_data.iloc[row_idx, 0]  # Run ID is first column now (no checkbox)
            logger.info("Extracted run_id from DataFrame: {}", run_id)
        else:
            run_id = table_data[row_idx][0] if row_idx < len(table_data) else None
            logger.info("Extracted run_id from list: {}", run_id)

        if not run_id or not ops:
            logger.warning("No run_id ({}) or ops ({}), hiding details", run_id, ops)
            return [gr.update(visible=False)] + [gr.update()] * 16

        # Get full run details
        run_details = ops.get_run(run_id)
        logger.info("Retrieved run_details: {}", bool(run_details))
        if not run_details:
            logger.warning("No run_details found for run_id: {}", run_id)
            return [gr.update(visible=False)] + [gr.update()] * 16

        # Extract details
        # Get output video from files array
        outputs = run_details.get("outputs", {})
        files = outputs.get("files", []) if isinstance(outputs, dict) else []

        # Find the output.mp4 file
        output_video = ""
        for file_path in files:
            if file_path.endswith("output.mp4"):
                # Normalize path for Windows
                output_video = str(Path(file_path))
                break

        logger.info("Output video path: {}", output_video)

        # Get prompt text (will need to fetch from prompt later)
        prompt_text = run_details.get("prompt_text", "")

        # If prompt_text is not in run, fetch it from the prompt
        if not prompt_text and run_details.get("prompt_id"):
            prompt = ops.get_prompt(run_details["prompt_id"])
            if prompt:
                prompt_text = prompt.get("prompt_text", "")

        # Get input videos and control weights
        input_videos = []
        control_weights = {"vis": 0, "edge": 0, "depth": 0, "seg": 0}
        prompt_id = run_details.get("prompt_id")
        prompt_name = ""  # Initialize prompt_name
        run_id = run_details.get("id", "")

        # Read spec.json just for control weights
        spec_data = {}
        if run_id:
            spec_path = Path(
                f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/inputs/spec.json"
            )
            if spec_path.exists():
                try:
                    import json

                    with open(spec_path) as f:
                        spec_data = json.load(f)
                    logger.info("Loaded spec.json for run {}", run_id)
                except Exception as e:
                    logger.warning("Failed to load spec.json: {}", str(e))

        # Get prompt inputs for video paths
        prompt_inputs = {}
        if prompt_id and ops:
            prompt = ops.get_prompt(prompt_id)
            if prompt:
                prompt_inputs = prompt.get("inputs", {})
                # Get the prompt name from parameters
                prompt_params = prompt.get("parameters", {})
                prompt_name = prompt_params.get("name", "")

        # Process videos based on spec.json weights and prompt inputs
        if spec_data:
            # Add main video from prompt if it exists
            if prompt_inputs.get("video"):
                path = Path(prompt_inputs["video"])
                if path.exists():
                    # Main video doesn't need weight in label since it's always 1.0
                    input_videos.append((str(path), "Color/Visual"))
                    control_weights["vis"] = 1.0

            # Process each control type
            control_types = {"edge": "Edge", "depth": "Depth", "seg": "Segmentation"}

            for control_key, control_label in control_types.items():
                control_config = spec_data.get(control_key, {})
                weight = control_config.get("control_weight", 0)

                # Only process if weight > 0
                if weight > 0:
                    control_weights[control_key] = weight
                    # Include weight in the label
                    label_with_weight = f"{control_label} (Weight: {weight})"

                    # First try prompt's input for this control
                    if prompt_inputs.get(control_key):
                        control_path = Path(prompt_inputs[control_key])
                        if control_path.exists():
                            input_videos.append((str(control_path), label_with_weight))
                            logger.info("Using prompt's {} input: {}", control_key, control_path)
                            continue

                    # If no prompt input, check for AI-generated control
                    generated_path = Path(
                        f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{control_key}_input_control.mp4"
                    )
                    if generated_path.exists():
                        input_videos.append((str(generated_path), label_with_weight))
                        logger.info(
                            "Using AI-generated {} control: {}", control_key, generated_path
                        )
                    else:
                        logger.warning(
                            "No video found for {} control (weight={})", control_key, weight
                        )

        # Fallback if no spec.json - use prompt inputs with default weights
        elif prompt_inputs:
            # Map the actual keys to display labels
            video_keys = {
                "video": ("Color/Visual", 1.0),
                "edge": ("Edge", 0.5),
                "depth": ("Depth", 0.5),
                "seg": ("Segmentation", 0.5),
            }
            for key, (label, default_weight) in video_keys.items():
                if prompt_inputs.get(key):
                    path = Path(prompt_inputs[key])
                    if path.exists():
                        # Add weight to label for controls
                        if key != "video":
                            label = f"{label} (Weight: {default_weight})"
                        input_videos.append((str(path), label))
                        # Set default weight for backward compatibility
                        if key == "video":
                            control_weights["vis"] = default_weight
                        else:
                            control_weights[key] = default_weight

        # Use control weights from spec.json, fallback to execution_config if needed
        exec_config = run_details.get("execution_config", {})
        if not any(control_weights.values()):
            # No weights from spec.json, try execution_config
            weights = exec_config.get("weights", {})
            control_weights = weights if weights else control_weights

        params = exec_config  # Use entire execution_config as parameters

        # Get metadata
        duration = "N/A"
        if run_details.get("created_at") and run_details.get("completed_at"):
            try:
                start = datetime.fromisoformat(run_details["created_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(run_details["completed_at"].replace("Z", "+00:00"))
                duration_delta = end - start
                duration = str(duration_delta).split(".")[0]
            except Exception:  # noqa: S110
                pass

        # Get log path
        log_path = run_details.get("log_path", "")
        log_content = ""
        if log_path and Path(log_path).exists():
            try:
                with open(log_path) as f:
                    lines = f.readlines()
                    log_content = "".join(lines[-15:])  # Last 15 lines
            except Exception:
                log_content = "Error reading log file"

        logger.info(
            "Returning updates - visible: True, run_id: {}, output_video: {}", run_id, output_video
        )

        # Prepare individual video updates (up to 4 videos)
        video_updates = []
        for i in range(4):
            if i < len(input_videos):
                video_path, label = input_videos[i]
                video_updates.append(gr.update(value=video_path, label=label, visible=True))
            else:
                video_updates.append(gr.update(value=None, visible=False))

        # Format input paths for display
        input_paths_text = ""
        for video_path, label in input_videos:
            input_paths_text += f"{label}: {video_path}\n"

        return [
            gr.update(visible=True),  # runs_details_group
            gr.update(value=run_id),  # runs_detail_id (hidden)
            gr.update(value=run_details.get("status", "")),  # runs_detail_status (hidden)
            video_updates[0],  # runs_input_video_1
            video_updates[1],  # runs_input_video_2
            video_updates[2],  # runs_input_video_3
            video_updates[3],  # runs_input_video_4
            gr.update(
                value=output_video if output_video and Path(output_video).exists() else None
            ),  # runs_output_video
            gr.update(value=prompt_text),  # runs_prompt_text
            gr.update(value=run_id),  # runs_info_id
            gr.update(value=run_details.get("prompt_id", "")),  # runs_info_prompt_id
            gr.update(value=run_details.get("status", "")),  # runs_info_status
            gr.update(value=duration),  # runs_info_duration
            gr.update(value=run_details.get("run_type", "inference")),  # runs_info_type
            gr.update(value=prompt_name),  # runs_info_prompt_name
            gr.update(value=run_details.get("created_at", "")[:19]),  # runs_info_created
            gr.update(value=run_details.get("completed_at", "")[:19]),  # runs_info_completed
            gr.update(value=output_video if output_video else "Not found"),  # runs_info_output_path
            gr.update(
                value=input_paths_text.strip() if input_paths_text else "No input videos"
            ),  # runs_info_input_paths
            gr.update(value=params),  # runs_params_json
            gr.update(value=log_path),  # runs_log_path
            gr.update(value=log_content),  # runs_log_output
        ]

    except Exception as e:
        logger.error("Error selecting run: {}", str(e))
        return [gr.update(visible=False)] + [gr.update()] * 21


def load_run_logs(log_path):
    """Load full log file content."""
    try:
        if not log_path or not Path(log_path).exists():
            return "No log file available"

        with open(log_path) as f:
            content = f.read()

        return content
    except Exception as e:
        return f"Error reading log file: {e}"


def preview_delete_run(selected_run_id):
    """Preview what will be deleted for a run."""
    try:
        if not selected_run_id:
            return (
                gr.update(visible=False),  # Hide dialog
                "",  # No preview text
                False,  # Reset checkbox
                "",  # No run ID
            )

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        if not ops:
            return (
                gr.update(visible=False),
                "Error: Cannot connect to API",
                False,
                "",
            )

        # Get preview of what will be deleted
        preview = ops.preview_run_deletion(selected_run_id, keep_outputs=False)

        if not preview.get("run"):
            return (
                gr.update(visible=False),
                f"Run {selected_run_id[:8]} not found",
                False,
                "",
            )

        run_info = preview["run"]
        output_dir = preview.get("output_directory", "")
        file_count = preview.get("file_count", 0)
        total_size = preview.get("total_size_mb", 0)

        # Build preview text
        preview_text = f"""### ⚠️ Delete Run Confirmation

**Run ID:** {run_info.get('id', '')}
**Status:** {run_info.get('status', 'unknown')}
**Created:** {run_info.get('created_at', '')[:19] if run_info.get('created_at') else 'unknown'}

**Output Directory:** {output_dir}
**Files:** {file_count} files
**Total Size:** {total_size:.2f} MB

⚠️ **Warning:** This action cannot be undone!
"""

        return (
            gr.update(visible=True),  # Show dialog
            preview_text,  # Preview text
            False,  # Default to keep outputs
            selected_run_id,  # Store run ID for confirmation
        )

    except Exception as e:
        logger.error("Error previewing run deletion: {}", str(e))
        return (
            gr.update(visible=False),
            f"Error: {e}",
            False,
            "",
        )


def confirm_delete_run(run_id, delete_outputs):
    """Actually delete the run after confirmation."""
    try:
        if not run_id:
            return "No run selected", gr.update(visible=False)

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        if not ops:
            return "Error: Cannot connect to API", gr.update(visible=False)

        # Delete the run (keep_outputs is opposite of delete_outputs)
        keep_outputs = not delete_outputs
        result = ops.delete_run(run_id, keep_outputs=keep_outputs)

        if result.get("success"):
            msg = f"✅ Successfully deleted run {run_id[:8]}..."
            if delete_outputs:
                msg += " (output files deleted)"
            else:
                msg += " (output files preserved)"
            return msg, gr.update(visible=False)
        else:
            error_msg = result.get("message", result.get("error", "Unknown error"))
            return f"❌ Failed to delete run: {error_msg}", gr.update(visible=False)

    except Exception as e:
        logger.error("Error deleting run {}: {}", run_id, str(e))
        return f"❌ Error deleting run: {e}", gr.update(visible=False)


def cancel_delete_run():
    """Cancel run deletion."""
    return "Deletion cancelled", gr.update(visible=False)


def update_runs_selection_info(table_data, evt: gr.SelectData):
    """Update the selection info text and return selected run ID."""
    try:
        if evt is None or evt.index is None or table_data is None:
            return "No run selected", ""

        # Get selected run ID
        import pandas as pd

        row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index

        if isinstance(table_data, pd.DataFrame):
            run_id = table_data.iloc[row_idx, 0]  # Run ID is first column
        else:
            run_id = table_data[row_idx][0] if row_idx < len(table_data) else ""

        if run_id:
            return f"Selected: {run_id[:8]}...", run_id
        return "No run selected", ""
    except Exception:
        return "No run selected", ""
