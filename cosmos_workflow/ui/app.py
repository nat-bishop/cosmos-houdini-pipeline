#!/usr/bin/env python3
"""Comprehensive Gradio UI for Cosmos Workflow - Full Featured Application."""

import atexit
import os
import signal
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.ui.log_viewer import LogViewer
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
    """Handle input selection from gallery."""
    if evt.index is None:
        return "", "", "", "", "", gr.update(visible=False), ""

    directories = get_input_directories()
    if evt.index >= len(directories):
        return "", "", "", "", "", gr.update(visible=False), ""

    selected_dir = directories[evt.index]

    # Format directory info with proper line breaks
    from datetime import datetime

    # Use line breaks with proper Markdown formatting
    info_parts = []
    info_parts.append(f"**Name:** {selected_dir['name']}")
    info_parts.append("")
    info_parts.append(f"**Path:** `{selected_dir['path']}`")
    info_parts.append("")
    info_parts.append("**Resolution:** 1920x1080")  # TODO: Extract from video
    info_parts.append("")
    info_parts.append("**Duration:** 120 frames (5.0 seconds @ 24fps)")  # TODO: Extract from video
    info_parts.append("")

    # Get creation time from directory
    dir_stat = os.stat(selected_dir["path"])
    created_time = datetime.fromtimestamp(dir_stat.st_ctime, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    info_parts.append(f"**Created:** {created_time}")
    info_parts.append("")

    info_text = "\n".join(info_parts)

    info_text += "\n**Multimodal Control Inputs:**\n"

    for file_info in selected_dir["files"]:
        size_mb = file_info["size"] / (1024 * 1024)
        file_type = ""
        if "color" in file_info["name"]:
            file_type = " (RGB)"
        elif "depth" in file_info["name"]:
            file_type = " (Depth Map)"
        elif "segmentation" in file_info["name"]:
            file_type = " (Semantic Segmentation)"
        info_text += f"- {file_info['name']}{file_type} ({size_mb:.2f} MB)\n"

    # Load videos for preview
    color_video = (
        str(Path(selected_dir["path"]) / "color.mp4") if selected_dir["has_color"] else None
    )
    depth_video = (
        str(Path(selected_dir["path"]) / "depth.mp4") if selected_dir["has_depth"] else None
    )
    seg_video = (
        str(Path(selected_dir["path"]) / "segmentation.mp4")
        if selected_dir["has_segmentation"]
        else None
    )

    # Convert path to forward slashes for cross-platform compatibility in input field
    video_dir_value = selected_dir["path"].replace("\\", "/")

    return (
        info_text,
        selected_dir["path"],  # Store the directory path
        color_video,
        depth_video,
        seg_video,
        gr.update(visible=True),
        video_dir_value,  # Return normalized path for create_video_dir field
    )


# ============================================================================
# Phase 2: Prompt Management Functions
# ============================================================================


def list_prompts(model_type="all", limit=50):
    """List prompts using CosmosAPI, formatted for display."""
    try:
        # Use CosmosAPI exactly like the CLI does
        if model_type == "all":
            prompts = ops.list_prompts(limit=limit)
        else:
            prompts = ops.list_prompts(model_type=model_type, limit=limit)

        # Format for Gradio Dataframe display
        table_data = []
        for prompt in prompts:
            # Extract fields safely
            prompt_id = prompt.get("id", "")
            name = prompt.get("parameters", {}).get("name", "unnamed")
            model_type = prompt.get("model_type", "transfer")
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

            table_data.append([prompt_id, name, model_type, prompt_text, created_at])

        return table_data
    except Exception as e:
        logger.error("Failed to list prompts: {}", e)
        return []


def create_prompt(prompt_text, video_dir, name, negative_prompt, model_type):
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
            model_type=model_type,
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
        details += f"**Model Type:** {prompt.get('model_type', 'transfer')}\n"
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


def load_ops_prompts(model_type="all", limit=50):
    """Load prompts for operations table with selection column."""
    try:
        if not ops:
            return []

        # Use CosmosAPI to get prompts
        if model_type == "all":
            prompts = ops.list_prompts(limit=limit)
        else:
            prompts = ops.list_prompts(model_type=model_type, limit=limit)

        # Format for operations table with selection column
        table_data = []
        for prompt in prompts:
            prompt_id = prompt.get("id", "")
            name = prompt.get("parameters", {}).get("name", "unnamed")
            model = prompt.get("model_type", "transfer")
            text = prompt.get("prompt_text", "")
            created = prompt.get("created_at", "")[:19] if prompt.get("created_at") else ""

            # Truncate text for display
            if len(text) > 60:
                text = text[:57] + "..."

            # Add with selection checkbox (False by default) and created date
            table_data.append([False, prompt_id, name, model, text, created])

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


def select_all_prompts(dataframe_data):
    """Select all prompts in the table."""
    if dataframe_data is None:
        return []

    import pandas as pd

    if isinstance(dataframe_data, pd.DataFrame):
        # DataFrame format - set first column to True
        dataframe_data = dataframe_data.copy()
        dataframe_data.iloc[:, 0] = True
        return dataframe_data
    else:
        # List format
        updated_data = []
        for row in dataframe_data:
            new_row = row.copy() if isinstance(row, list) else list(row)
            new_row[0] = True
            updated_data.append(new_row)
        return updated_data


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
        if dataframe_data is None or evt is None:
            return ["", "", "", "", "", "", ""]

        # Get the selected row index
        row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index

        # Extract row data
        import pandas as pd

        if isinstance(dataframe_data, pd.DataFrame):
            row = dataframe_data.iloc[row_idx]
            # Columns: ["☑", "ID", "Name", "Model", "Prompt Text", "Created"]
            prompt_id = str(row.iloc[1]) if len(row) > 1 else ""
        else:
            row = dataframe_data[row_idx] if row_idx < len(dataframe_data) else []
            prompt_id = str(row[1]) if len(row) > 1 else ""

        if not prompt_id:
            return ["", "", "", "", "", "", ""]

        # Use the global ops (CosmosAPI) to get full prompt details
        if ops:
            prompt_details = ops.get_prompt(prompt_id)
            if prompt_details:
                name = prompt_details.get("parameters", {}).get("name", "unnamed")
                model = prompt_details.get("model_type", "transfer")
                prompt_text = prompt_details.get("prompt_text", "")
                negative_prompt = prompt_details.get("parameters", {}).get("negative_prompt", "")
                created = (
                    prompt_details.get("created_at", "")[:19]
                    if prompt_details.get("created_at")
                    else ""
                )

                # Get video directory from inputs
                inputs = prompt_details.get("inputs", {})
                video_dir = (
                    inputs.get("video", "").replace("/color.mp4", "") if inputs.get("video") else ""
                )

                return [prompt_id, name, model, prompt_text, negative_prompt, created, video_dir]

        return ["", "", "", "", "", "", ""]

    except Exception as e:
        logger.error("Error selecting prompt row: %s", str(e))
        return ["", "", "", "", "", "", ""]


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

    # Custom CSS for 16:9 aspect ratio in galleries with larger thumbnails
    custom_css = """
    /* Design System: Hierarchy, Contrast, Balance, Movement */
    :root {
        --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        --secondary-gradient: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        --success-gradient: linear-gradient(135deg, #00d2ff 0%, #3a7bd5 100%);
        --dark-bg: #1a1b26;
        --card-bg: rgba(255, 255, 255, 0.02);
        --border-glow: rgba(102, 126, 234, 0.5);
    }

    /* Animated header with gradient */
    h1 {
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        animation: gradientShift 6s ease infinite;
    }

    @keyframes gradientShift {
        0%, 100% { filter: hue-rotate(0deg); }
        50% { filter: hue-rotate(30deg); }
    }

    /* Card glassmorphism effects */
    .gr-box, .gr-group {
        background: var(--card-bg) !important;
        backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .gr-box:hover, .gr-group:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2) !important;
        border-color: var(--border-glow) !important;
    }

    /* Button animations */
    button {
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }

    button.primary, button[variant="primary"] {
        background: var(--primary-gradient) !important;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3) !important;
    }

    button:hover {
        transform: translateY(-2px) scale(1.02);
    }

    button::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: left 0.5s;
    }

    button:hover::before {
        left: 100%;
    }

    /* Gallery enhancements with hover effects */
    #input_gallery .thumbnail-item {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        min-height: 200px !important;
        border-radius: 8px !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        border: 2px solid transparent !important;
    }

    #input_gallery video {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        width: 100% !important;
        height: auto !important;
        min-height: 200px !important;
        border-radius: 8px !important;
    }

    #input_gallery .grid-container {
        gap: 20px !important;
        padding: 12px !important;
    }

    #output_gallery .thumbnail-item {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        min-height: 150px !important;
        border-radius: 8px !important;
        transition: all 0.3s !important;
    }

    #output_gallery video {
        aspect-ratio: 16 / 9 !important;
        object-fit: cover !important;
        width: 100% !important;
        height: auto !important;
        border-radius: 8px !important;
    }

    .thumbnail-item:hover {
        transform: scale(1.05);
        border-color: var(--border-glow) !important;
        box-shadow: 0 8px 20px rgba(102, 126, 234, 0.3) !important;
    }

    /* Tab styling */
    .tab-nav button.selected {
        background: var(--primary-gradient) !important;
        color: white !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
    }

    /* Table with hover effects */
    .dataframe tbody tr {
        transition: background 0.2s !important;
    }

    .dataframe tbody tr:hover {
        background: rgba(102, 126, 234, 0.1) !important;
    }

    /* Progress animation */
    @keyframes shimmer {
        0% { transform: translateX(-100%); }
        100% { transform: translateX(100%); }
    }

    /* Status pulse animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* Interactive table rows */
    .prompts-table tr {
        cursor: pointer;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .prompts-table tr:hover {
        background: linear-gradient(90deg, rgba(102, 126, 234, 0.1), rgba(118, 75, 162, 0.1)) !important;
        transform: translateX(4px);
    }

    .prompts-table tr.selected {
        background: rgba(102, 126, 234, 0.2) !important;
        border-left: 3px solid #667eea !important;
    }

    /* Checkbox animations */
    input[type="checkbox"] {
        transition: all 0.2s !important;
    }

    input[type="checkbox"]:checked {
        transform: scale(1.1);
        box-shadow: 0 0 10px rgba(102, 126, 234, 0.5) !important;
    }

    /* Staggered animations for batch operations */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .batch-operation {
        animation: fadeInUp 0.3s ease-out;
    }

    /* Loading skeleton */
    .loading-skeleton {
        background: linear-gradient(90deg, var(--card-bg) 25%, rgba(102, 126, 234, 0.1) 50%, var(--card-bg) 75%);
        background-size: 200% 100%;
        animation: loading 1.5s infinite;
    }

    @keyframes loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    /* Professional detail cards */
    .detail-card {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.05));
        border: 1px solid rgba(102, 126, 234, 0.2);
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .detail-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba(102, 126, 234, 0.2);
    }

    /* Split view layout */
    .split-view {
        display: flex;
        gap: 16px;
        height: calc(100vh - 200px);
    }

    .split-left {
        flex: 1.5;
        overflow-y: auto;
    }

    .split-right {
        flex: 1;
        overflow-y: auto;
        border-left: 1px solid rgba(102, 126, 234, 0.2);
        padding-left: 16px;
    }

    /* More CSS animations continues...
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }

    /* Slider enhancements */
    input[type="range"]::-webkit-slider-thumb:hover {
        transform: scale(1.2);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5) !important;
    }

    /* Focus states for accessibility */
    *:focus {
        outline: 2px solid var(--border-glow) !important;
        outline-offset: 2px !important;
    }
    """

    with gr.Blocks(title="Cosmos Workflow Manager", css=custom_css) as app:
        gr.Markdown("# 🌌 Cosmos Workflow Manager")
        gr.Markdown("Comprehensive UI for managing Cosmos Transfer workflows")

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

                        refresh_inputs_btn = gr.Button(
                            "🔄 Refresh Inputs", variant="secondary", size="sm"
                        )

                    # Right: Selected input details (smaller)
                    with gr.Column(scale=1):
                        selected_info = gr.Markdown("Select an input to view details")

                        # Hidden field to store selected directory path
                        selected_dir_path = gr.Textbox(visible=False)

                        with gr.Group(visible=False) as preview_group:
                            gr.Markdown("#### Video Previews")

                            # Use tabs for cleaner video preview layout
                            with gr.Tabs():
                                with gr.Tab("Color (RGB)"):
                                    color_preview = gr.Video(height=300, autoplay=False)

                                with gr.Tab("Depth Map"):
                                    depth_preview = gr.Video(height=300, autoplay=False)

                                with gr.Tab("Segmentation"):
                                    seg_preview = gr.Video(height=300, autoplay=False)

                        # Create Prompt Section (moved from Prompts tab)
                        gr.Markdown("#### Create New Prompt")

                        with gr.Group():
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

                            create_model_type = gr.Dropdown(
                                choices=["transfer", "upscale", "enhance"],
                                value="transfer",
                                label="Model Type",
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
                                ops_model_filter = gr.Dropdown(
                                    choices=[
                                        "all",
                                        "transfer",
                                        "upscale",
                                        "enhance",
                                        "reason",
                                        "predict",
                                    ],
                                    value="all",
                                    label="Model Type",
                                    scale=1,
                                )
                                ops_limit = gr.Number(
                                    value=50,
                                    label="Limit",
                                    minimum=1,
                                    maximum=500,
                                    scale=1,
                                )
                                ops_refresh_btn = gr.Button(
                                    "🔄 Refresh",
                                    variant="secondary",
                                    size="sm",
                                    scale=1,
                                )

                            # Enhanced prompts table with selection
                            ops_prompts_table = gr.Dataframe(
                                headers=["☑", "ID", "Name", "Model", "Prompt Text", "Created"],
                                datatype=["bool", "str", "str", "str", "str", "str"],
                                interactive=True,  # Allow checkbox interaction
                                col_count=(6, "fixed"),
                                wrap=True,
                                elem_classes=["prompts-table"],
                            )

                            # Selection controls with visual feedback
                            with gr.Row(elem_classes=["batch-operation"]):
                                select_all_btn = gr.Button(
                                    "☑ Select All", size="sm", variant="secondary"
                                )
                                clear_selection_btn = gr.Button(
                                    "☐ Clear", size="sm", variant="secondary"
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
                                    scale=2,
                                )
                                selected_prompt_model = gr.Textbox(
                                    label="Model Type",
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

                            refresh_outputs_btn = gr.Button(
                                "🔄 Refresh Outputs", variant="secondary", size="sm"
                            )

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
                        with gr.Group(visible=False) as output_details_group:
                            gr.Markdown("#### Output Details")

                            output_info = gr.Markdown("Select an output to view details")

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
            # Tab 4: Jobs & Queue (formerly Log Monitor)
            # ========================================
            with gr.Tab("📦 Jobs & Queue", id=4):
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
                        check_jobs_btn = gr.Button("🔄 Refresh Jobs", size="sm")

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

        # Input browser events
        refresh_inputs_btn.click(fn=load_input_gallery, inputs=[], outputs=[input_gallery])

        input_gallery.select(
            fn=on_input_select,
            inputs=[input_gallery],
            outputs=[
                selected_info,
                selected_dir_path,
                color_preview,
                depth_preview,
                seg_preview,
                preview_group,
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
                create_model_type,
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

                run_info = f"**Output Video**\n\nPath: {video_path}\n\n"

                # Get full run details using CosmosAPI
                if run_id and ops:
                    logger.info("Fetching run with ID: {}", run_id)
                    run = ops.get_run(run_id)
                    logger.info("Got run data: {}", bool(run))
                    if run:
                        # Add run information
                        run_info += "**Run Details**\n"
                        run_info += f"- Run ID: {run.get('id', 'unknown')[:12]}\n"
                        run_info += f"- Status: {run.get('status', 'unknown')}\n"
                        run_info += f"- Created: {run.get('created_at', '')[:19]}\n"
                        run_info += f"- Model: {run.get('model_type', 'transfer')}\n\n"

                        # Get prompt information
                        prompt_id = run.get("prompt_id")
                        logger.info("Run has prompt_id: {}", prompt_id)
                        if prompt_id:
                            try:
                                prompt = ops.get_prompt(prompt_id)
                                logger.info("Got prompt data: {}", bool(prompt))
                                if prompt:
                                    run_info += "**Prompt Information**\n"
                                    run_info += f"- Name: {prompt.get('parameters', {}).get('name', 'unnamed')}\n"
                                    run_info += (
                                        f"- Text: {prompt.get('prompt_text', '')[:100]}...\n\n"
                                    )

                                    # Get input video paths
                                    inputs = prompt.get("inputs", {})
                                    logger.info(
                                        "Prompt has inputs: {}",
                                        list(inputs.keys()) if inputs else "None",
                                    )
                                    if inputs:
                                        run_info += "**Input Videos**\n"
                                        if inputs.get("video"):
                                            run_info += f"- Color: {inputs['video']}\n"
                                        if inputs.get("depth"):
                                            run_info += f"- Depth: {inputs['depth']}\n"
                                        if inputs.get("seg"):
                                            run_info += f"- Segmentation: {inputs['seg']}\n"
                            except Exception as e:
                                logger.error("Error getting prompt {}: {}", prompt_id, e)
                                run_info += "**Prompt Information**\n"
                                run_info += f"- Unable to load prompt details: {e}\n\n"

                logger.info("Returning run_info with {} characters", len(run_info))
                result = (
                    gr.update(visible=True),  # Show details group
                    run_info,  # Output info with full details
                    str(video_path),  # Video path for display
                    str(video_path),  # Store path for download
                )
                logger.info("Returning result tuple with {} items", len(result))
                return result

            logger.info("No valid selection, returning default values")
            return gr.update(visible=False), "Select an output", None, ""

        def download_output(output_path):
            """Prepare output for download."""
            if output_path and Path(output_path).exists():
                return output_path
            return None

        refresh_outputs_btn.click(
            fn=load_outputs,
            inputs=[output_status_filter, output_model_filter, output_limit],
            outputs=[output_gallery, outputs_table],
        )

        output_gallery.select(
            fn=select_output,
            inputs=[output_gallery, outputs_table],
            outputs=[output_details_group, output_info, output_video, output_path_display],
        )

        # Download functionality will be handled through the video component itself

        # Operations tab events
        ops_refresh_btn.click(
            fn=load_ops_prompts, inputs=[ops_model_filter, ops_limit], outputs=[ops_prompts_table]
        )

        # Selection controls
        select_all_btn.click(
            fn=select_all_prompts, inputs=[ops_prompts_table], outputs=[ops_prompts_table]
        ).then(fn=update_selection_count, inputs=[ops_prompts_table], outputs=[selection_count])

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
                selected_prompt_model,
                selected_prompt_text,
                selected_prompt_negative,
                selected_prompt_created,
                selected_prompt_video_dir,
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
            inputs=[ops_model_filter, ops_limit],
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
            inputs=[ops_model_filter, ops_limit],
            outputs=[ops_prompts_table],
        )

        # Log monitor events (existing)
        check_jobs_btn.click(
            fn=check_running_jobs,
            inputs=[],
            outputs=[running_jobs_display, job_status],
        )

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

        # Auto-load data on app start
        app.load(fn=load_input_gallery, inputs=[], outputs=[input_gallery]).then(
            fn=check_running_jobs, inputs=[], outputs=[running_jobs_display, job_status]
        ).then(
            fn=load_outputs,
            inputs=[output_status_filter, output_model_filter, output_limit],
            outputs=[output_gallery, outputs_table],
        ).then(
            fn=lambda: load_ops_prompts("all", 50),  # Load operations prompts
            inputs=[],
            outputs=[ops_prompts_table],
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
