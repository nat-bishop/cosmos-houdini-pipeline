#!/usr/bin/env python3
"""Simple Gradio UI for Cosmos Workflow - Log Viewer."""

import gradio as gr

from cosmos_workflow.api import WorkflowOperations
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.ui.log_viewer import LogViewer
from cosmos_workflow.utils.logging import logger

# Load configuration
config = ConfigManager()

# Initialize unified operations
ops = WorkflowOperations(config=config)

# Initialize log viewer
log_viewer = LogViewer(max_lines=2000)


def get_running_jobs():
    """Get currently running jobs from database."""
    try:
        # Get running runs from database
        running_runs = ops.list_runs(status="running", limit=10)

        if not running_runs:
            return None, "No active jobs found"

        jobs = []
        for run in running_runs:
            prompt = ops.get_prompt(run.get("prompt_id"))
            prompt_text = prompt.get("prompt_text", "Unknown")[:50] if prompt else "Unknown"

            jobs.append(
                {
                    "run_id": run.get("id"),  # Fixed: database field is 'id' not 'run_id'
                    "prompt_name": run.get("prompt_name", "Unknown"),
                    "prompt_text": prompt_text,
                    "started_at": run.get("started_at", "Unknown"),
                }
            )

        return jobs, f"Found {len(jobs)} active job(s)"
    except Exception as e:
        logger.error("Failed to get running jobs: %s", e)
        return None, f"Error: {e}"


def stream_callback(content):
    """Callback for log streaming."""
    log_viewer.add_from_stream(content)


def start_log_streaming(run_id):
    """Start streaming logs for a run using the new RemoteLogStreamer API."""
    if not run_id:
        return "Please enter a Run ID", log_viewer.get_html()

    # Get run details
    run = ops.get_run(run_id)
    if not run:
        return f"Run {run_id} not found", log_viewer.get_html()

    # Clear previous logs
    log_viewer.clear()

    try:
        # Use the new stream_run_logs API with callback
        ops.stream_run_logs(run_id=run_id, callback=stream_callback, follow=True)
        prompt_name = run.get("prompt_name", run_id)
        return f"Streaming logs for {prompt_name}", log_viewer.get_html()
    except Exception as e:
        return f"Failed to start streaming: {e}", log_viewer.get_html()


def refresh_logs():
    """Refresh the log display."""
    return log_viewer.get_html()


def filter_logs(level_filter, search_text):
    """Apply filters to the logs."""
    return log_viewer.get_html(level_filter=level_filter, search=search_text)


def get_log_stats():
    """Get statistics about current logs."""
    stats = log_viewer.get_stats()
    return f"Total: {stats['total']} | Errors: {stats['errors']} | Warnings: {stats['warnings']}"


def clear_logs():
    """Clear all logs."""
    log_viewer.clear()
    return log_viewer.get_html(), "Logs cleared"


def check_running_jobs():
    """Check for running jobs and format for display."""
    jobs, message = get_running_jobs()

    if jobs:
        display_text = f"{message}\n\n"
        for job in jobs:
            display_text += f"Run ID: {job['run_id']}\n"
            display_text += f"Prompt: {job['prompt_text']}...\n"
            display_text += f"Started: {job['started_at']}\n"
            display_text += "-" * 40 + "\n"
        return display_text.strip(), jobs[0]["run_id"] if jobs else ""
    else:
        return message, ""


def check_and_auto_stream():
    """Check for running jobs and auto-start streaming if job exists."""
    jobs, message = get_running_jobs()

    if jobs:
        # Auto-start streaming for the first (and typically only) job
        first_job = jobs[0]
        run_id = first_job["run_id"]
        prompt_name = first_job["prompt_name"]

        # Format job display
        display_text = f"{message}\n\n"
        for job in jobs:
            display_text += f"Run ID: {job['run_id']}\n"
            display_text += f"Prompt: {job['prompt_text']}...\n"
            display_text += f"Started: {job['started_at']}\n"
            display_text += "-" * 40 + "\n"

        # Auto-start streaming
        streaming_status, log_html = start_log_streaming(run_id)

        # Show which job is being streamed
        job_status = f"Auto-streaming: {prompt_name} ({run_id})"

        return display_text.strip(), job_status, streaming_status, log_html
    else:
        # No jobs - show waiting message
        job_status = "No active jobs. Waiting..."
        return message, job_status, "Waiting for active jobs", log_viewer.get_html()


def create_ui():
    """Create the Gradio interface."""
    with gr.Blocks(title="Cosmos Log Viewer") as app:
        gr.Markdown("# Cosmos Workflow - Log Viewer")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Controls")

                # Running jobs section
                gr.Markdown("#### Active Jobs")
                running_jobs_display = gr.Textbox(
                    label="Active Runs",
                    value="Checking for active jobs...",
                    interactive=False,
                    lines=3,
                )
                check_jobs_btn = gr.Button("Check Active Jobs", size="sm")

                # Job status display (replaces manual run ID input)
                job_status = gr.Textbox(
                    label="Current Job",
                    value="Checking for active jobs...",
                    interactive=False,
                )

                refresh_btn = gr.Button("Refresh", size="sm")

                # Filters
                gr.Markdown("### Filters")
                level_filter = gr.Dropdown(
                    label="Log Level",
                    choices=["ALL", "ERROR", "WARNING", "INFO"],
                    value="ALL",
                )

                search_input = gr.Textbox(
                    label="Search",
                    placeholder="Search logs...",
                )

                # Stats
                gr.Markdown("### Statistics")
                _ = gr.Textbox(
                    label="Log Stats",
                    value="Total: 0 | Errors: 0 | Warnings: 0",
                    interactive=False,
                )

                # Actions
                gr.Markdown("### Actions")
                clear_btn = gr.Button("Clear Logs", variant="stop")

                # Status
                status_display = gr.Textbox(
                    label="Status",
                    value="Ready",
                    interactive=False,
                )

            with gr.Column(scale=3):
                gr.Markdown("### Log Output")
                log_display = gr.HTML(
                    value=log_viewer.get_html(),
                    elem_id="log_display",
                )

        # Event handlers
        check_jobs_btn.click(
            fn=check_running_jobs,
            inputs=[],
            outputs=[running_jobs_display, job_status],
        )

        refresh_btn.click(
            fn=refresh_logs,
            inputs=[],
            outputs=[log_display],
        )

        level_filter.change(
            fn=filter_logs,
            inputs=[level_filter, search_input],
            outputs=[log_display],
        )

        search_input.change(
            fn=filter_logs,
            inputs=[level_filter, search_input],
            outputs=[log_display],
        )

        clear_btn.click(
            fn=clear_logs,
            inputs=[],
            outputs=[log_display, status_display],
        )

        # Auto-refresh could be added with a timer if needed
        # For now, users can click the Refresh button

        # Check for running jobs on load and auto-stream if available
        app.load(
            fn=check_and_auto_stream,
            inputs=[],
            outputs=[running_jobs_display, job_status, status_display, log_display],
        )

    return app


if __name__ == "__main__":
    # Get UI configuration from config.toml
    ui_config = config._config_data.get("ui", {})
    host = ui_config.get("host", "0.0.0.0")  # noqa: S104
    port = ui_config.get("port", 7860)
    share = ui_config.get("share", False)

    logger.info(f"Starting Gradio UI on {host}:{port}")

    app = create_ui()
    app.launch(
        share=share,
        server_name=host,
        server_port=port,
    )
