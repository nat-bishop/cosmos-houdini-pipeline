#!/usr/bin/env python3
"""Active Jobs Tab UI for Cosmos Workflow Manager.

This module contains only the UI creation code for the Active Jobs tab.
Business logic remains in the main app.py file.
"""

import gradio as gr

from cosmos_workflow.ui.log_viewer import LogViewer


def create_jobs_tab_ui():
    """Create the Active Jobs tab UI components.

    Returns:
        dict: Dictionary of all UI components for event binding
    """
    components = {}

    # Initialize log viewer
    log_viewer = LogViewer(max_lines=2000)

    with gr.Tab("🚀 Active Jobs", id=5) as components["jobs_tab"]:
        gr.Markdown("### Active Job Monitoring & Logs")
        gr.Markdown("Monitor active GPU jobs and view real-time execution logs")

        with gr.Row():
            with gr.Column(scale=1):
                # Active Job Section
                gr.Markdown("#### 🚀 Active Job")
                with gr.Group():
                    # Active Job Card
                    components["active_job_card"] = gr.Markdown(
                        """**No Active Job**

Currently idle - no jobs running
                        """,
                        elem_classes=["status-card"],
                    )

                # Container details display
                components["running_jobs_display"] = gr.Textbox(
                    label="Container Details",
                    value="No active containers found",
                    interactive=False,
                    visible=True,
                    lines=6,
                )

                # Job Control Section
                gr.Markdown("#### ⚙️ Job Controls")
                with gr.Group():
                    components["kill_job_btn"] = gr.Button(
                        "🛑 Kill Active Job",
                        variant="stop",
                        size="sm",
                        interactive=True,
                    )

                    # Kill confirmation dialog (hidden by default)
                    with gr.Group(visible=False) as components["kill_confirmation"]:
                        gr.Markdown("⚠️ **Confirm Kill Active Job**")
                        components["kill_preview"] = gr.Markdown(
                            "This will stop the currently running container."
                        )
                        with gr.Row():
                            components["confirm_kill_btn"] = gr.Button(
                                "⚠️ Confirm Kill",
                                variant="stop",
                                size="sm",
                            )
                            components["cancel_kill_btn"] = gr.Button(
                                "Cancel",
                                variant="secondary",
                                size="sm",
                            )

                # Log Streaming Controls
                gr.Markdown("#### 📊 Log Streaming")
                components["job_status"] = gr.Textbox(
                    label="Stream Status",
                    value="Logs will auto-start when switching to this tab",
                    interactive=False,
                )
                components["stream_btn"] = gr.Button(
                    "🔄 Refresh & Stream", variant="primary", size="sm"
                )

            with gr.Column(scale=3):
                gr.Markdown("#### 📝 Log Output")
                components["log_display"] = gr.Textbox(
                    value="",
                    label=None,
                    interactive=False,
                    lines=25,
                    max_lines=25,
                    autoscroll=True,
                    elem_id="log_display",
                    container=False,
                )

                # Clear logs button
                components["clear_logs_btn"] = gr.Button(
                    "🗑️ Clear Logs", size="sm", variant="secondary"
                )

    # Store log_viewer reference for access by business logic
    components["log_viewer"] = log_viewer

    return components
