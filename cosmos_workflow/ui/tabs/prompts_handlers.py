#!/usr/bin/env python3
"""Event handlers for Prompts tab functionality."""

from datetime import datetime, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.services.simple_queue_service import SimplifiedQueueService
from cosmos_workflow.ui.utils import dataframe as df_utils
from cosmos_workflow.ui.utils import video as video_utils
from cosmos_workflow.ui.utils.formatting import parse_timestamp_safe, truncate_text
from cosmos_workflow.utils.logging import logger


def select_all_prompts(table_data):
    """Select all prompts in the table."""
    try:
        # Handle empty data
        if table_data is None:
            return [], "No Prompts Selected", []

        # Use utility to select all
        updated_data = df_utils.select_all(table_data)
        count = df_utils.count_selected(updated_data)
        selected_ids = get_selected_prompt_ids(updated_data)

        if count == 0:
            return updated_data, "No Prompts Selected", selected_ids
        elif count == 1:
            return updated_data, f"**{count}** prompt selected", selected_ids
        else:
            return updated_data, f"**{count}** prompts selected", selected_ids

    except Exception as e:
        logger.error("Error selecting all prompts: {}", str(e))
        return table_data, "Error selecting prompts", []


def clear_selection(table_data):
    """Clear all selections in the prompts table."""
    try:
        # Handle empty data
        if table_data is None:
            return [], "No Prompts Selected", []

        # Use utility to clear selection
        updated_data = df_utils.clear_selection(table_data)
        return updated_data, "No Prompts Selected", []

    except Exception as e:
        logger.error("Error clearing selection: {}", str(e))
        return table_data, "Error clearing selection", []


def update_selection_count(table_data):
    """Update the count of selected prompts and return selected IDs."""
    try:
        if table_data is None:
            logger.debug("update_selection_count: table_data is None")
            return "No Prompts Selected", []

        # Use utility to count selected
        count = df_utils.count_selected(table_data)
        logger.info("update_selection_count: count={}", count)

        # Get selected IDs for the state
        selected_ids = get_selected_prompt_ids(table_data)

        if count == 0:
            return "No Prompts Selected", selected_ids
        elif count == 1:
            return f"**{count}** prompt selected", selected_ids
        else:
            return f"**{count}** prompts selected", selected_ids

    except Exception as e:
        logger.error("Error updating selection count: {}", str(e))
        return "Error counting selection", []


def get_selected_prompt_ids(table_data):
    """Extract IDs of selected prompts from table data."""
    # Use utility to get selected IDs (ID is in column 1)
    selected_ids = df_utils.get_selected_ids(table_data, id_column=1)
    logger.debug("Selected %d prompts from table", len(selected_ids))
    return selected_ids


def preview_delete_prompts(table_data):
    """Preview what will be deleted for selected prompts."""
    try:
        selected_ids = get_selected_prompt_ids(table_data)

        if not selected_ids:
            return (
                gr.update(visible=False),  # Hide dialog
                "",  # No preview text
                False,  # Reset checkbox
                "",  # No IDs to store
            )

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        if not ops:
            return (
                gr.update(visible=False),
                "Error: Cannot connect to API",
                False,
                "",
            )

        # Build preview for each prompt
        preview_lines = []
        total_runs = 0
        total_size = 0
        has_active_runs = False

        for prompt_id in selected_ids:
            preview = ops.preview_prompt_deletion(prompt_id, keep_outputs=False)
            if preview and preview.get("prompt"):
                prompt_info = preview["prompt"]
                runs = preview.get("runs", [])
                size_mb = preview.get("total_size_mb", 0)

                # Check for active runs
                active_runs = [r for r in runs if r.get("status") in ["running", "pending"]]
                if active_runs:
                    has_active_runs = True
                    preview_lines.append(
                        f"⚠️ **{prompt_info.get('id', '')[:8]}...** - {prompt_info.get('prompt_text', '')[:50]}... "
                        f"({len(active_runs)} ACTIVE RUNS!)"
                    )
                else:
                    preview_lines.append(
                        f"• **{prompt_info.get('id', '')[:8]}...** - {prompt_info.get('prompt_text', '')[:50]}... "
                        f"({len(runs)} runs, {size_mb:.1f} MB)"
                    )

                total_runs += len(runs)
                total_size += size_mb

        # Build preview text
        preview_text = f"""### ⚠️ Delete Prompts Confirmation

**Selected Prompts:** {len(selected_ids)}
**Total Runs:** {total_runs}
**Total Size:** {total_size:.2f} MB

**Prompts to delete:**
"""
        preview_text += "\n".join(preview_lines)

        if has_active_runs:
            preview_text += (
                "\n\n🚨 **WARNING:** Some prompts have active runs! These cannot be deleted."
            )

        preview_text += "\n\n⚠️ **Warning:** This action cannot be undone!"

        # Store selected IDs as comma-separated string
        ids_string = ",".join(selected_ids)

        return (
            gr.update(visible=True),  # Show dialog
            preview_text,  # Preview text
            False,  # Default to keep outputs
            ids_string,  # Store IDs for confirmation
        )

    except Exception as e:
        logger.error("Error previewing prompt deletion: {}", str(e))
        return (
            gr.update(visible=False),
            f"Error: {e}",
            False,
            "",
        )


def confirm_delete_prompts(prompt_ids_string, delete_outputs):
    """Actually delete the prompts after confirmation."""
    try:
        if not prompt_ids_string:
            return (
                gr.update(),  # ops_prompts_table
                gr.update(visible=False),  # Hide dialog
            )

        prompt_ids = prompt_ids_string.split(",")
        if not prompt_ids:
            return (
                gr.update(),  # ops_prompts_table
                gr.update(visible=False),  # Hide dialog
            )

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        if not ops:
            return (
                gr.update(),  # ops_prompts_table
                gr.update(visible=False),  # Hide dialog
            )

        # Delete each prompt
        keep_outputs = not delete_outputs
        deleted_count = 0
        failed_prompts = []

        for prompt_id in prompt_ids:
            try:
                # Check for active runs first
                preview = ops.preview_prompt_deletion(prompt_id, keep_outputs)
                if preview and preview.get("runs"):
                    active_runs = [
                        r for r in preview["runs"] if r.get("status") in ["running", "pending"]
                    ]
                    if active_runs:
                        failed_prompts.append(f"{prompt_id[:8]} (has active runs)")
                        continue

                # Delete the prompt
                result = ops.delete_prompt(prompt_id, keep_outputs=keep_outputs)
                if result.get("success"):
                    deleted_count += 1
                else:
                    failed_prompts.append(
                        f"{prompt_id[:8]} ({result.get('error', 'unknown error')})"
                    )

            except Exception as e:
                logger.error("Error deleting prompt {}: {}", prompt_id, str(e))
                failed_prompts.append(f"{prompt_id[:8]} ({e!s})")

        # Build result message
        if deleted_count > 0:
            msg = f"✅ Successfully deleted {deleted_count} prompt(s)"
            if delete_outputs:
                msg += " (output files deleted)"
            else:
                msg += " (output files preserved)"
        else:
            msg = "❌ No prompts were deleted"

        if failed_prompts:
            msg += f"\n\n⚠️ Failed to delete: {', '.join(failed_prompts)}"

        # Need to refresh the tables after deletion
        # Return: ops_prompts_table, prompts_delete_dialog
        # Note: prompts_table doesn't exist as a component, so we skip it
        return (
            gr.update(),  # ops_prompts_table - will be refreshed by .then()
            gr.update(visible=False),  # Hide dialog
        )

    except Exception as e:
        logger.error("Error deleting prompts: {}", str(e))
        return (
            gr.update(),  # ops_prompts_table
            gr.update(visible=False),  # Hide dialog
        )


def cancel_delete_prompts():
    """Cancel prompt deletion."""
    # Return: prompts_delete_dialog visibility update
    return gr.update(visible=False)  # Hide dialog


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
            prompt_text = truncate_text(prompt_text, max_length=50)

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


def filter_prompts(
    prompts, search_text="", enhanced_filter="all", runs_filter="all", date_filter="all"
):
    """Apply filters to prompts list."""
    filtered = prompts

    # Apply search filter
    if search_text:
        search_lower = search_text.lower()
        filtered = [
            p
            for p in filtered
            if search_lower in p.get("id", "").lower()  # Search in prompt ID
            or search_lower in p.get("parameters", {}).get("name", "").lower()
            or search_lower in p.get("prompt_text", "").lower()
            or search_lower
            in p.get("inputs", {}).get("video", "").lower()  # Search in video directory
        ]

    # Apply enhanced filter
    if enhanced_filter == "enhanced":
        filtered = [p for p in filtered if p.get("parameters", {}).get("enhanced", False)]
    elif enhanced_filter == "not_enhanced":
        filtered = [p for p in filtered if not p.get("parameters", {}).get("enhanced", False)]

    # Apply runs filter
    if runs_filter != "all":
        # Get run counts for each prompt
        ops = CosmosAPI()

        # Build a mapping of prompt_id -> run count
        prompt_run_counts = {}
        for prompt in filtered:
            prompt_id = prompt.get("id")
            if prompt_id:
                # Get runs for this prompt
                runs = ops.list_runs(prompt_id=prompt_id, limit=1)  # Just check if any exist
                prompt_run_counts[prompt_id] = len(runs)

        # Filter based on run counts
        if runs_filter == "no_runs":
            filtered = [p for p in filtered if prompt_run_counts.get(p.get("id"), 0) == 0]
        elif runs_filter == "has_runs":
            filtered = [p for p in filtered if prompt_run_counts.get(p.get("id"), 0) > 0]

    # Apply date filter
    if date_filter != "all":
        now = datetime.now(timezone.utc)
        filtered_by_date = []

        for prompt in filtered:
            created_str = prompt.get("created_at", "")
            if not created_str:
                continue

            # Use safe timestamp parser
            created = parse_timestamp_safe(created_str)
            if created:
                # Calculate days old
                days_old = (now - created).days

                if date_filter == "today" and days_old == 0:
                    filtered_by_date.append(prompt)
                elif date_filter == "last_7_days" and days_old <= 7:
                    filtered_by_date.append(prompt)
                elif date_filter == "last_30_days" and days_old <= 30:
                    filtered_by_date.append(prompt)
                elif date_filter == "older_than_30_days" and days_old > 30:
                    filtered_by_date.append(prompt)

        filtered = filtered_by_date

    return filtered


def load_ops_prompts(
    limit=50, search_text="", enhanced_filter="all", runs_filter="all", date_filter="all"
):
    """Load prompts for operations table with selection column and filtering."""
    try:
        # Debug logging
        logger.info(
            "load_ops_prompts called with: limit={}, search_text='{}', enhanced_filter='{}', runs_filter='{}', date_filter='{}'",
            limit,
            search_text,
            enhanced_filter,
            runs_filter,
            date_filter,
        )

        # Create fresh CosmosAPI instance
        ops = CosmosAPI()

        # Use CosmosAPI to get prompts (get more than limit to filter)
        prompts = ops.list_prompts(
            limit=limit * 3
            if search_text
            or enhanced_filter != "all"
            or runs_filter != "all"
            or date_filter != "all"
            else limit
        )

        # Apply filters
        filtered_prompts = filter_prompts(
            prompts, search_text, enhanced_filter, runs_filter, date_filter
        )
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
            text = truncate_text(text, max_length=60)

            # Add with selection checkbox (False by default) and created date
            table_data.append([False, prompt_id, name, text, created])

        return table_data
    except Exception as e:
        logger.error("Failed to load prompts for operations: {}", e)
        return []


def calculate_run_statistics(runs):
    """Calculate run statistics by model type and status.

    Args:
        runs: List of run dictionaries

    Returns:
        Dictionary with counts by model_type for completed runs
    """
    stats = {"transfer": 0, "upscale": 0, "enhance": 0, "total_completed": 0}

    for run in runs:
        if run.get("status") == "completed":
            model_type = run.get("model_type", "").lower()
            if model_type in stats:
                stats[model_type] += 1
            stats["total_completed"] += 1

    return stats


def calculate_average_rating(runs):
    """Calculate average rating for completed runs.

    Args:
        runs: List of run dictionaries

    Returns:
        Tuple of (average_rating, rated_count) or (None, 0) if no ratings
    """
    ratings = []
    for run in runs:
        if run.get("status") == "completed" and run.get("rating") is not None:
            rating = run.get("rating")
            if isinstance(rating, int | float) and 1 <= rating <= 5:
                ratings.append(rating)

    if ratings:
        return sum(ratings) / len(ratings), len(ratings)
    return None, 0


def get_video_thumbnail(video_path):
    """Get or generate thumbnail for video file.

    Checks for existing thumbnail first, generates if missing.
    Since generation only happens once per video, this is acceptable.

    Args:
        video_path: Path to video file

    Returns:
        Path to thumbnail image or None if failed
    """
    if not video_path:
        return None

    video_file = Path(video_path)
    if not video_file.exists():
        logger.debug("Video file not found: {}", video_path)
        return None

    # Check for existing thumbnail next to the video file
    # Format: video.mp4 → video.thumb.jpg
    expected_thumb = video_file.parent / f"{video_file.stem}.thumb.jpg"
    if expected_thumb.exists():
        return str(expected_thumb)

    # Generate thumbnail if it doesn't exist (only happens once per video)
    try:
        logger.info("Generating thumbnail for input video: {}", video_file.name)
        thumb_path = video_utils.generate_thumbnail_fast(str(video_file))
        if thumb_path:
            logger.info("Generated thumbnail: {}", thumb_path)
            return thumb_path
    except Exception as e:
        logger.error("Failed to generate thumbnail for {}: {}", video_path, e)

    return None


def on_prompt_row_select(dataframe_data, evt: gr.SelectData):
    """Handle row selection in prompts table to show details."""
    try:
        logger.info("on_prompt_row_select called with evt.index: {}", evt.index if evt else "None")

        if dataframe_data is None or evt is None:
            logger.warning("on_prompt_row_select: dataframe_data or evt is None")
            # Return gr.update() objects to force UI refresh - now with additional fields
            return [
                gr.update(value=""),  # prompt_id
                gr.update(value=""),  # name
                gr.update(value=""),  # prompt_text
                gr.update(value=""),  # negative_prompt
                gr.update(value=""),  # created
                gr.update(value=""),  # video_dir
                gr.update(value=False),  # enhanced
                gr.update(value="No data"),  # runs_stats
                gr.update(value="N/A"),  # rating
                gr.update(value=None),  # thumbnail
            ]

        # Get the selected row index
        row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index
        logger.info("Selected row index: {}", row_idx)

        # Extract prompt ID using utility
        # Columns: ["☑", "ID", "Name", "Prompt Text", "Created"]
        prompt_id = df_utils.get_cell_value(dataframe_data, row_idx, 1, default="")
        if prompt_id:
            prompt_id = str(prompt_id)

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
                gr.update(value="No data"),
                gr.update(value="N/A"),
                gr.update(value=None),
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

            # Fetch runs for this prompt
            runs = ops.list_runs(prompt_id=prompt_id, limit=100)

            # Calculate run statistics
            stats = calculate_run_statistics(runs)
            if stats["total_completed"] > 0:
                parts = []
                if stats["transfer"] > 0:
                    parts.append(f"{stats['transfer']} inference")
                if stats["upscale"] > 0:
                    parts.append(f"{stats['upscale']} upscale")
                if stats["enhance"] > 0:
                    parts.append(f"{stats['enhance']} enhance")
                stats_text = f"{stats['total_completed']} completed ({', '.join(parts)})"
            else:
                stats_text = "No completed runs"

            # Calculate average rating
            avg_rating, rated_count = calculate_average_rating(runs)
            if avg_rating is not None:
                rating_text = (
                    f"{avg_rating:.1f}/5 ({rated_count} {'run' if rated_count == 1 else 'runs'})"
                )
            else:
                rating_text = "No ratings yet"

            # Generate thumbnail for input video
            video_path = inputs.get("video", "")
            thumbnail_path = get_video_thumbnail(video_path) if video_path else None

            logger.info(
                "Returning prompt details: id=%s, name=%s, enhanced=%s, runs=%d",
                prompt_id,
                name,
                enhanced,
                len(runs),
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
                gr.update(value=stats_text),
                gr.update(value=rating_text),
                gr.update(value=thumbnail_path),
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
            gr.update(value="No data"),
            gr.update(value="N/A"),
            gr.update(value=None),
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
            gr.update(value="Error loading"),
            gr.update(value="Error loading"),
            gr.update(value=None),
        ]


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
    queue_service: SimplifiedQueueService,
    progress=None,
):
    """Run inference on selected prompts with queue progress tracking."""
    if progress is None:
        progress = gr.Progress()

    try:
        # Get selected prompt IDs using utility
        selected_ids = df_utils.get_selected_ids(dataframe_data, id_column=1)

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

        # Always use batch inference for consistency (even for single prompts)
        # This ensures consistent file naming and processing
        job_type = "batch_inference"

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
            status_msg = f"✅ Job {job_id} queued at position #{position}\n📋 {len(selected_ids)} prompt(s) will be processed"
        else:
            gr.Info(f"🚀 Job {job_id} starting immediately")
            status_msg = (
                f"✅ Job {job_id} starting now\n📋 Processing {len(selected_ids)} prompt(s)"
            )

        # Return 3 values: queue_table (None to refresh), inference_status, status_display
        return None, status_msg, gr.update(value=status_msg, visible=True)

    except Exception as e:
        logger.error("Failed to run inference: {}", e)
        error_msg = f"❌ Error: {e}"
        # Return 3 values on error as well
        return None, error_msg, gr.update(value=error_msg, visible=True)


def run_enhance_on_selected(
    dataframe_data,
    create_new,
    force_overwrite,
    queue_service: SimplifiedQueueService,
    progress=None,
):
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

        # Get selected prompt IDs using utility
        selected_ids = df_utils.get_selected_ids(dataframe_data, id_column=1)

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
            status_msg = f"✅ Queued {len(job_ids)} enhancement job(s)\n📋 Will {action} {len(selected_ids)} prompt(s)\nFirst job at position #{position}"
        else:
            gr.Info(f"🌟 Starting {len(job_ids)} enhancement job(s) now")
            action = "creating new" if create_new else "updating"
            status_msg = f"✅ Started {len(job_ids)} enhancement job(s)\n📋 {action.title()} {len(selected_ids)} prompt(s)"

        # Return 3 values: queue_table (None to refresh), enhance_status, status_display
        return None, status_msg, gr.update(value=status_msg, visible=True)

    except Exception as e:
        import traceback

        logger.error("Failed to run enhancement: {}", str(e))
        logger.error("Traceback: {}", traceback.format_exc())
        error_msg = f"❌ Error: {e}"
        # Return 3 values on error as well
        return None, error_msg, gr.update(value=error_msg, visible=True)
