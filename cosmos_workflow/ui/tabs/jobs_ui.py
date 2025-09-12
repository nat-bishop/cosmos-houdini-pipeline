#!/usr/bin/env python3
"""Jobs & Queue Tab UI for Cosmos Workflow Manager.

This module contains only the UI creation code for the Jobs & Queue tab.
Business logic remains in the main app.py file.
"""

import gradio as gr
from cosmos_workflow.ui.log_viewer import LogViewer


def create_jobs_tab_ui():
    """Create the Jobs & Queue tab UI components.

    Returns:
        dict: Dictionary of all UI components for event binding
    """
    components = {}

    # Initialize log viewer
    log_viewer = LogViewer(max_lines=2000)

    with gr.Tab("📦 Jobs & Queue", id=5) as components["jobs_tab"]:
        gr.Markdown("### Jobs, Queue & Log Monitoring")
        gr.Markdown("Monitor active jobs, queue status, and view real-time logs")

        with gr.Row():
            with gr.Column(scale=1):
                # Queue Status Section
                gr.Markdown("#### 📦 Queue Status")
                with gr.Group():
                    components["queue_status"] = gr.Textbox(
                        label="Current Queue",
                        value="Queue: Empty | GPU: Available",
                        interactive=False,
                    )
                    components["execution_status"] = gr.Textbox(
                        label="GPU Status",
                        value="Idle",
                        interactive=False,
                    )
                    # Auto-refresh queue status
                    components["queue_timer"] = gr.Timer(value=2.0, active=True)

                # Active Jobs Section
                gr.Markdown("#### 🚀 Active Jobs")
                components["running_jobs_display"] = gr.Textbox(
                    label="Running Containers",
                    value="Checking for active containers...",
                    interactive=False,
                    lines=5,
                )
                # Individual refresh button removed - using global refresh

                # Recent Runs
                gr.Markdown("#### 📋 Recent Runs")
                components["recent_runs_table"] = gr.Dataframe(
                    headers=["Run ID", "Status", "Started"],
                    datatype=["str", "str", "str"],
                    interactive=False,
                    wrap=True,
                )

                # Log Streaming Controls
                gr.Markdown("#### 📊 Log Streaming")
                components["job_status"] = gr.Textbox(
                    label="Stream Status",
                    value="Click 'Start Streaming' to begin",
                    interactive=False,
                )
                components["stream_btn"] = gr.Button(
                    "▶️ Start Streaming", variant="primary", size="sm"
                )

            with gr.Column(scale=3):
                gr.Markdown("#### 📝 Log Output")
                components["log_display"] = gr.HTML(
                    value=log_viewer.get_html(),
                    elem_id="log_display",
                )

                # Log Statistics at bottom
                with gr.Row():
                    components["log_stats"] = gr.Textbox(
                        label="Log Statistics",
                        value="Total: 0 | Errors: 0 | Warnings: 0",
                        interactive=False,
                        scale=2,
                    )
                    components["clear_logs_btn"] = gr.Button("🗑️ Clear Logs", size="sm", scale=1)

    # Store log_viewer reference for access by business logic
    components["log_viewer"] = log_viewer

    return components
