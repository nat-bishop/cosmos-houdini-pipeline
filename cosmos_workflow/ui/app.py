#!/usr/bin/env python3
"""Simple Gradio UI for Cosmos Workflow - Log Viewer."""

import gradio as gr

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.ui.log_viewer import LogViewer
from cosmos_workflow.utils.logging import logger

# Load configuration
config = ConfigManager()

# Initialize unified operations
ops = CosmosAPI(config=config)

# Initialize log viewer
log_viewer = LogViewer(max_lines=2000)


def stream_callback(content):
    """Callback for log streaming."""
    log_viewer.add_from_stream(content)


def start_log_streaming():
    """Start streaming logs from active container."""
    # Clear previous logs
    log_viewer.clear()

    try:
        # Get active containers
        containers = ops.get_active_containers()

        if not containers:
            return "No active containers found", log_viewer.get_html()

        if len(containers) > 1:
            # Multiple containers - use the first one
            container_id = containers[0]["container_id"]
            message = f"Multiple containers found, streaming from {container_id}"
        else:
            container_id = containers[0]["container_id"]
            message = f"Streaming logs from container {container_id}"

        # Stream with callback for UI updates
        ops.stream_container_logs(container_id, callback=stream_callback)
        return message, log_viewer.get_html()
    except RuntimeError as e:
        return f"Error: {e}", log_viewer.get_html()
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
                status = "Multiple containers active - streaming will fail"

            return display_text.strip(), status
        else:
            return "No active containers found", "No containers to stream from"
    except Exception as e:
        return f"Error: {e}", "Error checking containers"


def check_and_auto_stream():
    """Check for active containers and auto-start streaming if available."""
    try:
        containers = ops.get_active_containers()

        if containers:
            # Format container display
            display_text = f"Found {len(containers)} active container(s)\n\n"
            for container in containers:
                display_text += f"Container: {container['container_id']}\n"
                display_text += f"Image: {container.get('image', 'Unknown')}\n"
                display_text += f"Status: {container.get('status', 'Unknown')}\n"
                display_text += "-" * 40 + "\n"

            # Auto-start streaming if single container
            if len(containers) == 1:
                streaming_status, log_html = start_log_streaming()
                job_status = f"Auto-streaming from container {containers[0]['container_id']}"
            else:
                job_status = "Multiple containers found. Click 'Start Streaming' to begin."
                streaming_status = "Multiple containers active"
                log_html = log_viewer.get_html()

            return display_text.strip(), job_status, streaming_status, log_html
        else:
            # No containers - show waiting message
            job_status = "No active containers. Waiting..."
            return (
                "No active containers found",
                job_status,
                "Waiting for containers",
                log_viewer.get_html(),
            )
    except Exception as e:
        return f"Error: {e}", "Error checking containers", "Error", log_viewer.get_html()


def create_ui():
    """Create the Gradio interface."""
    with gr.Blocks(title="Cosmos Log Viewer") as app:
        gr.Markdown("# Cosmos Workflow - Log Viewer")

        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("### Controls")

                # Running jobs section
                gr.Markdown("#### Active Containers")
                running_jobs_display = gr.Textbox(
                    label="Active Containers",
                    value="Checking for active containers...",
                    interactive=False,
                    lines=3,
                )
                check_jobs_btn = gr.Button("Check Active Containers", size="sm")

                # Job status display
                job_status = gr.Textbox(
                    label="Stream Status",
                    value="Click 'Start Streaming' to stream from active container",
                    interactive=False,
                )

                stream_btn = gr.Button("Start Streaming", variant="primary", size="sm")
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

        stream_btn.click(
            fn=start_log_streaming,
            inputs=[],
            outputs=[job_status, log_display],
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

    logger.info("Starting Gradio UI on %s:%d", host, port)

    app = create_ui()
    app.launch(
        share=share,
        server_name=host,
        server_port=port,
    )
