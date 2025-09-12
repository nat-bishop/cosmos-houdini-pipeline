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
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.ui.helpers import (
    extract_video_metadata,
)
from cosmos_workflow.ui.log_viewer import LogViewer
from cosmos_workflow.ui.styles import get_custom_css
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
    try:
        result = ops.kill_containers()
        if result["killed_count"] > 0:
            logger.info("Killed {} container(s)", result["killed_count"])
    except Exception as e:
        logger.debug("Cleanup error (expected on shutdown): {}", e)


# Register cleanup - reuse existing kill_containers() method
atexit.register(cleanup_on_shutdown)
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


def get_prompt_details(prompt_id):
    """Get detailed information about a specific prompt."""
    try:
        if not prompt_id:
            return "No prompt selected"

        prompt = ops.get_prompt(prompt_id)
        if not prompt:
            return f"Prompt {prompt_id} not found"

        # Format detailed view
        details = f"**Prompt ID:** {prompt['id']}\n"
        details += f"**Name:** {prompt.get('parameters', {}).get('name', 'unnamed')}\n"
        # Model type removed - prompts don't have model types
        details += f"**Created:** {prompt.get('created_at', 'unknown')}\n\n"

        details += "**Prompt Text:**\n"
        details += f"{prompt.get('prompt_text', '')}\n\n"

        negative = prompt.get("parameters", {}).get("negative_prompt")
        if negative:
            details += "**Negative Prompt:**\n"
            details += f"{negative}\n\n"

        inputs = prompt.get("inputs", {})
        if inputs:
            details += "**Input Files:**\n"
            if inputs.get("video"):
                details += f"- Color: {inputs['video']}\n"
            if inputs.get("depth"):
                details += f"- Depth: {inputs['depth']}\n"
            if inputs.get("seg"):
                details += f"- Segmentation: {inputs['seg']}\n"

        return details
    except Exception as e:
        logger.error("Failed to get prompt details: {}", e)
        return f"Error getting prompt details: {e}"


def populate_from_input_dir(selected_dir_path):
    """Populate the video directory field from selected input."""
    if selected_dir_path:
        return selected_dir_path
    return ""


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


def list_prompts_for_input(video_dir):
    """List prompts associated with a specific input directory."""
    try:
        all_prompts = ops.list_prompts(limit=100)

        if not video_dir:
            return all_prompts

        # Filter prompts that use this video directory
        video_path = Path(video_dir)
        filtered = []

        for prompt in all_prompts:
            inputs = prompt.get("inputs", {})
            if inputs.get("video"):
                prompt_video_path = Path(inputs["video"]).parent
                if prompt_video_path == video_path:
                    filtered.append(prompt)

        return filtered
    except Exception as e:
        logger.error("Failed to filter prompts for input: {}", e)
        return []


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
    """Create the comprehensive Gradio interface."""

    # Get custom CSS from styles module
    custom_css = get_custom_css()

    # Get refresh interval from config
    ui_config = config._config_data.get("ui", {})
    default_refresh_interval = ui_config.get("refresh_interval", 5)

    with gr.Blocks(title="Cosmos Workflow Manager", css=custom_css) as app:
        gr.Markdown("# 🌌 Cosmos Workflow Manager")
        gr.Markdown("Comprehensive UI for managing Cosmos Transfer workflows")

        # Global Refresh Control Panel
        with gr.Row():
            with gr.Column(scale=3):
                # Status indicators
                refresh_status = gr.Textbox(
                    label="System Status",
                    value="✅ Connected | Last refresh: Never",
                    interactive=False,
                    container=False,
                    elem_classes=["status-indicator"],
                )
            with gr.Column(scale=1):
                # Auto-refresh controls
                with gr.Row():
                    auto_refresh_enabled = gr.Checkbox(
                        label="Auto-refresh",
                        value=True,
                        container=False,
                        elem_classes=["auto-refresh-toggle"],
                    )
                    refresh_interval = gr.Slider(
                        minimum=2,
                        maximum=30,
                        value=default_refresh_interval,
                        step=1,
                        label="Interval (s)",
                        container=False,
                        visible=True,
                    )
                    manual_refresh_btn = gr.Button(
                        "🔄 Refresh Now",
                        variant="secondary",
                        size="sm",
                    )

        # Global timer for auto-refresh
        global_refresh_timer = gr.Timer(value=float(default_refresh_interval), active=True)

        with gr.Tabs():
            # ========================================
            # Tab 1: Inputs Browser with Create Prompt
            # ========================================
            with gr.Tab("📁 Inputs", id=1):
                gr.Markdown("### Input Video Browser")
                gr.Markdown("Browse input videos and create prompts directly")

                with gr.Row():
                    # Left: Gallery of inputs - MUCH LARGER (2x the right panel)
                    with gr.Column(scale=2):
                        input_gallery = gr.Gallery(
                            label="Input Directories",
                            show_label=True,
                            elem_id="input_gallery",
                            columns=4,  # 4 columns for larger thumbnails
                            rows=3,  # Allow 3 rows
                            object_fit="contain",  # Try contain for better aspect ratio
                            height=900,  # Much larger height for bigger thumbnails
                            preview=False,  # Disable preview for cleaner look
                            allow_preview=False,
                            interactive=False,  # Prevent uploads
                        )

                        # Individual refresh button removed - using global refresh

                    # Right: Input Details with tabs
                    with gr.Column(scale=1):
                        # Hidden field to store selected directory path
                        selected_dir_path = gr.Textbox(visible=False)

                        # Keep preview_group for compatibility but hidden
                        with gr.Group(visible=False) as preview_group:
                            pass

                        # Tabs for Input Details and Create Prompt
                        with gr.Tabs(visible=False) as input_tabs_group:
                            # Input Details Tab
                            with gr.Tab("📁 Input Details"):
                                with gr.Group(elem_classes=["detail-card"]):
                                    # File information section
                                    gr.Markdown("#### 📂 File Information")

                                    input_name = gr.Textbox(
                                        label="Name",
                                        interactive=False,
                                    )

                                    input_path = gr.Textbox(
                                        label="Path",
                                        interactive=False,
                                    )

                                    input_created = gr.Textbox(
                                        label="Created",
                                        interactive=False,
                                    )

                                    # Video metadata as regular textboxes
                                    input_resolution = gr.Textbox(
                                        label="Resolution",
                                        interactive=False,
                                    )

                                    input_duration = gr.Textbox(
                                        label="Duration",
                                        interactive=False,
                                    )

                                    with gr.Row():
                                        input_fps = gr.Textbox(
                                            label="FPS",
                                            interactive=False,
                                            scale=1,
                                        )

                                        input_codec = gr.Textbox(
                                            label="Codec",
                                            interactive=False,
                                            scale=1,
                                        )

                                    input_files = gr.Textbox(
                                        label="Available Control Inputs",
                                        lines=3,
                                        interactive=False,
                                    )

                                    # Video previews at the bottom
                                    gr.Markdown("#### 🎬 Video Previews")
                                    video_preview_gallery = gr.Gallery(
                                        label="Available Videos",
                                        columns=3,
                                        height=200,  # Fixed height to prevent excess space
                                        object_fit="contain",  # Changed to contain to fit videos properly
                                        elem_id="video_preview_gallery",
                                        show_label=False,
                                        allow_preview=True,  # Allow clicking to preview
                                        container=False,  # Remove extra container padding
                                    )

                            # Create Prompt Tab
                            with gr.Tab("✨ Create Prompt"):
                                with gr.Group(elem_classes=["detail-card"]):
                                    # Video Directory at the top for easy access
                                    create_video_dir = gr.Textbox(
                                        label="Video Directory",
                                        placeholder="Auto-filled when selecting an input",
                                        info="Must contain color.mp4",
                                    )

                                    create_prompt_text = gr.Textbox(
                                        label="Prompt Text",
                                        placeholder="Enter your prompt description here...",
                                        lines=3,
                                        max_lines=10,
                                    )

                                    create_name = gr.Textbox(
                                        label="Name (Optional)",
                                        placeholder="Leave empty for auto-generated name",
                                        info="A descriptive name for this prompt",
                                    )

                                    # Get default negative prompt from config
                                    default_negative = (
                                        config._config_data.get("generation", {})
                                        .get(
                                            "negative_prompt",
                                            "The video captures a game playing, with bad crappy graphics...",
                                        )
                                        .strip()
                                    )

                                    create_negative = gr.Textbox(
                                        label="Negative Prompt",
                                        value=default_negative,  # Pre-fill with default
                                        lines=3,
                                        info="Edit to customize or leave as default",
                                    )

                                    create_prompt_btn = gr.Button(
                                        "✨ Create Prompt", variant="primary", size="lg"
                                    )

                                    create_status = gr.Markdown("")

            # ========================================
            # Tab 2: UNIFIED Prompts & Operations (Merged)
            # ========================================
            with gr.Tab("🚀 Prompts", id=2, elem_classes=["prompts-tab"]):
                gr.Markdown("### Prompt Management & Operations")
                gr.Markdown("View, select, and execute operations on your prompts")

                with gr.Row(elem_classes=["split-view"]):
                    # Left: Prompt selection table with enhanced interactivity
                    with gr.Column(scale=3, elem_classes=["split-left"]):
                        with gr.Group(elem_classes=["detail-card"]):
                            gr.Markdown("#### 📋 Prompts Library")

                            # Filter row with animations
                            with gr.Row(elem_classes=["batch-operation"]):
                                ops_limit = gr.Number(
                                    value=50,
                                    label="Limit",
                                    minimum=1,
                                    maximum=500,
                                    scale=1,
                                )
                                # Individual refresh button removed - using global refresh

                            # Enhanced prompts table with selection
                            ops_prompts_table = gr.Dataframe(
                                headers=["☑", "ID", "Name", "Prompt Text", "Created"],
                                datatype=["bool", "str", "str", "str", "str"],
                                interactive=True,  # Must be True for select event to work
                                col_count=(5, "fixed"),
                                wrap=True,
                                elem_classes=["prompts-table"],
                            )

                            # Selection controls with visual feedback
                            with gr.Row(elem_classes=["batch-operation"]):
                                clear_selection_btn = gr.Button(
                                    "☐ Clear Selection", size="sm", variant="secondary"
                                )
                                selection_count = gr.Markdown(
                                    "**0** prompts selected", elem_classes=["selection-counter"]
                                )

                    # Right: Split view for details and operations
                    with gr.Column(scale=2, elem_classes=["split-right"]):
                        # Prompt Details Section
                        with gr.Group(elem_classes=["detail-card"], visible=True):
                            gr.Markdown("#### 📝 Prompt Details")

                            selected_prompt_id = gr.Textbox(
                                label="Prompt ID",
                                interactive=False,
                                elem_classes=["loading-skeleton"],
                            )

                            with gr.Row():
                                selected_prompt_name = gr.Textbox(
                                    label="Name",
                                    interactive=False,
                                    scale=3,
                                )
                                selected_prompt_enhanced = gr.Checkbox(
                                    label="✨ Enhanced",
                                    interactive=False,
                                    scale=1,
                                )

                            selected_prompt_text = gr.Textbox(
                                label="Prompt Text",
                                lines=3,
                                interactive=False,
                            )

                            selected_prompt_negative = gr.Textbox(
                                label="Negative Prompt",
                                lines=2,
                                interactive=False,
                            )

                            with gr.Row():
                                selected_prompt_created = gr.Textbox(
                                    label="Created",
                                    interactive=False,
                                    scale=1,
                                )
                                selected_prompt_video_dir = gr.Textbox(
                                    label="Video Directory",
                                    interactive=False,
                                    scale=2,
                                )

                        # Operation Controls Section
                        gr.Markdown("#### ⚡ Operation Controls")

                        # Tabs for different operations
                        with gr.Tabs():
                            # Inference tab
                            with gr.Tab("Inference"):
                                gr.Markdown("##### Inference Parameters")

                                with gr.Group():
                                    # Weights control
                                    gr.Markdown("**Control Weights**")
                                    with gr.Row():
                                        weight_vis = gr.Slider(
                                            label="Visual",
                                            minimum=0.0,
                                            maximum=1.0,
                                            value=0.25,
                                            step=0.05,
                                        )
                                        weight_edge = gr.Slider(
                                            label="Edge",
                                            minimum=0.0,
                                            maximum=1.0,
                                            value=0.25,
                                            step=0.05,
                                        )
                                    with gr.Row():
                                        weight_depth = gr.Slider(
                                            label="Depth",
                                            minimum=0.0,
                                            maximum=1.0,
                                            value=0.25,
                                            step=0.05,
                                        )
                                        weight_seg = gr.Slider(
                                            label="Segmentation",
                                            minimum=0.0,
                                            maximum=1.0,
                                            value=0.25,
                                            step=0.05,
                                        )

                                    # Advanced parameters
                                    with gr.Accordion("Advanced", open=False):
                                        with gr.Row():
                                            inf_steps = gr.Number(
                                                label="Steps",
                                                value=35,
                                                minimum=1,
                                                maximum=100,
                                            )
                                            inf_guidance = gr.Number(
                                                label="Guidance (CFG)",
                                                value=7.0,
                                                minimum=1.0,
                                                maximum=20.0,
                                            )
                                            inf_seed = gr.Number(
                                                label="Seed",
                                                value=1,
                                                minimum=0,
                                            )

                                        with gr.Row():
                                            inf_fps = gr.Number(
                                                label="FPS",
                                                value=24,
                                                minimum=1,
                                                maximum=60,
                                            )
                                            inf_sigma_max = gr.Number(
                                                label="Sigma Max",
                                                value=70.0,
                                            )

                                        inf_blur_strength = gr.Dropdown(
                                            label="Blur Strength",
                                            choices=[
                                                "very_low",
                                                "low",
                                                "medium",
                                                "high",
                                                "very_high",
                                            ],
                                            value="medium",
                                        )
                                        inf_canny_threshold = gr.Dropdown(
                                            label="Canny Threshold",
                                            choices=[
                                                "very_low",
                                                "low",
                                                "medium",
                                                "high",
                                                "very_high",
                                            ],
                                            value="medium",
                                        )

                                # Run button
                                run_inference_btn = gr.Button(
                                    "🚀 Run Inference",
                                    variant="primary",
                                    size="lg",
                                )

                                inference_status = gr.Markdown("")

                            # Prompt Enhance tab
                            with gr.Tab("Prompt Enhance"):
                                gr.Markdown("##### Enhancement Settings")

                                with gr.Group():
                                    gr.Markdown("**AI Model:** pixtral")

                                    enhance_create_new = gr.Radio(
                                        label="Action",
                                        choices=[
                                            ("Create new enhanced prompt", True),
                                            ("Overwrite existing prompt", False),
                                        ],
                                        value=True,
                                    )

                                    enhance_force = gr.Checkbox(
                                        label="Force overwrite (delete existing runs if needed)",
                                        value=False,
                                        visible=False,  # Show only when overwrite is selected
                                    )

                                # Run button
                                run_enhance_btn = gr.Button(
                                    "✨ Enhance Prompts",
                                    variant="primary",
                                    size="lg",
                                )

                                enhance_status = gr.Markdown("")

                        # Removed execution status from here - moved to Jobs tab

            # ========================================
            # Tab 4: Outputs (Phase 4 Implementation)
            # ========================================
            with gr.Tab("🎬 Outputs", id=3):
                gr.Markdown("### Output Gallery")
                gr.Markdown("View and download generated video outputs from completed runs")

                with gr.Row():
                    # Left: Filters and run list
                    with gr.Column(scale=1):
                        gr.Markdown("#### Filter Options")

                        with gr.Group():
                            output_status_filter = gr.Dropdown(
                                choices=["completed", "all"],
                                value="completed",
                                label="Run Status",
                                info="Filter by run status",
                            )

                            output_model_filter = gr.Dropdown(
                                choices=["all", "transfer", "upscale"],
                                value="all",
                                label="Model Type",
                                info="Filter by model type",
                            )

                            output_limit = gr.Number(
                                value=20,
                                label="Limit",
                                minimum=1,
                                maximum=100,
                                info="Number of outputs to display",
                            )

                            # Individual refresh button removed - using global refresh

                        gr.Markdown("#### Recent Outputs")
                        outputs_table = gr.Dataframe(
                            headers=["Run ID", "Prompt", "Status", "Created"],
                            datatype=["str", "str", "str", "str"],
                            interactive=False,
                            wrap=True,
                        )

                    # Right: Video gallery and details
                    with gr.Column(scale=2):
                        gr.Markdown("#### Generated Videos")

                        output_gallery = gr.Gallery(
                            label="Output Videos",
                            show_label=False,
                            elem_id="output_gallery",
                            columns=3,
                            rows=2,
                            object_fit="contain",
                            height=400,
                            preview=False,
                            allow_preview=False,
                            interactive=False,  # Prevent uploads - this is output only
                        )

                        # Selected output details
                        with gr.Group(
                            visible=False, elem_classes=["detail-card"]
                        ) as output_details_group:
                            gr.Markdown("#### 🎬 Output Details")

                            # Structured output fields matching Prompt Details style
                            output_run_id = gr.Textbox(
                                label="Run ID",
                                interactive=False,
                                elem_classes=["loading-skeleton"],
                            )

                            with gr.Row():
                                output_status = gr.Textbox(
                                    label="Status",
                                    interactive=False,
                                    scale=1,
                                )
                                output_created = gr.Textbox(
                                    label="Created",
                                    interactive=False,
                                    scale=3,
                                )

                            output_prompt_name = gr.Textbox(
                                label="Prompt Name",
                                interactive=False,
                            )

                            output_prompt_text = gr.Textbox(
                                label="Prompt Text",
                                lines=3,
                                interactive=False,
                            )

                            with gr.Row():
                                output_input_color = gr.Textbox(
                                    label="Input Color Video",
                                    interactive=False,
                                    scale=1,
                                )
                                output_input_depth = gr.Textbox(
                                    label="Input Depth Video",
                                    interactive=False,
                                    scale=1,
                                )
                                output_input_seg = gr.Textbox(
                                    label="Input Segmentation Video",
                                    interactive=False,
                                    scale=1,
                                )

                            with gr.Row():
                                output_video = gr.Video(
                                    label="Generated Video", height=350, autoplay=False
                                )

                            with gr.Row():
                                gr.Button("💾 Download Video", variant="primary", size="sm")

                                output_path_display = gr.Textbox(
                                    label="Output Path", interactive=False, visible=False
                                )

            # ========================================
            # Tab 4: Run History - Comprehensive Run Management
            # ========================================
            with gr.Tab("📊 Run History", id=4):
                gr.Markdown("### Comprehensive Run History & Management")
                gr.Markdown("View, filter, and manage all runs with detailed information")

                with gr.Row():
                    # Left: Filters and controls
                    with gr.Column(scale=1):
                        gr.Markdown("#### 🔍 Filter Options")

                        with gr.Group(elem_classes=["detail-card"]):
                            history_status_filter = gr.Dropdown(
                                choices=[
                                    "all",
                                    "completed",
                                    "running",
                                    "pending",
                                    "failed",
                                    "cancelled",
                                ],
                                value="all",
                                label="Status Filter",
                                info="Filter runs by status",
                            )

                            history_date_filter = gr.Dropdown(
                                choices=[
                                    "all",
                                    "today",
                                    "yesterday",
                                    "last_7_days",
                                    "last_30_days",
                                ],
                                value="all",
                                label="Date Range",
                                info="Filter by creation date",
                            )

                            history_search = gr.Textbox(
                                label="Search",
                                placeholder="Search by prompt text or ID...",
                                info="Search in prompt text or run ID",
                            )

                            history_limit = gr.Number(
                                value=100,
                                label="Max Results",
                                minimum=10,
                                maximum=500,
                                info="Maximum number of runs to display",
                            )

                            # Individual refresh button removed - using global refresh

                        # Statistics Panel
                        gr.Markdown("#### 📈 Statistics")
                        with gr.Group(elem_classes=["detail-card"]):
                            history_stats = gr.Markdown(
                                value="Loading statistics...", elem_classes=["loading-skeleton"]
                            )

                    # Center: Run table with enhanced display
                    with gr.Column(scale=3):
                        gr.Markdown("#### 📋 Run Records")

                        history_table = gr.Dataframe(
                            headers=[
                                "☑",
                                "Run ID",
                                "Prompt",
                                "Status",
                                "Duration",
                                "Created",
                                "Output",
                            ],
                            datatype=["bool", "str", "str", "str", "str", "str", "str"],
                            interactive=False,  # Set to False to enable proper row selection
                            col_count=(7, "fixed"),
                            wrap=True,
                            elem_classes=["prompts-table"],
                        )

                        # Batch operations
                        with gr.Row(elem_classes=["batch-operation"]):
                            history_select_all_btn = gr.Button(
                                "☑ Select All", size="sm", variant="secondary"
                            )
                            history_clear_selection_btn = gr.Button(
                                "☐ Clear Selection", size="sm", variant="secondary"
                            )
                            history_selection_count = gr.Markdown("**0** runs selected")
                            history_delete_selected_btn = gr.Button(
                                "🗑️ Delete Selected", size="sm", variant="stop", visible=False
                            )

                    # Right: Detailed run information
                    with gr.Column(scale=2):
                        with gr.Group(elem_classes=["detail-card"]):
                            gr.Markdown("#### 📝 Run Details")

                            with gr.Tabs():
                                # General Info Tab
                                with gr.Tab("General"):
                                    history_run_id = gr.Textbox(
                                        label="Run ID",
                                        interactive=False,
                                        elem_classes=["loading-skeleton"],
                                    )

                                    with gr.Row():
                                        history_status = gr.Textbox(
                                            label="Status", interactive=False, scale=1
                                        )
                                        history_duration = gr.Textbox(
                                            label="Duration", interactive=False, scale=1
                                        )
                                        history_run_type = gr.Textbox(
                                            label="Run Type", interactive=False, scale=1
                                        )

                                    history_prompt_name = gr.Textbox(
                                        label="Prompt Name", interactive=False
                                    )

                                    history_prompt_text = gr.Textbox(
                                        label="Prompt Text", lines=4, interactive=False
                                    )

                                    with gr.Row():
                                        history_created = gr.Textbox(
                                            label="Created At", interactive=False, scale=1
                                        )
                                        history_completed = gr.Textbox(
                                            label="Completed At", interactive=False, scale=1
                                        )

                                # Parameters Tab
                                with gr.Tab("Parameters"):
                                    gr.Markdown("#### Control Weights")
                                    with gr.Row():
                                        history_weight_vis = gr.Textbox(
                                            label="Visual", interactive=False, scale=1
                                        )
                                        history_weight_edge = gr.Textbox(
                                            label="Edge", interactive=False, scale=1
                                        )
                                        history_weight_depth = gr.Textbox(
                                            label="Depth", interactive=False, scale=1
                                        )
                                        history_weight_seg = gr.Textbox(
                                            label="Segmentation", interactive=False, scale=1
                                        )

                                    gr.Markdown("#### Inference Parameters")
                                    history_params = gr.JSON(label="", container=False)

                                # Logs Tab
                                with gr.Tab("Logs"):
                                    history_log_path = gr.Textbox(
                                        label="Log File Path", interactive=False
                                    )

                                    history_log_content = gr.Textbox(
                                        label="Log Output",
                                        lines=15,
                                        interactive=False,
                                        show_copy_button=True,
                                    )

                                    history_load_logs_btn = gr.Button(
                                        "📄 Load Full Logs", size="sm"
                                    )

                                # Output Tab
                                with gr.Tab("Output"):
                                    history_output_video = gr.Video(
                                        label="Generated Output", height=300, autoplay=False
                                    )

                                    history_output_path = gr.Textbox(
                                        label="Output Path", interactive=False
                                    )

                                    with gr.Row():
                                        gr.Button(
                                            "💾 Download", variant="primary", size="sm"
                                        )  # TODO: Add download handler
                                        gr.Button(
                                            "🗑️ Delete Run", variant="stop", size="sm"
                                        )  # TODO: Add delete handler

            # ========================================
            # Tab 5: Jobs & Queue (formerly Log Monitor)
            # ========================================
            with gr.Tab("📦 Jobs & Queue", id=5):
                gr.Markdown("### Jobs, Queue & Log Monitoring")
                gr.Markdown("Monitor active jobs, queue status, and view real-time logs")

                with gr.Row():
                    with gr.Column(scale=1):
                        # Queue Status Section
                        gr.Markdown("#### 📦 Queue Status")
                        with gr.Group():
                            queue_status = gr.Textbox(
                                label="Current Queue",
                                value="Queue: Empty | GPU: Available",
                                interactive=False,
                            )
                            execution_status = gr.Textbox(
                                label="GPU Status",
                                value="Idle",
                                interactive=False,
                            )
                            # Auto-refresh queue status
                            queue_timer = gr.Timer(value=2.0, active=True)

                        # Active Jobs Section
                        gr.Markdown("#### 🚀 Active Jobs")
                        running_jobs_display = gr.Textbox(
                            label="Running Containers",
                            value="Checking for active containers...",
                            interactive=False,
                            lines=5,
                        )
                        # Individual refresh button removed - using global refresh

                        # Recent Runs
                        gr.Markdown("#### 📋 Recent Runs")
                        recent_runs_table = gr.Dataframe(
                            headers=["Run ID", "Status", "Started"],
                            datatype=["str", "str", "str"],
                            interactive=False,
                            wrap=True,
                        )

                        # Log Streaming Controls
                        gr.Markdown("#### 📊 Log Streaming")
                        job_status = gr.Textbox(
                            label="Stream Status",
                            value="Click 'Start Streaming' to begin",
                            interactive=False,
                        )
                        stream_btn = gr.Button("▶️ Start Streaming", variant="primary", size="sm")

                    with gr.Column(scale=3):
                        gr.Markdown("#### 📝 Log Output")
                        log_display = gr.HTML(
                            value=log_viewer.get_html(),
                            elem_id="log_display",
                        )

                        # Log Statistics at bottom
                        with gr.Row():
                            gr.Textbox(
                                label="Log Statistics",
                                value="Total: 0 | Errors: 0 | Warnings: 0",
                                interactive=False,
                                scale=2,
                            )
                            gr.Button("🗑️ Clear Logs", size="sm", scale=1)

        # ============================================
        # Run History Functions
        # ============================================

        def load_run_history(status_filter, date_filter, search_query, limit):
            """Load run history with filtering and search."""
            try:
                if not ops:
                    return [], "No connection to backend"

                # Get all runs
                runs = ops.list_runs(
                    status=status_filter if status_filter != "all" else None, limit=int(limit)
                )

                # Apply date filter
                from datetime import datetime, timedelta, timezone

                now = datetime.now(timezone.utc)

                if date_filter == "today":
                    cutoff = now - timedelta(days=1)
                elif date_filter == "yesterday":
                    cutoff = now - timedelta(days=2)
                    end_cutoff = now - timedelta(days=1)
                elif date_filter == "last_7_days":
                    cutoff = now - timedelta(days=7)
                elif date_filter == "last_30_days":
                    cutoff = now - timedelta(days=30)
                else:
                    cutoff = None

                if cutoff:
                    filtered_runs = []
                    for run in runs:
                        created = run.get("created_at", "")
                        if created:
                            try:
                                run_time = datetime.fromisoformat(created.replace("Z", "+00:00"))
                                if date_filter == "yesterday":
                                    if cutoff <= run_time < end_cutoff:
                                        filtered_runs.append(run)
                                elif run_time >= cutoff:
                                    filtered_runs.append(run)
                            except Exception:
                                pass  # Skip invalid date formats
                    runs = filtered_runs

                # Apply search filter
                if search_query and search_query.strip():
                    search_lower = search_query.lower()
                    filtered_runs = []
                    for run in runs:
                        # Search in run ID
                        if search_lower in run.get("id", "").lower():
                            filtered_runs.append(run)
                            continue

                        # Search in prompt text
                        prompt_id = run.get("prompt_id")
                        if prompt_id:
                            try:
                                prompt = ops.get_prompt(prompt_id)
                                if prompt and search_lower in prompt.get("prompt_text", "").lower():
                                    filtered_runs.append(run)
                            except Exception:
                                pass  # Skip invalid date formats
                    runs = filtered_runs

                # Format table data
                table_data = []
                for run in runs:
                    run_id = run.get("id", "")
                    status = run.get("status", "unknown")
                    created = run.get("created_at", "")[:19] if run.get("created_at") else ""

                    # Calculate duration for completed runs
                    duration = "-"
                    if status == "completed" and run.get("completed_at"):
                        try:
                            start = datetime.fromisoformat(
                                run.get("created_at", "").replace("Z", "+00:00")
                            )
                            end = datetime.fromisoformat(
                                run.get("completed_at", "").replace("Z", "+00:00")
                            )
                            delta = end - start
                            minutes = int(delta.total_seconds() / 60)
                            seconds = int(delta.total_seconds() % 60)
                            duration = f"{minutes}m {seconds}s"
                        except Exception:
                            pass  # Skip invalid date formats

                    # Get prompt name
                    prompt_name = "-"
                    prompt_id = run.get("prompt_id")
                    if prompt_id:
                        try:
                            prompt = ops.get_prompt(prompt_id)
                            if prompt:
                                prompt_name = prompt.get("parameters", {}).get("name", "unnamed")
                                if len(prompt_name) > 30:
                                    prompt_name = prompt_name[:27] + "..."
                        except Exception:
                            pass  # Skip invalid date formats

                    # Check for output
                    output_exists = "No"
                    output_path = Path("outputs") / f"run_{run_id}" / "outputs" / "output.mp4"
                    if output_path.exists():
                        output_exists = "Yes"

                    table_data.append(
                        [
                            False,  # Checkbox
                            run_id,
                            prompt_name,
                            status,
                            duration,
                            created,
                            output_exists,
                        ]
                    )

                # Calculate statistics
                total = len(runs)
                completed = sum(1 for r in runs if r.get("status") == "completed")
                running = sum(1 for r in runs if r.get("status") == "running")
                pending = sum(1 for r in runs if r.get("status") == "pending")
                failed = sum(1 for r in runs if r.get("status") == "failed")

                stats_text = f"""**Total Runs:** {total}

**Status Breakdown:**
- ✅ Completed: {completed}
- 🔄 Running: {running}
- ⏳ Pending: {pending}
- ❌ Failed: {failed}

**Success Rate:** {(completed / total * 100) if total > 0 else 0:.1f}%
"""

                return table_data, stats_text

            except Exception as e:
                logger.error("Failed to load run history: {}", e)
                return [], f"Error: {e}"

        def select_run_from_history(evt: gr.SelectData, table_data):
            """Handle run selection from history table."""
            try:
                import pandas as pd

                if evt.index is None or table_data is None:
                    return [
                        gr.update(value=""),  # history_run_id
                        gr.update(value=""),  # history_status
                        gr.update(value=""),  # history_duration
                        gr.update(value=""),  # history_run_type
                        gr.update(value=""),  # history_prompt_name
                        gr.update(value=""),  # history_prompt_text
                        gr.update(value=""),  # history_created
                        gr.update(value=""),  # history_completed
                        gr.update(value=""),  # history_weight_vis
                        gr.update(value=""),  # history_weight_edge
                        gr.update(value=""),  # history_weight_depth
                        gr.update(value=""),  # history_weight_seg
                        gr.update(value={}),  # history_params
                        gr.update(value=""),  # history_log_path
                        gr.update(value=""),  # history_log_content
                        gr.update(value=None),  # history_output_video
                        gr.update(value=""),  # history_output_path
                    ]

                # Check if table_data is empty DataFrame
                if isinstance(table_data, pd.DataFrame) and table_data.empty:
                    return [
                        gr.update(value=""),  # history_run_id
                        gr.update(value=""),  # history_status
                        gr.update(value=""),  # history_duration
                        gr.update(value=""),  # history_run_type
                        gr.update(value=""),  # history_prompt_name
                        gr.update(value=""),  # history_prompt_text
                        gr.update(value=""),  # history_created
                        gr.update(value=""),  # history_completed
                        gr.update(value=""),  # history_weight_vis
                        gr.update(value=""),  # history_weight_edge
                        gr.update(value=""),  # history_weight_depth
                        gr.update(value=""),  # history_weight_seg
                        gr.update(value={}),  # history_params
                        gr.update(value=""),  # history_log_path
                        gr.update(value=""),  # history_log_content
                        gr.update(value=None),  # history_output_video
                        gr.update(value=""),  # history_output_path
                    ]

                # Get selected row
                row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index

                if isinstance(table_data, pd.DataFrame):
                    row = table_data.iloc[row_idx]
                    run_id = str(row.iloc[1]) if len(row) > 1 else ""
                else:
                    row = table_data[row_idx] if row_idx < len(table_data) else []
                    run_id = str(row[1]) if len(row) > 1 else ""

                if not run_id or not ops:
                    return [
                        gr.update(value=""),  # history_run_id
                        gr.update(value=""),  # history_status
                        gr.update(value=""),  # history_duration
                        gr.update(value=""),  # history_run_type
                        gr.update(value=""),  # history_prompt_name
                        gr.update(value=""),  # history_prompt_text
                        gr.update(value=""),  # history_created
                        gr.update(value=""),  # history_completed
                        gr.update(value=""),  # history_weight_vis
                        gr.update(value=""),  # history_weight_edge
                        gr.update(value=""),  # history_weight_depth
                        gr.update(value=""),  # history_weight_seg
                        gr.update(value={}),  # history_params
                        gr.update(value=""),  # history_log_path
                        gr.update(value=""),  # history_log_content
                        gr.update(value=None),  # history_output_video
                        gr.update(value=""),  # history_output_path
                    ]

                # Get full run details
                run = ops.get_run(run_id)
                if not run:
                    return [
                        gr.update(value=""),  # history_run_id
                        gr.update(value=""),  # history_status
                        gr.update(value=""),  # history_duration
                        gr.update(value=""),  # history_run_type
                        gr.update(value=""),  # history_prompt_name
                        gr.update(value=""),  # history_prompt_text
                        gr.update(value=""),  # history_created
                        gr.update(value=""),  # history_completed
                        gr.update(value=""),  # history_weight_vis
                        gr.update(value=""),  # history_weight_edge
                        gr.update(value=""),  # history_weight_depth
                        gr.update(value=""),  # history_weight_seg
                        gr.update(value={}),  # history_params
                        gr.update(value=""),  # history_log_path
                        gr.update(value=""),  # history_log_content
                        gr.update(value=None),  # history_output_video
                        gr.update(value=""),  # history_output_path
                    ]

                # Extract basic info
                status = run.get("status", "unknown")
                run_type = run.get("model_type", "unknown").title()  # Get run type and capitalize
                created = run.get("created_at", "")[:19] if run.get("created_at") else ""
                completed = run.get("completed_at", "")[:19] if run.get("completed_at") else "-"

                # Calculate duration
                duration = "-"
                if status == "completed" and run.get("completed_at"):
                    try:
                        from datetime import datetime

                        start = datetime.fromisoformat(
                            run.get("created_at", "").replace("Z", "+00:00")
                        )
                        end = datetime.fromisoformat(
                            run.get("completed_at", "").replace("Z", "+00:00")
                        )
                        delta = end - start
                        minutes = int(delta.total_seconds() / 60)
                        seconds = int(delta.total_seconds() % 60)
                        duration = f"{minutes}m {seconds}s"
                    except Exception:
                        pass  # Skip invalid data

                # Get prompt details
                prompt_name = ""
                prompt_text = ""
                prompt_id = run.get("prompt_id")
                if prompt_id:
                    try:
                        prompt = ops.get_prompt(prompt_id)
                        if prompt:
                            prompt_name = prompt.get("parameters", {}).get("name", "unnamed")
                            prompt_text = prompt.get("prompt_text", "")
                    except Exception:
                        pass  # Skip invalid data

                # Get parameters
                params = run.get("parameters", {})
                weights = params.get("weights", {})

                # Extract individual weight values
                weight_vis = str(weights.get("vis", ""))
                weight_edge = str(weights.get("edge", ""))
                weight_depth = str(weights.get("depth", ""))
                weight_seg = str(weights.get("seg", ""))

                inference_params = {
                    "num_steps": params.get("num_steps", 35),
                    "guidance_scale": params.get("guidance_scale", 7.0),
                    "seed": params.get("seed", 1),
                    "fps": params.get("fps", 24),
                    "sigma_max": params.get("sigma_max", 70.0),
                    "blur_strength": params.get("blur_strength", "medium"),
                    "canny_threshold": params.get("canny_threshold", "medium"),
                }

                # Get log path
                log_path = run.get("log_path", "")
                log_content = "Click 'Load Full Logs' to view log output"

                # Get output path and video
                output_path = ""
                output_video = None
                run_output_dir = Path("outputs") / f"run_{run_id}" / "outputs"
                video_file = run_output_dir / "output.mp4"
                if video_file.exists():
                    output_path = str(video_file)
                    output_video = str(video_file)

                return [
                    gr.update(value=run_id),  # history_run_id
                    gr.update(value=status),  # history_status
                    gr.update(value=duration),  # history_duration
                    gr.update(value=run_type),  # history_run_type (NEW)
                    gr.update(value=prompt_name),  # history_prompt_name
                    gr.update(value=prompt_text),  # history_prompt_text
                    gr.update(value=created),  # history_created
                    gr.update(value=completed),  # history_completed
                    gr.update(value=weight_vis),  # history_weight_vis (NEW)
                    gr.update(value=weight_edge),  # history_weight_edge (NEW)
                    gr.update(value=weight_depth),  # history_weight_depth (NEW)
                    gr.update(value=weight_seg),  # history_weight_seg (NEW)
                    gr.update(value=inference_params),  # history_params
                    gr.update(value=log_path),  # history_log_path
                    gr.update(value=log_content),  # history_log_content
                    gr.update(value=output_video),  # history_output_video
                    gr.update(value=output_path),  # history_output_path
                ]

            except Exception as e:
                logger.error("Error selecting run from history: {}", e)
                return [
                    gr.update(value=""),  # history_run_id
                    gr.update(value=""),  # history_status
                    gr.update(value=""),  # history_duration
                    gr.update(value=""),  # history_run_type
                    gr.update(value=""),  # history_prompt_name
                    gr.update(value=""),  # history_prompt_text
                    gr.update(value=""),  # history_created
                    gr.update(value=""),  # history_completed
                    gr.update(value=""),  # history_weight_vis
                    gr.update(value=""),  # history_weight_edge
                    gr.update(value=""),  # history_weight_depth
                    gr.update(value=""),  # history_weight_seg
                    gr.update(value=""),  # history_params
                    gr.update(value=""),  # history_log_path
                    gr.update(value=""),  # history_log_content
                    gr.update(value=None),  # history_output_video
                    gr.update(value=""),  # history_output_path
                ]

        def load_run_logs(run_id):
            """Load full log content for a run."""
            try:
                if not run_id or not ops:
                    return "No run selected"

                run = ops.get_run(run_id)
                if not run:
                    return "Run not found"

                log_path = run.get("log_path", "")
                if not log_path:
                    return "No log path available for this run"

                # Try to read log file
                log_file = Path(log_path)
                if log_file.exists():
                    with open(log_file) as f:
                        content = f.read()
                        if content:
                            return content
                        else:
                            return "Log file is empty"
                else:
                    return f"Log file not found: {log_path}"

            except Exception as e:
                logger.error("Error loading logs: {}", e)
                return f"Error loading logs: {e}"

        def update_history_selection_count(table_data):
            """Update the selection count for history table."""
            try:
                if table_data is None:
                    return "**0** runs selected", gr.update(visible=False)

                import pandas as pd

                if isinstance(table_data, pd.DataFrame):
                    if not table_data.empty:
                        first_col_values = (
                            table_data.values[:, 0] if table_data.shape[1] > 0 else []
                        )
                        selected = sum(1 for val in first_col_values if val is True)
                    else:
                        selected = 0
                else:
                    selected = sum(1 for row in table_data if len(row) > 0 and row[0] is True)

                count_text = f"**{selected}** run{'s' if selected != 1 else ''} selected"
                show_delete = selected > 0

                return count_text, gr.update(visible=show_delete)

            except Exception as e:
                logger.debug("Error counting selection: {}", e)
                return "**0** runs selected", gr.update(visible=False)

        def select_all_runs(table_data):
            """Select all runs in the history table."""
            if table_data is None:
                return []

            import pandas as pd

            if isinstance(table_data, pd.DataFrame):
                table_data = table_data.copy()
                table_data.iloc[:, 0] = True
                return table_data
            else:
                updated_data = []
                for row in table_data:
                    new_row = row.copy() if isinstance(row, list) else list(row)
                    new_row[0] = True
                    updated_data.append(new_row)
                return updated_data

        def clear_all_runs(table_data):
            """Clear all selections in the history table."""
            if table_data is None:
                return []

            import pandas as pd

            if isinstance(table_data, pd.DataFrame):
                table_data = table_data.copy()
                table_data.iloc[:, 0] = False
                return table_data
            else:
                updated_data = []
                for row in table_data:
                    new_row = row.copy() if isinstance(row, list) else list(row)
                    new_row[0] = False
                    updated_data.append(new_row)
                return updated_data

        # ============================================
        # Event Handlers
        # ============================================

        # Global refresh function
        def global_refresh_all():
            """Refresh all data across all tabs."""
            from datetime import datetime

            try:
                # Get current status
                status = f"✅ Connected | Last refresh: {datetime.now().strftime('%H:%M:%S')}"

                # Load all data
                inputs_data = load_input_gallery()
                prompts_data = load_ops_prompts(50)
                outputs_data = load_outputs("all", "all", 50)
                history_data = load_run_history("all", "all", "", 100)
                jobs_data = check_running_jobs()

                return (
                    status,  # refresh_status
                    inputs_data,  # input_gallery
                    prompts_data,  # ops_prompts_table
                    outputs_data[0],  # output_gallery
                    outputs_data[1],  # outputs_table
                    history_data[0],  # history_table
                    history_data[1],  # history_stats
                    jobs_data[0],  # running_jobs_display
                    jobs_data[1],  # job_status
                )
            except Exception as e:
                logger.error("Error during global refresh: %s", str(e))
                return (
                    f"❌ Error: {e!s}",
                    gr.Gallery(),
                    gr.Dataframe(),
                    gr.Gallery(),
                    gr.Dataframe(),
                    gr.Dataframe(),
                    gr.Textbox(),
                    gr.Textbox(),
                    gr.Textbox(),
                )

        # Global refresh controls
        # Connect timer to refresh function
        global_refresh_timer.tick(
            fn=global_refresh_all,
            inputs=[],
            outputs=[
                refresh_status,
                input_gallery,
                ops_prompts_table,
                output_gallery,
                outputs_table,
                history_table,
                history_stats,
                running_jobs_display,
                job_status,
            ],
        )

        # Manual refresh button
        manual_refresh_btn.click(
            fn=global_refresh_all,
            inputs=[],
            outputs=[
                refresh_status,
                input_gallery,
                ops_prompts_table,
                output_gallery,
                outputs_table,
                history_table,
                history_stats,
                running_jobs_display,
                job_status,
            ],
        )

        # Auto-refresh toggle
        auto_refresh_enabled.change(
            fn=lambda enabled: gr.Timer(active=enabled),
            inputs=[auto_refresh_enabled],
            outputs=[global_refresh_timer],
        )

        # Refresh interval change
        refresh_interval.change(
            fn=lambda interval: gr.Timer(value=interval, active=True),
            inputs=[refresh_interval],
            outputs=[global_refresh_timer],
        )

        # Input browser events
        input_gallery.select(
            fn=on_input_select,
            inputs=[input_gallery],
            outputs=[
                selected_dir_path,
                preview_group,
                input_tabs_group,  # The tabs container
                input_name,
                input_path,
                input_created,
                input_resolution,  # Now plain text
                input_duration,  # Now plain text
                input_fps,  # Now plain text
                input_codec,  # Now plain text
                input_files,
                video_preview_gallery,
                create_video_dir,  # Auto-fill the video directory in create prompt form
            ],
        )

        # Removed redundant event handler - create_video_dir is already updated by input_gallery.select

        # Create prompt button event (from Inputs tab)
        create_prompt_btn.click(
            fn=create_prompt,
            inputs=[
                create_prompt_text,
                create_video_dir,
                create_name,
                create_negative,
            ],
            outputs=[create_status],
        )

        # Load initial data will be done via app.load event

        # Output gallery events
        def load_outputs(status_filter, model_filter, limit):
            """Load outputs from completed runs using CosmosAPI."""
            try:
                if not ops:
                    logger.warning("CosmosAPI not initialized")
                    return [], []

                # Use CosmosAPI to get runs
                runs = ops.list_runs(
                    status=status_filter if status_filter != "all" else None, limit=int(limit)
                )
                logger.info("Found {} runs from CosmosAPI", len(runs))

                # Filter by model type if specified
                if model_filter != "all":
                    runs = [r for r in runs if r.get("model_type") == model_filter]

                # Filter runs with video outputs
                runs_with_outputs = []
                gallery_items = []

                for run in runs:
                    # Construct the path to the output video based on run ID
                    # Run IDs are in format "rs_XXXXX" and directories are "run_rs_XXXXX"
                    run_id = run.get("id")
                    output_path = Path("outputs") / f"run_{run_id}" / "outputs" / "output.mp4"
                    logger.debug("Checking for output at: {}", output_path)

                    if output_path.exists():
                        runs_with_outputs.append(run)

                        # Get prompt text from the prompt if available
                        prompt_text = "No prompt"
                        prompt_id = run.get("prompt_id")
                        if prompt_id:
                            try:
                                prompt = ops.get_prompt(prompt_id)
                                if prompt:
                                    prompt_text = prompt.get("prompt_text", "No prompt")
                            except Exception as e:
                                logger.debug(f"Could not get prompt {prompt_id}: {e}")
                                prompt_text = "N/A"

                        # Add to gallery (path, label)
                        gallery_items.append(
                            (str(output_path), f"Run {run['id'][:8]}: {prompt_text[:50]}...")
                        )

                # Create table data
                table_data = []
                for run in runs_with_outputs[:10]:  # Limit table to 10 rows
                    # Get prompt name
                    prompt_name = "N/A"
                    prompt_id = run.get("prompt_id")
                    if prompt_id:
                        try:
                            prompt = ops.get_prompt(prompt_id)
                            if prompt:
                                prompt_name = prompt.get("parameters", {}).get(
                                    "name", prompt.get("prompt_text", "N/A")[:30]
                                )
                                if len(prompt_name) > 30:
                                    prompt_name = prompt_name[:30] + "..."
                        except Exception as e:
                            logger.debug(f"Could not get prompt {prompt_id}: {e}")
                            prompt_name = "N/A"

                    table_data.append(
                        [
                            run["id"],  # Store full ID, Gradio will truncate display
                            prompt_name,
                            run.get("status", "unknown"),
                            run.get("created_at", "N/A")[:19],
                        ]
                    )

                logger.info(
                    "Returning {} gallery items and {} table rows",
                    len(gallery_items),
                    len(table_data),
                )
                return gallery_items, table_data

            except Exception as e:
                logger.error(f"Error loading outputs: {e}")
                return [], []

        def select_output(evt: gr.SelectData, gallery_data, table_data):
            """Handle output selection from gallery - show full run details."""
            logger.info(
                "select_output called - evt.index: {}, gallery_data: {}, table_data type: {}",
                evt.index,
                bool(gallery_data),
                type(table_data),
            )
            if evt.index is not None and gallery_data:
                selected = gallery_data[evt.index]
                video_path = selected[0] if isinstance(selected, tuple) else selected
                logger.info("Selected output video: {}", video_path)

                # Get run_id from the table data at the same index
                # Table data format: [run_id, prompt_name, status, created_at]
                run_id = None
                if table_data is not None and len(table_data) > 0 and evt.index < len(table_data):
                    # table_data is a DataFrame, use iloc for positional indexing
                    run_id = table_data.iloc[evt.index, 0]  # First column is run_id
                    logger.info("Got run_id from table data: {}", run_id)

                if not run_id and Path(video_path).exists():
                    # Fallback: try to extract from path if it's not a temp file
                    if "gradio" not in str(video_path).lower():
                        path_parts = Path(video_path).parts
                        for part in path_parts:
                            if part.startswith("run_"):
                                run_id = part[4:]  # Remove 'run_' prefix
                                break
                        logger.info("Extracted run_id from path: {}", run_id)

                # Initialize variables for structured fields
                run = None
                prompt = None
                inputs = {}
                prompt_id = None

                # Get full run details using CosmosAPI
                if run_id and ops:
                    logger.info("Fetching run with ID: {}", run_id)
                    run = ops.get_run(run_id)
                    logger.info("Got run data: {}", bool(run))
                    if run:
                        prompt_id = run.get("prompt_id")

                        # Get prompt details if available
                        if prompt_id:
                            try:
                                prompt = ops.get_prompt(prompt_id)
                                if prompt:
                                    inputs = prompt.get("inputs", {})
                            except Exception as e:
                                logger.error("Error getting prompt {}: {}", prompt_id, e)

                # Extract details for structured fields
                run_id_text = run.get("id", "unknown") if run else ""
                status_text = run.get("status", "unknown") if run else ""
                created_text = run.get("created_at", "")[:19] if run else ""

                prompt_name_text = (
                    prompt.get("parameters", {}).get("name", "unnamed") if prompt else ""
                )
                prompt_text_full = prompt.get("prompt_text", "") if prompt else ""

                # Input paths
                color_path = inputs.get("video", "") if inputs else ""
                depth_path = inputs.get("depth", "") if inputs else ""
                seg_path = inputs.get("seg", "") if inputs else ""

                return (
                    gr.update(visible=True),  # output_details_group
                    run_id_text,  # output_run_id
                    status_text,  # output_status
                    created_text,  # output_created
                    prompt_name_text,  # output_prompt_name
                    prompt_text_full,  # output_prompt_text
                    color_path,  # output_input_color
                    depth_path,  # output_input_depth
                    seg_path,  # output_input_seg
                    str(video_path),  # output_video
                    str(video_path),  # output_path_display
                )

            logger.info("No valid selection, returning default values")
            return (
                gr.update(visible=False),  # output_details_group
                "",  # output_run_id
                "",  # output_status
                "",  # output_created
                "",  # output_prompt_name
                "",  # output_prompt_text
                "",  # output_input_color
                "",  # output_input_depth
                "",  # output_input_seg
                None,  # output_video
                "",  # output_path_display
            )

        def download_output(output_path):
            """Prepare output for download."""
            if output_path and Path(output_path).exists():
                return output_path
            return None

        # refresh_outputs_btn.click removed - using global refresh

        output_gallery.select(
            fn=select_output,
            inputs=[output_gallery, outputs_table],
            outputs=[
                output_details_group,
                output_run_id,
                output_status,
                output_created,
                output_prompt_name,
                output_prompt_text,
                output_input_color,
                output_input_depth,
                output_input_seg,
                output_video,
                output_path_display,
            ],
        )

        # Download functionality will be handled through the video component itself

        # Operations tab events
        # ops_refresh_btn.click removed - using global refresh

        # Selection controls
        clear_selection_btn.click(
            fn=clear_all_prompts, inputs=[ops_prompts_table], outputs=[ops_prompts_table]
        ).then(fn=update_selection_count, inputs=[ops_prompts_table], outputs=[selection_count])

        # Update selection count when table changes
        ops_prompts_table.change(
            fn=update_selection_count, inputs=[ops_prompts_table], outputs=[selection_count]
        )

        # Add row selection handler for prompt details
        ops_prompts_table.select(
            fn=on_prompt_row_select,
            inputs=[ops_prompts_table],
            outputs=[
                selected_prompt_id,
                selected_prompt_name,
                selected_prompt_text,
                selected_prompt_negative,
                selected_prompt_created,
                selected_prompt_video_dir,
                selected_prompt_enhanced,
            ],
        )

        # Enhance tab - toggle force visibility
        enhance_create_new.change(
            fn=toggle_enhance_force_visibility, inputs=[enhance_create_new], outputs=[enhance_force]
        )

        # Run inference button
        run_inference_btn.click(
            fn=run_inference_on_selected,
            inputs=[
                ops_prompts_table,
                weight_vis,
                weight_edge,
                weight_depth,
                weight_seg,
                inf_steps,
                inf_guidance,
                inf_seed,
                inf_fps,
                inf_sigma_max,
                inf_blur_strength,
                inf_canny_threshold,
            ],
            outputs=[inference_status, execution_status],
        ).then(
            # Refresh prompts table after inference
            fn=load_ops_prompts,
            inputs=[ops_limit],
            outputs=[ops_prompts_table],
        )

        # Run enhance button
        run_enhance_btn.click(
            fn=run_enhance_on_selected,
            inputs=[ops_prompts_table, enhance_create_new, enhance_force],
            outputs=[enhance_status, execution_status],
        ).then(
            # Refresh prompts table after enhancement
            fn=load_ops_prompts,
            inputs=[ops_limit],
            outputs=[ops_prompts_table],
        )

        # Log monitor events (existing)
        # check_jobs_btn.click removed - using global refresh

        stream_btn.click(
            fn=start_log_streaming,
            inputs=[],
            outputs=[job_status, log_display],
        )

        # Queue status timer - updates every 2 seconds
        queue_timer.tick(
            fn=get_queue_status,
            inputs=[],
            outputs=[queue_status],
        ).then(
            fn=get_recent_runs,
            inputs=[],
            outputs=[recent_runs_table],
        )

        # Run History tab events
        # history_refresh_btn.click removed - using global refresh

        history_table.select(
            fn=select_run_from_history,
            inputs=[history_table],
            outputs=[
                history_run_id,
                history_status,
                history_duration,
                history_run_type,  # NEW
                history_prompt_name,
                history_prompt_text,
                history_created,
                history_completed,
                history_weight_vis,  # NEW
                history_weight_edge,  # NEW
                history_weight_depth,  # NEW
                history_weight_seg,  # NEW
                history_params,
                history_log_path,
                history_log_content,
                history_output_video,
                history_output_path,
            ],
        )

        history_table.change(
            fn=update_history_selection_count,
            inputs=[history_table],
            outputs=[history_selection_count, history_delete_selected_btn],
        )

        history_select_all_btn.click(
            fn=select_all_runs, inputs=[history_table], outputs=[history_table]
        ).then(
            fn=update_history_selection_count,
            inputs=[history_table],
            outputs=[history_selection_count, history_delete_selected_btn],
        )

        history_clear_selection_btn.click(
            fn=clear_all_runs, inputs=[history_table], outputs=[history_table]
        ).then(
            fn=update_history_selection_count,
            inputs=[history_table],
            outputs=[history_selection_count, history_delete_selected_btn],
        )

        history_load_logs_btn.click(
            fn=load_run_logs, inputs=[history_run_id], outputs=[history_log_content]
        )

        # Auto-load data on app start
        app.load(fn=load_input_gallery, inputs=[], outputs=[input_gallery]).then(
            fn=check_running_jobs, inputs=[], outputs=[running_jobs_display, job_status]
        ).then(
            fn=load_outputs,
            inputs=[output_status_filter, output_model_filter, output_limit],
            outputs=[output_gallery, outputs_table],
        ).then(
            fn=lambda: load_ops_prompts(50),  # Load operations prompts
            inputs=[],
            outputs=[ops_prompts_table],
        ).then(
            fn=lambda: load_run_history("all", "all", "", 100),  # Load run history
            inputs=[],
            outputs=[history_table, history_stats],
        )

    return app


if __name__ == "__main__":
    # Get UI configuration from config.toml
    ui_config = config._config_data.get("ui", {})
    host = ui_config.get("host", "127.0.0.1")
    port = ui_config.get("port", 7860)
    share = ui_config.get("share", False)

    logger.info("Starting Cosmos Workflow Manager on {}:{}", host, port)

    app = create_ui()

    # Configure queue for synchronous execution
    # This ensures jobs run sequentially on the GPU
    app.queue(
        max_size=50,  # Maximum number of jobs that can be queued
        default_concurrency_limit=1,  # Process one job at a time (GPU constraint)
        status_update_rate="auto",  # Update queue status automatically
    ).launch(
        share=share,
        server_name=host,
        server_port=port,
        show_error=True,
        inbrowser=True,  # Auto-open browser
    )
