#!/usr/bin/env python3
"""Event handlers for Runs tab functionality."""

import gradio as gr
from pathlib import Path
from datetime import datetime, timedelta, timezone
from cosmos_workflow.utils.logging import logger


def load_runs_data(status_filter, date_filter, search_text, limit):
    """Load runs data for both gallery and table with filtering."""
    try:
        # Import here to avoid circular dependency
        from cosmos_workflow.ui.app import ops

        if not ops:
            logger.warning("CosmosAPI not initialized")
            return [], [], "No data available"

        # Query runs with status filter
        all_runs = ops.list_runs(
            status=None if status_filter == "all" else status_filter, limit=int(limit)
        )

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
            if run.get("status") == "completed" and run.get("output_path"):
                output_path = Path(run["output_path"])
                if output_path.exists():
                    label = f"{run.get('id', '')[:8]}... - {run.get('prompt_text', '')[:30]}"
                    gallery_data.append((str(output_path), label))

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
        **Completed:** {sum(1 for r in filtered_runs if r.get('status') == 'completed')}
        **Running:** {sum(1 for r in filtered_runs if r.get('status') == 'running')}
        **Failed:** {sum(1 for r in filtered_runs if r.get('status') == 'failed')}
        """

        return gallery_data, table_data, stats

    except Exception as e:
        logger.error("Error loading runs data: %s", str(e))
        return [], [], "Error loading data"


def on_runs_table_select(table_data, evt: gr.SelectData = None):
    """Handle selection of a run from the table."""
    try:
        if not evt or table_data is None:
            return [gr.update(visible=False)] + [gr.update()] * 20

        # Import here to avoid circular dependency
        from cosmos_workflow.ui.app import ops

        # Get selected row
        row_idx = evt.index[0] if isinstance(evt.index, (list, tuple)) else evt.index

        # Extract run ID from table
        import pandas as pd
        if isinstance(table_data, pd.DataFrame):
            run_id = table_data.iloc[row_idx, 1]  # Run ID is second column
        else:
            run_id = table_data[row_idx][1] if row_idx < len(table_data) else None

        if not run_id or not ops:
            return [gr.update(visible=False)] + [gr.update()] * 20

        # Get full run details
        run_details = ops.get_run(run_id)
        if not run_details:
            return [gr.update(visible=False)] + [gr.update()] * 20

        # Extract details
        output_video = run_details.get("output_path", "")
        prompt_text = run_details.get("prompt_text", "")

        # Get input videos
        input_videos = []
        inputs = run_details.get("inputs", {})
        for key in ["video", "edge", "depth", "segmentation"]:
            if key in inputs and inputs[key]:
                path = Path(inputs[key])
                if path.exists():
                    label = key.capitalize()
                    input_videos.append((str(path), label))

        # Get weights
        params = run_details.get("parameters", {})
        weights = params.get("weights", {})

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
                with open(log_path, "r") as f:
                    lines = f.readlines()
                    log_content = "".join(lines[-15:])  # Last 15 lines
            except Exception:
                log_content = "Error reading log file"

        return [
            gr.update(visible=True),  # runs_details_group
            gr.update(value=run_id),  # runs_detail_id (hidden)
            gr.update(value=run_details.get("status", "")),  # runs_detail_status (hidden)
            gr.update(value=input_videos),  # runs_input_videos
            gr.update(value=output_video if Path(output_video).exists() else None),  # runs_output_video
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
            gr.update(value=params.get("prompt_name", "")),  # runs_info_prompt_name
            gr.update(value=run_details.get("created_at", "")[:19]),  # runs_info_created
            gr.update(value=run_details.get("completed_at", "")[:19]),  # runs_info_completed
            gr.update(value=params),  # runs_params_json
            gr.update(value=log_path),  # runs_log_path
            gr.update(value=log_content),  # runs_log_output
        ]

    except Exception as e:
        logger.error("Error selecting run: %s", str(e))
        return [gr.update(visible=False)] + [gr.update()] * 20


def load_run_logs(log_path):
    """Load full log file content."""
    try:
        if not log_path or not Path(log_path).exists():
            return "No log file available"

        with open(log_path, "r") as f:
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
        # Import here to avoid circular dependency
        from cosmos_workflow.ui.app import ops

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
                logger.error("Error deleting run %s: %s", run_id, str(e))

        # Remove deleted runs from table
        if isinstance(table_data, pd.DataFrame):
            table_data = table_data[~table_data.iloc[:, 1].isin(selected_ids)]
        else:
            table_data = [row for row in table_data if row[1] not in selected_ids]

        return table_data, f"Deleted {deleted_count} runs"

    except Exception as e:
        logger.error("Error deleting runs: %s", str(e))
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