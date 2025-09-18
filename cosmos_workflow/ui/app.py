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
- Active Jobs: Real-time container monitoring with auto-refresh and log streaming

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
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.queue_service import QueueService

# Import modular UI components
from cosmos_workflow.ui.components.header import create_header_ui
from cosmos_workflow.ui.helpers import (
    extract_video_metadata,
)
from cosmos_workflow.ui.log_viewer import LogViewer
from cosmos_workflow.ui.queue_handlers import QueueHandlers
from cosmos_workflow.ui.styles_simple import get_custom_css
from cosmos_workflow.ui.tabs.inputs_ui import create_inputs_tab_ui
from cosmos_workflow.ui.tabs.jobs_handlers import (
    cancel_kill_confirmation,
    execute_kill_job,
    show_kill_confirmation,
)
from cosmos_workflow.ui.tabs.jobs_ui import create_jobs_tab_ui
from cosmos_workflow.ui.tabs.prompts_handlers import (
    cancel_delete_prompts,
    clear_selection,
    confirm_delete_prompts,
    preview_delete_prompts,
    select_all_prompts,
)
from cosmos_workflow.ui.tabs.prompts_handlers import (
    update_selection_count as prompts_update_selection_count,
)
from cosmos_workflow.ui.tabs.prompts_ui import create_prompts_tab_ui
from cosmos_workflow.ui.tabs.runs_handlers import (
    cancel_delete_run,
    confirm_delete_run,
    load_run_logs,
    load_runs_data,
    on_runs_gallery_select,
    on_runs_table_select,
    preview_delete_run,
    save_run_rating,
    update_runs_selection_info,
)
from cosmos_workflow.ui.tabs.runs_ui import create_runs_tab_ui
from cosmos_workflow.utils.logging import logger

# Load configuration
config = ConfigManager()

# Initialize log viewer (reusing existing component)
log_viewer = LogViewer(max_lines=2000)

# Initialize Queue Service for UI use
queue_service = None
queue_handlers = None


# Simple shutdown cleanup using existing methods
def cleanup_on_shutdown(signum=None, frame=None):
    """Kill containers and cleanup running jobs on shutdown."""
    global queue_service

    if signum:
        logger.info("Shutting down gracefully...")

    # Mark any running jobs as cancelled before stopping queue processor
    # This prevents zombie jobs that can't complete without the app
    if queue_service:
        try:
            from datetime import datetime, timezone

            from cosmos_workflow.database.models import JobQueue

            # Get a database session
            if queue_service.db_session:
                session = queue_service.db_session
            else:
                session = queue_service.db_connection.Session()

            try:
                # Find and cancel all running jobs
                running_jobs = session.query(JobQueue).filter(JobQueue.status == "running").all()

                if running_jobs:
                    for job in running_jobs:
                        job.status = "cancelled"
                        job.completed_at = datetime.now(timezone.utc)
                        job.result = {"reason": "Application shutdown"}
                        logger.info("Marking running job {} as cancelled due to shutdown", job.id)

                    session.commit()
                    logger.info("Cancelled {} running job(s) on shutdown", len(running_jobs))

            finally:
                if not queue_service.db_session:
                    session.close()

        except Exception as e:
            logger.error("Error cancelling running jobs on shutdown: {}", e)

    # Stop queue processor if running
    if queue_service:
        try:
            queue_service.stop_background_processor()
            logger.info("Stopped queue processor")
        except Exception as e:
            logger.error("Error stopping queue processor: {}", e)

    # Check config to see if we should cleanup containers
    ui_config = config.get_ui_config()
    should_cleanup = ui_config.get("cleanup_containers_on_exit", False)

    if not should_cleanup:
        logger.info("Container cleanup disabled in config - leaving containers running")
        return

    try:
        ops = CosmosAPI()
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


def filter_input_directories(search_text="", date_filter="all", sort_by="name_asc"):
    """Filter input directories based on criteria.

    Args:
        search_text: Text to search in directory names
        date_filter: Filter by date range (all, today, last_7_days, etc.)
        sort_by: Sort order (name_asc, name_desc, date_newest, date_oldest)

    Returns:
        Tuple of (filtered_directories, total_count, filtered_count)
    """
    import time

    all_dirs = get_input_directories()
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


def load_input_gallery(search_text="", date_filter="all", sort_by="name_asc"):
    """Load input directories for gallery display with filtering.

    Args:
        search_text: Text to search in directory names
        date_filter: Filter by date range
        sort_by: Sort order

    Returns:
        Tuple of (gallery_items, results_text)
    """
    filtered_dirs, total_count, filtered_count = filter_input_directories(
        search_text, date_filter, sort_by
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


def on_input_select(evt: gr.SelectData, gallery_data):
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

    directories = get_input_directories()
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


# ============================================================================
# Phase 2: Prompt Management Functions
# ============================================================================


def list_prompts(limit=50):
    """List prompts using CosmosAPI, formatted for display."""
    try:
        # Use CosmosAPI to list prompts
        ops = CosmosAPI()
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
        logger.error("Failed to create prompt: {}", e)
        gr.Error(f"Failed to create prompt: {e}")
        return ""


# ============================================================================
# Phase 3: Operations Functions
# ============================================================================


def filter_prompts(prompts, search_text="", enhanced_filter="all", date_filter="all"):
    """Apply filters to prompts list."""
    filtered = prompts

    # Apply search filter
    if search_text:
        search_lower = search_text.lower()
        filtered = [
            p
            for p in filtered
            if search_lower in p.get("parameters", {}).get("name", "").lower()
            or search_lower in p.get("prompt_text", "").lower()
            or search_lower
            in p.get("inputs", {}).get("video", "").lower()  # Search in video directory
        ]

    # Apply enhanced filter
    if enhanced_filter == "enhanced":
        filtered = [p for p in filtered if p.get("parameters", {}).get("enhanced", False)]
    elif enhanced_filter == "not_enhanced":
        filtered = [p for p in filtered if not p.get("parameters", {}).get("enhanced", False)]

    # Apply date filter
    if date_filter != "all":
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        filtered_by_date = []

        for prompt in filtered:
            created_str = prompt.get("created_at", "")
            if not created_str:
                continue

            try:
                # Handle both timezone-aware and naive dates
                if "Z" in created_str or "+" in created_str or "-" in created_str[-6:]:
                    # Has timezone info
                    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                else:
                    # No timezone info - assume UTC
                    created = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)

                # Fix: properly calculate days_old with timezone-aware datetime
                days_old = (now - created).days

                if date_filter == "today" and days_old == 0:
                    filtered_by_date.append(prompt)
                elif date_filter == "last_7_days" and days_old <= 7:
                    filtered_by_date.append(prompt)
                elif date_filter == "last_30_days" and days_old <= 30:
                    filtered_by_date.append(prompt)
                elif date_filter == "older_than_30_days" and days_old > 30:
                    filtered_by_date.append(prompt)
            except Exception as e:
                # Skip prompts with invalid date format
                logger.debug("Skipping prompt with invalid date format: %s", e)
                continue

        filtered = filtered_by_date

    return filtered


def load_ops_prompts(limit=50, search_text="", enhanced_filter="all", date_filter="all"):
    """Load prompts for operations table with selection column and filtering."""
    try:
        # Debug logging
        logger.info(
            "load_ops_prompts called with: limit={}, search_text='{}', enhanced_filter='{}', date_filter='{}'",
            limit,
            search_text,
            enhanced_filter,
            date_filter,
        )

        # Create fresh CosmosAPI instance
        ops = CosmosAPI()

        # Use CosmosAPI to get prompts (get more than limit to filter)
        prompts = ops.list_prompts(
            limit=limit * 3
            if search_text or enhanced_filter != "all" or date_filter != "all"
            else limit
        )

        # Apply filters
        filtered_prompts = filter_prompts(prompts, search_text, enhanced_filter, date_filter)
        logger.info("Filtered {} prompts to {} results", len(prompts), len(filtered_prompts))

        # Limit results
        filtered_prompts = filtered_prompts[:limit]

        # Format for operations table with selection column
        table_data = []
        for prompt in filtered_prompts:
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
        logger.debug("Error counting selection: {}", str(e))
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
        logger.info("on_prompt_row_select called with evt.index: {}", evt.index if evt else "None")

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
        logger.info("Selected row index: {}", row_idx)

        # Extract row data
        import pandas as pd

        if isinstance(dataframe_data, pd.DataFrame):
            row = dataframe_data.iloc[row_idx]
            # Columns: ["☑", "ID", "Name", "Prompt Text", "Created"]
            prompt_id = str(row.iloc[1]) if len(row) > 1 else ""
        else:
            row = dataframe_data[row_idx] if row_idx < len(dataframe_data) else []
            prompt_id = str(row[1]) if len(row) > 1 else ""

        logger.info("Selected prompt_id: {}", prompt_id)

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

        # Use CosmosAPI to get full prompt details
        ops = CosmosAPI()
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

        logger.warning("No prompt details found for {}", prompt_id)
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
        logger.error("Error selecting prompt row: {}", str(e))
        import traceback

        logger.error("Traceback: {}", traceback.format_exc())
        return [
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=""),
            gr.update(value=False),
        ]


def get_recent_runs(limit=5):
    """Get recent runs for the Jobs tab."""
    try:
        # Create fresh CosmosAPI instance
        ops = CosmosAPI()
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
    except Exception as e:
        logger.error("Error getting recent runs: {}", str(e))
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
    global queue_service

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
            return "❌ No prompts selected"

        # Build weights dictionary
        weights = {
            "vis": weight_vis,
            "edge": weight_edge,
            "depth": weight_depth,
            "seg": weight_seg,
        }

        logger.info("Starting inference on {} prompts", len(selected_ids))

        # Prepare config for queue
        config = {
            "weights": weights,
            "num_steps": int(steps),
            "guidance_scale": guidance,
            "seed": int(seed),
            "fps": int(fps),
            "sigma_max": sigma_max,
            "blur_strength": blur_strength,
            "canny_threshold": canny_threshold,
        }

        # Determine job type
        job_type = "inference" if len(selected_ids) == 1 else "batch_inference"

        # Add job to queue
        job_id = queue_service.add_job(
            prompt_ids=selected_ids,
            job_type=job_type,
            config=config,
        )

        # Get queue position
        position = queue_service.get_position(job_id)

        # Show immediate feedback with queue position
        if position:
            gr.Info(f"🎯 Added to queue at position #{position} - Job ID: {job_id}")
            return f"✅ Job {job_id} queued at position #{position}\n📋 {len(selected_ids)} prompt(s) will be processed"
        else:
            gr.Info(f"🚀 Job {job_id} starting immediately")
            return f"✅ Job {job_id} starting now\n📋 Processing {len(selected_ids)} prompt(s)"

    except Exception as e:
        logger.error("Failed to run inference: {}", e)
        return f"❌ Error: {e}"


def run_enhance_on_selected(dataframe_data, create_new, force_overwrite, progress=None):
    """Run enhancement on selected prompts with queue progress tracking."""
    global queue_service

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
            return "❌ No prompts selected"

        # Always use pixtral model
        model = "pixtral"
        logger.info("Starting enhancement on {} prompts with model {}", len(selected_ids), model)

        # Add all enhancement jobs to queue
        job_ids = []
        for prompt_id in selected_ids:
            config = {
                "create_new": create_new,
                "enhancement_model": model,
                "force_overwrite": force_overwrite,
            }

            job_id = queue_service.add_job(
                prompt_ids=[prompt_id],
                job_type="enhancement",
                config=config,
            )
            job_ids.append(job_id)

        # Get queue position for first job
        position = queue_service.get_position(job_ids[0]) if job_ids else None

        # Show immediate feedback
        if position:
            gr.Info(
                f"🌟 Added {len(job_ids)} enhancement job(s) to queue starting at position #{position}"
            )
            action = "create new" if create_new else "update"
            return f"✅ Queued {len(job_ids)} enhancement job(s)\n📋 Will {action} {len(selected_ids)} prompt(s)\nFirst job at position #{position}"
        else:
            gr.Info(f"🌟 Starting {len(job_ids)} enhancement job(s) now")
            action = "creating new" if create_new else "updating"
            return f"✅ Started {len(job_ids)} enhancement job(s)\n📋 {action.title()} {len(selected_ids)} prompt(s)"

    except Exception as e:
        import traceback

        logger.error("Failed to run enhancement: {}", str(e))
        logger.error("Traceback: {}", traceback.format_exc())
        return f"❌ Error: {e}"


# ============================================================================
# Existing Log Streaming Functions (keeping from original)
# ============================================================================


def start_log_streaming(auto_start=False):
    """Generator that streams logs to the UI.

    Args:
        auto_start: If True, don't clear logs (useful for auto-start on tab switch)
    """
    if not auto_start:
        log_viewer.clear()

    try:
        ops = CosmosAPI()
        containers = ops.get_active_containers()

        if not containers:
            yield "No active containers found", log_viewer.get_text()
            return

        if len(containers) > 1:
            container_id = containers[0]["container_id"]
            message = f"Multiple containers found, streaming from {container_id}"
        else:
            container_id = containers[0]["container_id"]
            message = f"Streaming logs from container {container_id}"

        yield message, log_viewer.get_text()

        try:
            for log_line in ops.stream_logs_generator(container_id):
                log_viewer.add_from_stream(log_line)
                yield message, log_viewer.get_text()
        except KeyboardInterrupt:
            yield "Streaming stopped", log_viewer.get_text()

    except RuntimeError as e:
        yield f"Error: {e}", log_viewer.get_text()
    except Exception as e:
        yield f"Failed to start streaming: {e}", log_viewer.get_text()


def refresh_jobs_on_tab_select(tab_idx):
    """Refresh jobs status when switching to jobs tab."""
    if tab_idx == 3:
        # Refresh the jobs status
        jobs_result = check_running_jobs()
        return jobs_result[0], jobs_result[1], jobs_result[2], log_viewer.get_text()
    else:
        # No update for other tabs
        return gr.update(), gr.update(), gr.update(), gr.update()


def refresh_and_stream():
    """Refresh jobs status and start streaming if container is active."""
    # First refresh the jobs status
    jobs_result = check_running_jobs()

    # Check if there's an active container
    if "Ready to stream" in jobs_result[1]:
        # Start streaming automatically
        for status, logs in start_log_streaming(auto_start=True):
            yield jobs_result[0], status, jobs_result[2], logs
    else:
        # Just return the refreshed status without streaming
        yield jobs_result[0], jobs_result[1], jobs_result[2], log_viewer.get_text()


def check_running_jobs():
    """Check for active containers and system status on remote instance."""
    try:
        ops = CosmosAPI()
        # Get comprehensive status like CLI does
        status_info = ops.check_status()

        # Build container details display
        container_details_text = ""

        # SSH Status
        if status_info.get("ssh_status") == "connected":
            container_details_text += "SSH Connection     ✓ Connected\n"
        else:
            container_details_text += "SSH Connection     ✗ Failed\n"

        # Docker status
        docker_info = status_info.get("docker_status", {})
        if isinstance(docker_info, dict) and docker_info.get("docker_running"):
            container_details_text += "Docker Daemon      ✓ Running\n"
        else:
            container_details_text += "Docker Daemon      ✗ Not running\n"

        # GPU information
        gpu_info = status_info.get("gpu_info", {})
        if gpu_info:
            gpu_name = gpu_info.get("name", "Unknown")
            gpu_memory = gpu_info.get("memory_total", "Unknown")
            container_details_text += f"GPU                {gpu_name} ({gpu_memory})\n"
            container_details_text += (
                f"CUDA Version       {gpu_info.get('cuda_version', 'Unknown')}\n"
            )

            # Add GPU utilization metrics
            gpu_util = gpu_info.get("gpu_utilization")
            if gpu_util:
                container_details_text += f"GPU Usage          {gpu_util}\n"

            # Add memory usage details
            mem_used = gpu_info.get("memory_used")
            mem_total = gpu_info.get("memory_total")
            mem_util = gpu_info.get("memory_utilization")
            if mem_used and mem_total and mem_util:
                container_details_text += (
                    f"Memory Usage       {mem_used} / {mem_total} ({mem_util})\n"
                )
        else:
            container_details_text += "GPU                Not detected\n"

        # Active run information
        active_run = status_info.get("active_run")
        active_job_display = ""

        if active_run:
            container_details_text += f"Active Operation   {active_run['model_type'].upper()}\n"
            container_details_text += f"  Run ID           {active_run['id']}\n"
            container_details_text += f"  Prompt ID        {active_run['prompt_id']}\n"
            if active_run.get("started_at"):
                container_details_text += f"  Started          {active_run['started_at']}\n"

            # Format active job card
            active_job_display = f"""**🟢 Active Job Running**

**Operation:** {active_run["model_type"].upper()}
**Run ID:** {active_run["id"]}
**Prompt ID:** {active_run["prompt_id"]}
**Status:** {active_run.get("status", "Running")}
"""
            if active_run.get("started_at"):
                active_job_display += f"**Started:** {active_run['started_at']}"

        # Container information
        container = status_info.get("container")
        if container:
            container_name = container.get("name", "Unknown")
            container_status = container.get("status", "Unknown")
            container_id = container.get("id_short", container.get("id", "Unknown")[:12])

            container_details_text += f"Running Container  {container_name}\n"
            container_details_text += f"  Status           {container_status}\n"
            container_details_text += f"  Container ID     {container_id}\n"

            # If no active run info, create basic active job display from container
            if not active_job_display:
                active_job_display = f"""**🟢 Container Running**

**Container:** {container_name}
**ID:** {container_id}
**Status:** {container_status}
"""

            status = "Ready to stream from active container"
        else:
            if active_run:
                # Run without container - zombie run
                container_details_text += (
                    "Running Container  Missing! (Database shows active run)\n"
                )
                active_job_display = f"""**⚠️ Zombie Run Detected**

**Run ID:** {active_run["id"]}
Container missing - may need cleanup
"""
                status = "Container missing but run active in database"
            else:
                container_details_text += "Running Container  None\n"
                active_job_display = """**No Active Job**

Currently idle - no jobs running"""
                status = "No containers to stream from"

        return container_details_text.strip(), status, active_job_display

    except Exception as e:
        error_display = f"""**⚠️ Error**

{e}"""
        return f"Error: {e}", "Error checking containers", error_display


# ============================================================================
# Main UI Creation
# ============================================================================


def create_ui():
    """Create the comprehensive Gradio interface using modular components."""
    global queue_service, queue_handlers

    # Initialize Queue Service with database
    database_path = "outputs/cosmos.db"
    db_connection = DatabaseConnection(database_path)
    queue_service = QueueService(db_connection=db_connection)
    queue_handlers = QueueHandlers(queue_service)

    # Start the background processor
    queue_service.start_background_processor()

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
        with gr.Tabs() as tabs:
            # Create each tab UI
            inputs_components = create_inputs_tab_ui(config)
            components.update(inputs_components)

            prompts_components = create_prompts_tab_ui()
            components.update(prompts_components)

            runs_components = create_runs_tab_ui()
            components.update(runs_components)

            jobs_components = create_jobs_tab_ui()
            components.update(jobs_components)

        components["tabs"] = tabs

        # ============================================
        # Navigation State Management
        # ============================================
        # State for cross-tab navigation and filtering
        navigation_state = gr.State(
            value={
                "filter_type": None,  # "prompt_ids" or None
                "filter_values": [],  # List of IDs being filtered
                "source_tab": None,  # Where navigation originated from
            }
        )
        components["navigation_state"] = navigation_state

        # State to store selected prompt IDs (avoids dataframe preprocessing issues)
        selected_prompt_ids_state = gr.State(value=[])
        components["selected_prompt_ids_state"] = selected_prompt_ids_state

        # State to hold pending navigation data (prevents race condition)
        pending_nav_data = gr.State(value=None)
        components["pending_nav_data"] = pending_nav_data

        # State to track last selected run ID to avoid unnecessary scrolling
        last_selected_run_id = gr.State(value=None)
        components["last_selected_run_id"] = last_selected_run_id

        # ============================================
        # Event Handlers
        # ============================================

        # Tab navigation handler - check for navigation state when switching tabs
        def handle_tab_select(tab_index, nav_state, pending_data):
            """Handle tab selection and apply navigation filters."""
            # tab_index is now directly a number
            logger.info(
                "handle_tab_select called: tab={}, nav_state={}, has_pending={}",
                tab_index,
                nav_state,
                pending_data is not None,
            )

            # Auto-refresh Jobs tab when switching to it (index 3)
            if tab_index == 3:
                logger.info("Switching to Jobs tab - refreshing status")
                # Refresh jobs data immediately
                jobs_result = check_running_jobs()
                # Also start streaming automatically if there's an active container
                if "Ready to stream" in jobs_result[1]:
                    logger.info("Active container detected - starting log stream")
                    # Return the refreshed data
                    return (
                        nav_state,
                        pending_data,
                        gr.update(),  # runs_gallery - no update
                        gr.update(),  # runs_table - no update
                        gr.update(),  # runs_stats - no update
                        gr.update(),  # runs_nav_filter_row - no update
                        gr.update(),  # runs_prompt_filter - no update
                        jobs_result[0],  # Update container details
                        jobs_result[1],  # Update job status
                        jobs_result[2],  # Update active job card
                    )
                else:
                    # Just return the refreshed data without streaming
                    return (
                        nav_state,
                        pending_data,
                        gr.update(),  # runs_gallery - no update
                        gr.update(),  # runs_table - no update
                        gr.update(),  # runs_stats - no update
                        gr.update(),  # runs_nav_filter_row - no update
                        gr.update(),  # runs_prompt_filter - no update
                        jobs_result[0],  # Update container details
                        jobs_result[1],  # Update job status
                        jobs_result[2],  # Update active job card
                    )

            # Check if there's pending navigation data (from View Runs button)
            if tab_index == 2 and pending_data is not None:
                logger.info("Using pending navigation data for Runs tab")
                gallery_data = pending_data.get("gallery", [])
                table_data = pending_data.get("table", [])
                stats = pending_data.get("stats", "No data")
                prompt_names = pending_data.get("prompt_names", [])

                # Format prompt names for display
                if prompt_names:
                    filter_display = f"**Filtering by {len(prompt_names)} prompt(s):**\n"
                    # Show up to 3 prompt IDs - full IDs, no truncation
                    display_names = []
                    for name in prompt_names[:3]:
                        display_names.append(f"• {name}")
                    filter_display += "\n".join(display_names)
                    if len(prompt_names) > 3:
                        filter_display += f"\n• ... and {len(prompt_names) - 3} more"
                else:
                    filter_display = ""

                # Clear the pending data and update display
                return (
                    nav_state,  # Keep the navigation state as-is
                    None,  # Clear pending data after consuming it
                    gallery_data,  # Update gallery
                    table_data,  # Update table
                    stats,  # Update stats
                    gr.update(visible=bool(prompt_names)),  # Show filter indicator if filtering
                    gr.update(value=filter_display),  # Update filter display with formatted text
                    gr.update(),  # Don't change running_jobs_display
                    gr.update(),  # Don't change job_status
                    gr.update(),  # Don't change active_job_card
                )

            # Check if we're navigating to Runs tab (index 2) with pending filter
            elif tab_index == 2 and nav_state and nav_state.get("filter_type") == "prompt_ids":
                prompt_ids = nav_state.get("filter_values", [])
                logger.info("Switching to Runs tab with filter for prompts: {}", prompt_ids)

                if prompt_ids:
                    # Load runs for the filtered prompts
                    from cosmos_workflow.ui.tabs.runs_handlers import load_runs_for_multiple_prompts

                    # Load filtered data
                    gallery_data, table_data, stats, prompt_names = load_runs_for_multiple_prompts(
                        prompt_ids, "all", "all", "all", "", 50
                    )

                    # Table data should be a list of lists for Gradio dataframe
                    # Only create empty list if data is None or invalid
                    if table_data is None:
                        table_data = []
                    elif isinstance(table_data, dict):
                        # If it's a dict (from error handling), extract the data
                        table_data = table_data.get("data", [])

                    logger.info(
                        "Loaded {} runs for filtered prompts", len(table_data) if table_data else 0
                    )

                    # Clear navigation state after use to prevent re-filtering
                    cleared_nav_state = {
                        "filter_type": None,
                        "filter_values": [],
                        "source_tab": None,
                    }

                    # Format prompt names for display
                    if prompt_names:
                        filter_display = f"**Filtering by {len(prompt_names)} prompt(s):**\n"
                        # Show up to 3 prompt IDs - full IDs, no truncation
                        display_names = []
                        for name in prompt_names[:3]:
                            display_names.append(f"• {name}")
                        filter_display += "\n".join(display_names)
                        if len(prompt_names) > 3:
                            filter_display += f"\n• ... and {len(prompt_names) - 3} more"
                    else:
                        filter_display = ""

                    # Show filter indicator with prompt names
                    return (
                        cleared_nav_state,  # Clear navigation state
                        None,  # Clear pending data
                        gallery_data if gallery_data else [],  # Update gallery
                        table_data,  # Update table
                        stats if stats else "No data",  # Update stats
                        gr.update(visible=True),  # Show filter indicator row
                        gr.update(
                            value=filter_display
                        ),  # Update filter display with formatted text
                        gr.update(),  # Don't change running_jobs_display
                        gr.update(),  # Don't change job_status
                        gr.update(),  # Don't change active_job_card
                    )

            # Check if we're navigating to Runs tab without filter - load default data
            elif tab_index == 2 and (not nav_state or nav_state.get("filter_type") is None):
                logger.info("Switching to Runs tab without filter - loading default data")
                # Load default runs data
                gallery_data, table_data, stats = load_runs_data("all", "all", "all", "", 50)

                # Table data should be a list of lists for Gradio dataframe
                # Only create empty list if data is None or invalid
                if table_data is None:
                    table_data = []
                elif isinstance(table_data, dict):
                    # If it's a dict (from error handling), extract the data
                    table_data = table_data.get("data", [])

                return (
                    nav_state
                    if nav_state
                    else {
                        "filter_type": None,
                        "filter_values": [],
                        "source_tab": None,
                    },  # Keep current navigation state
                    None,  # Clear pending data
                    gallery_data if gallery_data else [],  # Update gallery with default data
                    table_data,  # Update table with default data
                    stats if stats else "No data",  # Update stats
                    gr.update(visible=False),  # Hide filter indicator
                    gr.update(),  # Don't change filter dropdown
                    gr.update(),  # Don't change running_jobs_display
                    gr.update(),  # Don't change job_status
                    gr.update(),  # Don't change active_job_card
                )

            # No navigation action needed for other tabs
            return (
                nav_state,  # Keep current navigation state
                None,  # Clear pending data
                gr.update(),  # Don't change gallery
                gr.update(),  # Don't change table
                gr.update(),  # Don't change stats
                gr.update(),  # Don't change filter indicator
                gr.update(),  # Don't change filter dropdown
                gr.update(),  # Don't change running_jobs_display
                gr.update(),  # Don't change job_status
                gr.update(),  # Don't change active_job_card
            )

        # Create a number component to track selected tab index
        selected_tab_index = gr.Number(value=0, visible=False)

        def update_tab_index(evt: gr.SelectData):
            """Update the selected tab index when tabs change."""
            return evt.index

        tabs.select(
            fn=update_tab_index,
            inputs=[],
            outputs=[selected_tab_index],
        ).then(
            fn=handle_tab_select,
            inputs=[selected_tab_index, navigation_state, pending_nav_data],
            outputs=[
                navigation_state,
                pending_nav_data,  # Clear pending data after use
                components.get("runs_gallery"),
                components.get("runs_table"),
                components.get("runs_stats"),
                components.get("runs_nav_filter_row"),
                components.get("runs_prompt_filter"),
                components.get("running_jobs_display"),  # Add Jobs tab outputs
                components.get("job_status"),
                components.get("active_job_card"),
            ],
        ).then(
            # Auto-refresh when switching to Jobs tab
            fn=refresh_jobs_on_tab_select,
            inputs=[selected_tab_index],
            outputs=[
                components.get("running_jobs_display"),
                components.get("job_status"),
                components.get("active_job_card"),
                components.get("log_display"),
            ]
            if all(
                k in components
                for k in ["running_jobs_display", "job_status", "active_job_card", "log_display"]
            )
            else [],
        )

        # Import additional functions for runs tab

        # Global refresh function
        def global_refresh_all(
            # Inputs tab filters
            inputs_search="",
            inputs_date_filter="all",
            inputs_sort="name_asc",
            # Prompts tab filters
            prompts_search="",
            prompts_enhanced_filter="all",
            prompts_date_filter="all",
            # Runs tab filters
            runs_status_filter="all",
            runs_date_filter="all",
            runs_type_filter="all",
            runs_search="",
            runs_limit=50,
        ):
            """Refresh all data across all tabs while preserving filters.

            Args:
                inputs_search: Search text for inputs
                inputs_date_filter: Date filter for inputs
                inputs_sort: Sort order for inputs
                prompts_search: Search text for prompts filtering
                prompts_enhanced_filter: Enhanced status filter for prompts
                prompts_date_filter: Date range filter for prompts
                runs_status_filter: Status filter for runs
                runs_date_filter: Date filter for runs
                runs_search: Search text for runs
                runs_limit: Max results for runs
            """
            from datetime import datetime

            try:
                # Get current status
                status = f"✅ Connected | Last refresh: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"

                # Load all data with filter parameters
                inputs_data, inputs_count = load_input_gallery(
                    inputs_search,
                    inputs_date_filter,
                    inputs_sort,
                )
                prompts_data = load_ops_prompts(
                    50, prompts_search, prompts_enhanced_filter, prompts_date_filter
                )
                jobs_result = check_running_jobs()
                jobs_data = (jobs_result[0], jobs_result[1])  # Keep compatibility for other uses

                # Load runs data with filters
                runs_gallery, runs_table, runs_stats = load_runs_data(
                    runs_status_filter, runs_date_filter, runs_type_filter, runs_search, runs_limit
                )

                return (
                    status,  # refresh_status
                    inputs_data,  # input_gallery
                    inputs_count,  # inputs_results_count
                    prompts_data,  # ops_prompts_table
                    jobs_data[0],  # running_jobs_display
                    jobs_data[1],  # job_status
                    runs_gallery,  # runs_gallery
                    runs_table,  # runs_table
                    runs_stats,  # runs_stats
                )
            except Exception as e:
                logger.error("Error during global refresh: {}", str(e))
                return (
                    "❌ Error - Check logs",
                    [],
                    "**0** directories found",
                    [],
                    "Error loading data",
                    "Error",
                    [],
                    [],
                    "Error loading data",
                )

        # Header/Manual Refresh Events

        if "manual_refresh_btn" in components:
            # Manual refresh: preserve filters
            manual_refresh_inputs = []

            # Add Inputs tab filter inputs
            if "inputs_search" in components:
                manual_refresh_inputs.append(components["inputs_search"])
            if "inputs_date_filter" in components:
                manual_refresh_inputs.append(components["inputs_date_filter"])
            if "inputs_sort" in components:
                manual_refresh_inputs.append(components["inputs_sort"])

            # Add Prompts tab filter inputs
            if "prompts_search" in components:
                manual_refresh_inputs.append(components["prompts_search"])
            if "prompts_enhanced_filter" in components:
                manual_refresh_inputs.append(components["prompts_enhanced_filter"])
            if "prompts_date_filter" in components:
                manual_refresh_inputs.append(components["prompts_date_filter"])

            # Add Runs tab filter inputs
            if "runs_status_filter" in components:
                manual_refresh_inputs.append(components["runs_status_filter"])
            if "runs_date_filter" in components:
                manual_refresh_inputs.append(components["runs_date_filter"])
            if "runs_type_filter" in components:
                manual_refresh_inputs.append(components["runs_type_filter"])
            if "runs_search" in components:
                manual_refresh_inputs.append(components["runs_search"])
            if "runs_limit" in components:
                manual_refresh_inputs.append(components["runs_limit"])

            # Build outputs list including all tab components
            manual_refresh_outputs = []
            if "refresh_status" in components:
                manual_refresh_outputs.append(components["refresh_status"])
            if "input_gallery" in components:
                manual_refresh_outputs.append(components["input_gallery"])
            if "inputs_results_count" in components:
                manual_refresh_outputs.append(components["inputs_results_count"])
            if "ops_prompts_table" in components:
                manual_refresh_outputs.append(components["ops_prompts_table"])
            if "running_jobs_display" in components:
                manual_refresh_outputs.append(components["running_jobs_display"])
            if "job_status" in components:
                manual_refresh_outputs.append(components["job_status"])
            if "runs_gallery" in components:
                manual_refresh_outputs.append(components["runs_gallery"])
            if "runs_table" in components:
                manual_refresh_outputs.append(components["runs_table"])
            if "runs_stats" in components:
                manual_refresh_outputs.append(components["runs_stats"])

            # Create the handler with proper parameter unpacking
            def manual_refresh_handler(*args):
                # Unpack arguments based on what's available
                idx = 0

                # Inputs filters
                i_search = args[idx] if len(args) > idx else ""
                idx += 1
                i_date = args[idx] if len(args) > idx else "all"
                idx += 1
                i_sort = args[idx] if len(args) > idx else "name_asc"
                idx += 1

                # Prompts filters
                p_search = args[idx] if len(args) > idx else ""
                idx += 1
                p_enhanced = args[idx] if len(args) > idx else "all"
                idx += 1
                p_date = args[idx] if len(args) > idx else "all"
                idx += 1

                # Runs filters
                r_status = args[idx] if len(args) > idx else "all"
                idx += 1
                r_date = args[idx] if len(args) > idx else "all"
                idx += 1
                r_type = args[idx] if len(args) > idx else "all"
                idx += 1
                r_search = args[idx] if len(args) > idx else ""
                idx += 1
                r_limit = args[idx] if len(args) > idx else 50

                return global_refresh_all(
                    inputs_search=i_search,
                    inputs_date_filter=i_date,
                    inputs_sort=i_sort,
                    prompts_search=p_search,
                    prompts_enhanced_filter=p_enhanced,
                    prompts_date_filter=p_date,
                    runs_status_filter=r_status,
                    runs_date_filter=r_date,
                    runs_type_filter=r_type,
                    runs_search=r_search,
                    runs_limit=r_limit,
                )

            components["manual_refresh_btn"].click(
                fn=manual_refresh_handler,
                inputs=manual_refresh_inputs,
                outputs=manual_refresh_outputs,
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

        # Inputs filtering events
        if all(
            k in components
            for k in [
                "inputs_search",
                "inputs_date_filter",
                "inputs_sort",
            ]
        ):
            filter_inputs = [
                components["inputs_search"],
                components["inputs_date_filter"],
                components["inputs_sort"],
            ]
            filter_outputs = [
                components["input_gallery"],
                components["inputs_results_count"],
            ]

            # Search box with debouncing (responds to text changes)
            if "inputs_search" in components:
                components["inputs_search"].change(
                    fn=load_input_gallery,
                    inputs=filter_inputs,
                    outputs=filter_outputs,
                )

            # Dropdown filters respond immediately

            if "inputs_date_filter" in components:
                components["inputs_date_filter"].change(
                    fn=load_input_gallery,
                    inputs=filter_inputs,
                    outputs=filter_outputs,
                )

            # Sort dropdown
            if "inputs_sort" in components:
                components["inputs_sort"].change(
                    fn=load_input_gallery,
                    inputs=filter_inputs,
                    outputs=filter_outputs,
                )

        if "create_prompt_btn" in components:
            # Create prompt with Gradio's built-in progress indicator
            components["create_prompt_btn"].click(
                fn=create_prompt,
                inputs=[
                    components["create_prompt_text"],
                    components["create_video_dir"],
                    components["create_name"],
                    components["create_negative"],
                ],
                outputs=[components.get("create_progress_area")],  # Invisible area for spinner
                show_progress="full",  # This enables Gradio's built-in button spinner
                queue=True,  # Explicitly enable queue for progress to work
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

        # Prompts filtering events
        prompts_filter_inputs = get_components(
            "ops_limit",
            "prompts_search",
            "prompts_enhanced_filter",
            "prompts_date_filter",
        )
        if prompts_filter_inputs and "ops_prompts_table" in components:
            # Connect all filter controls to update the table
            for filter_component in [
                "prompts_search",
                "prompts_enhanced_filter",
                "prompts_date_filter",
            ]:
                if filter_component in components:
                    components[filter_component].change(
                        fn=load_ops_prompts,
                        inputs=prompts_filter_inputs,
                        outputs=[components["ops_prompts_table"]],
                    )

        # Prompts selection controls
        if "select_all_btn" in components:
            components["select_all_btn"].click(
                fn=select_all_prompts,
                inputs=[components["ops_prompts_table"]],
                outputs=[
                    components["ops_prompts_table"],
                    components["selection_count"],
                ],
            )

        if "clear_selection_btn" in components:
            components["clear_selection_btn"].click(
                fn=clear_selection,
                inputs=[components["ops_prompts_table"]],
                outputs=[
                    components["ops_prompts_table"],
                    components["selection_count"],
                ],
            )

        # Prompts delete operations - Two-step process with preview
        if "delete_selected_btn" in components and "ops_prompts_table" in components:
            # Step 1: Show preview when delete button is clicked
            components["delete_selected_btn"].click(
                fn=preview_delete_prompts,
                inputs=[components["ops_prompts_table"]],
                outputs=[
                    components.get("prompts_delete_dialog"),
                    components.get("prompts_delete_preview"),
                    components.get("prompts_delete_outputs_checkbox"),
                    components.get("prompts_delete_ids_hidden"),
                ],
                scroll_to_output=True,  # Scroll to the delete confirmation dialog
            )

            # Step 2: Confirm deletion
            if "prompts_confirm_delete_btn" in components:
                components["prompts_confirm_delete_btn"].click(
                    fn=confirm_delete_prompts,
                    inputs=[
                        components.get("prompts_delete_ids_hidden"),
                        components.get("prompts_delete_outputs_checkbox"),
                    ],
                    outputs=[
                        components.get("selection_count"),
                        components.get("prompts_delete_dialog"),
                    ],
                ).then(
                    fn=load_ops_prompts,
                    inputs=[components.get("ops_limit")],
                    outputs=[components.get("ops_prompts_table")],
                )

            # Cancel deletion
            if "prompts_cancel_delete_btn" in components:
                components["prompts_cancel_delete_btn"].click(
                    fn=cancel_delete_prompts,
                    inputs=[],
                    outputs=[
                        components.get("selection_count"),
                        components.get("prompts_delete_dialog"),
                    ],
                )

        # Navigation to Runs tab with filtering
        # NOTE: tabs is a variable, not a component - we just need to check it exists
        if (
            "view_runs_btn" in components
            and tabs is not None  # Check tabs variable exists, not in components
            and "runs_gallery" in components
            and "runs_table" in components
            and "runs_stats" in components
            and "runs_nav_filter_row" in components
            and "runs_prompt_filter" in components
        ):

            def prepare_runs_navigation(selected_ids):
                """Navigate to Runs tab with filtering - sets pending data to avoid race condition."""
                from cosmos_workflow.ui.tabs.runs_handlers import load_runs_for_multiple_prompts
                from cosmos_workflow.utils.logging import logger

                # Selected IDs are now passed directly from state
                logger.info(f"prepare_runs_navigation called with selected_ids: {selected_ids}")

                if not selected_ids:
                    return (
                        {
                            "filter_type": None,
                            "filter_values": [],
                            "source_tab": None,
                        },  # Clear navigation state
                        None,  # No pending data
                        "⚠️ Please select at least one prompt before viewing runs.",
                        gr.update(),  # Don't switch tabs (keep current)
                        gr.update(),  # Don't update runs_gallery
                        gr.update(),  # Don't update runs_table
                        gr.update(),  # Don't update runs_stats
                        gr.update(),  # Don't update runs_nav_filter_row
                        gr.update(),  # Don't update runs_prompt_filter
                    )

                # Cap at 20 prompts for performance
                if len(selected_ids) > 20:
                    selected_ids = selected_ids[:20]
                    status_msg = f"✅ Navigating to Runs tab with first 20 of {len(selected_ids)} selected prompts..."
                else:
                    status_msg = (
                        f"✅ Navigating to Runs tab with {len(selected_ids)} selected prompt(s)..."
                    )

                # Load filtered data
                logger.info(f"Loading runs data for prompts: {selected_ids}")
                gallery_data, table_data, stats, prompt_names = load_runs_for_multiple_prompts(
                    selected_ids, "all", "all", "all", "", 50
                )

                # Ensure table_data is a list for Gradio dataframe
                if table_data is None:
                    table_data = []
                elif isinstance(table_data, dict):
                    table_data = table_data.get("data", [])

                logger.info(
                    f"Loaded {len(table_data) if table_data else 0} runs for filtered prompts"
                )

                # Set navigation state with filter information
                nav_state_with_filter = {
                    "filter_type": "prompts",
                    "filter_values": selected_ids,
                    "source_tab": "prompts",
                }

                # Prepare pending data that will be consumed by handle_tab_select
                pending_data = {
                    "gallery": gallery_data if gallery_data else [],
                    "table": table_data if table_data else [],
                    "stats": stats if stats else "No data",
                    "prompt_names": prompt_names if prompt_names else [],
                }

                # Return navigation state and pending data
                # The actual components will be updated by handle_tab_select when it consumes pending_data
                return (
                    nav_state_with_filter,  # Set navigation state
                    pending_data,  # Set pending data for handle_tab_select to consume
                    status_msg,
                    2,  # Switch to Runs tab (index 2)
                    gr.update(),  # Don't update gallery yet
                    gr.update(),  # Don't update table yet
                    gr.update(),  # Don't update stats yet
                    gr.update(),  # Don't update filter row yet
                    gr.update(),  # Don't update filter dropdown yet
                )

            # Combined navigation and data loading to avoid race conditions
            # Use the state that tracks selected IDs properly
            components["view_runs_btn"].click(
                fn=prepare_runs_navigation,
                inputs=[selected_prompt_ids_state],
                outputs=[
                    navigation_state,  # Update navigation state
                    pending_nav_data,  # Set pending data for handle_tab_select
                    components["selection_count"],  # Update status message
                    selected_tab_index,  # Update selected tab index (hidden number component)
                    components["runs_gallery"],  # Update runs gallery with filtered data
                    components["runs_table"],  # Update runs table with filtered data
                    components["runs_stats"],  # Update runs stats
                    components["runs_nav_filter_row"],  # Show/hide filter indicator
                    components["runs_prompt_filter"],  # Update filter dropdown
                ],
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[2]?.click(); }, 100); return []; }",
                queue=False,
            )

        # Navigation from Inputs to Prompts tab
        if "view_prompts_for_input_btn" in components and "selected_dir_path" in components:

            def prepare_prompts_navigation_from_input(input_name):
                """Navigate to Prompts tab with search filter for input directory."""
                from cosmos_workflow.utils.logging import logger

                logger.info(
                    f"prepare_prompts_navigation_from_input called with input_name: {input_name}"
                )

                if not input_name:
                    return (
                        "⚠️ Please select an input directory first.",
                        gr.update(),  # Don't change search
                        gr.update(),  # Don't switch tabs
                    )

                # Extract just the directory name (remove any path prefixes)
                search_term = input_name.split("/")[-1] if "/" in input_name else input_name
                search_term = search_term.split("\\")[-1] if "\\" in search_term else search_term

                logger.info(f"Navigating to Prompts tab with search: {search_term}")

                return (
                    f"✅ Navigating to Prompts tab to show prompts using '{search_term}'...",
                    gr.update(value=search_term),  # Update search field
                    1,  # Switch to Prompts tab (index 1)
                )

            components["view_prompts_for_input_btn"].click(
                fn=prepare_prompts_navigation_from_input,
                inputs=[
                    components["selected_dir_path"]
                ],  # Use the State component which stores the path
                outputs=[
                    components["refresh_status"],  # Status message (reuse refresh status)
                    components["prompts_search"],  # Update search field in prompts tab
                    selected_tab_index,  # Update selected tab index
                ],
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[1]?.click(); }, 100); return []; }",
                queue=False,
            ).then(
                # After updating search, reload the prompts table with the new search term
                fn=lambda search_term: load_ops_prompts(50, search_term, "all", "all"),
                inputs=[components["prompts_search"]],
                outputs=[components["ops_prompts_table"]],
            )

        # Navigation from Inputs to Runs tab
        if "view_runs_for_input_btn" in components and "selected_dir_path" in components:

            def prepare_runs_navigation_from_input(input_path):
                """Navigate to Runs tab with filtering by input directory."""
                from cosmos_workflow.api.cosmos_api import CosmosAPI
                from cosmos_workflow.utils.logging import logger

                logger.info(
                    f"prepare_runs_navigation_from_input called with input_path: {input_path}"
                )

                if not input_path:
                    return (
                        gr.update(),  # navigation_state - no update
                        gr.update(),  # pending_nav_data - no update
                        "⚠️ Please select an input directory first.",  # status message
                        gr.update(),  # selected_tab_index - no update
                        gr.update(),  # runs_gallery - no update
                        gr.update(),  # runs_table - no update
                        gr.update(),  # runs_stats - no update
                        gr.update(visible=False),  # runs_nav_filter_row - keep hidden
                        gr.update(),  # runs_prompt_filter - no update
                    )

                # Get all prompts and filter by input directory (same logic as View Prompts)
                ops = CosmosAPI()
                all_prompts = ops.list_prompts(limit=1000)

                # Extract directory name from path
                input_name = input_path.split("/")[-1] if "/" in input_path else input_path
                input_name = input_name.split("\\")[-1] if "\\" in input_name else input_name

                # Find prompts that use this input directory
                matching_prompt_ids = []
                for prompt in all_prompts:
                    inputs = prompt.get("inputs", {})
                    video_path = inputs.get("video", "")
                    # Check if the input name appears in the video path
                    if input_name in video_path:
                        matching_prompt_ids.append(prompt.get("id"))

                logger.info(
                    f"Found {len(matching_prompt_ids)} prompts using input directory '{input_name}'"
                )

                if not matching_prompt_ids:
                    return (
                        gr.update(),  # navigation_state
                        gr.update(),  # pending_nav_data
                        f"No prompts found using input '{input_name}'",  # status
                        gr.update(),  # selected_tab_index
                        gr.update(),  # runs_gallery
                        gr.update(),  # runs_table
                        gr.update(),  # runs_stats
                        gr.update(visible=False),  # runs_nav_filter_row
                        gr.update(),  # runs_prompt_filter
                    )

                # Now call the existing prepare_runs_navigation with these prompt IDs
                # This will handle all the filtering and navigation properly
                return prepare_runs_navigation(matching_prompt_ids)

            components["view_runs_for_input_btn"].click(
                fn=prepare_runs_navigation_from_input,
                inputs=[components["selected_dir_path"]],
                outputs=[
                    navigation_state,  # Update navigation state
                    pending_nav_data,  # Set pending data for handle_tab_select
                    components["refresh_status"],  # Status message
                    selected_tab_index,  # Update selected tab index
                    components["runs_gallery"],  # Update runs gallery with filtered data
                    components["runs_table"],  # Update runs table with filtered data
                    components["runs_stats"],  # Update runs stats
                    components["runs_nav_filter_row"],  # Show filter indicator
                    components["runs_prompt_filter"],  # Show filter text
                ],
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[2]?.click(); }, 100); return []; }",
                queue=False,
            )

        # Update selection count when selection changes
        if "ops_prompts_table" in components:

            def update_selection_and_state(table_data):
                """Update selection count and store selected IDs in state."""
                from cosmos_workflow.ui.tabs.prompts_handlers import get_selected_prompt_ids
                from cosmos_workflow.utils.logging import logger

                # Get selection count display
                count_display = prompts_update_selection_count(table_data)

                # Get selected IDs for state
                selected_ids = get_selected_prompt_ids(table_data)
                logger.info(f"update_selection_and_state: selected_ids={selected_ids}")

                return count_display, selected_ids

            # Track both row selection and checkbox changes
            components["ops_prompts_table"].select(
                fn=update_selection_and_state,
                inputs=[components["ops_prompts_table"]],
                outputs=[components["selection_count"], selected_prompt_ids_state],
            )

            # Also track when checkboxes are changed
            components["ops_prompts_table"].change(
                fn=update_selection_and_state,
                inputs=[components["ops_prompts_table"]],
                outputs=[components["selection_count"], selected_prompt_ids_state],
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
                # Run inference and then update Jobs & Queue status
                components["run_inference_btn"].click(
                    fn=run_inference_on_selected,
                    inputs=inputs,
                    outputs=outputs,
                ).then(
                    # Update Jobs & Queue tab to show the running container
                    fn=check_running_jobs,
                    inputs=[],
                    outputs=[
                        components.get("running_jobs_display"),
                        components.get("job_status"),
                        components.get("active_job_card"),
                    ],
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
        if all(
            k in components
            for k in [
                "runs_status_filter",
                "runs_date_filter",
                "runs_type_filter",
                "runs_search",
                "runs_limit",
            ]
        ):
            filter_inputs = [
                components["runs_status_filter"],
                components["runs_date_filter"],
                components["runs_type_filter"],
                components["runs_search"],
                components["runs_limit"],
            ]
            # Update gallery, table and stats
            filter_outputs = get_components("runs_gallery", "runs_table", "runs_stats")
            if filter_outputs:
                for filter_component in [
                    "runs_status_filter",
                    "runs_date_filter",
                    "runs_type_filter",
                    "runs_search",
                    "runs_limit",
                ]:
                    components[filter_component].change(
                        fn=load_runs_data,
                        inputs=filter_inputs,
                        outputs=filter_outputs,
                    )

        # Runs table selection
        if "runs_table" in components:
            runs_output_keys = [
                "runs_details_group",
                "runs_detail_id",
                "runs_detail_status",
                # Content block visibility
                "runs_main_content_transfer",
                "runs_main_content_enhance",
                "runs_main_content_upscale",
                # Transfer content components
                "runs_input_video_1",
                "runs_input_video_2",
                "runs_input_video_3",
                "runs_input_video_4",
                "runs_output_video",
                "runs_prompt_text",
                # Enhancement content components
                "runs_original_prompt_enhance",
                "runs_enhanced_prompt_enhance",
                "runs_enhance_stats",
                # Upscale content components
                "runs_output_video_upscale",
                "runs_original_video_upscale",
                "runs_upscale_stats",
                "runs_upscale_prompt",
                # Info tab components
                "runs_info_id",
                "runs_info_prompt_id",
                "runs_info_status",
                "runs_info_duration",
                "runs_info_type",
                "runs_info_prompt_name",
                "runs_info_rating",
                "runs_info_created",
                "runs_info_completed",
                "runs_info_output_path",
                "runs_info_input_paths",
                # Parameters and Logs
                "runs_params_json",
                "runs_log_path",
                "runs_log_output",
            ]
            outputs = get_components(*runs_output_keys)
            if outputs:
                logger.info("Connecting runs_table.select with {} outputs", len(outputs))
                components["runs_table"].select(
                    fn=on_runs_table_select,
                    inputs=[components["runs_table"]],
                    outputs=outputs,
                    # Note: scroll_to_output removed to prevent scrolling when tab loads
                )
            else:
                missing_runs = [k for k in runs_output_keys if k not in components]
                logger.warning("Missing components for runs table select: {}", missing_runs)
                # Try to connect with whatever components we have
                available_outputs = [components[k] for k in runs_output_keys if k in components]
                if available_outputs:
                    logger.info(
                        "Connecting with {} available outputs (partial)", len(available_outputs)
                    )
                    components["runs_table"].select(
                        fn=on_runs_table_select,
                        inputs=[components["runs_table"]],
                        outputs=available_outputs,
                        # Note: scroll_to_output removed to prevent scrolling when tab loads
                    )

            # Update selection info when a row is selected
            if "runs_selected_info" in components and "runs_selected_id" in components:
                components["runs_table"].select(
                    fn=update_runs_selection_info,
                    inputs=[components["runs_table"]],  # Pass table data
                    outputs=[components["runs_selected_info"], components["runs_selected_id"]],
                )

        # Runs gallery selection - reuse same outputs as table
        if "runs_gallery" in components:
            runs_output_keys = [
                "runs_details_group",
                "runs_detail_id",
                "runs_detail_status",
                # Content block visibility
                "runs_main_content_transfer",
                "runs_main_content_enhance",
                "runs_main_content_upscale",
                # Transfer content components
                "runs_input_video_1",
                "runs_input_video_2",
                "runs_input_video_3",
                "runs_input_video_4",
                "runs_output_video",
                "runs_prompt_text",
                # Enhancement content components
                "runs_original_prompt_enhance",
                "runs_enhanced_prompt_enhance",
                "runs_enhance_stats",
                # Upscale content components
                "runs_output_video_upscale",
                "runs_original_video_upscale",
                "runs_upscale_stats",
                "runs_upscale_prompt",
                # Info tab components
                "runs_info_id",
                "runs_info_prompt_id",
                "runs_info_status",
                "runs_info_duration",
                "runs_info_type",
                "runs_info_prompt_name",
                "runs_info_rating",
                "runs_info_created",
                "runs_info_completed",
                "runs_info_output_path",
                "runs_info_input_paths",
                # Parameters and Logs
                "runs_params_json",
                "runs_log_path",
                "runs_log_output",
            ]
            outputs = get_components(*runs_output_keys)
            if outputs:
                logger.info("Connecting runs_gallery.select with {} outputs", len(outputs))
                # Add the selected_index state as an output
                outputs_with_index = [*outputs, components.get("runs_selected_index")]

                # Modified handler that also tracks the index
                def on_gallery_select_with_index(evt: gr.SelectData):
                    result = on_runs_gallery_select(evt)
                    # Add the selected index to the results
                    return [*result, evt.index if evt else 0]

                components["runs_gallery"].select(
                    fn=on_gallery_select_with_index,
                    inputs=[],
                    outputs=outputs_with_index,
                    # Note: scroll_to_output removed to prevent scrolling when tab loads
                )

        # Navigation buttons for gallery
        if (
            "runs_prev_btn" in components
            and "runs_next_btn" in components
            and "runs_selected_index" in components
        ):
            # Previous button handler
            def navigate_gallery_prev(current_index):
                """Navigate to previous item in gallery."""
                new_index = max(0, current_index - 1)
                return gr.update(selected_index=new_index), new_index

            # Next button handler
            def navigate_gallery_next(current_index):
                """Navigate to next item in gallery."""
                # We don't know the max, so just increment and let Gradio handle bounds
                new_index = current_index + 1
                return gr.update(selected_index=new_index), new_index

            components["runs_prev_btn"].click(
                fn=navigate_gallery_prev,
                inputs=[components["runs_selected_index"]],
                outputs=[components["runs_gallery"], components["runs_selected_index"]],
            )

            components["runs_next_btn"].click(
                fn=navigate_gallery_next,
                inputs=[components["runs_selected_index"]],
                outputs=[components["runs_gallery"], components["runs_selected_index"]],
            )

        # Delete selected run operation - Two-step process with preview
        if "runs_delete_selected_btn" in components and "runs_selected_id" in components:
            # Step 1: Show preview when delete button is clicked
            components["runs_delete_selected_btn"].click(
                fn=preview_delete_run,
                inputs=[components["runs_selected_id"]],
                outputs=[
                    components.get("runs_delete_dialog"),
                    components.get("runs_delete_preview"),
                    components.get("runs_delete_outputs_checkbox"),
                    components.get("runs_delete_id_hidden"),
                ],
            )

            # Step 2: Confirm deletion
            if "runs_confirm_delete_btn" in components:
                components["runs_confirm_delete_btn"].click(
                    fn=confirm_delete_run,
                    inputs=[
                        components.get("runs_delete_id_hidden"),
                        components.get("runs_delete_outputs_checkbox"),
                    ],
                    outputs=[
                        components.get("runs_selected_info"),
                        components.get("runs_delete_dialog"),
                    ],
                ).then(
                    fn=load_runs_data,
                    inputs=[
                        components.get("runs_status_filter"),
                        components.get("runs_date_filter"),
                        components.get("runs_type_filter"),
                        components.get("runs_search"),
                        components.get("runs_limit"),
                    ],
                    outputs=[
                        components.get("runs_gallery"),
                        components.get("runs_table"),
                        components.get("runs_stats"),
                    ],
                )

            # Cancel deletion
            if "runs_cancel_delete_btn" in components:
                components["runs_cancel_delete_btn"].click(
                    fn=cancel_delete_run,
                    inputs=[],
                    outputs=[
                        components.get("runs_selected_info"),
                        components.get("runs_delete_dialog"),
                    ],
                )

        # Clear navigation filter button
        if "clear_nav_filter_btn" in components:
            components["clear_nav_filter_btn"].click(
                fn=load_runs_data,  # Load all runs without filter
                inputs=[
                    components.get("runs_status_filter"),
                    components.get("runs_date_filter"),
                    components.get("runs_type_filter"),
                    components.get("runs_search"),
                    components.get("runs_limit"),
                ],
                outputs=[
                    components.get("runs_gallery"),
                    components.get("runs_table"),
                    components.get("runs_stats"),
                ],
            ).then(
                fn=lambda: (gr.update(visible=False), gr.update(value="")),
                inputs=[],
                outputs=[
                    components.get("runs_nav_filter_row"),
                    components.get("runs_prompt_filter"),
                ],
            )

        # Load logs button
        if all(k in components for k in ["runs_load_logs_btn", "runs_log_path", "runs_log_output"]):
            components["runs_load_logs_btn"].click(
                fn=load_run_logs,
                inputs=[components["runs_log_path"]],
                outputs=[components["runs_log_output"]],
            )

        # Rating change handler
        if all(k in components for k in ["runs_info_rating", "runs_info_id"]):
            components["runs_info_rating"].change(
                fn=save_run_rating,
                inputs=[components["runs_info_id"], components["runs_info_rating"]],
                outputs=[components["runs_info_rating"]],
            )

        # Active Jobs Tab Events
        # Add stream button handler for manual refresh
        if "stream_btn" in components:

            def manual_refresh_jobs():
                """Manual refresh and stream for jobs tab."""
                yield from refresh_and_stream()

            outputs = get_components(
                "running_jobs_display", "job_status", "active_job_card", "log_display"
            )
            if outputs:
                components["stream_btn"].click(
                    fn=manual_refresh_jobs,
                    outputs=outputs,
                )

        # Clear logs button
        if "clear_logs_btn" in components and "log_viewer" in components:
            components["clear_logs_btn"].click(
                fn=lambda: (components["log_viewer"].clear(), components["log_viewer"].get_text()),
                outputs=[components.get("log_display")],
            )

        # Queue Control Events
        if "kill_job_btn" in components:
            # Kill job button shows confirmation
            components["kill_job_btn"].click(
                fn=show_kill_confirmation,
                outputs=[
                    components.get("kill_confirmation"),
                    components.get("kill_preview"),
                ],
            )

            # Cancel kill button
            components["cancel_kill_btn"].click(
                fn=cancel_kill_confirmation,
                outputs=components.get("kill_confirmation"),
            )

            # Confirm kill button
            components["confirm_kill_btn"].click(
                fn=execute_kill_job,
                outputs=[
                    components.get("kill_confirmation"),
                    components.get("job_status"),
                ],
            ).then(
                fn=check_running_jobs,
                outputs=[
                    components.get("running_jobs_display"),
                    components.get("job_status"),
                    components.get("active_job_card"),
                ],
            )

        # Queue Display Events
        if "refresh_queue_btn" in components and queue_handlers:
            # Refresh queue display
            components["refresh_queue_btn"].click(
                fn=queue_handlers.get_queue_display,
                outputs=[
                    components.get("queue_status"),
                    components.get("queue_table"),
                ],
            )

            # Cancel selected job
            if "cancel_job_btn" in components and "selected_job_id" in components:

                def cancel_selected_job(job_id):
                    """Cancel the selected job and refresh the queue."""
                    if not job_id:
                        return "No job selected", None, []

                    # Cancel the job
                    result = queue_handlers.cancel_job(job_id)

                    # Refresh queue display
                    status_text, table_data = queue_handlers.get_queue_display()

                    # Return updated displays
                    return result, status_text, table_data

                components["cancel_job_btn"].click(
                    fn=cancel_selected_job,
                    inputs=components["selected_job_id"],
                    outputs=[
                        components.get("job_status"),
                        components.get("queue_status"),
                        components.get("queue_table"),
                    ],
                )

            # Auto-refresh queue every 5 seconds when on jobs tab
            def auto_refresh_queue():
                """Auto-refresh queue display."""
                return queue_handlers.get_queue_display()

            # Set up a timer for auto-refresh
            # Create a timer that triggers every 5 seconds (less frequent to avoid conflicts)
            timer = gr.Timer(value=5, active=True)
            timer.tick(
                fn=auto_refresh_queue,
                outputs=[
                    components.get("queue_status"),
                    components.get("queue_table"),
                ],
            )

        # Queue table select handler (outside the refresh button check)
        if "queue_table" in components and "job_details" in components and queue_handlers:

            def on_queue_table_select(table_data, evt: gr.SelectData):
                """Handle selection of a job from the queue table."""
                try:
                    logger.info("Queue table select event triggered")

                    # Get selected row index
                    row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index
                    logger.info("Selected row index: {}", row_idx)

                    # Extract job ID from table (column 1 has Job ID)
                    import pandas as pd

                    if isinstance(table_data, pd.DataFrame):
                        job_id = table_data.iloc[row_idx, 1]  # Job ID is in column 1
                    else:
                        job_id = table_data[row_idx][1] if row_idx < len(table_data) else None

                    logger.info("Selected job ID: {}", job_id)

                    if not job_id:
                        return gr.update(value="No job selected"), gr.update(visible=False), None

                    # Get job details
                    details = queue_handlers.get_job_details(job_id)

                    # Check if this is a queued job (to show cancel button)
                    # Extract status from the table data to determine if cancellable
                    if isinstance(table_data, pd.DataFrame):
                        status = table_data.iloc[row_idx, 3]  # Status is in column 3
                    else:
                        status = table_data[row_idx][3] if row_idx < len(table_data) else None

                    # Show cancel button only for queued jobs
                    show_cancel = status == "queued"

                    return gr.update(value=details), gr.update(visible=show_cancel), job_id

                except Exception as e:
                    logger.error("Error selecting job from queue: {}", e)
                    return (
                        gr.update(value=f"Error loading job details: {e}"),
                        gr.update(visible=False),
                        None,
                    )

            # Connect queue table select event
            components["queue_table"].select(
                fn=on_queue_table_select,
                inputs=[components["queue_table"]],
                outputs=[
                    components.get("job_details"),
                    components.get("cancel_job_btn"),
                    components.get("selected_job_id"),
                ],
            )

        # Load initial data
        initial_outputs = get_components(
            "input_gallery",
            "inputs_results_count",
            "ops_prompts_table",
            "running_jobs_display",
            "job_status",
        )

        # Debug: Check which components are missing
        required_components = [
            "input_gallery",
            "inputs_results_count",
            "ops_prompts_table",
            "running_jobs_display",
            "job_status",
        ]
        missing = [k for k in required_components if k not in components]
        if missing:
            logger.warning("Missing components for initial load: {}", missing)

        if initial_outputs:
            logger.info("Setting up initial data load with {} outputs", len(initial_outputs))

            def load_initial_data():
                """Load initial data efficiently."""
                gallery_data, results_text = load_input_gallery()
                prompts_data = load_ops_prompts(50)
                # Only call check_running_jobs once
                try:
                    jobs_result = check_running_jobs()
                    jobs_display = jobs_result[0]
                    job_status = jobs_result[1]
                    # Note: active_job_card (jobs_result[2]) is not used here for initial load
                except Exception as e:
                    logger.debug("Could not check running jobs: {}", e)
                    jobs_display = "No containers"
                    job_status = "Not connected"
                return gallery_data, results_text, prompts_data, jobs_display, job_status

            app.load(
                fn=load_initial_data,
                outputs=initial_outputs,
            )
        else:
            logger.warning("Could not set up initial data load - missing components")

    # Enable queue for long-running operations (prevents timeout)
    app.queue(
        max_size=100,  # Maximum number of queued requests
        default_concurrency_limit=1,  # Process one inference at a time
    )

    return app


# ============================================================================
# Application Entry Point
# ============================================================================
# For Gradio auto-reload CLI compatibility
# ============================================================================

# Lazy initialization to avoid creating UI on every import
_demo = None


def get_demo():
    """Get or create the demo instance."""
    global _demo
    if _demo is None:
        _demo = create_ui()
    return _demo


# Create the demo variable that Gradio CLI expects
demo = get_demo()

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)  # noqa: S104
