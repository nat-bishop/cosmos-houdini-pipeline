#!/usr/bin/env python3
"""Input Video Browser Tab for Cosmos Workflow UI.

This module contains all functionality for the Inputs tab, including:
- Video directory browsing
- Metadata extraction
- Preview galleries
- Prompt creation from inputs
"""

import os
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.ui.helpers import extract_video_metadata
from cosmos_workflow.utils.logging import logger


def get_input_directories(inputs_dir):
    """Get all input video directories with metadata.

    Args:
        inputs_dir: Path to the inputs directory

    Returns:
        List of directory information dictionaries
    """
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


def load_input_gallery(inputs_dir):
    """Load input directories for gallery display.

    Args:
        inputs_dir: Path to the inputs directory

    Returns:
        List of (video_path, label) tuples for gallery
    """
    directories = get_input_directories(inputs_dir)
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


def on_input_select(evt: gr.SelectData, gallery_data, inputs_dir):
    """Handle input selection from gallery with real video metadata extraction.

    Args:
        evt: Gradio selection event
        gallery_data: Current gallery data
        inputs_dir: Path to the inputs directory

    Returns:
        Tuple of updates for all dependent components
    """
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

    directories = get_input_directories(inputs_dir)
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


def create_prompt(prompt_text, video_dir, name, negative_prompt, ops):
    """Create a new prompt with the given parameters.

    Args:
        prompt_text: The prompt text
        video_dir: Video directory path
        name: Prompt name
        negative_prompt: Negative prompt text
        ops: CosmosAPI instance

    Returns:
        Tuple of (status message, updated prompts table)
    """
    try:
        if not prompt_text:
            return gr.update(value="❌ Prompt text is required"), gr.update()

        if not video_dir:
            return gr.update(value="❌ Video directory is required"), gr.update()

        # Create the prompt using ops
        result = ops.create_prompt(
            prompt_text=prompt_text,
            video_directory=video_dir,
            name=name,
            negative_prompt=negative_prompt,
        )

        if result and result.get("id"):
            # Refresh prompts table
            from cosmos_workflow.ui.tabs.prompts import load_ops_prompts

            prompts_df = load_ops_prompts(50, ops)
            return (
                gr.update(value=f"✅ Created prompt: {result['id']}"),
                gr.update(value=prompts_df),
            )
        else:
            return gr.update(value="❌ Failed to create prompt"), gr.update()

    except Exception as e:
        logger.error("Failed to create prompt: {}", e)
        return gr.update(value=f"❌ Error: {e}"), gr.update()


def create_inputs_tab(ops, config):
    """Create the Inputs tab UI.

    Args:
        ops: CosmosAPI instance
        config: ConfigManager instance

    Returns:
        Tuple of (tab_ui, components_dict)
    """
    local_config = config.get_local_config()
    inputs_dir = Path(local_config.videos_dir)

    components = {}

    with gr.Tab("📁 Inputs") as inputs_tab:
        with gr.Column():
            gr.Markdown("### Input Video Browser")
            gr.Markdown("Browse input videos and create prompts directly")

            # Main gallery for input directories
            with gr.Column():
                input_gallery = gr.Gallery(
                    label="Input Directories",
                    value=lambda: load_input_gallery(inputs_dir),
                    columns=3,
                    rows=2,
                    height="auto",
                    preview=True,
                    elem_classes=["gallery-container"],
                )
                components["input_gallery"] = input_gallery

                # Hidden field to store selected directory path
                selected_dir_path = gr.Textbox(visible=False)
                components["selected_dir_path"] = selected_dir_path

                # Keep preview_group for compatibility but hidden
                with gr.Group(visible=False) as preview_group:
                    pass
                components["preview_group"] = preview_group

                # Tabs for Input Details and Create Prompt
                with gr.Tabs(visible=False) as input_tabs_group:
                    # Input Details Tab
                    with gr.Tab("📊 Input Details"):
                        with gr.Group(elem_classes=["detail-card"]):
                            with gr.Row():
                                input_name = gr.Textbox(label="Name", interactive=False, scale=2)
                                input_created = gr.Textbox(
                                    label="Created", interactive=False, scale=1
                                )
                            input_path = gr.Textbox(label="Path", interactive=False)

                            gr.Markdown("**Video Properties**")
                            with gr.Row():
                                input_resolution = gr.Textbox(label="Resolution", interactive=False)
                                input_duration = gr.Textbox(label="Duration", interactive=False)
                                input_fps = gr.Textbox(label="FPS", interactive=False)
                                input_codec = gr.Textbox(label="Codec", interactive=False)

                            input_files = gr.Textbox(
                                label="Files in Directory",
                                interactive=False,
                                lines=3,
                            )

                            # Preview gallery for videos in selected directory
                            video_preview_gallery = gr.Gallery(
                                label="Video Previews",
                                columns=3,
                                rows=1,
                                height="auto",
                                preview=True,
                                interactive=True,
                                allow_preview=True,
                                container=False,
                            )

                    # Create Prompt Tab
                    with gr.Tab("✨ Create Prompt"):
                        with gr.Group(elem_classes=["detail-card"]):
                            # Video Directory at the top for easy access
                            create_video_dir = gr.Textbox(
                                label="Video Directory",
                                placeholder="Path to video directory (auto-filled from selection)",
                                interactive=True,
                            )

                            # Main prompt inputs
                            create_prompt_text = gr.Textbox(
                                label="Prompt Text",
                                placeholder="Describe what you want to generate...",
                                lines=3,
                                interactive=True,
                            )

                            with gr.Row():
                                create_name = gr.Textbox(
                                    label="Name (Optional)",
                                    placeholder="Give your prompt a memorable name",
                                    interactive=True,
                                    scale=2,
                                )

                            create_negative = gr.Textbox(
                                label="Negative Prompt (Optional)",
                                placeholder="What to avoid in generation...",
                                lines=2,
                                interactive=True,
                            )

                            # Action buttons
                            with gr.Row():
                                create_prompt_btn = gr.Button(
                                    "🚀 Create Prompt", variant="primary", scale=2
                                )
                                create_status = gr.Textbox(
                                    label="Status",
                                    interactive=False,
                                    scale=3,
                                    max_lines=1,
                                )

                components["input_tabs_group"] = input_tabs_group
                components["input_name"] = input_name
                components["input_path"] = input_path
                components["input_created"] = input_created
                components["input_resolution"] = input_resolution
                components["input_duration"] = input_duration
                components["input_fps"] = input_fps
                components["input_codec"] = input_codec
                components["input_files"] = input_files
                components["video_preview_gallery"] = video_preview_gallery
                components["create_video_dir"] = create_video_dir
                components["create_prompt_text"] = create_prompt_text
                components["create_name"] = create_name
                components["create_negative"] = create_negative
                components["create_prompt_btn"] = create_prompt_btn
                components["create_status"] = create_status

    return inputs_tab, components
