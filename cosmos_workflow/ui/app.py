#!/usr/bin/env python3
"""Comprehensive Gradio UI for Cosmos Workflow - Full Featured Application.

This module provides a complete web-based interface for the Cosmos Workflow System,
featuring advanced run management, filtering capabilities, and professional design.

Key Features:
- **Run History Management**: Comprehensive filtering, search, and batch operations
- **Enhanced Status Indicators**: Visual indicators for AI-enhanced prompts
- **Multi-tab Run Details**: General, Parameters, Logs, and Output information
- **Professional Design System**: Gradient animations and glassmorphism effects
- **Advanced Filtering**: Multi-criteria filtering with real-time search
- **Batch Operations**: Select and manage multiple runs simultaneously

Interface Tabs:
- Inputs: Video browser with prompt creation and multimodal preview
- Prompts: Unified prompt management with enhanced status indicators
- Outputs: Generated video gallery with comprehensive metadata
- Run History: Advanced run filtering, statistics, and batch management
- Jobs & Queue: Real-time monitoring and log streaming

The interface integrates with CosmosAPI for all operations, providing a complete
workflow management system from input preparation to output generation.
"""

import atexit
import os
import signal
import threading
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config import ConfigManager

# Import modular UI components
from cosmos_workflow.ui.components.header import create_header_ui
from cosmos_workflow.ui.helpers import (
    extract_video_metadata,
)
from cosmos_workflow.ui.log_viewer import LogViewer
from cosmos_workflow.ui.styles import get_custom_css
from cosmos_workflow.ui.tabs.inputs_ui import create_inputs_tab_ui
from cosmos_workflow.ui.tabs.jobs_ui import create_jobs_tab_ui
from cosmos_workflow.ui.tabs.prompts_ui import create_prompts_tab_ui
from cosmos_workflow.ui.tabs.runs_ui import create_runs_tab_ui
from cosmos_workflow.ui.tabs.runs_handlers import (
    load_runs_data,
    on_runs_table_select,
    load_run_logs,
    select_all_runs,
    clear_runs_selection,
    delete_selected_runs,
    update_runs_selection_info,
)
from cosmos_workflow.utils.logging import logger

# Load configuration
config = ConfigManager()

# Initialize unified operations - using CosmosAPI like CLI does
# Skip initialization during testing
if os.environ.get("COSMOS_TEST_MODE") != "true":
    ops = CosmosAPI(config=config)
else:
    ops = None  # Mock for testing

# Initialize log viewer (reusing existing component)
log_viewer = LogViewer(max_lines=2000)


# Simple shutdown cleanup using existing methods
def cleanup_on_shutdown(signum=None, frame=None):
    """Kill containers on shutdown using existing CosmosAPI method."""
    if signum:
        logger.info("Shutting down gracefully...")

    # Check config to see if we should cleanup containers
    ui_config = config.get_ui_config()
    should_cleanup = ui_config.get("cleanup_containers_on_exit", False)

    if not should_cleanup:
        logger.info("Container cleanup disabled in config - leaving containers running")
        return

    try:
        result = ops.kill_containers()
        if result["killed_count"] > 0:
            logger.info("Killed {} container(s)", result["killed_count"])
    except Exception as e:
        logger.debug("Cleanup error (expected on shutdown): {}", e)


# Register cleanup - reuse existing kill_containers() method
atexit.register(cleanup_on_shutdown)
# Only register signal handlers in main thread
if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGINT, cleanup_on_shutdown)
    signal.signal(signal.SIGTERM, cleanup_on_shutdown)

# Get paths from config
local_config = config.get_local_config()
inputs_dir = Path(local_config.videos_dir)  # This is already "inputs/videos" from config
outputs_dir = Path(local_config.outputs_dir)


# ============================================================================
# Phase 1: Input Browser Functions
# ============================================================================


def get_input_directories():
    """Get all input video directories with metadata."""
    directories = []

    if not inputs_dir.exists():
        logger.warning("Inputs directory does not exist: {}", inputs_dir)
        return []

    for dir_path in sorted(inputs_dir.iterdir()):
        if dir_path.is_dir():
            # Check for required files
            color_video = dir_path / "color.mp4"
            depth_video = dir_path / "depth.mp4"
            seg_video = dir_path / "segmentation.mp4"

            dir_info = {
                "name": dir_path.name,
                "path": str(dir_path),
                "has_color": color_video.exists(),
                "has_depth": depth_video.exists(),
                "has_segmentation": seg_video.exists(),
                "files": [],
            }

            # Get all files in directory
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    dir_info["files"].append(
                        {
                            "name": file_path.name,
                            "size": file_path.stat().st_size,
                            "path": str(file_path),
                        }
                    )

            directories.append(dir_info)

    return directories


def load_input_gallery():
    """Load input directories for gallery display."""
    directories = get_input_directories()
    gallery_items = []

    for dir_info in directories:
        # Use color.mp4 as thumbnail if it exists
        color_path = Path(dir_info["path"]) / "color.mp4"
        if color_path.exists():
            gallery_items.append((str(color_path), dir_info["name"]))
        else:
            # Use a placeholder or first video file found
            for file_info in dir_info["files"]:
                if file_info["name"].endswith(".mp4"):
                    gallery_items.append((file_info["path"], dir_info["name"]))
                    break

    return gallery_items


def on_input_select(evt: gr.SelectData, gallery_data):
    """Handle input selection from gallery with real video metadata extraction."""
    if evt.index is None:
        return (
            gr.update(value=""),  # selected_dir_path
            gr.update(visible=False),  # preview_group (compatibility)
            gr.update(visible=False),  # input_tabs_group
            gr.update(value=""),  # input_name
            gr.update(value=""),  # input_path
            gr.update(value=""),  # input_created
            gr.update(value=""),  # input_resolution
            gr.update(value=""),  # input_duration
            gr.update(value=""),  # input_fps
            gr.update(value=""),  # input_codec
            gr.update(value=""),  # input_files
            gr.update(value=[]),  # video_preview_gallery
            gr.update(value=""),  # create_video_dir
        )

    directories = get_input_directories()
    if evt.index >= len(directories):
        return (
            gr.update(value=""),  # selected_dir_path
            gr.update(visible=False),  # preview_group (compatibility)
            gr.update(visible=False),  # input_tabs_group
            gr.update(value=""),  # input_name
            gr.update(value=""),  # input_path
            gr.update(value=""),  # input_created
            gr.update(value=""),  # input_resolution
            gr.update(value=""),  # input_duration
            gr.update(value=""),  # input_fps
            gr.update(value=""),  # input_codec
            gr.update(value=""),  # input_files
            gr.update(value=[]),  # video_preview_gallery
            gr.update(value=""),  # create_video_dir
        )

    selected_dir = directories[evt.index]

    # Format directory info for structured fields
    from datetime import datetime

    # Extract individual field values
    name = selected_dir["name"]
    path = selected_dir["path"]

    # Extract real video metadata from color video
    metadata = {
        "resolution": "Unknown",
        "duration": "Unknown",
        "fps": "Unknown",
        "codec": "Unknown",
    }
    if selected_dir["has_color"]:
        color_path = Path(selected_dir["path"]) / "color.mp4"
        if color_path.exists():
            metadata = extract_video_metadata(color_path)

    # Format metadata as plain text values
    resolution_text = metadata["resolution"]
    duration_text = metadata["duration"]
    fps_text = metadata["fps"]
    codec_text = metadata["codec"]

    # Get creation time from directory
    dir_stat = os.stat(selected_dir["path"])
    created_time = datetime.fromtimestamp(dir_stat.st_ctime, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    # Format file list with better descriptions
    files_list = []
    for file_info in selected_dir["files"]:
        size_mb = file_info["size"] / (1024 * 1024)
        file_type = ""
        if "color" in file_info["name"]:
            file_type = " 🎨 RGB"
        elif "depth" in file_info["name"]:
            file_type = " 🏔️ Depth"
        elif "segmentation" in file_info["name"]:
            file_type = " 🧩 Segmentation"
        files_list.append(f"• {file_info['name']}{file_type} ({size_mb:.1f} MB)")

    files_text = "\n".join(files_list)

    # Load videos for preview gallery
    video_gallery_items = []
    if selected_dir["has_color"]:
        color_path = str(Path(selected_dir["path"]) / "color.mp4")
        video_gallery_items.append((color_path, "Color (RGB)"))
    if selected_dir["has_depth"]:
        depth_path = str(Path(selected_dir["path"]) / "depth.mp4")
        video_gallery_items.append((depth_path, "Depth Map"))
    if selected_dir["has_segmentation"]:
        seg_path = str(Path(selected_dir["path"]) / "segmentation.mp4")
        video_gallery_items.append((seg_path, "Segmentation"))

    # Convert path to forward slashes for cross-platform compatibility in input field
    video_dir_value = selected_dir["path"].replace("\\", "/")

    return (
        gr.update(value=selected_dir["path"]),  # selected_dir_path
        gr.update(visible=False),  # preview_group (compatibility)
        gr.update(visible=True),  # input_tabs_group
        gr.update(value=name),  # input_name
        gr.update(value=path),  # input_path
        gr.update(value=created_time),  # input_created
        gr.update(value=resolution_text),  # input_resolution
        gr.update(value=duration_text),  # input_duration
        gr.update(value=fps_text),  # input_fps
        gr.update(value=codec_text),  # input_codec
        gr.update(value=files_text),  # input_files
        gr.update(value=video_gallery_items),  # video_preview_gallery
        gr.update(value=video_dir_value),  # create_video_dir (auto-fill)
    )


# ============================================================================
# Phase 2: Prompt Management Functions
# ============================================================================


def list_prompts(limit=50):
    """List prompts using CosmosAPI, formatted for display."""
    try:
        # Use CosmosAPI to list prompts
        prompts = ops.list_prompts(limit=limit)

        # Format for Gradio Dataframe display
        table_data = []
        for prompt in prompts:
            # Extract fields safely
            prompt_id = prompt.get("id", "")
            name = prompt.get("parameters", {}).get("name", "unnamed")
            prompt_text = prompt.get("prompt_text", "")

            # Truncate long prompt text for display
            if len(prompt_text) > 50:
                prompt_text = prompt_text[:47] + "..."

            # Format created_at timestamp
            created_at = prompt.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    created_at = dt.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    pass

            table_data.append([prompt_id, name, prompt_text, created_at])

        return table_data
    except Exception as e:
        logger.error("Failed to list prompts: {}", e)
        return []


def create_prompt(prompt_text, video_dir, name, negative_prompt):
    """Create a new prompt using CosmosAPI."""
    try:
        # Validate inputs
        if not prompt_text or not prompt_text.strip():
            return "❌ Error: Prompt text is required"

        if not video_dir or not video_dir.strip():
            return "❌ Error: Video directory is required"

        # Convert to Path and validate
        video_path = Path(video_dir.strip())
        if not video_path.is_absolute():
            # If it's a relative path, use it as-is (already relative to project root)
            video_path = Path(video_dir.strip())

        # Use CosmosAPI to create prompt (it handles validation)
        prompt = ops.create_prompt(
            prompt_text=prompt_text.strip(),
            video_dir=video_path,
            name=name.strip() if name and name.strip() else None,
            negative_prompt=negative_prompt.strip()
            if negative_prompt and negative_prompt.strip()
            else None,
        )

        # Success message with prompt ID
        prompt_id = prompt.get("id", "unknown")
        prompt_name = prompt.get("parameters", {}).get("name", "unnamed")
        return f"✅ Created prompt **{prompt_id}**\nName: {prompt_name}"

    except FileNotFoundError as e:
        return f"❌ Error: {e}"
    except ValueError as e:
        return f"❌ Error: {e}"
    except Exception as e:
        logger.error("Failed to create prompt: {}", e)
        return f"❌ Error creating prompt: {e}"


# ============================================================================
# Phase 3: Operations Functions
# ============================================================================


def load_ops_prompts(limit=50):
    """Load prompts for operations table with selection column."""
    try:
        if not ops:
            return []

        # Use CosmosAPI to get prompts
        prompts = ops.list_prompts(limit=limit)

        # Format for operations table with selection column
        table_data = []
        for prompt in prompts:
            prompt_id = prompt.get("id", "")
            name = prompt.get("parameters", {}).get("name", "unnamed")
            # Model type removed - prompts don't have model types
            text = prompt.get("prompt_text", "")
            created = prompt.get("created_at", "")[:19] if prompt.get("created_at") else ""

            # Truncate text for display
            if len(text) > 60:
                text = text[:57] + "..."

            # Add with selection checkbox (False by default) and created date
            table_data.append([False, prompt_id, name, text, created])

        return table_data
    except Exception as e:
        logger.error("Failed to load prompts for operations: {}", e)
        return []


def update_selection_count(dataframe_data):
    """Update the selection count based on checked rows."""
    try:
        if dataframe_data is None:
            return "**0** prompts selected"

        # Handle both list and dataframe formats
        import pandas as pd

        if isinstance(dataframe_data, pd.DataFrame):
            # It's a pandas DataFrame - Gradio returns DataFrame with values
            if not dataframe_data.empty:
                # Access the actual values array and check first column
                first_col_values = (
                    dataframe_data.values[:, 0] if dataframe_data.shape[1] > 0 else []
                )
                selected = sum(1 for val in first_col_values if val is True)
            else:
                selected = 0
        elif isinstance(dataframe_data, list):
            # List format - check if rows have boolean first element
            selected = sum(1 for row in dataframe_data if len(row) > 0 and row[0] is True)
        elif hasattr(dataframe_data, "__len__"):
            # Could be a numpy array or similar
            try:
                selected = sum(1 for row in dataframe_data if len(row) > 0 and row[0] is True)
            except Exception:
                return "**0** prompts selected"
        else:
            return "**0** prompts selected"

        return f"**{selected}** prompt{'s' if selected != 1 else ''} selected"
    except Exception as e:
        logger.debug("Error counting selection: %s", str(e))
        return "**0** prompts selected"


def clear_all_prompts(dataframe_data):
    """Clear all selections in the table."""
    if dataframe_data is None:
        return []

    import pandas as pd

    if isinstance(dataframe_data, pd.DataFrame):
        # DataFrame format - set first column to False
        dataframe_data = dataframe_data.copy()
        dataframe_data.iloc[:, 0] = False
        return dataframe_data
    else:
        # List format
        updated_data = []
        for row in dataframe_data:
            new_row = row.copy() if isinstance(row, list) else list(row)
            new_row[0] = False
            updated_data.append(new_row)
        return updated_data


def toggle_enhance_force_visibility(create_new):
    """Show/hide force overwrite checkbox based on action selection."""
    # Show force checkbox only when overwrite is selected
    return gr.update(visible=not create_new)


def on_prompt_row_select(dataframe_data, evt: gr.SelectData):
    """Handle row selection in prompts table to show details."""
    try:
        logger.info("on_prompt_row_select called with evt.index: %s", evt.index if evt else "None")

        if dataframe_data is None or evt is None:
            logger.warning("on_prompt_row_select: dataframe_data or evt is None")
            # Return gr.update() objects to force UI refresh
            return [
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=False),
            ]

        # Get the selected row index
        row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index
        logger.info("Selected row index: %s", row_idx)

        # Extract row data
        import pandas as pd

        if isinstance(dataframe_data, pd.DataFrame):
            row = dataframe_data.iloc[row_idx]
            # Columns: ["☑", "ID", "Name", "Prompt Text", "Created"]
            prompt_id = str(row.iloc[1]) if len(row) > 1 else ""
        else:
            row = dataframe_data[row_idx] if row_idx < len(dataframe_data) else []
            prompt_id = str(row[1]) if len(row) > 1 else ""

        logger.info("Selected prompt_id: %s", prompt_id)

        if not prompt_id:
            return [
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=""),
                gr.update(value=False),
            ]

        # Use the global ops (CosmosAPI) to get full prompt details
        if ops:
            prompt_details = ops.get_prompt(prompt_id)
            if prompt_details:
                name = prompt_details.get("parameters", {}).get("name", "unnamed")
                prompt_text = prompt_details.get("prompt_text", "")
                negative_prompt = prompt_details.get("parameters", {}).get("negative_prompt", "")
                created = (
                    prompt_details.get("created_at", "")[:19]
                    if prompt_details.get("created_at")
                    else ""
                )
                enhanced = prompt_details.get("parameters", {}).get("enhanced", False)

                # Get video directory from inputs
                inputs = prompt_details.get("inputs", {})
                video_dir = (
                    inputs.get("video", "").replace("/color.mp4", "") if inputs.get("video") else ""
                )

                logger.info(
                    "Returning prompt details: id=%s, name=%s, enhanced=%s",
                    prompt_id,
                    name,
                    enhanced,
                )
                # Return gr.update() objects to force UI refresh
                return [
                    gr.update(value=prompt_id),
                    gr.update(value=name),
                    gr.update(value=prompt_text),
                    gr.update(value=negative_prompt),
                    gr.update(value=created),
                    gr.update(value=video_dir),
                    gr.update(value=enhanced),
                ]

        logger.warning("No prompt details found for %s", prompt_id)
        return [
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=False),
        ]

    except Exception as e:
        logger.error("Error selecting prompt row: %s", str(e))
        import traceback

        logger.error("Traceback: %s", traceback.format_exc())
        return [
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=False),
        ]


def get_queue_status():
    """Get current queue status information using CosmosAPI."""
    try:
        if ops:
            # Get running and pending runs
            running_runs = ops.list_runs(status="running", limit=10)
            pending_runs = ops.list_runs(status="pending", limit=10)

            running_count = len(running_runs)
            pending_count = len(pending_runs)

            if running_count > 0:
                current_run = running_runs[0]
                return (
                    f"Running: {current_run.get('id', '')[:8]}... | Queue: {pending_count} pending"
                )
            elif pending_count > 0:
                return f"Queue: {pending_count} pending | GPU: Ready"
            else:
                return "Queue: Empty | GPU: Available"
        return "Queue: Status unavailable"
    except Exception as e:
        logger.error("Error getting queue status: %s", str(e))
        return "Queue: Error getting status"


def get_recent_runs(limit=5):
    """Get recent runs for the Jobs tab."""
    try:
        if ops:
            # Get most recent runs
            runs = ops.list_runs(limit=limit)

            # Format for table display
            table_data = []
            for run in runs[:limit]:
                run_id = run.get("id", "")[:8]
                status = run.get("status", "unknown")
                created = run.get("created_at", "")[:19] if run.get("created_at") else ""
                table_data.append([run_id, status, created])

            return table_data
        return []
    except Exception as e:
        logger.error("Error getting recent runs: %s", str(e))
        return []


def run_inference_on_selected(
    dataframe_data,
    weight_vis,
    weight_edge,
    weight_depth,
    weight_seg,
    steps,
    guidance,
    seed,
    fps,
    sigma_max,
    blur_strength,
    canny_threshold,
    progress=None,
):
    """Run inference on selected prompts with queue progress tracking."""
    if progress is None:
        progress = gr.Progress()
    try:
        # Get selected prompt IDs
        selected_ids = []
        if dataframe_data is not None:
            # Handle different data formats
            import pandas as pd

            if isinstance(dataframe_data, pd.DataFrame):
                # DataFrame format
                for _, row in dataframe_data.iterrows():
                    if row.iloc[0]:  # Checkbox is checked
                        selected_ids.append(row.iloc[1])  # Prompt ID is second column
            else:
                # List format
                for row in dataframe_data:
                    if row[0]:  # Checkbox is checked
                        selected_ids.append(row[1])  # Prompt ID is second column

        if not selected_ids:
            return "❌ No prompts selected", "Idle"

        # Build weights dictionary
        weights = {
            "vis": weight_vis,
            "edge": weight_edge,
            "depth": weight_depth,
            "seg": weight_seg,
        }

        logger.info("Starting inference on {} prompts", len(selected_ids))

        # Run inference based on count
        if len(selected_ids) == 1:
            # Single inference
            progress(0.1, desc="Initializing inference...")

            result = ops.quick_inference(
                prompt_id=selected_ids[0],
                weights=weights,
                stream_output=False,  # Don't stream to console in UI
                num_steps=int(steps),
                guidance_scale=guidance,
                seed=int(seed),
                fps=int(fps),
                sigma_max=sigma_max,
                blur_strength=blur_strength,
                canny_threshold=canny_threshold,
            )

            progress(1.0, desc="Inference complete!")

            # Check for completed status (synchronous execution)
            if result.get("status") == "completed":
                output_msg = f"✅ Inference completed for {selected_ids[0]}"
                if result.get("output_path"):
                    output_msg += f"\n📁 Output: {result['output_path']}"
                return (output_msg, "Idle")
            elif result.get("status") == "started":  # Legacy support
                return (
                    f"✅ Inference started for {selected_ids[0]}",
                    f"Running: {result.get('run_id', 'unknown')}",
                )
            elif result.get("status") == "success":  # Legacy support
                return ("✅ Inference completed successfully", "Idle")
            else:
                return (f"❌ Inference failed: {result.get('error', 'Unknown error')}", "Idle")
        else:
            # Batch inference
            progress(0.1, desc=f"Starting batch inference for {len(selected_ids)} prompts...")

            result = ops.batch_inference(
                prompt_ids=selected_ids,
                shared_weights=weights,
                num_steps=int(steps),
                guidance_scale=guidance,
                seed=int(seed),
                fps=int(fps),
                sigma_max=sigma_max,
                blur_strength=blur_strength,
                canny_threshold=canny_threshold,
            )

            progress(1.0, desc="Batch inference complete!")

            successful = len(result.get("output_mapping", {}))
            return (
                f"✅ Batch inference completed: {successful}/{len(selected_ids)} successful",
                "Idle",
            )

    except Exception as e:
        logger.error("Failed to run inference: {}", e)
        return f"❌ Error: {e}", "Idle"


def run_enhance_on_selected(dataframe_data, create_new, force_overwrite, progress=None):
    """Run enhancement on selected prompts with queue progress tracking."""
    if progress is None:
        progress = gr.Progress()
    try:
        # Handle force_overwrite parameter - it might be None or wrapped
        if force_overwrite is None:
            force_overwrite = False
        elif hasattr(force_overwrite, "item"):
            # In case it's a numpy scalar or similar
            force_overwrite = bool(force_overwrite.item())
        else:
            force_overwrite = bool(force_overwrite)

        # Get selected prompt IDs
        selected_ids = []
        if dataframe_data is not None:
            # Handle different data formats
            import pandas as pd

            if isinstance(dataframe_data, pd.DataFrame):
                # DataFrame format
                for _, row in dataframe_data.iterrows():
                    if row.iloc[0]:  # Checkbox is checked
                        selected_ids.append(row.iloc[1])  # Prompt ID
            else:
                # List format
                for row in dataframe_data:
                    if row[0]:  # Checkbox is checked
                        selected_ids.append(row[1])  # Prompt ID

        if not selected_ids:
            return "❌ No prompts selected", "Idle"

        # Always use pixtral model
        model = "pixtral"
        logger.info("Starting enhancement on {} prompts with model {}", len(selected_ids), model)

        results = []
        errors = []

        for prompt_id in selected_ids:
            try:
                result = ops.enhance_prompt(
                    prompt_id=prompt_id,
                    create_new=create_new,
                    enhancement_model=model,
                    force_overwrite=force_overwrite,
                )

                if result.get("status") in ["success", "started"]:
                    results.append(prompt_id)
                else:
                    errors.append(f"{prompt_id}: {result.get('error', 'Unknown error')}")

            except Exception as e:
                errors.append(f"{prompt_id}: {e}")

        # Build status message
        if errors:
            error_msg = "\n".join(errors[:3])  # Show first 3 errors
            if len(errors) > 3:
                error_msg += f"\n... and {len(errors) - 3} more errors"
            return (f"⚠️ Enhanced {len(results)}/{len(selected_ids)} prompts\n{error_msg}", "Idle")
        else:
            action = "created new" if create_new else "updated"
            return (f"✅ Successfully {action} {len(results)} enhanced prompt(s)", "Idle")

    except Exception as e:
        import traceback

        logger.error("Failed to run enhancement: {}", str(e))
        logger.error("Traceback: {}", traceback.format_exc())
        return f"❌ Error: {e}", "Idle"


# ============================================================================
# Existing Log Streaming Functions (keeping from original)
# ============================================================================


def start_log_streaming():
    """Generator that streams logs to the UI."""
    log_viewer.clear()

    try:
        containers = ops.get_active_containers()

        if not containers:
            yield "No active containers found", log_viewer.get_html()
            return

        if len(containers) > 1:
            container_id = containers[0]["container_id"]
            message = f"Multiple containers found, streaming from {container_id}"
        else:
            container_id = containers[0]["container_id"]
            message = f"Streaming logs from container {container_id}"

        yield message, log_viewer.get_html()

        try:
            for log_line in ops.stream_logs_generator(container_id):
                log_viewer.add_from_stream(log_line)
                yield message, log_viewer.get_html()
        except KeyboardInterrupt:
            yield "Streaming stopped", log_viewer.get_html()

    except RuntimeError as e:
        yield f"Error: {e}", log_viewer.get_html()
    except Exception as e:
        yield f"Failed to start streaming: {e}", log_viewer.get_html()


def check_running_jobs():
    """Check for active containers on remote instance."""
    try:
        containers = ops.get_active_containers()

        if containers:
            display_text = f"Found {len(containers)} active container(s)\n\n"
            for container in containers:
                display_text += f"Container: {container['container_id']}\n"
                display_text += f"Image: {container.get('image', 'Unknown')}\n"
                display_text += f"Status: {container.get('status', 'Unknown')}\n"
                display_text += "-" * 40 + "\n"

            if len(containers) == 1:
                status = "Ready to stream from active container"
            else:
                status = "Multiple containers active"

            return display_text.strip(), status
        else:
            return "No active containers found", "No containers to stream from"
    except Exception as e:
        return f"Error: {e}", "Error checking containers"


# ============================================================================
# Main UI Creation
# ============================================================================


def create_ui():
    """Create the comprehensive Gradio interface using modular components."""

    # Get custom CSS from styles module
    custom_css = get_custom_css()

    # Initialize component registry
    components = {}

    # Helper to safely get component lists
    def get_components(*keys):
        """Get a list of components, skipping any that don't exist."""
        result = []
        for key in keys:
            if key in components:
                result.append(components[key])
        # Return the list if we have all requested components
        return result if len(result) == len(keys) else None

    with gr.Blocks(title="Cosmos Workflow Manager", css=custom_css) as app:
        # Create header with refresh controls
        header_components = create_header_ui(config)
        components.update(header_components)

        # Create tabs
        with gr.Tabs():
            # Create each tab UI
            inputs_components = create_inputs_tab_ui(config)
            components.update(inputs_components)

            prompts_components = create_prompts_tab_ui()
            components.update(prompts_components)

            runs_components = create_runs_tab_ui()
            components.update(runs_components)

            jobs_components = create_jobs_tab_ui()
            components.update(jobs_components)

        # ============================================
        # Event Handlers
        # ============================================

        # Import additional functions for runs tab

        # Global refresh function
        def global_refresh_all():
            """Refresh all data across all tabs."""
            from datetime import datetime

            try:
                # Get current status
                status = f"✅ Connected | Last refresh: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"

                # Load all data
                inputs_data = load_input_gallery()
                prompts_data = load_ops_prompts(50)
                jobs_data = check_running_jobs()

                return (
                    status,  # refresh_status
                    inputs_data,  # input_gallery
                    prompts_data,  # ops_prompts_table
                    jobs_data[0],  # running_jobs_display
                    jobs_data[1],  # job_status
                )
            except Exception as e:
                logger.error("Error during global refresh: %s", str(e))
                return (
                    "❌ Error - Check logs",
                    [],
                    [],
                    "Error loading data",
                    "Error",
                )

        # Header/Global Refresh Events
        if "global_refresh_timer" in components:
            components["global_refresh_timer"].tick(
                fn=global_refresh_all,
                outputs=[
                    components["refresh_status"],
                    components["input_gallery"],
                    components["ops_prompts_table"],
                    components["running_jobs_display"],
                    components["job_status"],
                ],
            )

        if "manual_refresh_btn" in components:
            components["manual_refresh_btn"].click(
                fn=global_refresh_all,
                outputs=[
                    components["refresh_status"],
                    components["input_gallery"],
                    components["ops_prompts_table"],
                    components["running_jobs_display"],
                    components["job_status"],
                ],
            )

        # Inputs Tab Events
        if "input_gallery" in components:
            components["input_gallery"].select(
                fn=on_input_select,
                inputs=[components["input_gallery"]],
                outputs=[
                    components["selected_dir_path"],
                    components["preview_group"],
                    components["input_tabs_group"],
                    components["input_name"],
                    components["input_path"],
                    components["input_created"],
                    components["input_resolution"],
                    components["input_duration"],
                    components["input_fps"],
                    components["input_codec"],
                    components["input_files"],
                    components["video_preview_gallery"],
                    components["create_video_dir"],
                ],
            )

        if "create_prompt_btn" in components:
            components["create_prompt_btn"].click(
                fn=create_prompt,
                inputs=[
                    components["create_prompt_text"],
                    components["create_video_dir"],
                    components["create_name"],
                    components["create_negative"],
                ],
                outputs=[components["create_status"]],
            )

        # Prompts Tab Events
        if "ops_prompts_table" in components:
            outputs = get_components(
                "selected_prompt_id",
                "selected_prompt_name",
                "selected_prompt_text",
                "selected_prompt_negative",
                "selected_prompt_created",
                "selected_prompt_video_dir",
                "selected_prompt_enhanced",
            )
            if outputs:
                components["ops_prompts_table"].select(
                    fn=on_prompt_row_select,
                    inputs=[components["ops_prompts_table"]],
                    outputs=outputs,
                )

            if "selection_count" in components:
                components["ops_prompts_table"].change(
                    fn=update_selection_count,
                    inputs=[components["ops_prompts_table"]],
                    outputs=[components["selection_count"]],
                )

        if "clear_selection_btn" in components:
            components["clear_selection_btn"].click(
                fn=clear_all_prompts,
                inputs=[components["ops_prompts_table"]],
                outputs=[components["ops_prompts_table"]],
            )

        if "run_inference_btn" in components and "ops_prompts_table" in components:
            inputs = get_components(
                "ops_prompts_table",
                "weight_vis",
                "weight_edge",
                "weight_depth",
                "weight_seg",
                "inf_steps",
                "inf_guidance",
                "inf_seed",
                "inf_fps",
                "inf_sigma_max",
                "inf_blur_strength",
                "inf_canny_threshold",
            )
            outputs = get_components("inference_status")
            if inputs and outputs:
                components["run_inference_btn"].click(
                    fn=run_inference_on_selected,
                    inputs=inputs,
                    outputs=outputs,
                )

        if "run_enhance_btn" in components:
            inputs = get_components(
                "ops_prompts_table",
                "enhance_create_new",
                "enhance_force",
            )
            outputs = get_components("enhance_status")
            if inputs and outputs:
                components["run_enhance_btn"].click(
                    fn=run_enhance_on_selected,
                    inputs=inputs,
                    outputs=outputs,
                )

        # Runs Tab Events
        # Runs filters - trigger data reload
        if all(k in components for k in ["runs_status_filter", "runs_date_filter", "runs_search", "runs_limit"]):
            filter_inputs = [
                components["runs_status_filter"],
                components["runs_date_filter"],
                components["runs_search"],
                components["runs_limit"],
            ]
            filter_outputs = get_components("runs_gallery", "runs_table", "runs_stats")
            if filter_outputs:
                for filter_component in ["runs_status_filter", "runs_date_filter", "runs_search", "runs_limit"]:
                    components[filter_component].change(
                        fn=load_runs_data,
                        inputs=filter_inputs,
                        outputs=filter_outputs,
                    )

        # Runs table selection
        if "runs_table" in components:
            outputs = get_components(
                "runs_details_group",
                "runs_output_video",
                "runs_input_videos",
                "runs_prompt_text",
                "runs_visual_weight",
                "runs_edge_weight",
                "runs_depth_weight",
                "runs_segmentation_weight",
                "runs_info_id",
                "runs_info_prompt_id",
                "runs_info_status",
                "runs_info_duration",
                "runs_info_type",
                "runs_info_prompt_name",
                "runs_info_created",
                "runs_info_completed",
                "runs_params_json",
                "runs_log_path",
                "runs_log_output",
            )
            if outputs:
                components["runs_table"].select(
                    fn=on_runs_table_select,
                    inputs=[components["runs_table"]],
                    outputs=outputs,
                )

            # Update selection info when table changes
            if "runs_selected_info" in components:
                components["runs_table"].change(
                    fn=update_runs_selection_info,
                    inputs=[components["runs_table"]],
                    outputs=[components["runs_selected_info"]],
                )

        # Batch operations
        if "runs_select_all_btn" in components and "runs_table" in components:
            components["runs_select_all_btn"].click(
                fn=select_all_runs,
                inputs=[components["runs_table"]],
                outputs=[components["runs_table"]],
            )

        if "runs_clear_selection_btn" in components and "runs_table" in components:
            components["runs_clear_selection_btn"].click(
                fn=clear_runs_selection,
                inputs=[components["runs_table"]],
                outputs=[components["runs_table"]],
            )

        if "runs_delete_selected_btn" in components and "runs_table" in components:
            delete_outputs = get_components("runs_table", "runs_selected_info")
            if delete_outputs:
                components["runs_delete_selected_btn"].click(
                    fn=delete_selected_runs,
                    inputs=[components["runs_table"]],
                    outputs=delete_outputs,
                )

        # Load logs button
        if all(k in components for k in ["runs_load_logs_btn", "runs_log_path", "runs_log_output"]):
            components["runs_load_logs_btn"].click(
                fn=load_run_logs,
                inputs=[components["runs_log_path"]],
                outputs=[components["runs_log_output"]],
            )

        # Jobs & Queue Tab Events
        if "stream_btn" in components:
            outputs = get_components("job_status", "log_display")
            if outputs:
                components["stream_btn"].click(
                    fn=start_log_streaming,
                    outputs=outputs,
                )

        # Load initial data
        initial_outputs = get_components(
            "input_gallery",
            "ops_prompts_table",
            "running_jobs_display",
            "job_status",
        )
        
        # Debug: Check which components are missing
        required_components = ["input_gallery", "ops_prompts_table", "running_jobs_display", "job_status"]
        missing = [k for k in required_components if k not in components]
        if missing:
            logger.warning("Missing components for initial load: %s", missing)
        
        if initial_outputs:
            logger.info("Setting up initial data load with %d outputs", len(initial_outputs))
            app.load(
                fn=lambda: (
                    load_input_gallery(),
                    load_ops_prompts(50),
                    check_running_jobs()[0] if ops else "No containers",
                    check_running_jobs()[1] if ops else "Not connected",
                ),
                outputs=initial_outputs,
            )
        else:
            logger.warning("Could not set up initial data load - missing components")

    return app


# ============================================================================
# Application Entry Point
# ============================================================================
# For Gradio auto-reload CLI compatibility
# ============================================================================

# Create the demo variable that Gradio CLI expects
demo = create_ui()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
