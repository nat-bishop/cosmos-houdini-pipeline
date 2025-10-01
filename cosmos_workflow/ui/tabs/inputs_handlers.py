#!/usr/bin/env python3
"""Input Video Browser Handlers for Cosmos Workflow UI.

This module contains the business logic for the Inputs tab.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.ui.utils import video as video_utils
from cosmos_workflow.utils.logging import logger


def get_input_directories(inputs_dir):
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

            # Get directory modification time
            dir_stat = dir_path.stat()

            dir_info = {
                "name": dir_path.name,
                "path": str(dir_path),
                "has_color": color_video.exists(),
                "has_depth": depth_video.exists(),
                "has_segmentation": seg_video.exists(),
                "mtime": dir_stat.st_mtime,  # Modification time for date filtering
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


def filter_input_directories(inputs_dir, search_text="", date_filter="all", sort_by="name_asc"):
    """Filter input directories based on criteria.

    Args:
        inputs_dir: Path to the inputs directory
        search_text: Text to search in directory names
        date_filter: Filter by date range (all, today, last_7_days, etc.)
        sort_by: Sort order (name_asc, name_desc, date_newest, date_oldest)

    Returns:
        Tuple of (filtered_directories, total_count, filtered_count)
    """
    all_dirs = get_input_directories(inputs_dir)
    total_count = len(all_dirs)
    filtered = all_dirs

    # Apply search filter
    if search_text and search_text.strip():
        search_lower = search_text.lower().strip()
        filtered = [d for d in filtered if search_lower in d["name"].lower()]

    # Apply date filter
    if date_filter != "all":
        current_time = time.time()
        if date_filter == "today":
            cutoff_time = current_time - (24 * 3600)  # 24 hours
        elif date_filter == "last_7_days":
            cutoff_time = current_time - (7 * 24 * 3600)
        elif date_filter == "last_30_days":
            cutoff_time = current_time - (30 * 24 * 3600)
        elif date_filter == "older_than_30_days":
            cutoff_time = current_time - (30 * 24 * 3600)
            filtered = [d for d in filtered if d["mtime"] < cutoff_time]
        else:
            cutoff_time = 0

        if date_filter != "older_than_30_days" and cutoff_time > 0:
            filtered = [d for d in filtered if d["mtime"] >= cutoff_time]

    # Apply sorting
    if sort_by == "name_asc":
        filtered = sorted(filtered, key=lambda x: x["name"].lower())
    elif sort_by == "name_desc":
        filtered = sorted(filtered, key=lambda x: x["name"].lower(), reverse=True)
    elif sort_by == "date_newest":
        filtered = sorted(filtered, key=lambda x: x["mtime"], reverse=True)
    elif sort_by == "date_oldest":
        filtered = sorted(filtered, key=lambda x: x["mtime"])

    return filtered, total_count, len(filtered)


def load_input_gallery(inputs_dir, search_text="", date_filter="all", sort_by="name_asc"):
    """Load input directories for gallery display with filtering.

    Args:
        inputs_dir: Path to the inputs directory
        search_text: Text to search in directory names
        date_filter: Filter by date range
        sort_by: Sort order

    Returns:
        Tuple of (gallery_items, results_text)
    """
    filtered_dirs, total_count, filtered_count = filter_input_directories(
        inputs_dir, search_text, date_filter, sort_by
    )

    gallery_items = []
    for dir_info in filtered_dirs:
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

    # Format results text - simpler without bold
    if search_text or date_filter != "all" or sort_by != "name_asc":
        results_text = f"{filtered_count} of {total_count} directories"
    else:
        results_text = f"{total_count} directories found"

    return gallery_items, results_text


def on_input_select(evt: gr.SelectData, gallery_data, inputs_dir):
    """Handle input selection from gallery with real video metadata extraction."""
    if evt.index is None:
        return (
            "",  # selected_dir_path - State component needs raw value
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
            "",  # selected_dir_path - State component needs raw value
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
            metadata = video_utils.extract_video_metadata(color_path)

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
        selected_dir["path"],  # selected_dir_path - State component needs raw value, not gr.update
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


def create_prompt(prompt_text, video_dir, name, negative_prompt):
    """Create a new prompt using CosmosAPI."""
    try:
        # Validate inputs
        if not prompt_text or not prompt_text.strip():
            gr.Error("Prompt text is required")
            return ""

        if not video_dir or not video_dir.strip():
            gr.Error("Video directory is required")
            return ""

        # Convert to Path and validate
        video_path = Path(video_dir.strip())
        if not video_path.is_absolute():
            # If it's a relative path, use it as-is (already relative to project root)
            video_path = Path(video_dir.strip())

        # Use CosmosAPI to create prompt (it handles validation)
        ops = CosmosAPI()
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

        # Show success notification
        gr.Info(f"Created prompt: {prompt_id} - {prompt_name}")
        return ""  # Return empty string for the invisible output component

    except FileNotFoundError as e:
        gr.Error(str(e))
        return ""
    except ValueError as e:
        gr.Error(str(e))
        return ""
    except Exception as e:
        gr.Error(f"Failed to create prompt: {e}")
        return ""
