#!/usr/bin/env python3
"""Prompts Tab UI for Cosmos Workflow Manager.

This module contains only the UI creation code for the Prompts tab.
Business logic remains in the main app.py file.
"""

import gradio as gr


def create_prompts_tab_ui():
    """Create the Prompts tab UI components.

    Returns:
        dict: Dictionary of all UI components for event binding
    """
    components = {}

    with gr.Tab("🚀 Prompts", id=2, elem_classes=["prompts-tab"]) as components["prompts_tab"]:
        gr.Markdown("### Prompt Management & Operations")
        gr.Markdown("View, select, and execute operations on your prompts")

        with gr.Row(elem_classes=["split-view"]):
            # Left: Prompt selection table with enhanced interactivity
            with gr.Column(scale=3, elem_classes=["split-left"]):
                with gr.Group(elem_classes=["detail-card"]):
                    gr.Markdown("#### 📋 Prompts Library")

                    # Filter row with animations
                    with gr.Row(elem_classes=["batch-operation"]):
                        components["prompts_search"] = gr.Textbox(
                            label="Search",
                            placeholder="Search by ID (ps_xxx), name, or prompt text...",
                            scale=2,
                        )

                        components["prompts_enhanced_filter"] = gr.Dropdown(
                            label="Enhanced Status",
                            choices=[
                                ("All", "all"),
                                ("Enhanced", "enhanced"),
                                ("Not Enhanced", "not_enhanced"),
                            ],
                            value="all",
                            interactive=True,
                            filterable=False,
                            scale=1,
                        )

                        components["prompts_runs_filter"] = gr.Dropdown(
                            label="Run Status",
                            choices=[
                                ("All", "all"),
                                ("No Runs", "no_runs"),
                                ("Has Runs", "has_runs"),
                            ],
                            value="all",
                            interactive=True,
                            filterable=False,
                            scale=1,
                        )

                        components["prompts_date_filter"] = gr.Dropdown(
                            label="Date Range",
                            choices=[
                                ("All", "all"),
                                ("Today", "today"),
                                ("Last 7 Days", "last_7_days"),
                                ("Last 30 Days", "last_30_days"),
                                ("Older than 30 Days", "older_than_30_days"),
                            ],
                            value="all",
                            interactive=True,
                            filterable=False,
                            scale=1,
                        )

                        components["ops_limit"] = gr.Number(
                            value=50,
                            label="Limit",
                            minimum=1,
                            maximum=500,
                            scale=1,
                        )

                    # Enhanced prompts table with selection
                    with gr.Column(
                        elem_id="prompts-table-wrapper", elem_classes=["prompts-table-container"]
                    ):
                        components["ops_prompts_table"] = gr.Dataframe(
                            headers=["☑", "ID", "Name", "Prompt Text", "Created"],
                            datatype=["bool", "str", "str", "str", "str"],
                            interactive=True,  # Must be True for select event to work
                            col_count=(5, "fixed"),
                            wrap=True,
                            elem_id="prompts-dataframe",
                            elem_classes=["prompts-table"],
                        )

                    # Selection controls with visual feedback
                    with gr.Row(elem_classes=["batch-operation"]):
                        components["select_all_btn"] = gr.Button(
                            "☑ Select All", size="sm", variant="secondary"
                        )
                        components["clear_selection_btn"] = gr.Button(
                            "☐ Clear Selection", size="sm", variant="secondary"
                        )
                        components["delete_selected_btn"] = gr.Button(
                            "🗑️ Delete Selected", size="sm", variant="stop"
                        )
                        components["view_runs_btn"] = gr.Button(
                            "→ View Runs", size="sm", variant="primary", visible=True
                        )
                        components["selection_count"] = gr.Markdown(
                            "**0** prompts selected", elem_classes=["selection-counter"]
                        )

            # Right: Split view for details and operations
            with gr.Column(scale=2, elem_classes=["split-right"]):
                # Unified tabs for Prompt Details, Inference, and Prompt Enhance
                with gr.Tabs():
                    # Prompt Details tab
                    with gr.Tab("📝 Prompt Details"):
                        gr.Markdown("##### Prompt Information")

                        components["selected_prompt_id"] = gr.Textbox(
                            label="Prompt ID",
                            interactive=False,
                            elem_classes=["loading-skeleton"],
                        )

                        with gr.Row():
                            components["selected_prompt_name"] = gr.Textbox(
                                label="Name",
                                interactive=False,
                                scale=3,
                            )
                            components["selected_prompt_enhanced"] = gr.Checkbox(
                                label="✨ Enhanced",
                                interactive=False,
                                scale=1,
                            )

                        components["selected_prompt_text"] = gr.Textbox(
                            label="Prompt Text",
                            lines=3,
                            interactive=False,
                        )

                        components["selected_prompt_negative"] = gr.Textbox(
                            label="Negative Prompt",
                            lines=2,
                            interactive=False,
                        )

                        with gr.Row():
                            components["selected_prompt_created"] = gr.Textbox(
                                label="Created",
                                interactive=False,
                                scale=1,
                            )
                            components["selected_prompt_video_dir"] = gr.Textbox(
                                label="Video Directory",
                                interactive=False,
                                scale=2,
                            )

                    # Inference tab
                    with gr.Tab("🚀 Inference"):
                        gr.Markdown("##### Inference Parameters")

                        with gr.Group():
                            # Weights control
                            gr.Markdown("**Control Weights**")
                            with gr.Row():
                                components["weight_vis"] = gr.Slider(
                                    label="Visual",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.25,
                                    step=0.05,
                                )
                                components["weight_edge"] = gr.Slider(
                                    label="Edge",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.25,
                                    step=0.05,
                                )
                            with gr.Row():
                                components["weight_depth"] = gr.Slider(
                                    label="Depth",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.25,
                                    step=0.05,
                                )
                                components["weight_seg"] = gr.Slider(
                                    label="Segmentation",
                                    minimum=0.0,
                                    maximum=1.0,
                                    value=0.25,
                                    step=0.05,
                                )

                            # Advanced parameters
                            with gr.Accordion("Advanced", open=False):
                                with gr.Row():
                                    components["inf_steps"] = gr.Number(
                                        label="Steps",
                                        value=35,
                                        minimum=1,
                                        maximum=100,
                                    )
                                    components["inf_guidance"] = gr.Number(
                                        label="Guidance (CFG)",
                                        value=7.0,
                                        minimum=1.0,
                                        maximum=20.0,
                                    )
                                    components["inf_seed"] = gr.Number(
                                        label="Seed",
                                        value=1,
                                        minimum=0,
                                    )

                                with gr.Row():
                                    components["inf_fps"] = gr.Number(
                                        label="FPS",
                                        value=24,
                                        minimum=1,
                                        maximum=60,
                                    )
                                    components["inf_sigma_max"] = gr.Number(
                                        label="Sigma Max",
                                        value=70.0,
                                    )

                                components["inf_blur_strength"] = gr.Dropdown(
                                    label="Blur Strength",
                                    choices=[
                                        "very_low",
                                        "low",
                                        "medium",
                                        "high",
                                        "very_high",
                                    ],
                                    value="medium",
                                    interactive=True,
                                )
                                components["inf_canny_threshold"] = gr.Dropdown(
                                    label="Canny Threshold",
                                    choices=[
                                        "very_low",
                                        "low",
                                        "medium",
                                        "high",
                                        "very_high",
                                    ],
                                    value="medium",
                                    interactive=True,
                                )

                        # Run button
                        components["run_inference_btn"] = gr.Button(
                            "🚀 Run Inference",
                            variant="primary",
                            size="lg",
                        )

                        components["inference_status"] = gr.Markdown("")

                    # Prompt Enhance tab
                    with gr.Tab("✨ Prompt Enhance"):
                        gr.Markdown("##### Enhancement Settings")

                        with gr.Group():
                            gr.Markdown("**AI Model:** pixtral")

                            components["enhance_create_new"] = gr.Radio(
                                label="Action",
                                choices=[
                                    ("Create new enhanced prompt", True),
                                    ("Overwrite existing prompt", False),
                                ],
                                value=True,
                            )

                            components["enhance_force"] = gr.Checkbox(
                                label="Force overwrite (delete existing runs if needed)",
                                value=False,
                                visible=False,  # Show only when overwrite is selected
                            )

                        # Run button
                        components["run_enhance_btn"] = gr.Button(
                            "✨ Enhance Prompts",
                            variant="primary",
                            size="lg",
                        )

                        components["enhance_status"] = gr.Markdown("")

        # Delete confirmation dialog - placed outside split view for better layout
        with gr.Group(
            visible=False, elem_classes=["delete-confirmation-container", "detail-card"]
        ) as components["prompts_delete_dialog"]:
            gr.Markdown("### ⚠️ Confirm Deletion")
            components["prompts_delete_preview"] = gr.Textbox(
                label="Prompts to Delete", interactive=False, lines=5, max_lines=20, show_label=True
            )
            components["prompts_delete_outputs_checkbox"] = gr.Checkbox(
                label="Delete output files",
                value=False,
                info="Check to permanently delete all output files. Leave unchecked to preserve files.",
            )
            components["prompts_delete_ids_hidden"] = gr.Textbox(visible=False)
            with gr.Row():
                components["prompts_confirm_delete_btn"] = gr.Button(
                    "⚠️ Confirm Delete",
                    variant="stop",
                    size="sm",
                )
                components["prompts_cancel_delete_btn"] = gr.Button(
                    "Cancel",
                    variant="secondary",
                    size="sm",
                )

    return components
