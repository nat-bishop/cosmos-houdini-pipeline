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

                # Navigation filter indicator - shows when filtering by prompts
                components["runs_nav_filter_row"] = gr.Row(visible=False)
                with components["runs_nav_filter_row"]:
                    with gr.Column(scale=3):
                        # Use Markdown to display filter info more clearly
                        components["runs_prompt_filter"] = gr.Markdown(
                            value="",  # Will be populated dynamically
                            elem_classes=["filter-info-box"],
                        )
                    with gr.Column(scale=1):
                        components["clear_nav_filter_btn"] = gr.Button(
                            "Clear Filter", size="sm", variant="secondary"
                        )

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
                        interactive=True,
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
                        interactive=True,
                    )

                    components["runs_type_filter"] = gr.Dropdown(
                        choices=[
                            "all",
                            "transfer",  # inference runs
                            "enhance",
                            "upscale",
                        ],
                        value="all",
                        label="Run Type",
                        info="Filter by run type",
                        interactive=True,
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
                            columns=5,  # Changed to 5 columns
                            rows=3,  # Increased rows for better display
                            height="auto",  # Auto height to enable scrolling
                            object_fit="cover",  # Changed to cover to fill the space properly
                            preview=False,  # Disable preview to avoid duplication
                            allow_preview=False,  # Disable click to expand
                            show_download_button=True,
                            interactive=False,  # Read-only gallery
                        )

                    # Run Records tab
                    with gr.Tab("Run Records"):
                        # Single row operations
                        with gr.Row():
                            components["runs_delete_selected_btn"] = gr.Button(
                                "🗑️ Delete Selected Run",
                                size="sm",
                                variant="stop",
                            )
                            components["runs_selected_info"] = gr.Markdown("No run selected")

                        # Hidden component to store selected run ID
                        components["runs_selected_id"] = gr.Textbox(visible=False)

                        with gr.Column(
                            elem_id="runs-table-wrapper", elem_classes=["runs-table-container"]
                        ):
                            components["runs_table"] = gr.Dataframe(
                                headers=[
                                    "Run ID",
                                    "Status",
                                    "Prompt ID",
                                    "Run Type",
                                    "Duration",
                                    "Created",
                                ],
                                datatype=["str", "str", "str", "str", "str", "str"],
                                interactive=False,  # Make non-interactive to prevent editing
                                elem_id="runs-dataframe",
                                elem_classes=["run-history-table"],
                            )

                        # Delete confirmation dialog
                        with gr.Group(visible=False, elem_classes=["detail-card"]) as components[
                            "runs_delete_dialog"
                        ]:
                            components["runs_delete_preview"] = gr.Markdown()
                            components["runs_delete_outputs_checkbox"] = gr.Checkbox(
                                label="Delete output files",
                                value=False,
                                info="Check to permanently delete all output files. Leave unchecked to preserve files.",
                            )
                            components["runs_delete_id_hidden"] = gr.Textbox(visible=False)
                            with gr.Row():
                                components["runs_confirm_delete_btn"] = gr.Button(
                                    "⚠️ Confirm Delete",
                                    variant="stop",
                                    size="sm",
                                )
                                components["runs_cancel_delete_btn"] = gr.Button(
                                    "Cancel",
                                    variant="secondary",
                                    size="sm",
                                )

                # Run Details below both tabs
                with gr.Group(visible=False, elem_classes=["detail-card"]) as components[
                    "runs_details_group"
                ]:
                    # Header with navigation buttons
                    with gr.Row():
                        with gr.Column(scale=4):
                            gr.Markdown("### 📋 Run Details")
                        with gr.Column(scale=1):
                            with gr.Row():
                                components["runs_prev_btn"] = gr.Button(
                                    "◀ Previous", size="sm", variant="secondary"
                                )
                                components["runs_next_btn"] = gr.Button(
                                    "Next ▶", size="sm", variant="secondary"
                                )

                    # State to track current gallery selection index
                    components["runs_selected_index"] = gr.State(0)

                    with gr.Tabs():
                        # Main Tab - Dynamic content based on model type
                        with gr.Tab("Main"):
                            # Transfer/Default content (visible by default)
                            with gr.Column(visible=True) as components[
                                "runs_main_content_transfer"
                            ]:
                                # Generated Output
                                gr.Markdown("#### Generated Output")
                                components["runs_output_video"] = gr.Video(
                                    label="Output Video",
                                    show_label=False,
                                    autoplay=True,
                                    loop=True,
                                    height=500,
                                )

                                # Input Videos
                                gr.Markdown("#### Input Videos")

                                # Create individual video components for better control
                                with gr.Row(equal_height=True):
                                    # Create 4 video slots (max possible: color, edge, depth, seg)
                                    with gr.Column(scale=1, min_width=200):
                                        components["runs_input_video_1"] = gr.Video(
                                            label="Video 1",
                                            visible=False,
                                            autoplay=False,
                                            loop=True,
                                            show_download_button=False,
                                            interactive=False,
                                            container=True,
                                        )
                                    with gr.Column(scale=1, min_width=200):
                                        components["runs_input_video_2"] = gr.Video(
                                            label="Video 2",
                                            visible=False,
                                            autoplay=False,
                                            loop=True,
                                            show_download_button=False,
                                            interactive=False,
                                            container=True,
                                        )
                                    with gr.Column(scale=1, min_width=200):
                                        components["runs_input_video_3"] = gr.Video(
                                            label="Video 3",
                                            visible=False,
                                            autoplay=False,
                                            loop=True,
                                            show_download_button=False,
                                            interactive=False,
                                            container=True,
                                        )
                                    with gr.Column(scale=1, min_width=200):
                                        components["runs_input_video_4"] = gr.Video(
                                            label="Video 4",
                                            visible=False,
                                            autoplay=False,
                                            loop=True,
                                            show_download_button=False,
                                            interactive=False,
                                            container=True,
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

                            # Enhancement content (hidden by default)
                            with gr.Column(visible=False) as components[
                                "runs_main_content_enhance"
                            ]:
                                gr.Markdown("#### Prompt Enhancement Results")

                                # Side-by-side prompts for comparison
                                with gr.Row():
                                    with gr.Column():
                                        gr.Markdown("**Original Prompt**")
                                        components["runs_original_prompt_enhance"] = gr.Textbox(
                                            label="Original",
                                            show_label=False,
                                            lines=8,
                                            max_lines=15,
                                            interactive=False,
                                        )
                                    with gr.Column():
                                        gr.Markdown("**Enhanced Prompt**")
                                        components["runs_enhanced_prompt_enhance"] = gr.Textbox(
                                            label="Enhanced",
                                            show_label=False,
                                            lines=8,
                                            max_lines=15,
                                            interactive=False,
                                        )

                                # Enhancement details
                                gr.Markdown("#### Enhancement Details")
                                components["runs_enhance_stats"] = gr.Markdown(
                                    "Loading enhancement details...",
                                    elem_classes=["detail-card"],
                                )

                            # Upscale content (hidden by default)
                            with gr.Column(visible=False) as components[
                                "runs_main_content_upscale"
                            ]:
                                # Upscaled Output
                                gr.Markdown("#### Upscaled Output")
                                components["runs_output_video_upscale"] = gr.Video(
                                    label="Upscaled Video",
                                    show_label=False,
                                    autoplay=True,
                                    loop=True,
                                    height=500,
                                )

                                # Original vs Upscaled comparison
                                with gr.Row():
                                    with gr.Column():
                                        gr.Markdown("**Original Video**")
                                        components["runs_original_video_upscale"] = gr.Video(
                                            label="Original",
                                            show_label=False,
                                            autoplay=False,
                                            loop=True,
                                            height=250,
                                        )
                                    with gr.Column():
                                        gr.Markdown("**Upscale Statistics**")
                                        components["runs_upscale_stats"] = gr.Markdown(
                                            "Loading upscale details...",
                                            elem_classes=["detail-card"],
                                        )

                                # Prompt used for upscaling (if any)
                                gr.Markdown("#### Upscaling Prompt")
                                components["runs_upscale_prompt"] = gr.Textbox(
                                    label="Prompt",
                                    show_label=False,
                                    lines=3,
                                    max_lines=6,
                                    interactive=False,
                                    placeholder="No prompt used for this upscale",
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

                            # Video Paths
                            gr.Markdown("#### Video Paths")
                            components["runs_info_output_path"] = gr.Textbox(
                                label="Output Video",
                                interactive=False,
                            )
                            components["runs_info_input_paths"] = gr.Textbox(
                                label="Input Videos",
                                lines=4,
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
                                components["runs_load_logs_btn"] = gr.Button("📄 Load Full Logs")
                                gr.Button("📋 Copy Logs")

    return components
