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
    """Create the comprehensive Gradio interface."""

    # Get custom CSS from styles module
    custom_css = get_custom_css()

    # Get refresh interval from config
    ui_config = config._config_data.get("ui", {})
    default_refresh_interval = ui_config.get("refresh_interval", 5)

    with gr.Blocks(title="Cosmos Workflow Manager", css=custom_css) as app:
        gr.Markdown("# 🌌 Cosmos Workflow Manager v1.2")
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
            # Tab 3: Unified Runs (Merged Outputs + Run History)
            # ========================================
            with gr.Tab("🎬 Runs", id=3):
                gr.Markdown("### Run Management Center")
                gr.Markdown(
                    "View, filter, and manage all runs with generated outputs and detailed information"
                )

                with gr.Row():
                    # Left: Filters and Statistics
                    with gr.Column(scale=1):
                        gr.Markdown("#### 🔍 Filter Options")

                        with gr.Group(elem_classes=["detail-card"]):
                            runs_status_filter = gr.Dropdown(
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

                            runs_date_filter = gr.Dropdown(
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

                            runs_search = gr.Textbox(
                                label="Search",
                                placeholder="Search by prompt text or ID...",
                                info="Search in prompt text or run ID",
                            )

                            runs_limit = gr.Number(
                                value=50,
                                label="Max Results",
                                minimum=10,
                                maximum=200,
                                info="Maximum number of runs to display",
                            )

                        gr.Markdown("#### 📊 Statistics")
                        with gr.Group(elem_classes=["detail-card"]):
                            runs_stats = gr.Markdown("Loading statistics...")

                    # Right: Gallery and Table tabs
                    with gr.Column(scale=3):
                        with gr.Tabs():
                            # Generated Videos tab
                            with gr.Tab("Generated Videos"):
                                runs_gallery = gr.Gallery(
                                    label="Output Videos",
                                    show_label=False,
                                    elem_id="runs_gallery",
                                    columns=3,
                                    rows=2,
                                    height=400,
                                    object_fit="contain",
                                    preview=False,  # Disable preview popup
                                    allow_preview=False,  # Disable click to expand
                                    show_download_button=True,
                                    interactive=False,  # Read-only gallery
                                )

                            # Run Records tab
                            with gr.Tab("Run Records"):
                                # Table with batch operations at the top
                                # Batch operations
                                with gr.Row():
                                    runs_select_all_btn = gr.Button("☑ Select All", size="sm")
                                    runs_clear_selection_btn = gr.Button(
                                        "☐ Clear Selection", size="sm"
                                    )
                                    runs_delete_selected_btn = gr.Button(
                                        "🗑️ Delete Selected",
                                        size="sm",
                                        variant="stop",
                                    )
                                    runs_selected_info = gr.Markdown("0 runs selected")

                                runs_table = gr.Dataframe(
                                    headers=[
                                        "Select",
                                        "Run ID",
                                        "Status",
                                        "Prompt",
                                        "Duration",
                                        "Created",
                                        "Completed",
                                    ],
                                    datatype=["bool", "str", "str", "str", "str", "str", "str"],
                                    interactive=True,
                                    max_height=400,  # Reduced height since details are below
                                    elem_classes=["run-history-table"],
                                )

                                # Run Details below the table for better visibility
                                with gr.Group(
                                    visible=False, elem_classes=["detail-card"]
                                ) as runs_details_group:
                                    gr.Markdown("### 📋 Run Details")

                                    with gr.Tabs():
                                        # Main Tab - Day-to-day essentials
                                        with gr.Tab("Main"):
                                            # Generated Output at the top
                                            gr.Markdown("#### Generated Output")
                                            runs_output_video = gr.Video(
                                                label="Output Video",
                                                show_label=False,
                                                autoplay=True,
                                                loop=True,
                                                height=500,
                                            )

                                            # Input Videos with control weights
                                            gr.Markdown("#### Input Videos & Control Weights")

                                            # Control weights in a single row with compact layout
                                            with gr.Row(equal_height=True):
                                                with gr.Column(scale=1, min_width=120):
                                                    gr.Markdown(
                                                        "**Color/Visual**",
                                                        elem_classes=["compact-label"],
                                                    )
                                                    runs_visual_weight = gr.Slider(
                                                        minimum=0,
                                                        maximum=1,
                                                        step=0.1,
                                                        value=0,
                                                        interactive=False,
                                                        show_label=False,
                                                        elem_classes=["compact-slider"],
                                                    )
                                                with gr.Column(scale=1, min_width=120):
                                                    gr.Markdown(
                                                        "**Edge**", elem_classes=["compact-label"]
                                                    )
                                                    runs_edge_weight = gr.Slider(
                                                        minimum=0,
                                                        maximum=1,
                                                        step=0.1,
                                                        value=0,
                                                        interactive=False,
                                                        show_label=False,
                                                        elem_classes=["compact-slider"],
                                                    )
                                                with gr.Column(scale=1, min_width=120):
                                                    gr.Markdown(
                                                        "**Depth**", elem_classes=["compact-label"]
                                                    )
                                                    runs_depth_weight = gr.Slider(
                                                        minimum=0,
                                                        maximum=1,
                                                        step=0.1,
                                                        value=0,
                                                        interactive=False,
                                                        show_label=False,
                                                        elem_classes=["compact-slider"],
                                                    )
                                                with gr.Column(scale=1, min_width=120):
                                                    gr.Markdown(
                                                        "**Segmentation**",
                                                        elem_classes=["compact-label"],
                                                    )
                                                    runs_segmentation_weight = gr.Slider(
                                                        minimum=0,
                                                        maximum=1,
                                                        step=0.1,
                                                        value=0,
                                                        interactive=False,
                                                        show_label=False,
                                                        elem_classes=["compact-slider"],
                                                    )

                                            # Input video gallery - 4 columns to show all videos in one row
                                            runs_input_videos = gr.Gallery(
                                                label="Input Frames",
                                                show_label=False,
                                                columns=4,  # 4 columns for all videos
                                                rows=1,
                                                height=200,
                                                object_fit="contain",
                                                allow_preview=True,
                                                container=True,  # Enable container for proper layout
                                                elem_classes=["input-videos-gallery"],
                                            )

                                            # Full Prompt
                                            gr.Markdown("#### Full Prompt")
                                            runs_prompt_text = gr.Textbox(
                                                label="Prompt Text",
                                                show_label=False,
                                                lines=4,
                                                max_lines=10,
                                                interactive=False,
                                            )

                                            # Hidden components to maintain interface compatibility
                                            runs_detail_id = gr.Textbox(visible=False)
                                            runs_detail_status = gr.Textbox(visible=False)

                                        # Info Tab - Run metadata
                                        with gr.Tab("Info"):
                                            with gr.Row():
                                                runs_info_id = gr.Textbox(
                                                    label="Run ID",
                                                    interactive=False,
                                                )
                                                runs_info_prompt_id = gr.Textbox(
                                                    label="Prompt ID",
                                                    interactive=False,
                                                )

                                            with gr.Row():
                                                runs_info_status = gr.Textbox(
                                                    label="Status",
                                                    interactive=False,
                                                )
                                                runs_info_duration = gr.Textbox(
                                                    label="Duration",
                                                    interactive=False,
                                                )
                                                runs_info_type = gr.Textbox(
                                                    label="Run Type",
                                                    interactive=False,
                                                )

                                            runs_info_prompt_name = gr.Textbox(
                                                label="Prompt Name",
                                                interactive=False,
                                            )

                                            with gr.Row():
                                                runs_info_created = gr.Textbox(
                                                    label="Created",
                                                    interactive=False,
                                                )
                                                runs_info_completed = gr.Textbox(
                                                    label="Completed",
                                                    interactive=False,
                                                )

                                        # Parameters Tab
                                        with gr.Tab("Parameters"):
                                            gr.Markdown("#### Execution Configuration")
                                            runs_params_json = gr.JSON(
                                                label="Inference Parameters",
                                                show_label=False,
                                            )

                                        # Logs Tab
                                        with gr.Tab("Logs"):
                                            runs_log_path = gr.Textbox(
                                                label="Log File Path",
                                                interactive=False,
                                            )
                                            runs_log_output = gr.Code(
                                                label="Log Output (Last 15 Lines)",
                                                language="shell",
                                                lines=15,
                                                interactive=False,
                                            )
                                            with gr.Row():
                                                runs_load_logs_btn = gr.Button("📄 Load Full Logs")
                                                gr.Button("📋 Copy Logs")

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
        # Event Handlers
        # ============================================

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
                    f"❌ Error: {e!s}",
                    gr.Gallery(),
                    gr.Dataframe(),
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

        # ========================================
        # Unified Runs Tab Event Handlers
        # ========================================
        def load_runs_data(status_filter, date_filter, search_text, limit):
            """Load runs data for both gallery and table with filtering."""
            try:
                if not ops:
                    logger.warning("CosmosAPI not initialized")
                    return [], [], "No data available"

                # Query runs with status filter
                all_runs = ops.list_runs(
                    status=None if status_filter == "all" else status_filter, limit=int(limit)
                )

                # Apply date filter
                from datetime import datetime, timedelta, timezone

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

                # Build gallery data (only completed runs with output files)
                gallery_data = []
                for run in filtered_runs:
                    if run.get("status") == "completed":
                        # Check if run has outputs.files array
                        if run.get("outputs") and run["outputs"].get("files"):
                            # Look for output.mp4 in the files list
                            for file_path in run["outputs"]["files"]:
                                if (
                                    "output.mp4" in file_path
                                    and "edge_input_control" not in file_path
                                ):
                                    output_path = Path(file_path)
                                    if output_path.exists() and output_path.is_file():
                                        gallery_data.append((str(output_path), run["id"]))
                                        logger.debug("Added video to gallery: %s", output_path)
                                    else:
                                        logger.debug("Skipping non-existent file: %s", output_path)
                                    break

                # Build table data (all filtered runs)
                table_data = []
                for run in filtered_runs:
                    # Calculate duration
                    duration = "N/A"
                    try:
                        if run.get("completed_at") and run.get("created_at"):
                            created = datetime.fromisoformat(
                                run["created_at"].replace("Z", "+00:00")
                            )
                            completed = datetime.fromisoformat(
                                run["completed_at"].replace("Z", "+00:00")
                            )
                            duration_delta = completed - created
                            minutes = int(duration_delta.total_seconds() / 60)
                            seconds = int(duration_delta.total_seconds() % 60)
                            duration = f"{minutes}m {seconds}s"
                    except Exception:
                        pass

                    # Format dates
                    created_str = (
                        run.get("created_at", "")[:19].replace("T", " ")
                        if run.get("created_at")
                        else ""
                    )
                    completed_str = (
                        run.get("completed_at", "")[:19].replace("T", " ")
                        if run.get("completed_at")
                        else ""
                    )

                    table_data.append(
                        [
                            False,  # Checkbox
                            run.get("id", ""),
                            run.get("status", ""),
                            run.get("prompt_text", "")[:50] + "..."
                            if len(run.get("prompt_text", "")) > 50
                            else run.get("prompt_text", ""),
                            duration,
                            created_str,
                            completed_str,
                        ]
                    )

                # Calculate statistics
                total = len(filtered_runs)
                by_status = {}
                for run in filtered_runs:
                    status = run.get("status", "unknown")
                    by_status[status] = by_status.get(status, 0) + 1

                completed = by_status.get("completed", 0)
                success_rate = f"{(completed / total * 100):.1f}%" if total > 0 else "N/A"

                stats_md = f"""
                **Total Runs:** {total}
                **Success Rate:** {success_rate}

                **By Status:**
                - ✅ Completed: {by_status.get("completed", 0)}
                - 🔄 Running: {by_status.get("running", 0)}
                - ⏳ Pending: {by_status.get("pending", 0)}
                - ❌ Failed: {by_status.get("failed", 0)}
                - 🚫 Cancelled: {by_status.get("cancelled", 0)}
                """

                logger.info(f"Found {total} runs from CosmosAPI")
                logger.info(
                    f"Returning {len(gallery_data)} gallery items and {len(table_data)} table rows"
                )

                return gallery_data, table_data, stats_md

            except Exception as e:
                logger.error("Error loading runs data: %s", e)
                return [], [], f"Error loading data: {e!s}"

        def handle_gallery_selection(evt: gr.SelectData):
            """Handle selection from gallery and update all detail fields."""
            try:
                if not ops or evt.value is None:
                    return (
                        gr.update(visible=False),  # runs_details_group
                        "",
                        "",
                        None,
                        "",
                        0,
                        0,
                        0,
                        0,
                        "",  # Main tab (9 values)
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",  # Info tab (8 values)
                        {},  # Parameters tab (1 value)
                        "",
                        "",  # Logs tab (2 values)
                    )

                # Gallery value is (path, label) tuple
                # Label format is "Run {run_id}: {prompt_text}..."
                label = (
                    evt.value.get("caption", "")
                    if isinstance(evt.value, dict)
                    else evt.value[1]
                    if isinstance(evt.value, tuple)
                    else ""
                )

                # Extract run ID from label
                if label.startswith("Run "):
                    run_id_part = label[4:].split(":")[0]
                    # Full run ID is in the gallery data
                    run_id = (
                        "rs_" + run_id_part if not run_id_part.startswith("rs_") else run_id_part
                    )
                else:
                    # Fallback: try to extract from the label directly
                    run_id = label

                logger.info(f"Selected run ID from gallery: {run_id}")

                # Create a fake SelectData event for handle_run_selection
                fake_evt = gr.SelectData(index=[0], value=None, target=None)
                # Create fake table data with the run_id
                fake_table_data = [["", run_id]]

                return handle_run_selection(fake_evt, fake_table_data)

            except Exception as e:
                logger.error("Error handling gallery selection: %s", e)
                return (
                    gr.update(visible=False),  # runs_details_group
                    "",
                    "",
                    None,
                    "",
                    0,
                    0,
                    0,
                    0,
                    "",  # Main tab (9 values)
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",  # Info tab (8 values)
                    {},  # Parameters tab (1 value)
                    "",
                    "",  # Logs tab (2 values)
                )

        def handle_run_selection(evt: gr.SelectData, table_data=None):
            """Handle selection from table and update all detail fields."""
            try:
                import pandas as pd

                if not ops:
                    return (
                        gr.update(visible=False),  # runs_details_group
                        "",
                        "",
                        None,
                        "",
                        0,
                        0,
                        0,
                        0,
                        "",  # Main tab (9 values) - None for Gallery
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",  # Info tab (8 values)
                        {},  # Parameters tab (1 value)
                        "",
                        "",  # Logs tab (2 values)
                    )

                # Get run ID from table selection
                if evt.index is None or table_data is None:
                    return (
                        gr.update(visible=False),  # runs_details_group
                        "",
                        "",
                        None,
                        "",
                        0,
                        0,
                        0,
                        0,
                        "",  # Main tab (9 values) - None for Gallery
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",  # Info tab (8 values)
                        {},  # Parameters tab (1 value)
                        "",
                        "",  # Logs tab (2 values)
                    )

                # Get run_id from the selected row (column 1 is Run ID)
                if isinstance(table_data, pd.DataFrame):
                    if table_data.empty or evt.index[0] >= len(table_data):
                        return (
                            gr.update(visible=False),  # runs_details_group
                            "",
                            "",
                            None,
                            "",
                            0,
                            0,
                            0,
                            0,
                            "",  # Main tab (9 values) - None for Gallery
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",  # Info tab (8 values)
                            {},  # Parameters tab (1 value)
                            "",
                            "",  # Logs tab (2 values)
                        )
                    run_id = table_data.iloc[evt.index[0], 1]  # Column 1 is Run ID
                else:
                    # Fallback for list data
                    run_id = table_data[evt.index[0]][1] if evt.index[0] < len(table_data) else None

                if not run_id:
                    return (
                        gr.update(visible=False),  # runs_details_group
                        "",
                        "",
                        None,
                        "",
                        0,
                        0,
                        0,
                        0,
                        "",  # Main tab (9 values) - None for Gallery
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",  # Info tab (8 values)
                        {},  # Parameters tab (1 value)
                        "",
                        "",  # Logs tab (2 values)
                    )

                logger.info(f"Selected run ID from table: {run_id}")

                # Fetch full run details
                run = ops.get_run(run_id)
                if not run:
                    return (
                        gr.update(visible=False),  # runs_details_group
                        "",
                        "",
                        None,
                        "",
                        0,
                        0,
                        0,
                        0,
                        "",  # Main tab (9 values) - None for Gallery
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",  # Info tab (8 values)
                        {},  # Parameters tab (1 value)
                        "",
                        "",  # Logs tab (2 values)
                    )

                # Extract control weights from execution_config.weights
                control_weights = run.get("execution_config", {}).get("weights", {})

                # Gather input videos and prompt text from the prompt
                input_videos = []
                prompt_text = ""
                prompt_id = run.get("prompt_id")

                if prompt_id:
                    prompt = ops.get_prompt(prompt_id)
                    if prompt:
                        # Get the prompt text
                        prompt_text = prompt.get("prompt_text", "")
                        video_path = prompt.get("inputs", {}).get("video", "")

                        # Log the raw video path for debugging
                        logger.debug(f"Raw video path from prompt: '{video_path}'")

                        # Only process video path if it's not empty and not just whitespace
                        if video_path and video_path.strip() and video_path.strip() != ".":
                            try:
                                video_path_stripped = video_path.strip()

                                # Skip if it's just the project root or problematic paths
                                # Check against known problematic paths WITHOUT calling Path.cwd()
                                problematic_paths = [
                                    ".",
                                    "",
                                    "F:\\Art\\cosmos-houdini-experiments",
                                    "F:/Art/cosmos-houdini-experiments",
                                    "f:\\art\\cosmos-houdini-experiments",  # lowercase variant
                                    "f:/art/cosmos-houdini-experiments",
                                ]

                                if video_path_stripped.lower() in [
                                    p.lower() for p in problematic_paths
                                ]:
                                    logger.debug(
                                        f"Skipping problematic path: '{video_path_stripped}' (matches project root)"
                                    )
                                else:
                                    # Convert to Path object (wrap in try-catch for permission errors)
                                    try:
                                        video_path_obj = Path(video_path_stripped)
                                    except (PermissionError, OSError) as e:
                                        logger.warning(
                                            f"Could not create Path object from '{video_path_stripped}': {e}"
                                        )
                                        video_path_obj = None

                                    # Make absolute if relative (safer approach)
                                    if video_path_obj and not video_path_obj.is_absolute():
                                        try:
                                            # Try to resolve, but catch any permission errors
                                            video_path_obj = video_path_obj.resolve(strict=False)
                                        except (PermissionError, OSError) as e:
                                            # If resolve fails, skip processing
                                            logger.warning(
                                                f"Could not resolve path '{video_path}': {e}"
                                            )
                                            video_path_obj = None

                                    if video_path_obj:
                                        # Check if this is a file path (not just a directory)
                                        # Wrap in try-catch as these calls can trigger permission errors on Windows
                                        try:
                                            is_file = video_path_obj.is_file()
                                            is_dir = video_path_obj.is_dir()
                                        except (PermissionError, OSError) as e:
                                            logger.warning(
                                                f"Could not check if path is file/dir '{video_path_obj}': {e}"
                                            )
                                            is_file = False
                                            is_dir = False

                                        if is_file:
                                            # Get the directory containing the videos
                                            video_dir = video_path_obj.parent
                                            try:
                                                if video_dir.exists() and video_dir.is_dir():
                                                    # Collect color, depth, and segmentation videos from input directory
                                                    for video_file in sorted(
                                                        video_dir.glob("*.mp4")
                                                    ):
                                                        if video_file.is_file():
                                                            input_videos.append(
                                                                str(video_file.resolve())
                                                            )
                                                    logger.info(
                                                        f"Found {len(input_videos)} videos in {video_dir}"
                                                    )
                                                else:
                                                    logger.warning(
                                                        f"Video directory does not exist: {video_dir}"
                                                    )
                                            except (PermissionError, OSError) as e:
                                                logger.warning(
                                                    f"Error accessing video directory: {e}"
                                                )
                                        elif is_dir:
                                            # If it's a directory, look for videos directly in it
                                            try:
                                                for video_file in sorted(
                                                    video_path_obj.glob("*.mp4")
                                                ):
                                                    if video_file.is_file():
                                                        input_videos.append(
                                                            str(video_file.resolve())
                                                        )
                                            except (PermissionError, OSError) as e:
                                                logger.warning(
                                                    f"Error scanning directory for videos: {e}"
                                                )
                                            logger.info(
                                                f"Found {len(input_videos)} videos in directory {video_path_obj}"
                                            )
                                        else:
                                            logger.warning(
                                                f"Video path does not exist: {video_path_obj}"
                                            )
                            except (PermissionError, OSError) as e:
                                logger.warning(f"Error accessing video path: {e}")
                                # Continue without input videos

                # Add edge control video from outputs if it exists
                if run.get("outputs") and run["outputs"].get("files"):
                    for file_path in run["outputs"]["files"]:
                        if "edge_input_control.mp4" in file_path:
                            # Insert edge video after color (position 1)
                            if len(input_videos) >= 1:
                                input_videos.insert(1, file_path)
                            else:
                                input_videos.append(file_path)
                            logger.info(f"Added edge control video: {file_path}")
                            break

                logger.info(f"Input videos for Gallery: {input_videos}")

                # Read last 15 lines of log
                log_content = ""
                log_path_str = run.get("log_path", "")
                if log_path_str:
                    log_path = Path(log_path_str)
                else:
                    log_path = Path("")

                if log_path_str and log_path.exists():
                    try:
                        with open(log_path) as f:
                            lines = f.readlines()
                            log_content = "".join(lines[-15:])
                    except Exception:
                        log_content = "Error reading log file"

                # Format dates
                created_str = (
                    run.get("created_at", "")[:19].replace("T", " ")
                    if run.get("created_at")
                    else ""
                )
                completed_str = (
                    run.get("completed_at", "")[:19].replace("T", " ")
                    if run.get("completed_at")
                    else ""
                )

                # Calculate duration
                duration = "N/A"
                try:
                    if run.get("completed_at") and run.get("created_at"):
                        from datetime import datetime

                        created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                        completed = datetime.fromisoformat(
                            run["completed_at"].replace("Z", "+00:00")
                        )
                        duration_delta = completed - created
                        minutes = int(duration_delta.total_seconds() / 60)
                        seconds = int(duration_delta.total_seconds() % 60)
                        duration = f"{minutes}m {seconds}s"
                except Exception:
                    pass

                # Construct the actual output video path
                output_video = None
                # Check if run has outputs.files array
                if run.get("outputs") and run["outputs"].get("files"):
                    # Look for output.mp4 in the files list
                    for file_path in run["outputs"]["files"]:
                        if "output.mp4" in file_path and "edge_input_control" not in file_path:
                            # Convert Windows path to forward slashes for Gradio
                            output_video = file_path.replace("\\", "/")
                            logger.info("Found output video path: %s", output_video)
                            # Verify the file exists
                            if not Path(file_path).exists():
                                logger.warning("Output video file does not exist: %s", file_path)
                                output_video = None
                            break

                # Return updates for ALL detail fields as a tuple in the correct order
                return (
                    gr.update(visible=True),  # runs_details_group
                    # Main tab
                    run.get("id", ""),  # runs_detail_id
                    run.get("status", ""),  # runs_detail_status
                    input_videos,  # runs_input_videos
                    output_video,  # runs_output_video
                    control_weights.get("vis", 0),  # runs_visual_weight
                    control_weights.get("edge", 0),  # runs_edge_weight
                    control_weights.get("depth", 0),  # runs_depth_weight
                    control_weights.get("seg", 0),  # runs_segmentation_weight
                    prompt_text,  # runs_prompt_text
                    # Info tab
                    run.get("id", ""),  # runs_info_id
                    run.get("prompt_id", ""),  # runs_info_prompt_id
                    run.get("status", ""),  # runs_info_status
                    duration,  # runs_info_duration
                    run.get("run_type", "inference"),  # runs_info_type
                    run.get("prompt_name", ""),  # runs_info_prompt_name
                    created_str,  # runs_info_created
                    completed_str,  # runs_info_completed
                    # Parameters tab
                    run.get("execution_config", {}),  # runs_params_json
                    # Logs tab
                    log_path_str,  # runs_log_path
                    log_content,  # runs_log_output
                )

            except Exception as e:
                logger.error("Error handling run selection: %s", str(e))
                # Return empty values for all outputs
                return (
                    gr.update(visible=False),  # runs_details_group
                    "",
                    "",
                    [],
                    "",
                    0,
                    0,
                    0,
                    0,
                    "",  # Main tab (9 values)
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",  # Info tab (8 values)
                    {},  # Parameters tab (1 value)
                    "",
                    "",  # Logs tab (2 values)
                )

        def update_runs_selection_info(dataframe):
            """Update the selected runs count."""
            if dataframe is None or len(dataframe) == 0:
                return "0 runs selected"

            selected_count = sum(1 for row in dataframe if row[0])  # Count checked rows
            return f"{selected_count} runs selected"

        def select_all_runs(dataframe):
            """Select all runs in the table."""
            if dataframe is None or len(dataframe) == 0:
                return dataframe

            # Set all checkboxes to True
            updated = [[True, *row[1:]] for row in dataframe]
            return updated

        def clear_runs_selection(dataframe):
            """Clear all selections in the table."""
            if dataframe is None or len(dataframe) == 0:
                return dataframe

            # Set all checkboxes to False
            updated = [[False, *row[1:]] for row in dataframe]
            return updated

        def delete_selected_runs(dataframe):
            """Delete selected runs."""
            try:
                if not ops or dataframe is None or len(dataframe) == 0:
                    return gr.update(), "No runs to delete"

                # Get selected run IDs
                selected_ids = [row[1] for row in dataframe if row[0]]

                if not selected_ids:
                    return gr.update(), "No runs selected"

                # Delete each run
                deleted_count = 0
                for run_id in selected_ids:
                    try:
                        ops.delete_run(run_id)
                        deleted_count += 1
                    except Exception as e:
                        logger.error("Error deleting run %s: %s", run_id, e)

                return gr.update(), f"Deleted {deleted_count} runs"

            except Exception as e:
                logger.error("Error deleting runs: %s", e)
                return gr.update(), f"Error: {e!s}"

        def load_full_logs(log_path):
            """Load full log file content."""
            try:
                path = Path(log_path)
                if path.exists():
                    with open(path) as f:
                        return f.read()
                return "Log file not found"
            except Exception as e:
                return f"Error reading log: {e!s}"

        # Output gallery events

        # Operations tab events

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

        # ========================================
        # Unified Runs Tab Event Connections
        # ========================================

        # Connect filters to load data
        runs_status_filter.change(
            fn=load_runs_data,
            inputs=[runs_status_filter, runs_date_filter, runs_search, runs_limit],
            outputs=[runs_gallery, runs_table, runs_stats],
        )

        runs_date_filter.change(
            fn=load_runs_data,
            inputs=[runs_status_filter, runs_date_filter, runs_search, runs_limit],
            outputs=[runs_gallery, runs_table, runs_stats],
        )

        runs_search.change(
            fn=load_runs_data,
            inputs=[runs_status_filter, runs_date_filter, runs_search, runs_limit],
            outputs=[runs_gallery, runs_table, runs_stats],
        )

        runs_limit.change(
            fn=load_runs_data,
            inputs=[runs_status_filter, runs_date_filter, runs_search, runs_limit],
            outputs=[runs_gallery, runs_table, runs_stats],
        )

        # Gallery selection
        runs_gallery.select(
            fn=handle_gallery_selection,
            inputs=[],
            outputs=[
                runs_details_group,
                # Main tab
                runs_detail_id,
                runs_detail_status,
                runs_input_videos,
                runs_output_video,
                runs_visual_weight,
                runs_edge_weight,
                runs_depth_weight,
                runs_segmentation_weight,
                runs_prompt_text,
                # Info tab
                runs_info_id,
                runs_info_prompt_id,
                runs_info_status,
                runs_info_duration,
                runs_info_type,
                runs_info_prompt_name,
                runs_info_created,
                runs_info_completed,
                # Parameters tab
                runs_params_json,
                # Logs tab
                runs_log_path,
                runs_log_output,
            ],
        )

        # Table selection
        runs_table.select(
            fn=handle_run_selection,
            inputs=[runs_table],
            outputs=[
                runs_details_group,
                # Main tab
                runs_detail_id,
                runs_detail_status,
                runs_input_videos,
                runs_output_video,
                runs_visual_weight,
                runs_edge_weight,
                runs_depth_weight,
                runs_segmentation_weight,
                runs_prompt_text,
                # Info tab
                runs_info_id,
                runs_info_prompt_id,
                runs_info_status,
                runs_info_duration,
                runs_info_type,
                runs_info_prompt_name,
                runs_info_created,
                runs_info_completed,
                # Parameters tab
                runs_params_json,
                # Logs tab
                runs_log_path,
                runs_log_output,
            ],
        )

        # Table batch operations
        runs_select_all_btn.click(fn=select_all_runs, inputs=[runs_table], outputs=[runs_table])

        runs_clear_selection_btn.click(
            fn=clear_runs_selection, inputs=[runs_table], outputs=[runs_table]
        )

        runs_table.change(
            fn=update_runs_selection_info, inputs=[runs_table], outputs=[runs_selected_info]
        )

        runs_delete_selected_btn.click(
            fn=delete_selected_runs, inputs=[runs_table], outputs=[runs_table, runs_selected_info]
        ).then(
            fn=load_runs_data,
            inputs=[runs_status_filter, runs_date_filter, runs_search, runs_limit],
            outputs=[runs_gallery, runs_table, runs_stats],
        )

        # Load full logs button
        runs_load_logs_btn.click(
            fn=load_full_logs, inputs=[runs_log_path], outputs=[runs_log_output]
        )

        # Auto-load data on app start
        app.load(fn=load_input_gallery, inputs=[], outputs=[input_gallery]).then(
            fn=check_running_jobs, inputs=[], outputs=[running_jobs_display, job_status]
        ).then(
            fn=lambda: load_ops_prompts(50),  # Load operations prompts
            inputs=[],
            outputs=[ops_prompts_table],
        ).then(
            fn=lambda: load_runs_data("all", "all", "", 50),  # Load runs for unified tab
            inputs=[],
            outputs=[runs_gallery, runs_table, runs_stats],
        )

    return app


# Create demo at module level for gradio CLI auto-reload
demo = create_ui()

if __name__ == "__main__":
    # Get UI configuration from config.toml
    ui_config = config._config_data.get("ui", {})
    host = ui_config.get("host", "127.0.0.1")
    port = ui_config.get("port", 7860)
    share = ui_config.get("share", False)

    logger.info("Starting Cosmos Workflow Manager on {}:{}", host, port)

    app = demo

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
        allowed_paths=["inputs/", "outputs/"],  # Allow serving video files
    )
