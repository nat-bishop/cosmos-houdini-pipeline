#!/usr/bin/env python3
"""Event handlers for Runs tab functionality."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import gradio as gr

from cosmos_workflow.utils.logging import logger


def load_runs_data(status_filter, date_filter, search_text, limit):
    """Load runs data for both gallery and table with filtering."""
    try:
        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()

        if not ops:
            logger.warning("CosmosAPI not initialized")
            return [], [], "No data available"

        # Query runs with status filter
        all_runs = ops.list_runs(
            status=None if status_filter == "all" else status_filter, limit=int(limit)
        )

        # Enrich runs with prompt text
        for run in all_runs:
            if not run.get("prompt_text") and run.get("prompt_id"):
                prompt = ops.get_prompt(run["prompt_id"])
                if prompt:
                    run["prompt_text"] = prompt.get("prompt_text", "")

        # Apply date filter
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
                # Extract output video from files array
                outputs = run.get("outputs", {})
                files = outputs.get("files", []) if isinstance(outputs, dict) else []

                # Find the output.mp4 file
                output_video = None
                for file_path in files:
                    if file_path.endswith("output.mp4"):
                        # Normalize path for Windows
                        output_video = Path(file_path)
                        if output_video.exists():
                            break

                if output_video:
                    # Get prompt text for label
                    prompt_text = run.get("prompt_text", "")
                    label = f"{run.get('id', '')[:8]}... - {prompt_text[:30]}"
                    gallery_data.append((str(output_video), label))

        # Build table data
        table_data = []
        for run in filtered_runs:
            run_id = run.get("id", "")
            status = run.get("status", "unknown")
            prompt_text = run.get("prompt_text", "")[:50]

            # Calculate duration
            duration = "N/A"
            if run.get("created_at") and run.get("completed_at"):
                try:
                    start = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(run["completed_at"].replace("Z", "+00:00"))
                    duration_delta = end - start
                    duration = str(duration_delta).split(".")[0]
                except Exception:
                    pass

            created = run.get("created_at", "")[:19] if run.get("created_at") else ""
            completed = run.get("completed_at", "")[:19] if run.get("completed_at") else ""

            # Add selection checkbox (False by default)
            table_data.append([False, run_id, status, prompt_text, duration, created, completed])

        # Build statistics
        stats = f"""
        **Total Runs:** {len(filtered_runs)}
        **Completed:** {sum(1 for r in filtered_runs if r.get("status") == "completed")}
        **Running:** {sum(1 for r in filtered_runs if r.get("status") == "running")}
        **Failed:** {sum(1 for r in filtered_runs if r.get("status") == "failed")}
        """

        return gallery_data, table_data, stats

    except Exception as e:
        import traceback

        logger.error("Error loading runs data: {}\n{}", str(e), traceback.format_exc())
        return [], [], "Error loading data"


def on_runs_table_select(table_data, evt: gr.SelectData):
    """Handle selection of a run from the table."""
    try:
        logger.info(
            "on_runs_table_select called - evt: {}, table_data type: {}", evt, type(table_data)
        )

        if evt is None or table_data is None:
            logger.warning("No evt or table_data, hiding details")
            return [gr.update(visible=False)] + [gr.update()] * 20

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()

        # Get selected row
        logger.info("Event index: {}, type: {}", evt.index, type(evt.index))
        row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index
        logger.info("Selected row index: {}", row_idx)

        # Extract run ID from table
        import pandas as pd

        if isinstance(table_data, pd.DataFrame):
            run_id = table_data.iloc[row_idx, 1]  # Run ID is second column
            logger.info("Extracted run_id from DataFrame: {}", run_id)
        else:
            run_id = table_data[row_idx][1] if row_idx < len(table_data) else None
            logger.info("Extracted run_id from list: {}", run_id)

        if not run_id or not ops:
            logger.warning("No run_id ({}) or ops ({}), hiding details", run_id, ops)
            return [gr.update(visible=False)] + [gr.update()] * 20

        # Get full run details
        run_details = ops.get_run(run_id)
        logger.info("Retrieved run_details: {}", bool(run_details))
        if not run_details:
            logger.warning("No run_details found for run_id: {}", run_id)
            return [gr.update(visible=False)] + [gr.update()] * 20

        # Extract details
        # Get output video from files array
        outputs = run_details.get("outputs", {})
        files = outputs.get("files", []) if isinstance(outputs, dict) else []

        # Find the output.mp4 file
        output_video = ""
        for file_path in files:
            if file_path.endswith("output.mp4"):
                # Normalize path for Windows
                output_video = str(Path(file_path))
                break

        logger.info("Output video path: {}", output_video)

        # Get prompt text (will need to fetch from prompt later)
        prompt_text = run_details.get("prompt_text", "")

        # If prompt_text is not in run, fetch it from the prompt
        if not prompt_text and run_details.get("prompt_id"):
            prompt = ops.get_prompt(run_details["prompt_id"])
            if prompt:
                prompt_text = prompt.get("prompt_text", "")

        # Get input videos from prompt
        input_videos = []
        prompt_id = run_details.get("prompt_id")
        if prompt_id and ops:
            prompt = ops.get_prompt(prompt_id)
            if prompt:
                prompt_inputs = prompt.get("inputs", {})
                for key in ["video", "edge", "depth", "segmentation"]:
                    if prompt_inputs.get(key):
                        path = Path(prompt_inputs[key])
                        if path.exists():
                            label = key.capitalize()
                            input_videos.append((str(path), label))

        # Get weights and parameters from execution_config
        exec_config = run_details.get("execution_config", {})
        weights = exec_config.get("weights", {})
        params = exec_config  # Use entire execution_config as parameters

        # Get metadata
        duration = "N/A"
        if run_details.get("created_at") and run_details.get("completed_at"):
            try:
                start = datetime.fromisoformat(run_details["created_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(run_details["completed_at"].replace("Z", "+00:00"))
                duration_delta = end - start
                duration = str(duration_delta).split(".")[0]
            except Exception:
                pass

        # Get log path
        log_path = run_details.get("log_path", "")
        log_content = ""
        if log_path and Path(log_path).exists():
            try:
                with open(log_path) as f:
                    lines = f.readlines()
                    log_content = "".join(lines[-15:])  # Last 15 lines
            except Exception:
                log_content = "Error reading log file"

        logger.info(
            "Returning updates - visible: True, run_id: {}, output_video: {}", run_id, output_video
        )

        return [
            gr.update(visible=True),  # runs_details_group
            gr.update(value=run_id),  # runs_detail_id (hidden)
            gr.update(value=run_details.get("status", "")),  # runs_detail_status (hidden)
            gr.update(value=input_videos),  # runs_input_videos
            gr.update(
                value=output_video if output_video and Path(output_video).exists() else None
            ),  # runs_output_video
            gr.update(value=weights.get("vis", 0)),  # runs_visual_weight
            gr.update(value=weights.get("edge", 0)),  # runs_edge_weight
            gr.update(value=weights.get("depth", 0)),  # runs_depth_weight
            gr.update(value=weights.get("seg", 0)),  # runs_segmentation_weight
            gr.update(value=prompt_text),  # runs_prompt_text
            gr.update(value=run_id),  # runs_info_id
            gr.update(value=run_details.get("prompt_id", "")),  # runs_info_prompt_id
            gr.update(value=run_details.get("status", "")),  # runs_info_status
            gr.update(value=duration),  # runs_info_duration
            gr.update(value=run_details.get("run_type", "inference")),  # runs_info_type
            gr.update(value="N/A"),  # runs_info_prompt_name (field doesn't exist)
            gr.update(value=run_details.get("created_at", "")[:19]),  # runs_info_created
            gr.update(value=run_details.get("completed_at", "")[:19]),  # runs_info_completed
            gr.update(value=params),  # runs_params_json
            gr.update(value=log_path),  # runs_log_path
            gr.update(value=log_content),  # runs_log_output
        ]

    except Exception as e:
        logger.error("Error selecting run: {}", str(e))
        return [gr.update(visible=False)] + [gr.update()] * 20


def load_run_logs(log_path):
    """Load full log file content."""
    try:
        if not log_path or not Path(log_path).exists():
            return "No log file available"

        with open(log_path) as f:
            content = f.read()

        return content
    except Exception as e:
        return f"Error reading log file: {e}"


def select_all_runs(table_data):
    """Select all runs in the table."""
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
            new_row = list(row)
            new_row[0] = True
            updated_data.append(new_row)
        return updated_data


def clear_runs_selection(table_data):
    """Clear all selections in the runs table."""
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
            new_row = list(row)
            new_row[0] = False
            updated_data.append(new_row)
        return updated_data


def delete_selected_runs(table_data):
    """Delete selected runs."""
    try:
        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()

        if not ops or table_data is None:
            return table_data, "0 runs selected"

        # Get selected run IDs
        selected_ids = []
        import pandas as pd

        if isinstance(table_data, pd.DataFrame):
            for _, row in table_data.iterrows():
                if row.iloc[0]:  # Checkbox is checked
                    selected_ids.append(row.iloc[1])  # Run ID
        else:
            for row in table_data:
                if row[0]:  # Checkbox is checked
                    selected_ids.append(row[1])  # Run ID

        if not selected_ids:
            return table_data, "0 runs selected"

        # Delete runs
        deleted_count = 0
        for run_id in selected_ids:
            try:
                result = ops.delete_run(run_id)
                if result.get("success"):
                    deleted_count += 1
            except Exception as e:
                logger.error("Error deleting run {}: {}", run_id, str(e))

        # Remove deleted runs from table
        if isinstance(table_data, pd.DataFrame):
            table_data = table_data[~table_data.iloc[:, 1].isin(selected_ids)]
        else:
            table_data = [row for row in table_data if row[1] not in selected_ids]

        return table_data, f"Deleted {deleted_count} runs"

    except Exception as e:
        logger.error("Error deleting runs: {}", str(e))
        return table_data, f"Error: {e}"


def update_runs_selection_info(table_data):
    """Update the selection info text based on checked rows."""
    try:
        if table_data is None:
            return "0 runs selected"

        import pandas as pd

        if isinstance(table_data, pd.DataFrame):
            selected = sum(1 for _, row in table_data.iterrows() if row.iloc[0])
        else:
            selected = sum(1 for row in table_data if row[0])

        return f"{selected} run{'s' if selected != 1 else ''} selected"
    except Exception:
        return "0 runs selected"
