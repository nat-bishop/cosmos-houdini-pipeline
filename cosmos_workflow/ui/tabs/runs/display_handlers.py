"""Display handlers for runs gallery and table selection.

This module handles user interactions with the runs display components,
including gallery selection, table selection, and selection info updates.
"""

import re
from pathlib import Path
from typing import Any

import gradio as gr

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.ui.models.responses import (
    RunDetailsResponse,
    create_empty_run_details_response,
)

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
    load_spec_and_weights as _load_spec_and_weights,
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
        return gr.update(visible=False), ""

    # Get selected row index
    row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index

    # Extract run ID from table
    run_id = df_utils.get_cell_value(table_data, row_idx, 0, default=None)
    logger.info("Selected run_id: {}", run_id)

    if not run_id:
        logger.warning("No run_id found in selected row")
        return gr.update(visible=False), ""

    # Show the row and update the hidden run_id
    return gr.update(visible=True), run_id


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

    # Get prompt text if not in run details
    if not prompt_text and prompt_id:
        prompt = ops.get_prompt(prompt_id)
        if prompt:
            prompt_text = prompt.get("prompt_text", "")

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

    # Use helper to load spec and weights
    spec_data = _load_spec_and_weights(run_id)

    # Get prompt inputs if available
    prompt_inputs = {}
    if prompt_id:
        prompt = ops.get_prompt(prompt_id)
        if prompt:
            prompt_inputs = prompt.get("inputs", {})

    # Use helper to build input gallery
    input_videos, control_weights = _build_input_gallery(spec_data, prompt_inputs, run_id)

    # Get execution config and parameters
    exec_config = run_details.get("execution_config", {})
    if not any(control_weights.values()):
        # No weights from spec.json, try execution_config
        if "weights" in exec_config:
            weights = exec_config["weights"]
            control_weights = {
                "vis": weights.get("vis", 0.0),
                "edge": weights.get("edge", 0.0),
                "depth": weights.get("depth", 0.0),
                "seg": weights.get("seg", 0.0),
            }

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

    # Extract navigation info from prepared data
    runs_nav_info_update = prepared_data.get("runs_nav_info", gr.update())
    runs_nav_prev_update = prepared_data.get("runs_nav_prev", gr.update())
    runs_nav_next_update = prepared_data.get("runs_nav_next", gr.update())

    # Prepare info content
    info_content = prepared_data.get("info_content", {})
    info_display = f"""
## Run Information

**Run ID**: {info_content.get("run_id", "")}
**Status**: {info_content.get("status", "")}
**Model Type**: {info_content.get("model_type", "")}
**Created**: {info_content.get("created", "")}
**Duration**: {info_content.get("duration", "")}
**Resolution**: {info_content.get("resolution", "")}
"""
    if info_content.get("parent_id"):
        info_display += f"\n**Parent ID**: {info_content['parent_id']}"
    if info_content.get("upscaled_from"):
        info_display += f"\n**Upscaled From**: {info_content['upscaled_from']}"

    # Prepare parameters content
    params_display = prepared_data.get("params_display", "")

    # Read log content
    logs_content = _read_log_content(log_path, 50) if log_path else ""

    # Create the response
    response = RunDetailsResponse(
        # Visibility controls
        runs_details_group=gr.update(visible=True),
        runs_nav_info=runs_nav_info_update,
        runs_nav_prev=runs_nav_prev_update,
        runs_nav_next=runs_nav_next_update,
        runs_info_display=gr.update(value=info_display),
        runs_params_display=gr.update(value=params_display),
        runs_logs_display=gr.update(value=logs_content),
        runs_main_output_video=gr.update(value=output_video, visible=bool(output_video)),
        runs_main_output_gallery=gr.update(
            value=output_gallery if output_gallery else [], visible=bool(output_gallery)
        ),
        runs_main_input_gallery=gr.update(value=input_videos, visible=bool(input_videos)),
        runs_main_upscaled_video=gr.update(value=upscaled_video, visible=bool(upscaled_video)),
        runs_upscaled_tab=gr.update(visible=show_upscaled_tab),
        runs_prompt_text=gr.update(value=prompt_text or ""),
        runs_selected_id=run_id,
        runs_detail_tabs=gr.update(selected=0),
        runs_detail_row1=gr.update(visible=True),
        runs_enhance_params_md=gr.update(value=prepared_data.get("enhance_params", "")),
        runs_transfer_params_md=gr.update(value=prepared_data.get("transfer_params", "")),
        runs_upscale_params_md=gr.update(value=prepared_data.get("upscale_params", "")),
        runs_detail_actions_row=gr.update(visible=True),
        runs_delete_selected_btn=gr.update(visible=True),
        runs_transfer_selected_btn=gr.update(
            visible=model_type == "transfer" and run_details.get("status") == "completed"
        ),
        runs_enhance_selected_btn=gr.update(
            visible=model_type == "transfer" and run_details.get("status") == "completed"
        ),
        runs_upscale_selected_btn=gr.update(
            visible=model_type == "transfer"
            and run_details.get("status") == "completed"
            and not show_upscaled_tab
        ),
        # Add all other required fields with appropriate values or gr.update()
        runs_selected_index=gr.update(),
        runs_delete_dialog=gr.update(),
        runs_delete_preview=gr.update(),
        runs_delete_confirm_text=gr.update(),
        runs_confirm_delete_btn=gr.update(),
        runs_cancel_delete_btn=gr.update(),
        runs_transfer_dialog=gr.update(),
        runs_transfer_preview=gr.update(),
        runs_transfer_options=gr.update(),
        runs_transfer_overwrite=gr.update(),
        runs_confirm_transfer_btn=gr.update(),
        runs_cancel_transfer_btn=gr.update(),
        runs_upscale_dialog=gr.update(),
        runs_upscale_preview=gr.update(),
        runs_upscale_status=gr.update(),
        runs_confirm_upscale_btn=gr.update(),
        runs_cancel_upscale_btn=gr.update(),
    )

    return list(response)
