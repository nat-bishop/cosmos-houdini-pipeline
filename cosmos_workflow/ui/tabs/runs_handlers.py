#!/usr/bin/env python3
"""Event handlers for Runs tab functionality."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.ui.models.responses import (
    RunDetailsResponse,
    create_empty_run_details_response,
)
from cosmos_workflow.ui.utils import dataframe as df_utils
from cosmos_workflow.ui.utils import video as video_utils
from cosmos_workflow.utils.logging import logger

# Thread pool for parallel thumbnail generation
THUMBNAIL_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def _apply_date_filter(runs: list, date_filter: str) -> list:
    """Apply date filter to runs list.

    Args:
        runs: List of run dictionaries
        date_filter: Date filter type (today, yesterday, last_7_days, last_30_days, all)

    Returns:
        Filtered list of runs
    """
    now = datetime.now(timezone.utc)
    filtered_runs = []

    for run in runs:
        # Parse run creation date
        try:
            created_str = run.get("created_at", "")
            if created_str:
                # Handle both timezone-aware and naive dates
                if "Z" in created_str or "+" in created_str or "-" in created_str[-6:]:
                    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                else:
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

        if date_match:
            filtered_runs.append(run)

    return filtered_runs


def _apply_run_filters(
    runs: list, type_filter: str, search_text: str, rating_filter: str | None = None
) -> list:
    """Apply type, search, and rating filters to runs.

    Args:
        runs: List of run dictionaries
        type_filter: Model type filter
        search_text: Text to search in run ID and prompt text
        rating_filter: Rating filter (unrated, 5, 4+, 3+, etc.)

    Returns:
        Filtered list of runs
    """
    filtered_runs = runs.copy()

    # Apply type filter
    if type_filter != "all":
        filtered_runs = [
            run for run in filtered_runs if run.get("model_type", "transfer") == type_filter
        ]

    # Apply text search
    if search_text:
        search_lower = search_text.lower()
        filtered_runs = [
            run
            for run in filtered_runs
            if search_lower in run.get("id", "").lower()
            or search_lower in run.get("prompt_text", "").lower()
        ]

    # Apply rating filter
    if rating_filter and rating_filter != "all":
        if rating_filter == "unrated":
            filtered_runs = [run for run in filtered_runs if not run.get("rating")]
        elif rating_filter == "5":
            filtered_runs = [run for run in filtered_runs if run.get("rating") == 5]
        elif isinstance(rating_filter, str) and rating_filter.endswith("+"):
            min_rating = int(rating_filter[0])
            filtered_runs = [
                run
                for run in filtered_runs
                if run.get("rating") and run.get("rating") >= min_rating
            ]

    return filtered_runs


def _build_gallery_data(runs: list, limit: int = 50) -> list:
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


def _build_runs_table_data(runs: list) -> list:
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
            except Exception:
                pass

        created = run.get("created_at", "")[:19] if run.get("created_at") else ""
        rating = run.get("rating")
        rating_display = str(rating) if rating else "-"

        table_data.append([run_id, status, model_type, duration, rating_display, created])

    return table_data


def _calculate_runs_statistics(runs: list, total_count: int) -> str:
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


def load_runs_data(status_filter, date_filter, type_filter, search_text, limit, rating_filter=None):
    """Load runs data for table with filtering and populate video grid.

    Simplified version using helper functions.
    """
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

        # Query runs from database
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

        # Apply filters using helpers
        filtered_runs = _apply_date_filter(all_runs, date_filter)
        filtered_runs = _apply_run_filters(filtered_runs, type_filter, search_text, rating_filter)

        # Store total count before limiting
        total_filtered = len(filtered_runs)

        # Limit to the user's Max Results setting
        display_limit = int(limit)
        filtered_runs = filtered_runs[:display_limit]

        # Build gallery data using helper
        gallery_data = _build_gallery_data(filtered_runs, limit=50)

        # Build table data using helper
        table_data = _build_runs_table_data(filtered_runs)

        # Calculate statistics using helper
        stats = _calculate_runs_statistics(filtered_runs, total_filtered)

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


def _extract_run_metadata(run_details: dict) -> dict:
    """Extract basic metadata from run details.

    Args:
        run_details: Raw run details from API

    Returns:
        Dictionary with duration, dates, status, etc.
    """
    metadata = {
        "duration": "N/A",
        "created_at": run_details.get("created_at", ""),
        "completed_at": run_details.get("completed_at", ""),
        "status": run_details.get("status", "unknown"),
        "log_path": run_details.get("log_path", ""),
    }

    # Calculate duration
    if metadata["created_at"] and metadata["completed_at"]:
        try:
            start = datetime.fromisoformat(metadata["created_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(metadata["completed_at"].replace("Z", "+00:00"))
            duration_delta = end - start
            metadata["duration"] = str(duration_delta).split(".")[0]
        except Exception:  # noqa: S110
            pass

    return metadata


def _resolve_video_paths(outputs: dict, run_id: str, ops) -> tuple:
    """Resolve output and upscaled video paths from run outputs.

    Args:
        outputs: Outputs dictionary from run details
        run_id: Run ID for checking upscaled version
        ops: CosmosAPI instance

    Returns:
        Tuple of (output_video_path, upscaled_video_path, show_upscaled_tab)
    """
    output_video = ""

    # New structure: outputs.output_path
    if isinstance(outputs, dict) and "output_path" in outputs:
        output_path = outputs["output_path"]
        if output_path and output_path.endswith(".mp4"):
            output_video = str(Path(output_path))

    # Old structure: outputs.files array
    elif isinstance(outputs, dict) and "files" in outputs:
        files = outputs.get("files", [])
        for file_path in files:
            if file_path.endswith("output.mp4"):
                output_video = str(Path(file_path))
                break

    # Check for upscaled version
    upscaled_video = None
    show_upscaled_tab = False

    if ops and run_id:
        upscaled_run = ops.get_upscaled_run(run_id)
        if upscaled_run and upscaled_run.get("status") == "completed":
            upscaled_outputs = upscaled_run.get("outputs", {})
            if isinstance(upscaled_outputs, dict) and "output_path" in upscaled_outputs:
                upscaled_path = upscaled_outputs["output_path"]
                if (
                    upscaled_path
                    and upscaled_path.endswith(".mp4")
                    and Path(upscaled_path).exists()
                ):
                    upscaled_video = str(Path(upscaled_path))
                    show_upscaled_tab = True
                    logger.info("Found upscaled video for run {}: {}", run_id, upscaled_video)

    return output_video, upscaled_video, show_upscaled_tab


def _load_spec_and_weights(run_id: str) -> dict:
    """Load spec.json and extract control weights.

    Args:
        run_id: Run ID to locate spec.json

    Returns:
        Dictionary with spec data or empty dict if not found
    """
    spec_data = {}
    if run_id:
        spec_path = Path(f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/inputs/spec.json")
        if spec_path.exists():
            try:
                import json

                with open(spec_path) as f:
                    spec_data = json.load(f)
                logger.info("Loaded spec.json for run {}", run_id)
            except Exception as e:
                logger.warning("Failed to load spec.json: {}", str(e))
    return spec_data


def _build_input_gallery(spec_data: dict, prompt_inputs: dict, run_id: str) -> tuple:
    """Build input video gallery from spec data and prompt inputs.

    Args:
        spec_data: Loaded spec.json data
        prompt_inputs: Input paths from prompt
        run_id: Run ID for locating generated controls

    Returns:
        Tuple of (input_videos list, control_weights dict)
    """
    input_videos = []
    control_weights = {"vis": 0, "edge": 0, "depth": 0, "seg": 0}

    if spec_data:
        # Add main video from prompt if it exists
        if prompt_inputs.get("video"):
            path = Path(prompt_inputs["video"])
            if path.exists():
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
                label_with_weight = f"{control_label} (Weight: {weight})"

                # First try prompt's input for this control
                if prompt_inputs.get(control_key):
                    control_path = Path(prompt_inputs[control_key])
                    if control_path.exists():
                        input_videos.append((str(control_path), label_with_weight))
                        continue

                # If no prompt input, check for AI-generated control
                indexed_path = Path(
                    f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{control_key}_input_control_0.mp4"
                )
                non_indexed_path = Path(
                    f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{control_key}_input_control.mp4"
                )

                if indexed_path.exists():
                    input_videos.append((str(indexed_path), label_with_weight))
                elif non_indexed_path.exists():
                    input_videos.append((str(non_indexed_path), label_with_weight))

    # Fallback if no spec.json - use prompt inputs with default weights
    elif prompt_inputs:
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
                    if key != "video":
                        label = f"{label} (Weight: {default_weight})"
                    input_videos.append((str(path), label))
                    if key == "video":
                        control_weights["vis"] = default_weight
                    else:
                        control_weights[key] = default_weight

    return input_videos, control_weights


def _prepare_transfer_ui_data(run_details: dict, exec_config: dict, outputs: dict) -> dict:
    """Prepare UI data for transfer model runs.

    Args:
        run_details: Full run details
        exec_config: Execution configuration
        outputs: Run outputs

    Returns:
        Dictionary with transfer-specific UI data
    """
    return {
        "show_transfer_content": True,
        "show_enhance_content": False,
        "show_upscale_content": False,
    }


def _prepare_enhance_ui_data(run_details: dict, exec_config: dict, outputs: dict) -> dict:
    """Prepare UI data for enhance model runs.

    Args:
        run_details: Full run details
        exec_config: Execution configuration
        outputs: Run outputs

    Returns:
        Dictionary with enhance-specific UI data
    """
    original_prompt = exec_config.get("original_prompt_text", "")
    enhanced_prompt = outputs.get("enhanced_text", "")
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

    return {
        "show_transfer_content": False,
        "show_enhance_content": True,
        "show_upscale_content": False,
        "original_prompt": original_prompt,
        "enhanced_prompt": enhanced_prompt,
        "enhance_stats_text": enhance_stats_text,
    }


def _prepare_upscale_ui_data(run_details: dict, exec_config: dict, outputs: dict) -> dict:
    """Prepare UI data for upscale model runs.

    Args:
        run_details: Full run details
        exec_config: Execution configuration
        outputs: Run outputs

    Returns:
        Dictionary with upscale-specific UI data
    """
    source_run_id = exec_config.get("source_run_id", "")
    input_video_source = exec_config.get("input_video_source", "")
    control_weight = exec_config.get("control_weight", 0.5)
    upscale_prompt = exec_config.get("prompt", "")

    # Get duration from metadata helper
    metadata = _extract_run_metadata(run_details)

    upscale_stats_text = f"""
    **Control Weight:** {control_weight}
    **Source:** {"Run " + source_run_id[:8] if source_run_id else "Direct video"}
    **Duration:** {metadata["duration"]}
    **Status:** {run_details.get("status", "unknown").title()}
    """

    return {
        "show_transfer_content": False,
        "show_enhance_content": False,
        "show_upscale_content": True,
        "input_video_source": input_video_source,
        "upscale_prompt": upscale_prompt,
        "upscale_stats_text": upscale_stats_text,
    }


def _read_log_content(log_path: str, lines: int = 15) -> str:
    """Read last N lines from log file.

    Args:
        log_path: Path to log file
        lines: Number of lines to read from end

    Returns:
        Log content or error message
    """
    if not log_path or not Path(log_path).exists():
        return ""

    try:
        with open(log_path) as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception:
        return "Error reading log file"


def on_runs_gallery_select(evt: gr.SelectData):
    """Handle selection of a run from the gallery."""
    try:
        logger.info("on_runs_gallery_select called - evt: {}", evt)

        if evt is None:
            logger.warning("No evt, hiding details")
            # Return empty response with all fields hidden/empty
            return list(create_empty_run_details_response())

        # The label now contains only rating and run ID in format "★★★☆☆||full_run_id"
        label = evt.value.get("caption", "") if isinstance(evt.value, dict) else ""
        if not label:
            logger.warning("No label in gallery selection")
            # Return empty response with all fields hidden/empty
            return list(create_empty_run_details_response())

        # Extract full run ID from label (after the || separator)
        if "||" in label:
            full_run_id = label.split("||")[-1].strip()  # Get the last part which is the run_id
            # Remove any upscale indicator like [4K ⬆️]
            if " [4K" in full_run_id:
                full_run_id = full_run_id.split(" [4K")[0].strip()
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
        # Return empty response with all fields hidden/empty
        return list(create_empty_run_details_response())

    except Exception as e:
        logger.error("Error selecting from gallery: {}", str(e))
        # Return empty response on error
        return list(create_empty_run_details_response())


def on_runs_table_select(table_data, evt: gr.SelectData):
    """Handle selection of a run from the table.

    Refactored version that uses helper functions for better maintainability.
    """
    try:
        logger.info(
            "on_runs_table_select called - evt: {}, table_data type: {}", evt, type(table_data)
        )

        # Early return for no selection
        if evt is None or table_data is None:
            logger.warning("No evt or table_data, hiding details")
            return list(create_empty_run_details_response())

        # Get selected row index
        row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index
        logger.info("Selected row index: {}", row_idx)

        # Extract run ID from table
        run_id = df_utils.get_cell_value(table_data, row_idx, 0, default=None)
        logger.info("Extracted run_id: {}", run_id)

        if not run_id:
            logger.warning("No run_id found in selected row")
            return list(create_empty_run_details_response())

        # Get run details from API
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()

        run_details = ops.get_run(run_id)
        if not run_details:
            logger.warning("No run_details found for run_id: {}", run_id)
            return list(create_empty_run_details_response())

        # Extract model type and basic info
        model_type = run_details.get("model_type", "transfer")
        prompt_id = run_details.get("prompt_id", "")
        prompt_text = run_details.get("prompt_text", "")
        logger.info("Run model type: {}, prompt_id: {}", model_type, prompt_id)

        # Use helper to extract metadata
        metadata = _extract_run_metadata(run_details)
        duration = metadata["duration"]
        log_path = metadata["log_path"]

        # Use helper to resolve video paths
        outputs = run_details.get("outputs", {})
        video_paths, output_gallery, output_video = _resolve_video_paths(outputs, run_id, ops)
        logger.info("Output video path: {}", output_video)

        # Get prompt text if not in run details
        if not prompt_text and prompt_id:
            prompt = ops.get_prompt(prompt_id)
            if prompt:
                prompt_text = prompt.get("prompt_text", "")

        # Get rating and prompt info
        rating_value = run_details.get("rating", None)
        prompt_name = ""

        # Check for upscaled version if this is a transfer run
        upscaled_video = None
        show_upscaled_tab = False
        if model_type == "transfer":
            upscaled_run = ops.get_upscaled_run(run_id)
            if upscaled_run and upscaled_run.get("status") == "completed":
                upscaled_outputs = upscaled_run.get("outputs", {})
                if isinstance(upscaled_outputs, dict) and "output_path" in upscaled_outputs:
                    upscaled_path = upscaled_outputs["output_path"]
                    if (
                        upscaled_path
                        and upscaled_path.endswith(".mp4")
                        and Path(upscaled_path).exists()
                    ):
                        upscaled_video = str(Path(upscaled_path))
                        show_upscaled_tab = True
                        logger.info("Found upscaled video: {}", upscaled_video)

        # Use helper to load spec and weights
        spec_data = _load_spec_and_weights(run_id)

        # Get prompt inputs if available
        prompt_inputs = {}
        if prompt_id:
            prompt = ops.get_prompt(prompt_id)
            if prompt:
                prompt_inputs = prompt.get("inputs", {})
                prompt_params = prompt.get("parameters", {})
                prompt_name = prompt_params.get("name", "")

        # Use helper to build input gallery
        input_videos, control_weights = _build_input_gallery(spec_data, prompt_inputs, run_id)

        # Get execution config and parameters
        exec_config = run_details.get("execution_config", {})
        if not any(control_weights.values()):
            # No weights from spec.json, try execution_config
            weights = exec_config.get("weights", {})
            control_weights = weights if weights else control_weights

        params = exec_config  # Use entire execution_config as parameters

        # Use helper to read log content
        log_content = _read_log_content(log_path) if log_path else "No log file available"

        logger.info(
            "Returning updates - visible: True, run_id: {}, output_video: {}, model_type: {}",
            run_id,
            output_video,
            model_type,
        )

        # Prepare model-specific content using helpers
        if model_type == "enhance":
            enhance_data = _prepare_enhance_ui_data(run_details, exec_config, outputs)
            show_transfer_content = False
            show_enhance_content = True
            show_upscale_content = False
            original_prompt = enhance_data["original_prompt"]
            enhanced_prompt = enhance_data["enhanced_prompt"]
            enhance_stats_text = enhance_data["enhance_stats_text"]
        elif model_type == "upscale":
            upscale_data = _prepare_upscale_ui_data(run_details, exec_config, outputs)
            show_transfer_content = False
            show_enhance_content = False
            show_upscale_content = True
            input_video_source = upscale_data["input_video_source"]
            upscale_prompt = upscale_data["upscale_prompt"]
            upscale_stats_text = upscale_data["upscale_stats_text"]
        else:
            # Default/Transfer runs
            show_transfer_content = True
            show_enhance_content = False
            show_upscale_content = False
            # Initialize enhance/upscale variables for default case
            original_prompt = ""
            enhanced_prompt = ""
            enhance_stats_text = ""
            input_video_source = ""
            upscale_prompt = ""
            upscale_stats_text = ""

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

        # Build response using NamedTuple for better maintainability
        response = RunDetailsResponse(
            # Main visibility controls
            runs_details_group=gr.update(visible=True),
            runs_detail_id=gr.update(value=run_id),
            runs_detail_status=gr.update(value=run_details.get("status", "")),
            # Content block visibility
            runs_main_content_transfer=gr.update(visible=show_transfer_content),
            runs_main_content_enhance=gr.update(visible=show_enhance_content),
            runs_main_content_upscale=gr.update(visible=show_upscale_content),
            # Transfer content components
            runs_input_video_1=video_updates[0],
            runs_input_video_2=video_updates[1],
            runs_input_video_3=video_updates[2],
            runs_input_video_4=video_updates[3],
            runs_output_video=gr.update(
                value=output_video if output_video and Path(output_video).exists() else None
            ),
            runs_prompt_text=gr.update(value=prompt_text),
            # Enhancement content components
            runs_original_prompt_enhance=gr.update(
                value=original_prompt if model_type == "enhance" else ""
            ),
            runs_enhanced_prompt_enhance=gr.update(
                value=enhanced_prompt if model_type == "enhance" else ""
            ),
            runs_enhance_stats=gr.update(
                value=enhance_stats_text if model_type == "enhance" else ""
            ),
            # Upscale content components
            runs_output_video_upscale=gr.update(
                value=output_video
                if model_type == "upscale" and output_video and Path(output_video).exists()
                else None
            ),
            runs_original_video_upscale=gr.update(
                value=input_video_source if model_type == "upscale" and input_video_source else None
            ),
            runs_upscale_stats=gr.update(
                value=upscale_stats_text if model_type == "upscale" else ""
            ),
            runs_upscale_prompt=gr.update(value=upscale_prompt if model_type == "upscale" else ""),
            # Info tab components
            runs_info_id=gr.update(value=run_id),
            runs_info_prompt_id=gr.update(value=run_details.get("prompt_id", "")),
            runs_info_status=gr.update(value=run_details.get("status", "")),
            runs_info_duration=gr.update(value=duration),
            runs_info_type=gr.update(value=model_type),
            runs_info_prompt_name=gr.update(value=prompt_name),
            # Star rating buttons
            star_1=star_updates[0],
            star_2=star_updates[1],
            star_3=star_updates[2],
            star_4=star_updates[3],
            star_5=star_updates[4],
            # Additional info fields
            runs_info_rating=gr.update(value=rating_value),
            runs_info_created=gr.update(value=run_details.get("created_at", "")[:19]),
            runs_info_completed=gr.update(value=run_details.get("completed_at", "")[:19]),
            runs_info_output_path=gr.update(value=output_video if output_video else "Not found"),
            runs_info_input_paths=gr.update(
                value=input_paths_text.strip() if input_paths_text else "No input videos"
            ),
            # Parameters and Logs tabs
            runs_params_json=gr.update(value=params),
            runs_log_path=gr.update(value=log_path),
            runs_log_output=gr.update(value=log_content),
            # Action buttons
            runs_upscale_selected_btn=gr.update(
                visible=run_details.get("status") == "completed"
                and run_details.get("model_type") == "transfer"
                and not ops.get_upscaled_run(run_id)
            ),
            # Selected run tracking
            runs_selected_id=gr.update(value=run_id),
            runs_selected_info=gr.update(value=f"Selected: {run_id[:12]}..."),
            # Upscaled output components
            runs_output_video_upscaled=gr.update(
                value=upscaled_video if upscaled_video and Path(upscaled_video).exists() else None
            ),
            runs_upscaled_tab=gr.update(visible=show_upscaled_tab),
        )

        # Return as list to maintain compatibility with Gradio
        return list(response)

    except Exception as e:
        logger.error("Error selecting run: {}", str(e))
        # Return empty response on error
        return list(create_empty_run_details_response())


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
        row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index

        # Extract run ID from table using utility
        run_id = df_utils.get_cell_value(table_data, row_idx, 0, default="")

        if run_id:
            return f"Selected: {run_id[:8]}...", run_id
        return "No run selected", ""
    except Exception:
        return "No run selected", ""


def load_runs_for_multiple_prompts(
    prompt_ids, status_filter, date_filter, type_filter, search_text, limit, rating_filter=None
):
    """Load runs data for multiple prompt IDs.

    This function collects runs from multiple prompts and uses the same
    filtering and display logic as load_runs_data.

    Args:
        prompt_ids: List of prompt IDs to filter by
        status_filter: Status filter to apply
        date_filter: Date range filter
        type_filter: Run type filter
        search_text: Search text
        limit: Maximum number of results
        rating_filter: Rating filter to apply

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

        # Apply all filters using helper functions
        filtered_runs = _apply_date_filter(all_runs, date_filter)

        # Apply status filter
        if status_filter != "all":
            filtered_runs = [r for r in filtered_runs if r.get("status") == status_filter]

        # Apply additional filters using helper
        filtered_runs = _apply_run_filters(filtered_runs, type_filter, search_text, rating_filter)

        # Store total count before limiting
        total_filtered = len(filtered_runs)

        # Limit to display count
        display_limit = int(limit)
        filtered_runs = filtered_runs[:display_limit]

        # Build gallery data using helper
        gallery_data = _build_gallery_data(filtered_runs, limit=50)

        # Build table data using helper
        table_data = _build_runs_table_data(filtered_runs)

        # Build statistics for multiple prompts
        stats = f"""
        **Filtering by:** {len(prompt_ids)} prompt(s)
        **Total Matching:** {total_filtered} (showing {len(filtered_runs)})
        **Completed:** {sum(1 for r in filtered_runs if r.get("status") == "completed")}
        **Running:** {sum(1 for r in filtered_runs if r.get("status") == "running")}
        **Failed:** {sum(1 for r in filtered_runs if r.get("status") == "failed")}
        """

        # Build prompt names list
        prompt_names = list(prompt_ids)

        # Check for empty results
        if prompt_ids and len(gallery_data) == 0 and len(table_data) == 0:
            stats = f"No runs found for {len(prompt_ids)} selected prompt(s)"
            logger.info("Filter yielded no results for {} prompts", len(prompt_ids))

        return gallery_data, table_data, stats, prompt_names

    except Exception as e:
        logger.error("Error loading runs for multiple prompts: {}", str(e))
        return [], [], "Error loading runs", []


# ========== Upscale Event Handlers ==========


def show_upscale_dialog(run_id):
    """Show the upscale configuration dialog.

    Args:
        run_id: The run ID to upscale

    Returns:
        Tuple of (dialog visibility, preview text, hidden run_id)
    """
    if not run_id:
        return gr.update(visible=False), gr.update(), gr.update()

    try:
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        run = ops.get_run(run_id)

        if not run:
            return gr.update(visible=False), gr.update(), gr.update()

        # Check if run can be upscaled
        if run["status"] != "completed":
            return (
                gr.update(visible=False),
                gr.update(),
                gr.update(
                    value=f"Run must be completed to upscale. Current status: {run['status']}"
                ),
            )

        if run.get("model_type") == "upscale":
            return (
                gr.update(visible=False),
                gr.update(),
                gr.update(value="Cannot upscale an already upscaled run"),
            )

        if run.get("model_type") != "transfer":
            return (
                gr.update(visible=False),
                gr.update(),
                gr.update(
                    value=f"Can only upscale inference runs, not {run.get('model_type')} runs"
                ),
            )

        # Check if already has upscaled version
        upscaled = ops.get_upscaled_run(run_id)
        if upscaled:
            return (
                gr.update(visible=False),
                gr.update(),
                gr.update(value=f"This run already has an upscaled version: {upscaled['id']}"),
            )

        preview_text = f"""
        **Run ID:** {run_id}
        **Status:** {run["status"]}
        **Type:** {run.get("model_type", "transfer")}

        This will create a new upscaling run that processes the output video to 4K resolution.
        The upscaling process typically takes 2-3 minutes.
        """

        return (
            gr.update(visible=True),  # runs_upscale_dialog
            gr.update(value=preview_text),  # runs_upscale_preview
            gr.update(value=run_id),  # runs_upscale_id_hidden
        )

    except Exception as e:
        logger.error("Error showing upscale dialog: {}", e)
        return gr.update(visible=False), gr.update(), gr.update()


def execute_upscale(run_id, control_weight, prompt_text):
    """Execute the upscaling operation via queue.

    Args:
        run_id: Run ID to upscale
        control_weight: Control weight (0.0-1.0)
        prompt_text: Optional guiding prompt

    Returns:
        Tuple of (dialog visibility, info message)
    """
    if not run_id:
        return gr.update(visible=False), gr.update(value="No run selected")

    try:
        from cosmos_workflow.database import init_database
        from cosmos_workflow.services.simple_queue_service import SimplifiedQueueService

        # Initialize queue service
        db = init_database("outputs/cosmos.db")
        queue_service = SimplifiedQueueService(db_connection=db)

        # Build job configuration
        config = {
            "run_id": run_id,  # Use correct parameter name
            "control_weight": control_weight,
        }
        if prompt_text and prompt_text.strip():
            config["prompt"] = prompt_text.strip()

        # Add to queue
        job_id = queue_service.add_job(
            prompt_ids=[],  # Upscaling doesn't need prompt_ids
            job_type="upscale",
            config=config,
        )

        logger.info("Added upscale job {} for run {}", job_id, run_id)

        return (
            gr.update(visible=False),  # Hide dialog
            gr.update(value=f"✅ Upscaling job queued (Job ID: {job_id})"),
        )

    except Exception as e:
        logger.error("Error starting upscale: {}", e)
        return (gr.update(visible=True), gr.update(value=f"❌ Error: {e!s}"))


def cancel_upscale():
    """Cancel the upscale dialog."""
    return gr.update(visible=False)


def load_runs_data_with_version_filter(
    status_filter, date_filter, type_filter, search_text, limit, rating_filter, version_filter
):
    """Load runs data with version filtering support.

    This modifies the initial query to handle version filtering at the database level,
    avoiding inefficient post-processing with multiple API calls.
    """
    try:
        logger.debug(
            "Loading runs data with filters: status={}, date={}, type={}, search={}, limit={}, rating={}, version={}",
            status_filter,
            date_filter,
            type_filter,
            search_text,
            limit,
            rating_filter,
            version_filter,
        )

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()

        if not ops:
            logger.warning("CosmosAPI not initialized")
            return [], [], "No data available"

        # Query with version filter applied at database level
        max_search_limit = 500
        all_runs = ops.list_runs(
            status=None if status_filter == "all" else status_filter,
            limit=max_search_limit,
            version_filter=version_filter,  # Pass version filter to SQL query
        )
        logger.info(
            "Fetched {} runs from database with version_filter={}", len(all_runs), version_filter
        )

        # Continue with the rest of the processing from load_runs_data
        # Enrich runs with prompt text and check for upscaled versions
        for run in all_runs:
            if not run.get("prompt_text") and run.get("prompt_id"):
                prompt = ops.get_prompt(run["prompt_id"])
                if prompt:
                    run["prompt_text"] = prompt.get("prompt_text", "")

            # Check if this transfer run has an upscaled version
            if run.get("model_type") == "transfer":
                upscaled_run = ops.get_upscaled_run(run["id"])
                if upscaled_run and upscaled_run.get("status") == "completed":
                    run["has_upscaled"] = True

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
                model_type = run.get("model_type", "transfer")
                type_match = type_filter == model_type

            # Add to filtered runs if both filters match
            if date_match and type_match:
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

        # Apply rating filter
        if rating_filter and rating_filter != "all":
            if rating_filter == "unrated":
                filtered_runs = [run for run in filtered_runs if not run.get("rating")]
            elif rating_filter == "5":
                filtered_runs = [run for run in filtered_runs if run.get("rating") == 5]
            elif isinstance(rating_filter, str) and rating_filter.endswith("+"):
                min_rating = int(rating_filter[0])
                filtered_runs = [
                    run
                    for run in filtered_runs
                    if run.get("rating") and run.get("rating") >= min_rating
                ]

        # Store total count before limiting for statistics
        total_filtered = len(filtered_runs)

        # Now limit to the user's Max Results setting
        display_limit = int(limit)
        filtered_runs = filtered_runs[:display_limit]

        # Build gallery and table data
        gallery_data = []
        video_paths = []
        completed_runs = [r for r in filtered_runs if r.get("status") == "completed"]

        for run in completed_runs:
            outputs = run.get("outputs", {})
            output_video = None
            run_id = run.get("id", "unknown")

            if isinstance(outputs, dict) and "output_path" in outputs:
                output_path = outputs["output_path"]
                if output_path and output_path.endswith(".mp4"):
                    output_video = Path(output_path)
                    if output_video.exists():
                        video_paths.append((output_video, run))

        # Generate thumbnails
        futures = []
        for video_path, _run in video_paths[:display_limit]:
            futures.append(
                THUMBNAIL_EXECUTOR.submit(video_utils.generate_thumbnail_fast, video_path)
            )

        # Collect results
        for i, future in enumerate(futures):
            try:
                thumb_path = future.result(timeout=3)
                video_path, run = video_paths[i]
                run_id = run.get("id", "unknown")
                rating = run.get("rating", 0) or 0
                rating_str = "★" * rating + "☆" * (5 - rating)

                # Add upscale indicator if this run has an upscaled version
                label = f"{rating_str}||{run_id}"
                if run.get("has_upscaled"):
                    label += " [4K ⬆️]"

                if thumb_path:
                    gallery_data.append((thumb_path, label))
                else:
                    gallery_data.append((str(video_path), label))
            except Exception:
                video_path, run = video_paths[i]
                run_id = run.get("id", "unknown")
                rating = run.get("rating", 0) or 0
                rating_str = "★" * rating + "☆" * (5 - rating)
                label = f"{rating_str}||{run_id}"
                if run.get("has_upscaled"):
                    label += " [4K ⬆️]"
                gallery_data.append((str(video_path), label))

        # Build table data
        table_data = []
        for run in filtered_runs:
            run_id = run.get("id", "")
            status_icon = {
                "completed": "✅",
                "running": "🔄",
                "failed": "❌",
                "pending": "⏳",
                "cancelled": "🚫",
            }.get(run.get("status", ""), "❓")

            model_icon = {"transfer": "🎬", "enhance": "✨", "upscale": "⬆️"}.get(
                run.get("model_type", "transfer"), "🎬"
            )

            prompt_preview = run.get("prompt_text", "")[:50]
            if len(run.get("prompt_text", "")) > 50:
                prompt_preview += "..."

            rating = run.get("rating", 0) or 0
            rating_str = "★" * rating + "☆" * (5 - rating) if rating > 0 else ""

            table_data.append(
                [
                    run_id,
                    f"{status_icon} {run.get('status', '')}",
                    f"{model_icon} {run.get('model_type', 'transfer')}",
                    prompt_preview,
                    rating_str,
                    run.get("created_at", "")[:19],
                ]
            )

        # Calculate statistics
        status_counts = {}
        for run in filtered_runs:
            status = run.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        stats_text = (
            f"Total Matching: {total_filtered} (showing {len(filtered_runs)}) | "
            f"Completed: {status_counts.get('completed', 0)} | "
            f"Running: {status_counts.get('running', 0)} | "
            f"Failed: {status_counts.get('failed', 0)}"
        )

        return gallery_data, table_data, stats_text

    except Exception as e:
        logger.error("Error loading runs data: {}", e, exc_info=True)
        return [], [], "Error loading data"
