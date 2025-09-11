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
ops = CosmosAPI(config=config)

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
        return "", "", "", "", gr.update(visible=False)

    directories = get_input_directories()
    if evt.index >= len(directories):
        return "", "", "", "", gr.update(visible=False)

    selected_dir = directories[evt.index]

    # Format directory info with proper line breaks
    from datetime import datetime

    # Use line breaks with proper Markdown formatting
    info_parts = []
    info_parts.append(f"**Name:** {selected_dir['name']}")
    info_parts.append("")
    info_parts.append(f"**Path:** {selected_dir['path']}")
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

    return (
        info_text,
        selected_dir["path"],  # Store the directory path
        color_video,
        depth_video,
        seg_video,
        gr.update(visible=True),
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

            # Truncate text for display
            if len(text) > 60:
                text = text[:57] + "..."

            # Add with selection checkbox (False by default)
            table_data.append([False, prompt_id, name, model, text])

        return table_data
    except Exception as e:
        logger.error("Failed to load prompts for operations: {}", e)
        return []


def update_selection_count(dataframe_data):
    """Update the selection count based on checked rows."""
    try:
        if dataframe_data is None:
            return "0 selected"

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
                return "0 selected"
        else:
            return "0 selected"

        return f"{selected} selected"
    except Exception as e:
        logger.debug("Error counting selection: %s", str(e))
        return "0 selected"


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


def get_queue_status():
    """Get current queue status information."""
    # In a real implementation, this would check actual queue status
    # For now, we'll return a simple status
    return "Queue: Ready | GPU: Available"


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

        with gr.Tabs() as tabs:
            # ========================================
            # Tab 1: Inputs Browser
            # ========================================
            with gr.Tab("📁 Inputs", id=1):
                gr.Markdown("### Input Video Browser")
                gr.Markdown("Browse and select input video directories for processing")

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

                            # Add button to create prompt for selected input
                            create_prompt_for_input_btn = gr.Button(
                                "✨ Create Prompt for This Input", variant="primary", size="sm"
                            )

            # ========================================
            # Tab 2: Prompts (Phase 2 Implementation)
            # ========================================
            with gr.Tab("✏️ Prompts", id="prompts_tab"):
                gr.Markdown("### Prompt Management")
                gr.Markdown("Create and manage prompts for your video inputs")

                with gr.Row():
                    # Left: Prompt list and filters
                    with gr.Column(scale=2):
                        gr.Markdown("#### Existing Prompts")

                        with gr.Row():
                            model_type_filter = gr.Dropdown(
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
                            limit_filter = gr.Number(
                                value=50, label="Limit", minimum=1, maximum=500, scale=1
                            )
                            refresh_prompts_btn = gr.Button(
                                "🔄 Refresh", variant="secondary", size="sm", scale=1
                            )

                        prompts_table = gr.Dataframe(
                            headers=["ID", "Name", "Model", "Prompt Text", "Created"],
                            datatype=["str", "str", "str", "str", "str"],
                            interactive=False,
                            wrap=True,
                        )

                        gr.Textbox(label="Selected Prompt ID", interactive=False, visible=False)

                    # Right: Create new prompt
                    with gr.Column(scale=1):
                        gr.Markdown("#### Create New Prompt")

                        with gr.Group():
                            # Video Directory at the top for easy access
                            create_video_dir = gr.Textbox(
                                label="Video Directory",
                                placeholder="Path to input video directory (e.g., inputs/videos/example)",
                                info="Must contain color.mp4 - auto-filled when clicking 'Create Prompt for This Input'",
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
            # Tab 3: Operations
            # ========================================
            with gr.Tab("🚀 Operations", id=3):
                gr.Markdown("### Run Operations")
                gr.Markdown("Execute inference and enhancement operations on your prompts")

                with gr.Row():
                    # Left: Prompt selection table
                    with gr.Column(scale=3):
                        gr.Markdown("#### Select Prompts")

                        # Filter row
                        with gr.Row():
                            ops_model_filter = gr.Dropdown(
                                choices=["all", "transfer", "upscale", "enhance"],
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

                        # Prompts table with selection
                        ops_prompts_table = gr.Dataframe(
                            headers=["Select", "ID", "Name", "Model", "Text"],
                            datatype=["bool", "str", "str", "str", "str"],
                            interactive=True,  # Allow checkbox interaction
                            col_count=(5, "fixed"),
                            wrap=True,
                        )

                        # Selection controls
                        with gr.Row():
                            select_all_btn = gr.Button("Select All", size="sm")
                            clear_selection_btn = gr.Button("Clear", size="sm")
                            selection_count = gr.Markdown("0 selected")

                    # Right: Operation controls
                    with gr.Column(scale=2):
                        gr.Markdown("#### Operation Controls")

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

                        # Execution status
                        gr.Markdown("#### Execution Status")
                        with gr.Group():
                            execution_status = gr.Textbox(
                                label="Current Status",
                                value="Idle",
                                interactive=False,
                            )
                            queue_status = gr.Textbox(
                                label="Queue Status",
                                value="No jobs queued",
                                interactive=False,
                            )
                            # Auto-refresh queue status
                            queue_timer = gr.Timer(value=2.0, active=True)  # Update every 2 seconds

            # ========================================
            # Tab 4: Outputs (Phase 4 Implementation)
            # ========================================
            with gr.Tab("🎬 Outputs", id=4):
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
            # Tab 5: Log Monitor (Existing functionality)
            # ========================================
            with gr.Tab("📊 Log Monitor", id=5):
                gr.Markdown("### Real-time Log Monitoring")

                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("#### Active Containers")
                        running_jobs_display = gr.Textbox(
                            label="Active Containers",
                            value="Checking for active containers...",
                            interactive=False,
                            lines=5,
                        )
                        check_jobs_btn = gr.Button("🔍 Check Active Containers", size="sm")

                        job_status = gr.Textbox(
                            label="Stream Status",
                            value="Click 'Start Streaming' to begin",
                            interactive=False,
                        )

                        stream_btn = gr.Button("▶️ Start Streaming", variant="primary", size="sm")

                        gr.Markdown("#### Log Statistics")
                        gr.Textbox(
                            label="Log Stats",
                            value="Total: 0 | Errors: 0 | Warnings: 0",
                            interactive=False,
                        )

                    with gr.Column(scale=3):
                        gr.Markdown("#### Log Output")
                        log_display = gr.HTML(
                            value=log_viewer.get_html(),
                            elem_id="log_display",
                        )

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
            ],
        )

        # Input-Prompt association with auto-navigation
        def navigate_to_prompt_creation(path):
            """Navigate to Prompts tab and populate the video directory."""
            input_id = Path(path).name if path else ""
            # Return values for: video_dir, tabs (switch to prompts_tab), and status
            return (
                path,  # Video directory
                gr.update(selected="prompts_tab"),  # Switch to Prompts tab using its ID
                f"🎯 Creating prompt for: {input_id}",  # Status message
            )

        create_prompt_for_input_btn.click(
            fn=navigate_to_prompt_creation,
            inputs=[selected_dir_path],
            outputs=[create_video_dir, tabs, create_status],
        )

        # Prompt management events
        refresh_prompts_btn.click(
            fn=list_prompts, inputs=[model_type_filter, limit_filter], outputs=[prompts_table]
        )

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
        ).then(fn=list_prompts, inputs=[model_type_filter, limit_filter], outputs=[prompts_table])

        # Load initial data will be done via app.load event

        # Output gallery events
        def load_outputs(status_filter, model_filter, limit):
            """Load outputs from completed runs."""
            try:
                # Get runs based on filter
                runs = ops.list_runs(
                    status=status_filter if status_filter != "all" else None, limit=int(limit)
                )

                # Filter by model type if specified
                if model_filter != "all":
                    runs = [r for r in runs if r.get("model_type") == model_filter]

                # Filter runs with video outputs
                runs_with_outputs = []
                gallery_items = []

                for run in runs:
                    # Construct the path to the output video based on run ID
                    run_id = run.get("id")
                    output_path = Path("outputs") / f"run_{run_id}" / "outputs" / "output.mp4"

                    if output_path.exists():
                        runs_with_outputs.append(run)
                        # Add to gallery (path, label)
                        prompt_text = run.get("prompt_text", "No prompt")[:50] + "..."
                        gallery_items.append(
                            (str(output_path), f"Run {run['id'][:8]}: {prompt_text}")
                        )

                # Create table data
                table_data = []
                for run in runs_with_outputs[:10]:  # Limit table to 10 rows
                    table_data.append(
                        [
                            run["id"][:12],
                            run.get("prompt_text", "N/A")[:30] + "...",
                            run.get("status", "unknown"),
                            run.get("created_at", "N/A")[:19],
                        ]
                    )

                return gallery_items, table_data

            except Exception as e:
                logger.error(f"Error loading outputs: {e}")
                return [], []

        def select_output(evt: gr.SelectData, gallery_data):
            """Handle output selection from gallery."""
            if evt.index is not None and gallery_data:
                selected = gallery_data[evt.index]
                video_path = selected[0] if isinstance(selected, tuple) else selected

                if Path(video_path).exists():
                    # Get run info from path
                    run_info = f"**Selected Output**\n\nPath: {video_path}\n"

                    return (
                        gr.update(visible=True),  # Show details group
                        run_info,  # Output info
                        str(video_path),  # Video path for display (ensure it's a string)
                        str(video_path),  # Store path for download (ensure it's a string)
                    )

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
            inputs=[output_gallery],
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
        )

        # Auto-load data on app start
        app.load(fn=load_input_gallery, inputs=[], outputs=[input_gallery]).then(
            fn=check_running_jobs, inputs=[], outputs=[running_jobs_display, job_status]
        ).then(
            fn=load_outputs,
            inputs=[output_status_filter, output_model_filter, output_limit],
            outputs=[output_gallery, outputs_table],
        ).then(
            fn=lambda: list_prompts("all", 50),  # Provide default values
            inputs=[],
            outputs=[prompts_table],
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
