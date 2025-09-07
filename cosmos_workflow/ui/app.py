#!/usr/bin/env python3
"""Simple Gradio UI for Cosmos Workflow - Log Viewer."""

import threading
from pathlib import Path

import gradio as gr

from cosmos_workflow.config import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.database import init_database
from cosmos_workflow.execution.docker_executor import DockerExecutor
from cosmos_workflow.monitoring.log_streamer import RemoteLogStreamer
from cosmos_workflow.services import WorkflowService
from cosmos_workflow.ui.log_viewer import LogViewer
from cosmos_workflow.utils.logging import logger

# Initialize services
config = ConfigManager()
local_config = config.get_local_config()
db_path = local_config.outputs_dir / "cosmos.db"
db = init_database(str(db_path))
service = WorkflowService(db, config)

# Initialize log viewer
log_viewer = LogViewer(max_lines=2000)

# SSH and Docker for streaming
ssh_manager = None
docker_executor = None
streamer = None
stream_thread = None


def initialize_remote_connection():
    """Initialize SSH and Docker connections."""
    global ssh_manager, docker_executor, streamer
    try:
        remote_config = config.get_remote_config()
        ssh_manager = SSHManager(
            hostname=remote_config.hostname,
            username=remote_config.username,
            key_filename=remote_config.ssh_key_path,
        )
        docker_executor = DockerExecutor(ssh_manager, config)
        streamer = RemoteLogStreamer(ssh_manager)
        return True, "Connected to remote GPU instance"
    except Exception as e:
        logger.error("Failed to connect: %s", e)
        return False, f"Connection failed: {e}"


def get_running_jobs():
    """Get currently running jobs from the database and Docker."""
    try:
        # First check database for running runs
        running_runs = service.list_runs(status="running", limit=10)

        jobs = []

        # Add database runs
        for run in running_runs:
            prompt_id = run.get("prompt_id", "Unknown")
            run_id = run.get("run_id", "Unknown")
            prompt = service.get_prompt(prompt_id) if prompt_id != "Unknown" else None
            prompt_text = prompt.get("prompt_text", "Unknown")[:50] if prompt else "Unknown"

            jobs.append(
                {
                    "run_id": run_id,
                    "prompt_id": prompt_id,
                    "prompt_text": prompt_text,
                    "started_at": run.get("started_at", "Unknown"),
                    "source": "database",
                }
            )

        # Also check for Docker containers if connected
        # Note: This would require SSH connection which may not always be available
        # For now, we'll just use database runs

        if not jobs:
            return None, "No running inference jobs found"

        return jobs, f"Found {len(jobs)} running inference job(s)"
    except Exception as e:
        logger.error("Failed to get running jobs: %s", e)
        return None, f"Error getting running jobs: {e}"


def stream_callback(content):
    """Callback for log streaming."""
    log_viewer.add_from_stream(content)


def start_log_streaming(run_id):
    """Start streaming logs for a run."""
    global stream_thread

    if not run_id:
        return "Please enter a Run ID", log_viewer.get_html()

    # Get run details
    run = service.get_run(run_id)
    if not run:
        return f"Run {run_id} not found", log_viewer.get_html()

    # Clear previous logs
    log_viewer.clear()

    # Check if we have a remote log path
    prompt_name = run.get("prompt_name", run_id)
    remote_log_path = f"/workspace/outputs/{prompt_name}/run.log"
    local_log_path = Path(f"outputs/{prompt_name}/logs/run_{run_id}.log")

    # Initialize connection if needed
    if not ssh_manager:
        success, msg = initialize_remote_connection()
        if not success:
            return msg, log_viewer.get_html()

    # Stop any existing stream
    if stream_thread and stream_thread.is_alive():
        return "Stream already running", log_viewer.get_html()

    # Start streaming in background
    stream_thread = threading.Thread(
        target=streamer.stream_remote_log,
        args=(remote_log_path, local_log_path),
        kwargs={
            "callback": stream_callback,
            "poll_interval": 2.0,
            "timeout": 3600,
            "wait_for_file": True,
            "completion_marker": "[COSMOS_COMPLETE]",
        },
        daemon=True,
    )
    stream_thread.start()

    return f"Streaming logs for run {run_id}", log_viewer.get_html()


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


def create_ui():
    """Create the Gradio interface."""
    with gr.Blocks(title="Cosmos Log Viewer") as app:
        gr.Markdown("# Cosmos Workflow - Log Viewer")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Controls")

                # Running jobs section
                gr.Markdown("#### Running Inference Jobs")
                running_jobs_display = gr.Textbox(
                    label="Active Inference Runs",
                    value="Checking for running inference jobs...",
                    interactive=False,
                    lines=3,
                )
                check_jobs_btn = gr.Button("Check Running Jobs", size="sm")

                # Run selection
                run_id_input = gr.Textbox(
                    label="Run ID",
                    placeholder="Enter run ID (e.g., run_xxxxx)",
                )

                with gr.Row():
                    start_btn = gr.Button("Start Streaming", variant="primary")
                    refresh_btn = gr.Button("Refresh")

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
            outputs=[running_jobs_display, run_id_input],
        )

        start_btn.click(
            fn=start_log_streaming,
            inputs=[run_id_input],
            outputs=[status_display, log_display],
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

        # Check for running jobs on load
        app.load(
            fn=check_running_jobs,
            inputs=[],
            outputs=[running_jobs_display, run_id_input],
        )

    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch(share=False, server_name="0.0.0.0", server_port=7860)  # noqa: S104
