#!/usr/bin/env python3
"""Inputs Tab UI for Cosmos Workflow Manager.

This module contains only the UI creation code for the Inputs tab.
Business logic remains in the main app.py file.
"""

import gradio as gr


def create_inputs_tab_ui(config):
    """Create the Inputs tab UI components.

    Args:
        config: ConfigManager instance for configuration

    Returns:
        dict: Dictionary of all UI components for event binding
    """
    components = {}

    with gr.Tab("📁 Inputs", id=1) as components["inputs_tab"]:
        gr.Markdown("### Input Video Browser")
        gr.Markdown("Browse input videos and create prompts directly")

        # Filter Section
        with gr.Group(elem_classes=["filter-section"]):
            with gr.Row():
                # Left side: Search and filters
                with gr.Column(scale=3):
                    with gr.Row():
                        components["inputs_search"] = gr.Textbox(
                            label="Search",
                            placeholder="Search directory names...",
                            scale=2,
                            container=True,
                        )

                        components["inputs_has_filter"] = gr.Dropdown(
                            label="Has Videos",
                            choices=[
                                ("All", "all"),
                                ("Has Color", "has_color"),
                                ("Has Depth", "has_depth"),
                                ("Has Segmentation", "has_segmentation"),
                                ("Complete Set", "complete_set"),
                                ("Incomplete Set", "incomplete_set"),
                            ],
                            value="all",
                            allow_custom_value=False,
                            scale=1,
                        )

                        components["inputs_date_filter"] = gr.Dropdown(
                            label="Date Range",
                            choices=[
                                ("All", "all"),
                                ("Today", "today"),
                                ("Last 7 Days", "last_7_days"),
                                ("Last 30 Days", "last_30_days"),
                                ("Older than 30 Days", "older_than_30_days"),
                            ],
                            value="all",
                            allow_custom_value=False,
                            scale=1,
                        )

                    # Second row with advanced filters
                    with gr.Row():
                        components["inputs_sort"] = gr.Dropdown(
                            label="Sort By",
                            choices=[
                                ("Name (A-Z)", "name_asc"),
                                ("Name (Z-A)", "name_desc"),
                                ("Date (Newest)", "date_newest"),
                                ("Date (Oldest)", "date_oldest"),
                            ],
                            value="name_asc",
                            allow_custom_value=False,
                            scale=1,
                        )

                        components["inputs_unused_only"] = gr.Checkbox(
                            label="Show only unused",
                            value=False,
                            scale=1,
                        )

                # Right side: Results counter and refresh
                with gr.Column(scale=1):
                    with gr.Row():
                        components["inputs_results_count"] = gr.Markdown(
                            "**0** directories found",
                            elem_classes=["results-counter"],
                        )
                        components["inputs_refresh_btn"] = gr.Button(
                            "🔄 Refresh",
                            size="sm",
                            variant="secondary",
                        )

        with gr.Row():
            # Left: Gallery of inputs - MUCH LARGER (2x the right panel)
            with gr.Column(scale=2):
                components["input_gallery"] = gr.Gallery(
                    label="Input Directories",
                    show_label=True,
                    elem_id="input_gallery",
                    columns=4,  # 4 columns for larger thumbnails
                    rows=3,  # Allow 3 rows
                    object_fit="contain",  # Try contain for better aspect ratio
                    height=900,  # Much larger height for bigger thumbnails
                    preview=False,  # Disable preview for cleaner look
                    allow_preview=False,
                    interactive=False,  # Prevent uploads
                )

            # Right: Input Details with tabs
            with gr.Column(scale=1):
                # Hidden field to store selected directory path
                components["selected_dir_path"] = gr.Textbox(visible=False)

                # Keep preview_group for compatibility but hidden
                with gr.Group(visible=False) as components["preview_group"]:
                    pass

                # Tabs for Input Details and Create Prompt
                with gr.Tabs(visible=False) as components["input_tabs_group"]:
                    # Input Details Tab
                    with gr.Tab("📁 Input Details"):
                        with gr.Group(elem_classes=["detail-card"]):
                            # File information section
                            gr.Markdown("#### 📂 File Information")

                            components["input_name"] = gr.Textbox(
                                label="Name",
                                interactive=False,
                            )

                            components["input_path"] = gr.Textbox(
                                label="Path",
                                interactive=False,
                            )

                            components["input_created"] = gr.Textbox(
                                label="Created",
                                interactive=False,
                            )

                            # Video metadata as regular textboxes
                            components["input_resolution"] = gr.Textbox(
                                label="Resolution",
                                interactive=False,
                            )

                            components["input_duration"] = gr.Textbox(
                                label="Duration",
                                interactive=False,
                            )

                            with gr.Row():
                                components["input_fps"] = gr.Textbox(
                                    label="FPS",
                                    interactive=False,
                                    scale=1,
                                )

                                components["input_codec"] = gr.Textbox(
                                    label="Codec",
                                    interactive=False,
                                    scale=1,
                                )

                            components["input_files"] = gr.Textbox(
                                label="Available Control Inputs",
                                lines=3,
                                interactive=False,
                            )

                            # Video previews at the bottom
                            gr.Markdown("#### 🎬 Video Previews")
                            components["video_preview_gallery"] = gr.Gallery(
                                label="Available Videos",
                                columns=3,
                                height=200,  # Fixed height to prevent excess space
                                object_fit="contain",  # Changed to contain to fit videos properly
                                elem_id="video_preview_gallery",
                                show_label=False,
                                allow_preview=True,  # Allow clicking to preview
                                container=False,  # Remove extra container padding
                            )

                    # Create Prompt Tab
                    with gr.Tab("✨ Create Prompt"):
                        with gr.Group(elem_classes=["detail-card"]):
                            # Video Directory at the top for easy access
                            components["create_video_dir"] = gr.Textbox(
                                label="Video Directory",
                                placeholder="Auto-filled when selecting an input",
                                info="Must contain color.mp4",
                            )

                            components["create_prompt_text"] = gr.Textbox(
                                label="Prompt Text",
                                placeholder="Enter your prompt description here...",
                                lines=3,
                                max_lines=10,
                            )

                            components["create_name"] = gr.Textbox(
                                label="Name (Optional)",
                                placeholder="Leave empty for auto-generated name",
                                info="A descriptive name for this prompt",
                            )

                            # Get default negative prompt from config
                            default_negative = (
                                config._config_data.get("generation", {})
                                .get(
                                    "negative_prompt",
                                    "The video captures a game playing, with bad crappy graphics...",
                                )
                                .strip()
                            )

                            components["create_negative"] = gr.Textbox(
                                label="Negative Prompt",
                                value=default_negative,  # Pre-fill with default
                                lines=3,
                                info="Edit to customize or leave as default",
                            )

                            components["create_prompt_btn"] = gr.Button(
                                "✨ Create Prompt", variant="primary", size="lg"
                            )

                            components["create_status"] = gr.Markdown("")

    return components
