#!/usr/bin/env python3
"""Runs Tab UI for Cosmos Workflow Manager.

This module contains only the UI creation code for the Runs tab.
Business logic remains in the main app.py file.
"""

import gradio as gr


def create_runs_tab_ui():
    """Create the Runs tab UI components.

    Returns:
        dict: Dictionary of all UI components for event binding
    """
    components = {}

    with gr.Tab("🎬 Runs", id=3) as components["runs_tab"]:
        gr.Markdown("### Run Management Center")
        gr.Markdown(
            "View, filter, and manage all runs with generated outputs and detailed information"
        )

        with gr.Row():
            # Left: Filters and Statistics
            with gr.Column(scale=1):
                gr.Markdown("#### 🔍 Filter Options")

                with gr.Group(elem_classes=["detail-card"]):
                    components["runs_status_filter"] = gr.Dropdown(
                        choices=[
                            "all",
                            "completed",
                            "running",
                            "pending",
                            "failed",
                            "cancelled",
                        ],
                        value="all",
                        label="Status Filter",
                        info="Filter runs by status",
                    )

                    components["runs_date_filter"] = gr.Dropdown(
                        choices=[
                            "all",
                            "today",
                            "yesterday",
                            "last_7_days",
                            "last_30_days",
                        ],
                        value="all",
                        label="Date Range",
                        info="Filter by creation date",
                    )

                    components["runs_search"] = gr.Textbox(
                        label="Search",
                        placeholder="Search by prompt text or ID...",
                        info="Search in prompt text or run ID",
                    )

                    components["runs_limit"] = gr.Number(
                        value=50,
                        label="Max Results",
                        minimum=10,
                        maximum=200,
                        info="Maximum number of runs to display",
                    )

                gr.Markdown("#### 📊 Statistics")
                with gr.Group(elem_classes=["detail-card"]):
                    components["runs_stats"] = gr.Markdown("Loading statistics...")

            # Right: Gallery and Table tabs
            with gr.Column(scale=3):
                with gr.Tabs():
                    # Generated Videos tab
                    with gr.Tab("Generated Videos"):
                        components["runs_gallery"] = gr.Gallery(
                            label="Output Videos",
                            show_label=False,
                            elem_id="runs_gallery",
                            columns=3,
                            rows=2,
                            height=400,
                            object_fit="contain",
                            preview=False,  # Disable preview popup
                            allow_preview=False,  # Disable click to expand
                            show_download_button=True,
                            interactive=False,  # Read-only gallery
                        )

                    # Run Records tab
                    with gr.Tab("Run Records"):
                        # Batch operations
                        with gr.Row():
                            components["runs_select_all_btn"] = gr.Button("☑ Select All", size="sm")
                            components["runs_clear_selection_btn"] = gr.Button(
                                "☐ Clear Selection", size="sm"
                            )
                            components["runs_delete_selected_btn"] = gr.Button(
                                "🗑️ Delete Selected",
                                size="sm",
                                variant="stop",
                            )
                            components["runs_selected_info"] = gr.Markdown("0 runs selected")

                        components["runs_table"] = gr.Dataframe(
                            headers=[
                                "Select",
                                "Run ID",
                                "Status",
                                "Prompt",
                                "Duration",
                                "Created",
                                "Completed",
                            ],
                            datatype=["bool", "str", "str", "str", "str", "str", "str"],
                            interactive=True,
                            max_height=400,
                            elem_classes=["run-history-table"],
                        )

                        # Run Details below the table
                        with gr.Group(visible=False, elem_classes=["detail-card"]) as components[
                            "runs_details_group"
                        ]:
                            gr.Markdown("### 📋 Run Details")

                            with gr.Tabs():
                                # Main Tab
                                with gr.Tab("Main"):
                                    # Generated Output
                                    gr.Markdown("#### Generated Output")
                                    components["runs_output_video"] = gr.Video(
                                        label="Output Video",
                                        show_label=False,
                                        autoplay=True,
                                        loop=True,
                                        height=500,
                                    )

                                    # Input Videos with control weights
                                    gr.Markdown("#### Input Videos & Control Weights")

                                    # Control weights in a single row
                                    with gr.Row(equal_height=True):
                                        with gr.Column(scale=1, min_width=120):
                                            gr.Markdown(
                                                "**Color/Visual**",
                                                elem_classes=["compact-label"],
                                            )
                                            components["runs_visual_weight"] = gr.Slider(
                                                minimum=0,
                                                maximum=1,
                                                step=0.1,
                                                value=0,
                                                interactive=False,
                                                show_label=False,
                                                elem_classes=["compact-slider"],
                                            )
                                        with gr.Column(scale=1, min_width=120):
                                            gr.Markdown("**Edge**", elem_classes=["compact-label"])
                                            components["runs_edge_weight"] = gr.Slider(
                                                minimum=0,
                                                maximum=1,
                                                step=0.1,
                                                value=0,
                                                interactive=False,
                                                show_label=False,
                                                elem_classes=["compact-slider"],
                                            )
                                        with gr.Column(scale=1, min_width=120):
                                            gr.Markdown("**Depth**", elem_classes=["compact-label"])
                                            components["runs_depth_weight"] = gr.Slider(
                                                minimum=0,
                                                maximum=1,
                                                step=0.1,
                                                value=0,
                                                interactive=False,
                                                show_label=False,
                                                elem_classes=["compact-slider"],
                                            )
                                        with gr.Column(scale=1, min_width=120):
                                            gr.Markdown(
                                                "**Segmentation**",
                                                elem_classes=["compact-label"],
                                            )
                                            components["runs_segmentation_weight"] = gr.Slider(
                                                minimum=0,
                                                maximum=1,
                                                step=0.1,
                                                value=0,
                                                interactive=False,
                                                show_label=False,
                                                elem_classes=["compact-slider"],
                                            )

                                    # Input video gallery
                                    components["runs_input_videos"] = gr.Gallery(
                                        label="Input Frames",
                                        show_label=False,
                                        columns=4,
                                        rows=1,
                                        height=200,
                                        object_fit="contain",
                                        allow_preview=True,
                                        container=True,
                                        elem_classes=["input-videos-gallery"],
                                    )

                                    # Full Prompt
                                    gr.Markdown("#### Full Prompt")
                                    components["runs_prompt_text"] = gr.Textbox(
                                        label="Prompt Text",
                                        show_label=False,
                                        lines=4,
                                        max_lines=10,
                                        interactive=False,
                                    )

                                    # Hidden components for compatibility
                                    components["runs_detail_id"] = gr.Textbox(visible=False)
                                    components["runs_detail_status"] = gr.Textbox(visible=False)

                                # Info Tab
                                with gr.Tab("Info"):
                                    with gr.Row():
                                        components["runs_info_id"] = gr.Textbox(
                                            label="Run ID",
                                            interactive=False,
                                        )
                                        components["runs_info_prompt_id"] = gr.Textbox(
                                            label="Prompt ID",
                                            interactive=False,
                                        )

                                    with gr.Row():
                                        components["runs_info_status"] = gr.Textbox(
                                            label="Status",
                                            interactive=False,
                                        )
                                        components["runs_info_duration"] = gr.Textbox(
                                            label="Duration",
                                            interactive=False,
                                        )
                                        components["runs_info_type"] = gr.Textbox(
                                            label="Run Type",
                                            interactive=False,
                                        )

                                    components["runs_info_prompt_name"] = gr.Textbox(
                                        label="Prompt Name",
                                        interactive=False,
                                    )

                                    with gr.Row():
                                        components["runs_info_created"] = gr.Textbox(
                                            label="Created",
                                            interactive=False,
                                        )
                                        components["runs_info_completed"] = gr.Textbox(
                                            label="Completed",
                                            interactive=False,
                                        )

                                # Parameters Tab
                                with gr.Tab("Parameters"):
                                    gr.Markdown("#### Execution Configuration")
                                    components["runs_params_json"] = gr.JSON(
                                        label="Inference Parameters",
                                        show_label=False,
                                    )

                                # Logs Tab
                                with gr.Tab("Logs"):
                                    components["runs_log_path"] = gr.Textbox(
                                        label="Log File Path",
                                        interactive=False,
                                    )
                                    components["runs_log_output"] = gr.Code(
                                        label="Log Output (Last 15 Lines)",
                                        language="shell",
                                        lines=15,
                                        interactive=False,
                                    )
                                    with gr.Row():
                                        components["runs_load_logs_btn"] = gr.Button(
                                            "📄 Load Full Logs"
                                        )
                                        gr.Button("📋 Copy Logs")

    return components
