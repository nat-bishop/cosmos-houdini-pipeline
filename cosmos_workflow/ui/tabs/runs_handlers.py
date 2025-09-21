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


def load_runs_data(status_filter, date_filter, type_filter, search_text, limit, rating_filter=None):
    """Load runs data for table with filtering and populate video grid."""
    try:
        logger.debug(
            "Loading runs data with filters: status={}, date={}, type={}, search={}, limit={}, rating={}",
            status_filter,
            date_filter,
            type_filter,
            search_text,
            limit,
            rating_filter,
        )

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()

        if not ops:
            logger.warning("CosmosAPI not initialized")
            return [], [], "No data available"

        # Query more runs initially to ensure filters have enough data to work with
        # We fetch up to 500 runs to search through, then limit display results later
        max_search_limit = 500
        all_runs = ops.list_runs(
            status=None if status_filter == "all" else status_filter, limit=max_search_limit
        )
        logger.info("Fetched {} runs from database", len(all_runs))

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
                    # Handle both timezone-aware and naive dates
                    if "Z" in created_str or "+" in created_str or "-" in created_str[-6:]:
                        # Has timezone info
                        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    else:
                        # No timezone info - assume UTC
                        created = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)
                else:
                    created = now
            except Exception:
                created = now

            # Apply date filter
            date_match = False
            if date_filter == "today":
                date_match = created.date() == now.date()
            elif date_filter == "yesterday":
                yesterday = now - timedelta(days=1)
                date_match = created.date() == yesterday.date()
            elif date_filter == "last_7_days":
                seven_days_ago = now - timedelta(days=7)
                date_match = created >= seven_days_ago
            elif date_filter == "last_30_days":
                thirty_days_ago = now - timedelta(days=30)
                date_match = created >= thirty_days_ago
            else:  # all
                date_match = True

            # Apply type filter
            type_match = False
            if type_filter == "all":
                type_match = True
            else:
                # Get model_type from run data (it's stored in database as model_type, not run_type)
                model_type = run.get(
                    "model_type", "transfer"
                )  # Default to transfer if not specified
                type_match = type_filter == model_type

            # Add to filtered runs if both filters match
            if date_match and type_match:
                filtered_runs.append(run)

        # Apply text search
        if search_text:
            search_lower = search_text.lower()
            initial_count = len(filtered_runs)
            filtered_runs = [
                run
                for run in filtered_runs
                if search_lower in run.get("id", "").lower()
                or search_lower in run.get("prompt_text", "").lower()
            ]
            logger.debug(
                "Text search '{}' reduced runs from {} to {}",
                search_text,
                initial_count,
                len(filtered_runs),
            )

        # Apply rating filter
        if rating_filter and rating_filter != "all":
            initial_count = len(filtered_runs)
            if rating_filter == "unrated":
                # Filter for runs with no rating
                filtered_runs = [run for run in filtered_runs if not run.get("rating")]
            elif rating_filter == 5:
                # Exact 5 stars
                filtered_runs = [run for run in filtered_runs if run.get("rating") == 5]
            elif isinstance(rating_filter, str) and rating_filter.endswith("+"):
                # Range filters like "4+", "3+", etc.
                min_rating = int(rating_filter[0])
                filtered_runs = [
                    run
                    for run in filtered_runs
                    if run.get("rating") and run.get("rating") >= min_rating
                ]
            logger.debug(
                "Rating filter '{}' reduced runs from {} to {}",
                rating_filter,
                initial_count,
                len(filtered_runs),
            )

        # Store total count before limiting for statistics
        total_filtered = len(filtered_runs)

        # Now limit to the user's Max Results setting
        display_limit = int(limit)
        filtered_runs = filtered_runs[:display_limit]

        # Build gallery data with thumbnails (only completed runs)
        gallery_data = []
        video_paths = []
        completed_runs = [r for r in filtered_runs if r.get("status") == "completed"]
        logger.debug("Processing {} completed runs for gallery", len(completed_runs))

        # First collect all video paths
        missing_videos = []
        for run in filtered_runs:
            if run.get("status") == "completed":
                outputs = run.get("outputs", {})
                output_video = None
                run_id = run.get("id", "unknown")

                # New structure: outputs.output_path
                if isinstance(outputs, dict) and "output_path" in outputs:
                    output_path = outputs["output_path"]
                    logger.debug(
                        "Run {} using new structure with output_path: {}", run_id, output_path
                    )
                    if output_path and output_path.endswith(".mp4"):
                        # Normalize path separators for cross-platform compatibility
                        raw_path = output_path
                        output_video = Path(output_path)
                        if str(raw_path) != str(output_video):
                            logger.debug("Path normalized from '{} to '{}'", raw_path, output_video)
                        if output_video.exists():
                            video_paths.append((output_video, run))
                            logger.debug("Found output video for run {}: {}", run_id, output_video)
                        else:
                            missing_videos.append((run_id, output_path))
                            logger.warning(
                                "Output video not found for run {}: {}", run_id, output_path
                            )

                # Old structure: outputs.files array
                elif isinstance(outputs, dict) and "files" in outputs:
                    files = outputs.get("files", [])
                    logger.debug(
                        "Run {} using old structure with files array ({} files)", run_id, len(files)
                    )
                    for file_path in files:
                        if file_path.endswith("output.mp4"):
                            # Normalize path for Windows
                            output_video = Path(file_path)
                            if output_video.exists():
                                video_paths.append((output_video, run))
                                logger.debug(
                                    "Found output video for run {}: {}", run_id, output_video
                                )
                            else:
                                missing_videos.append((run_id, file_path))
                                logger.warning(
                                    "Output video not found for run {}: {}", run_id, file_path
                                )
                            break
                else:
                    logger.debug("Run {} has no recognized output structure", run_id)

        if missing_videos:
            logger.warning(
                "Missing videos for {} runs: {}", len(missing_videos), missing_videos[:5]
            )  # Log first 5 for brevity

        # Generate thumbnails in parallel for speed
        if video_paths:
            logger.info("Generating thumbnails for {} videos (max 50)", min(len(video_paths), 50))
            futures = []
            for video_path, run in video_paths[:50]:  # Limit to 50 for performance
                future = THUMBNAIL_EXECUTOR.submit(generate_thumbnail_fast, video_path)
                futures.append((future, run))

            # Collect results
            successful_thumbs = 0
            failed_thumbs = 0
            for future, run in futures:
                try:
                    thumb_path = future.result(timeout=3)
                    if thumb_path:
                        # Include rating and run ID in label for gallery
                        full_id = run.get("id", "")
                        rating = run.get("rating")
                        if rating:
                            star_display = "★" * rating + "☆" * (5 - rating)
                        else:
                            star_display = "☆☆☆☆☆"  # Show empty stars instead of "No Rating"
                        # Keep run ID hidden with separator for selection
                        # The gallery will display the label but we still need the ID for selection
                        label = f"{star_display}||{full_id}"
                        gallery_data.append((thumb_path, label))
                        successful_thumbs += 1
                    else:
                        failed_thumbs += 1
                except Exception as e:
                    failed_thumbs += 1
                    logger.debug("Failed to generate thumbnail: {}", str(e))

            logger.info(
                "Gallery built: {} thumbnails generated, {} failed from {} completed runs",
                successful_thumbs,
                failed_thumbs,
                len(completed_runs),
            )

        # Build table data
        table_data = []
        for run in filtered_runs:
            run_id = run.get("id", "")
            status = run.get("status", "unknown")
            model_type = run.get("model_type", "transfer")  # Default to transfer if not specified

            # Calculate duration
            duration = "N/A"
            if run.get("created_at") and run.get("completed_at"):
                try:
                    # Handle both timezone-aware and naive dates for start time
                    created_str = run["created_at"]
                    if "Z" in created_str or "+" in created_str or "-" in created_str[-6:]:
                        start = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    else:
                        start = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)

                    # Handle both timezone-aware and naive dates for end time
                    completed_str = run["completed_at"]
                    if "Z" in completed_str or "+" in completed_str or "-" in completed_str[-6:]:
                        end = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
                    else:
                        end = datetime.fromisoformat(completed_str).replace(tzinfo=timezone.utc)
                    duration_delta = end - start
                    duration = str(duration_delta).split(".")[0]
                except Exception:  # noqa: S110
                    pass

            created = run.get("created_at", "")[:19] if run.get("created_at") else ""

            # Get rating and display as number for compact table
            rating = run.get("rating")
            rating_display = str(rating) if rating else "-"

            # Updated columns: Run ID, Status, Run Type, Duration, Rating, Created
            table_data.append([run_id, status, model_type, duration, rating_display, created])

        # Build statistics
        completed_count = sum(1 for r in filtered_runs if r.get("status") == "completed")
        running_count = sum(1 for r in filtered_runs if r.get("status") == "running")
        failed_count = sum(1 for r in filtered_runs if r.get("status") == "failed")

        stats = f"""
        **Total Matching:** {total_filtered} (showing {len(filtered_runs)})
        **Completed:** {completed_count}
        **Running:** {running_count}
        **Failed:** {failed_count}
        """

        logger.info(
            "Runs data loaded: {} total, {} shown, {} gallery items",
            total_filtered,
            len(filtered_runs),
            len(gallery_data),
        )

        # Return gallery data, table data and stats
        return gallery_data, table_data, stats

    except Exception as e:
        import traceback

        logger.error("Error loading runs data: {}\n{}", str(e), traceback.format_exc())
        # Return empty but properly formatted data
        empty_table = {
            "headers": ["Run ID", "Status", "Prompt ID", "Type", "Duration", "Rating", "Created"],
            "data": [],
        }
        return [], empty_table, "Error loading data"


def on_runs_gallery_select(evt: gr.SelectData):
    """Handle selection of a run from the gallery."""
    try:
        logger.info("on_runs_gallery_select called - evt: {}", evt)

        if evt is None:
            logger.warning("No evt, hiding details")
            return [gr.update(visible=False)] + [gr.update()] * 16

        # The label now contains only rating and run ID in format "★★★☆☆||full_run_id"
        label = evt.value.get("caption", "") if isinstance(evt.value, dict) else ""
        if not label:
            logger.warning("No label in gallery selection")
            return [gr.update(visible=False)] + [gr.update()] * 16

        # Extract full run ID from label (after the || separator)
        if "||" in label:
            full_run_id = label.split("||")[-1].strip()  # Get the last part which is the run_id
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
            return [gr.update(visible=False)] + [gr.update()] * 17

        # Get full run details
        run_details = ops.get_run(run_id)
        logger.info("Retrieved run_details: {}", bool(run_details))
        if not run_details:
            logger.warning("No run_details found for run_id: {}", run_id)
            return [gr.update(visible=False)] + [gr.update()] * 17

        # Get model type to determine which UI to show
        model_type = run_details.get("model_type", "transfer")
        logger.info("Run model type: {}", model_type)

        # Extract details
        # Get output video - handle both old and new output structures
        outputs = run_details.get("outputs", {})
        output_video = ""

        # New structure: outputs.output_path
        if isinstance(outputs, dict) and "output_path" in outputs:
            output_path = outputs["output_path"]
            if output_path and output_path.endswith(".mp4"):
                # Normalize path separators for cross-platform compatibility
                output_video = str(Path(output_path))

        # Old structure: outputs.files array
        elif isinstance(outputs, dict) and "files" in outputs:
            files = outputs.get("files", [])
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

        # Get rating if present
        rating_value = run_details.get("rating", None)

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
                    # Try indexed version first (from batch inference), then non-indexed (backward compat)
                    indexed_path = Path(
                        f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{control_key}_input_control_0.mp4"
                    )
                    non_indexed_path = Path(
                        f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{control_key}_input_control.mp4"
                    )

                    if indexed_path.exists():
                        logger.debug(
                            "Found indexed control file for {}: {}", control_key, indexed_path
                        )
                        input_videos.append((str(indexed_path), label_with_weight))
                        logger.info(
                            "Using AI-generated {} control (indexed): {}", control_key, indexed_path
                        )
                    elif non_indexed_path.exists():
                        input_videos.append((str(non_indexed_path), label_with_weight))
                        logger.info(
                            "Using AI-generated {} control: {}", control_key, non_indexed_path
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
            "Returning updates - visible: True, run_id: {}, output_video: {}, model_type: {}",
            run_id,
            output_video,
            model_type,
        )

        # Prepare model-specific content based on model type
        # TO ADD NEW MODEL TYPES:
        # 1. Add elif model_type == "your_type"
        # 2. Set content visibility and prepare data
        # 3. Add corresponding UI block in runs_ui.py

        if model_type == "enhance":
            # Enhancement runs: Hide transfer/upscale content, show enhance content
            show_transfer_content = False
            show_enhance_content = True
            show_upscale_content = False

            # Get original and enhanced prompts
            original_prompt = exec_config.get("original_prompt_text", "")
            enhanced_prompt = outputs.get("enhanced_text", "")

            # Build enhancement statistics
            enhancement_model = exec_config.get("model", "Unknown")
            create_new = exec_config.get("create_new", True)
            enhanced_at = outputs.get("enhanced_at", "")

            enhance_stats_text = f"""
            **Model Used:** {enhancement_model}
            **Mode:** {"Created new prompt" if create_new else "Overwrote original"}
            **Enhanced At:** {enhanced_at[:19] if enhanced_at else "Unknown"}
            **Original Length:** {len(original_prompt)} characters
            **Enhanced Length:** {len(enhanced_prompt)} characters
            **Status:** {run_details.get("status", "unknown").title()}
            """

        elif model_type == "upscale":
            # Upscale runs: Hide transfer/enhance content, show upscale content
            show_transfer_content = False
            show_enhance_content = False
            show_upscale_content = True

            # Get original video (source for upscaling)
            source_run_id = exec_config.get("source_run_id", "")
            input_video_source = exec_config.get("input_video_source", "")
            control_weight = exec_config.get("control_weight", 0.5)
            upscale_prompt = exec_config.get("prompt", "")

            # Build upscale statistics
            upscale_stats_text = f"""
            **Control Weight:** {control_weight}
            **Source:** {"Run " + source_run_id[:8] if source_run_id else "Direct video"}
            **Duration:** {duration}
            **Status:** {run_details.get("status", "unknown").title()}
            """

        else:
            # Default/Transfer runs: Show transfer content, hide others
            show_transfer_content = True
            show_enhance_content = False
            show_upscale_content = False

        # Prepare individual video updates for transfer/default content
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

        # Create star button updates based on rating
        star_updates = []
        for i in range(1, 6):
            if rating_value and i <= rating_value:
                star_updates.append(gr.update(value="★", elem_classes=["star-btn", "filled"]))
            else:
                star_updates.append(gr.update(value="☆", elem_classes=["star-btn"]))

        return [
            gr.update(visible=True),  # runs_details_group
            gr.update(value=run_id),  # runs_detail_id (hidden)
            gr.update(value=run_details.get("status", "")),  # runs_detail_status (hidden)
            # Content block visibility
            gr.update(visible=show_transfer_content),  # runs_main_content_transfer
            gr.update(visible=show_enhance_content),  # runs_main_content_enhance
            gr.update(visible=show_upscale_content),  # runs_main_content_upscale
            # Transfer content components
            video_updates[0],  # runs_input_video_1
            video_updates[1],  # runs_input_video_2
            video_updates[2],  # runs_input_video_3
            video_updates[3],  # runs_input_video_4
            gr.update(
                value=output_video if output_video and Path(output_video).exists() else None
            ),  # runs_output_video
            gr.update(value=prompt_text),  # runs_prompt_text
            # Enhancement content components
            gr.update(
                value=original_prompt if model_type == "enhance" else ""
            ),  # runs_original_prompt_enhance
            gr.update(
                value=enhanced_prompt if model_type == "enhance" else ""
            ),  # runs_enhanced_prompt_enhance
            gr.update(
                value=enhance_stats_text if model_type == "enhance" else ""
            ),  # runs_enhance_stats
            # Upscale content components
            gr.update(
                value=output_video
                if model_type == "upscale" and output_video and Path(output_video).exists()
                else None
            ),  # runs_output_video_upscale
            gr.update(
                value=input_video_source if model_type == "upscale" and input_video_source else None
            ),  # runs_original_video_upscale
            gr.update(
                value=upscale_stats_text if model_type == "upscale" else ""
            ),  # runs_upscale_stats
            gr.update(
                value=upscale_prompt if model_type == "upscale" else ""
            ),  # runs_upscale_prompt
            # Info tab components (always the same)
            gr.update(value=run_id),  # runs_info_id
            gr.update(value=run_details.get("prompt_id", "")),  # runs_info_prompt_id
            gr.update(value=run_details.get("status", "")),  # runs_info_status
            gr.update(value=duration),  # runs_info_duration
            gr.update(
                value=model_type
            ),  # runs_info_type (now shows model_type instead of run_type)
            gr.update(value=prompt_name),  # runs_info_prompt_name
            # Star rating buttons
            *star_updates,  # star_1 through star_5
            gr.update(value=rating_value),  # runs_info_rating
            gr.update(value=run_details.get("created_at", "")[:19]),  # runs_info_created
            gr.update(value=run_details.get("completed_at", "")[:19]),  # runs_info_completed
            gr.update(value=output_video if output_video else "Not found"),  # runs_info_output_path
            gr.update(
                value=input_paths_text.strip() if input_paths_text else "No input videos"
            ),  # runs_info_input_paths
            # Parameters and Logs tabs
            gr.update(value=params),  # runs_params_json
            gr.update(value=log_path),  # runs_log_path
            gr.update(value=log_content),  # runs_log_output
        ]

    except Exception as e:
        logger.error("Error selecting run: {}", str(e))
        return [gr.update(visible=False)] + [gr.update()] * 27  # Updated count for star buttons


def load_run_logs(log_path):
    """Load full log file content."""
    try:
        if not log_path:
            logger.debug("No log path specified for load_run_logs")
            return "No log file available"

        if not Path(log_path).exists():
            logger.warning("Log file not found: {}", log_path)
            return "No log file available"

        logger.debug("Loading logs from {}", log_path)
        with open(log_path) as f:
            content = f.read()

        return content
    except Exception as e:
        logger.error("Error reading log file {}: {}", log_path, str(e))
        return f"Error reading log file: {e}"


def save_run_rating(
    run_id, rating_value, status_filter, date_filter, type_filter, search_text, limit
):
    """Save the rating for a run when changed and refresh the runs display."""
    try:
        if not run_id:
            # Just refresh the display without saving
            gallery_data, table_data, stats = load_runs_data(
                status_filter, date_filter, type_filter, search_text, limit
            )
            return gr.update(), gallery_data, table_data, stats

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        if ops:
            # Save the rating
            ops.set_run_rating(run_id, rating_value)
            logger.info("Set rating {} for run {}", rating_value, run_id)

            # Refresh the runs display to show the updated rating in the table
            gallery_data, table_data, stats = load_runs_data(
                status_filter, date_filter, type_filter, search_text, limit
            )

            # Return the rating value and refreshed display data
            return gr.update(value=rating_value), gallery_data, table_data, stats

    except Exception as e:
        logger.error("Error saving rating: {}", str(e))
        # On error, still refresh display but don't change rating
        gallery_data, table_data, stats = load_runs_data(
            status_filter, date_filter, type_filter, search_text, limit
        )
        return gr.update(), gallery_data, table_data, stats


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
        output_dir = preview.get("directory_to_delete", "")
        file_count = preview.get("total_files", 0)
        total_size = preview.get("total_size", "0 B")

        # Build preview text
        preview_text = f"""### ⚠️ Delete Run Confirmation

**Run ID:** {run_info.get("id", "")}
**Status:** {run_info.get("status", "unknown")}
**Created:** {run_info.get("created_at", "")[:19] if run_info.get("created_at") else "unknown"}

**Output Directory:** {output_dir if output_dir else "No output directory"}
**Files:** {file_count} files
**Total Size:** {total_size}

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


def load_runs_for_multiple_prompts(
    prompt_ids, status_filter, date_filter, type_filter, search_text, limit, rating_filter=None
):
    """Load runs data for multiple prompt IDs.

    TODO: Optimize this to use a single query with IN clause in the future.
    Currently makes multiple API calls for simplicity and to avoid backend changes.

    Args:
        prompt_ids: List of prompt IDs to filter by
        status_filter: Status filter to apply
        date_filter: Date range filter
        type_filter: Run type filter
        search_text: Search text
        limit: Maximum number of results

    Returns:
        Tuple of (gallery_data, table_data, stats, prompt_names)
    """
    try:
        if not prompt_ids:
            # No prompts specified, return empty results (not all runs)
            logger.info("No prompt IDs provided for filtering - returning empty results")
            return [], [], "No prompts selected for filtering", []  # Return empty results

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        if not ops:
            logger.warning("CosmosAPI not initialized")
            return [], [], "No data available", []  # Add empty prompt_names for consistency

        # Collect runs from all specified prompts
        all_runs = []
        prompt_map = {}  # Map prompt_id to prompt data for quick lookup

        # Cap at 20 prompts for performance
        prompt_ids = prompt_ids[:20]

        for prompt_id in prompt_ids:
            try:
                # Get prompt data
                prompt = ops.get_prompt(prompt_id)
                if prompt:
                    prompt_map[prompt_id] = prompt

                # Get runs for this prompt - fetch ALL to allow proper filtering
                # Don't apply status filter here, we'll filter everything later
                runs = ops.list_runs(
                    prompt_id=prompt_id,
                    status=None,  # Get all statuses, we'll filter later
                    limit=500,  # Get many runs to filter properly (was implicitly limited before)
                )

                # Add prompt text to each run
                for run in runs:
                    if not run.get("prompt_text"):
                        run["prompt_text"] = prompt.get("prompt_text", "") if prompt else ""

                all_runs.extend(runs)

            except Exception as e:
                logger.error("Error loading runs for prompt {}: {}", prompt_id, str(e))
                continue

        # Sort by created_at descending
        all_runs.sort(key=lambda r: r.get("created_at", ""), reverse=True)

        # Apply date filter
        now = datetime.now(timezone.utc)
        filtered_runs = []

        for run in all_runs:
            # Parse run creation date
            try:
                created_str = run.get("created_at", "")
                if created_str:
                    # Handle both timezone-aware and naive dates
                    if "Z" in created_str or "+" in created_str or "-" in created_str[-6:]:
                        # Has timezone info
                        created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    else:
                        # No timezone info - assume UTC
                        created = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)
                else:
                    created = now
            except Exception:
                created = now

            # Apply date filter
            date_match = False
            if date_filter == "today":
                date_match = created.date() == now.date()
            elif date_filter == "yesterday":
                yesterday = now - timedelta(days=1)
                date_match = created.date() == yesterday.date()
            elif date_filter == "last_7_days":
                seven_days_ago = now - timedelta(days=7)
                date_match = created >= seven_days_ago
            elif date_filter == "last_30_days":
                thirty_days_ago = now - timedelta(days=30)
                date_match = created >= thirty_days_ago
            else:  # all
                date_match = True

            # Apply status filter
            status_match = False
            if status_filter == "all":
                status_match = True
            else:
                run_status = run.get("status", "")
                status_match = status_filter == run_status

            # Apply type filter
            type_match = False
            if type_filter == "all":
                type_match = True
            else:
                model_type = run.get("model_type", "transfer")
                type_match = type_filter == model_type

            # Add to filtered runs if all filters match
            if date_match and type_match and status_match:
                filtered_runs.append(run)

        # Apply text search
        if search_text:
            search_lower = search_text.lower()
            initial_count = len(filtered_runs)
            filtered_runs = [
                run
                for run in filtered_runs
                if search_lower in run.get("id", "").lower()
                or search_lower in run.get("prompt_text", "").lower()
            ]
            logger.debug(
                "Text search '{}' reduced runs from {} to {}",
                search_text,
                initial_count,
                len(filtered_runs),
            )

        # Apply rating filter
        if rating_filter and rating_filter != "all":
            initial_count = len(filtered_runs)
            if rating_filter == "unrated":
                # Filter for runs with no rating
                filtered_runs = [run for run in filtered_runs if not run.get("rating")]
            elif rating_filter == 5:
                # Exact 5 stars
                filtered_runs = [run for run in filtered_runs if run.get("rating") == 5]
            elif isinstance(rating_filter, str) and rating_filter.endswith("+"):
                # Range filters like "4+", "3+", etc.
                min_rating = int(rating_filter[0])
                filtered_runs = [
                    run
                    for run in filtered_runs
                    if run.get("rating") and run.get("rating") >= min_rating
                ]
            logger.debug(
                "Rating filter '{}' reduced runs from {} to {}",
                rating_filter,
                initial_count,
                len(filtered_runs),
            )

        # Store total count before limiting for statistics
        total_filtered = len(filtered_runs)

        # Now limit to the user's Max Results setting
        display_limit = int(limit)
        filtered_runs = filtered_runs[:display_limit]

        # Build gallery data with thumbnails (only completed runs)
        gallery_data = []
        video_paths = []
        completed_runs = [r for r in filtered_runs if r.get("status") == "completed"]
        logger.debug("Processing {} completed runs for gallery", len(completed_runs))

        # First collect all video paths
        missing_videos = []
        for run in filtered_runs:
            if run.get("status") == "completed":
                outputs = run.get("outputs", {})
                output_video = None
                run_id = run.get("id", "unknown")

                # New structure: outputs.output_path
                if isinstance(outputs, dict) and "output_path" in outputs:
                    output_path = outputs["output_path"]
                    logger.debug(
                        "Run {} using new structure with output_path: {}", run_id, output_path
                    )
                    if output_path and output_path.endswith(".mp4"):
                        # Normalize path separators for cross-platform compatibility
                        raw_path = output_path
                        output_video = Path(output_path)
                        if str(raw_path) != str(output_video):
                            logger.debug("Path normalized from '{} to '{}'", raw_path, output_video)
                        if output_video.exists():
                            video_paths.append((output_video, run))
                            logger.debug("Found output video for run {}: {}", run_id, output_video)
                        else:
                            missing_videos.append((run_id, output_path))
                            logger.warning(
                                "Output video not found for run {}: {}", run_id, output_path
                            )

                # Old structure: outputs.files array
                elif isinstance(outputs, dict) and "files" in outputs:
                    files = outputs.get("files", [])
                    logger.debug(
                        "Run {} using old structure with files array ({} files)", run_id, len(files)
                    )
                    for file_path in files:
                        if file_path.endswith("output.mp4"):
                            # Normalize path for Windows
                            output_video = Path(file_path)
                            if output_video.exists():
                                video_paths.append((output_video, run))
                                logger.debug(
                                    "Found output video for run {}: {}", run_id, output_video
                                )
                            else:
                                missing_videos.append((run_id, file_path))
                                logger.warning(
                                    "Output video not found for run {}: {}", run_id, file_path
                                )
                            break
                else:
                    logger.debug("Run {} has no recognized output structure", run_id)

        if missing_videos:
            logger.warning(
                "Missing videos for {} runs: {}", len(missing_videos), missing_videos[:5]
            )  # Log first 5 for brevity

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
                        # Include rating and run ID in label for gallery
                        full_id = run.get("id", "")
                        rating = run.get("rating")
                        if rating:
                            star_display = "★" * rating + "☆" * (5 - rating)
                        else:
                            star_display = "☆☆☆☆☆"  # Show empty stars instead of "No Rating"
                        # Keep run ID hidden with separator for selection
                        # The gallery will display the label but we still need the ID for selection
                        label = f"{star_display}||{full_id}"
                        gallery_data.append((thumb_path, label))
                except Exception as e:
                    logger.debug("Failed to generate thumbnail: {}", str(e))

        # Build table data
        table_data = []
        for run in filtered_runs:
            run_id = run.get("id", "")
            status = run.get("status", "unknown")
            prompt_id = run.get("prompt_id", "")
            model_type = run.get("model_type", "transfer")

            # Calculate duration
            duration = "N/A"
            if run.get("created_at") and run.get("completed_at"):
                try:
                    # Handle both timezone-aware and naive dates for start time
                    created_str = run["created_at"]
                    if "Z" in created_str or "+" in created_str or "-" in created_str[-6:]:
                        start = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    else:
                        start = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)

                    # Handle both timezone-aware and naive dates for end time
                    completed_str = run["completed_at"]
                    if "Z" in completed_str or "+" in completed_str or "-" in completed_str[-6:]:
                        end = datetime.fromisoformat(completed_str.replace("Z", "+00:00"))
                    else:
                        end = datetime.fromisoformat(completed_str).replace(tzinfo=timezone.utc)
                    duration_delta = end - start
                    duration = str(duration_delta).split(".")[0]
                except Exception as e:
                    logger.debug("Failed to calculate duration: {}", str(e))

            created = run.get("created_at", "")[:19] if run.get("created_at") else ""

            # Get rating and display as number for compact table
            rating = run.get("rating")
            rating_display = str(rating) if rating else "-"

            # Updated columns: Run ID, Status, Run Type, Duration, Rating, Created
            table_data.append([run_id, status, model_type, duration, rating_display, created])

        # Build statistics
        stats = f"""
        **Filtering by:** {len(prompt_ids)} prompt(s)
        **Total Matching:** {total_filtered} (showing {len(filtered_runs)})
        **Completed:** {sum(1 for r in filtered_runs if r.get("status") == "completed")}
        **Running:** {sum(1 for r in filtered_runs if r.get("status") == "running")}
        **Failed:** {sum(1 for r in filtered_runs if r.get("status") == "failed")}
        """

        # Build prompt names for filter display
        prompt_names = []
        for pid in prompt_ids:
            # Always use the full prompt ID
            prompt_names.append(pid)

        # Check if we have prompt_ids but no matching runs
        if prompt_ids and len(gallery_data) == 0 and len(table_data) == 0:
            # Had filters but no matches - return empty with appropriate message
            stats = f"No runs found for {len(prompt_ids)} selected prompt(s)"
            logger.info("Filter yielded no results for {} prompts", len(prompt_ids))

        return gallery_data, table_data, stats, prompt_names

    except Exception as e:
        logger.error("Error loading runs for multiple prompts: {}", str(e))
        return [], [], "Error loading runs", []
