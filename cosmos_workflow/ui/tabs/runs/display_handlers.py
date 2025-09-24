"""Display handlers for runs gallery and table selection.

This module handles user interactions with the runs display components,
including gallery selection, table selection, and selection info updates.
"""

import re
from pathlib import Path
from typing import Any

import gradio as gr

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.ui.models.responses import create_empty_run_details_response

# Import helper functions from new specialized modules
from cosmos_workflow.ui.tabs.runs.model_handlers import (
    prepare_enhance_ui_data as _prepare_enhance_ui_data,
)
from cosmos_workflow.ui.tabs.runs.model_handlers import (
    prepare_transfer_ui_data as _prepare_transfer_ui_data,
)
from cosmos_workflow.ui.tabs.runs.model_handlers import (
    prepare_upscale_ui_data as _prepare_upscale_ui_data,
)
from cosmos_workflow.ui.tabs.runs.run_details import (
    build_input_gallery as _build_input_gallery,
)
from cosmos_workflow.ui.tabs.runs.run_details import (
    extract_run_metadata as _extract_run_metadata,
)
from cosmos_workflow.ui.tabs.runs.run_details import (
    read_log_content as _read_log_content,
)
from cosmos_workflow.ui.tabs.runs.run_details import (
    resolve_video_paths as _resolve_video_paths,
)
from cosmos_workflow.ui.utils import dataframe as df_utils
from cosmos_workflow.utils.logging import logger


def on_runs_gallery_select(evt: gr.SelectData):
    """Handle selection of a run from the gallery.

    Args:
        evt: Gradio SelectData event

    Returns:
        List of values for run details components
    """
    try:
        logger.info("on_runs_gallery_select called - evt: {}", evt)

        if evt is None:
            logger.warning("No evt, hiding details")
            return list(create_empty_run_details_response())

        # The label contains rating and run ID in format "★★★☆☆||full_run_id"
        label = evt.value.get("caption", "") if isinstance(evt.value, dict) else ""
        if not label:
            logger.warning("No label in gallery selection")
            return list(create_empty_run_details_response())

        # Extract full run ID from label (after the || separator)
        if "||" in label:
            full_run_id = label.split("||")[-1].strip()
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
            match = (
                re.search(r"(rs_[a-f0-9]{32})", label)
                or re.search(r"(rs_[a-f0-9]+)\.\.\.", label)
                or re.search(r"(rs_[a-f0-9]{5,8})", label)
            )
            if match:
                run_id_prefix = match.group(1)
                # If it's a shortened ID, we need to find the full one
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
        return list(create_empty_run_details_response())

    except Exception as e:
        logger.error("Error selecting from gallery: {}", str(e))
        return list(create_empty_run_details_response())


def on_runs_table_select(table_data, evt: gr.SelectData):
    """Handle selection of a run from the table.

    Args:
        table_data: The table data (DataFrame or list)
        evt: Gradio SelectData event

    Returns:
        List of values for run details components
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
        ops = CosmosAPI()
        run_details = ops.get_run(run_id)
        if not run_details:
            logger.warning("No run_details found for run_id: {}", run_id)
            return list(create_empty_run_details_response())

        # Process and build the response
        return _build_run_details_response(run_details, ops)

    except Exception as e:
        logger.error("Error selecting from table: {}", str(e))
        return list(create_empty_run_details_response())


def update_runs_selection_info(table_data, evt: gr.SelectData):
    """Update the selection info when a run is selected from the table.

    Args:
        table_data: The table data (DataFrame or list)
        evt: Gradio SelectData event

    Returns:
        Tuple of (visibility, selected_id)
    """
    logger.info("update_runs_selection_info called")

    if evt is None or table_data is None:
        logger.warning("No evt or table_data")
        return gr.update(value="No run selected"), ""

    # Get selected row index
    row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index

    # Extract run ID from table
    run_id = df_utils.get_cell_value(table_data, row_idx, 0, default=None)
    logger.info("Selected run_id: {}", run_id)

    if not run_id:
        logger.warning("No run_id found in selected row")
        return gr.update(value="No run selected"), ""

    # Show the row and update the hidden run_id with selection info
    return gr.update(value=f"**Selected:** {run_id[:8]}..."), run_id


def _build_run_details_response(run_details: dict[str, Any], ops: CosmosAPI) -> list[Any]:
    """Build the complete response for run details display.

    This is a helper function that encapsulates the complex logic
    for preparing all the data needed for run details display.

    Args:
        run_details: The run details from the API
        ops: CosmosAPI instance

    Returns:
        List of values for all run details components
    """
    # Extract model type and basic info
    model_type = run_details.get("model_type", "transfer")
    prompt_id = run_details.get("prompt_id", "")
    prompt_text = run_details.get("prompt_text", "")
    run_id = run_details.get("id", "")

    logger.info("Run model type: {}, prompt_id: {}", model_type, prompt_id)

    # Use helper to extract metadata
    metadata = _extract_run_metadata(run_details)
    log_path = metadata["log_path"]

    # Use helper to resolve video paths
    outputs = run_details.get("outputs", {})
    video_paths, output_gallery, output_video = _resolve_video_paths(outputs, run_id, ops)
    logger.info("Output video path: {}", output_video)

    # Always get prompt name from database - this should never fail
    prompt_name = ""
    if prompt_id:
        prompt = ops.get_prompt(prompt_id)
        if prompt:
            prompt_name = prompt.get("name", "")
            # Also get prompt_text if it's missing from run details
            if not prompt_text:
                prompt_text = prompt.get("prompt_text", "")

            # Error if prompt exists but has no name
            if not prompt_name:
                logger.error("ERROR: Prompt {} exists but has no name field", prompt_id)
                prompt_name = "Not Found"
        else:
            # Error if prompt_id doesn't exist in database
            logger.error("ERROR: Prompt {} not found in database for run {}", prompt_id, run_id)
            prompt_name = "Not Found"
    else:
        # Error if run has no prompt_id
        logger.error("ERROR: Run {} has no prompt_id", run_id)
        prompt_name = "Not Found"

    # Get rating and prompt info (not used in current display)

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
            else:
                logger.info("Upscaled outputs format issue: {}", upscaled_outputs)
        else:
            if upscaled_run:
                logger.info("Upscaled run status: {}", upscaled_run.get("status"))
            else:
                logger.info("No upscaled run found for {}", run_id)

    # Get prompt inputs if available
    prompt_inputs = {}
    if prompt_id:
        prompt = ops.get_prompt(prompt_id)
        if prompt:
            prompt_inputs = prompt.get("inputs", {})

    # Get execution config - our source of truth for control weights
    exec_config = run_details.get("execution_config", {})

    # Build input gallery from execution config
    input_videos, control_weights, video_labels = _build_input_gallery(
        prompt_inputs, run_id, exec_config
    )

    # Get advanced params (currently not displayed but may be needed later)

    # Prepare display data based on model type
    prepared_data = {}
    if model_type == "transfer":
        prepared_data = _prepare_transfer_ui_data(run_details, exec_config, outputs)
    elif model_type == "enhance":
        prepared_data = _prepare_enhance_ui_data(run_details, exec_config, outputs)
    elif model_type == "upscale":
        metadata = _extract_run_metadata(run_details)
        prepared_data = _prepare_upscale_ui_data(
            run_details, exec_config, outputs, metadata["duration"]
        )

    # Get model type info
    model_type = run_details.get("model_type", "transfer")
    status = run_details.get("status", "")

    # Determine which content block should be visible
    show_transfer = model_type == "transfer"
    show_enhance = model_type == "enhance"
    show_upscale = model_type == "upscale"

    logger.info(
        "Content visibility - Transfer: {}, Enhance: {}, Upscale: {}, Upscaled Tab: {}",
        show_transfer,
        show_enhance,
        show_upscale,
        show_upscaled_tab,
    )
    logger.info("Upscaled video path: {}, Output video path: {}", upscaled_video, output_video)

    # Build params display
    params_display = ""
    if exec_config:
        import json

        params_display = json.dumps(exec_config, indent=2)

    # Read log content
    logs_content = _read_log_content(log_path, 50) if log_path else ""

    # Get rating if available
    rating = run_details.get("rating", 0)

    # Return only the components that actually exist in the UI
    # This list must match the runs_output_keys in wiring/runs.py EXACTLY in order
    return [
        # Main visibility controls
        gr.update(visible=True),  # runs_details_group
        run_id,  # runs_detail_id
        status,  # runs_detail_status
        # Content block visibility
        gr.update(visible=show_transfer),  # runs_main_content_transfer
        gr.update(visible=show_enhance),  # runs_main_content_enhance
        gr.update(visible=show_upscale),  # runs_main_content_upscale (ONLY for upscale model runs)
        # Transfer content (input videos with labels)
        gr.update(
            value=input_videos[0] if len(input_videos) > 0 else None,
            label=video_labels[0] if len(video_labels) > 0 else "Video 1",
            visible=len(input_videos) > 0,
        ),  # runs_input_video_1
        gr.update(
            value=input_videos[1] if len(input_videos) > 1 else None,
            label=video_labels[1] if len(video_labels) > 1 else "Video 2",
            visible=len(input_videos) > 1,
        ),  # runs_input_video_2
        gr.update(
            value=input_videos[2] if len(input_videos) > 2 else None,
            label=video_labels[2] if len(video_labels) > 2 else "Video 3",
            visible=len(input_videos) > 2,
        ),  # runs_input_video_3
        gr.update(
            value=input_videos[3] if len(input_videos) > 3 else None,
            label=video_labels[3] if len(video_labels) > 3 else "Video 4",
            visible=len(input_videos) > 3,
        ),  # runs_input_video_4
        gr.update(
            value=output_video if output_video else None, visible=bool(output_video)
        ),  # runs_output_video
        gr.update(
            visible=show_upscaled_tab
        ),  # runs_upscaled_tab - Show tab for transfer runs with upscales
        gr.update(
            value=upscaled_video if show_upscaled_tab else None
        ),  # runs_output_video_upscaled - Upscaled video in tab
        gr.update(value=prompt_text or ""),  # runs_prompt_text
        # Enhancement content
        gr.update(value=prepared_data.get("original_prompt", "")),  # runs_original_prompt_enhance
        gr.update(value=prepared_data.get("enhanced_prompt", "")),  # runs_enhanced_prompt_enhance
        gr.update(value=prepared_data.get("enhance_stats", "")),  # runs_enhance_stats
        # Upscale content (ONLY for upscale model runs, not transfer runs with upscales)
        gr.update(
            value=output_video if show_upscale else None
        ),  # runs_output_video_upscale - This is the upscaled output
        gr.update(
            value=prepared_data.get("original_video", "") if show_upscale else None
        ),  # runs_original_video_upscale - The original before upscaling
        gr.update(value=prepared_data.get("upscale_stats", "")),  # runs_upscale_stats
        gr.update(value=prepared_data.get("upscale_prompt", "")),  # runs_upscale_prompt
        # Info tab components
        gr.update(value=run_id),  # runs_info_id
        gr.update(value=status),  # runs_info_status
        gr.update(value=model_type),  # runs_info_type
        gr.update(value=metadata.get("duration", "")),  # runs_info_timestamp
        gr.update(value=prompt_id or ""),  # runs_info_prompt_id
        gr.update(value=prompt_name or ""),  # runs_info_prompt_name
        # Star rating buttons - update value and variant to show rating
        gr.update(
            value="★" if rating >= 1 else "☆", variant="primary" if rating >= 1 else "secondary"
        ),  # star_1
        gr.update(
            value="★" if rating >= 2 else "☆", variant="primary" if rating >= 2 else "secondary"
        ),  # star_2
        gr.update(
            value="★" if rating >= 3 else "☆", variant="primary" if rating >= 3 else "secondary"
        ),  # star_3
        gr.update(
            value="★" if rating >= 4 else "☆", variant="primary" if rating >= 4 else "secondary"
        ),  # star_4
        gr.update(
            value="★" if rating >= 5 else "☆", variant="primary" if rating >= 5 else "secondary"
        ),  # star_5
        # Parameters and Logs
        gr.update(value=params_display),  # runs_params_json
        gr.update(value=log_path or ""),  # runs_log_path
        gr.update(value=logs_content),  # runs_log_output
        # Action button
        gr.update(
            visible=model_type == "transfer" and status == "completed" and not show_upscaled_tab
        ),  # runs_upscale_selected_btn
    ]
