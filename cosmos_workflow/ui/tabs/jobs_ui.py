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
                    # Queue Summary Card
                    components["queue_summary_card"] = gr.Markdown(
                        """**Queue Summary**

📋 **Pending:** 0 runs
⏭️ **Next in Queue:** None
🖥️ **GPU Status:** Available
                        """,
                        elem_classes=["status-card"],
                    )

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

                # Auto-refresh timer (inactive by default)
                components["queue_timer"] = gr.Timer(value=2.0, active=False)

                # Queue Control Section
                gr.Markdown("#### ⚙️ Queue Controls")
                with gr.Group():
                    with gr.Row():
                        components["kill_job_btn"] = gr.Button(
                            "🛑 Kill Active Job",
                            variant="stop",
                            size="sm",
                        )
                        components["clear_queue_btn"] = gr.Button(
                            "🗑️ Clear Queue",
                            variant="stop",
                            size="sm",
                        )

                    # Confirmation dialogs (hidden by default)
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

                    with gr.Group(visible=False) as components["clear_confirmation"]:
                        gr.Markdown("⚠️ **Confirm Clear Queue**")
                        components["clear_preview"] = gr.Markdown(
                            "This will cancel all pending runs."
                        )
                        with gr.Row():
                            components["confirm_clear_btn"] = gr.Button(
                                "⚠️ Confirm Clear",
                                variant="stop",
                                size="sm",
                            )
                            components["cancel_clear_btn"] = gr.Button(
                                "Cancel",
                                variant="secondary",
                                size="sm",
                            )

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
