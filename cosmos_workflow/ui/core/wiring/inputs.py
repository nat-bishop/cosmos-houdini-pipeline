"""Event wiring for Inputs tab components."""

import functools
from pathlib import Path

import gradio as gr

from cosmos_workflow.ui.core.safe_wiring import safe_wire
from cosmos_workflow.ui.tabs.inputs_handlers import (
    create_prompt,
    filter_input_directories,
    get_input_directories,
    load_input_gallery,
    on_input_select,
)


def wire_inputs_events(components, config, api):
    """Wire events for the Inputs tab.

    Args:
        components: Dictionary of UI components
        config: Application configuration
        api: CosmosAPI instance
    """
    # Get the correct videos directory from config
    local_config = config.get_local_config()
    inputs_dir = Path(local_config.videos_dir)  # This is "inputs/videos" from config
    get_dirs_bound = functools.partial(get_input_directories, inputs_dir)
    filter_dirs_bound = functools.partial(filter_input_directories, inputs_dir)

    # Directory refresh
    if "refresh_dirs_btn" in components:
        components["refresh_dirs_btn"].click(
            fn=get_dirs_bound,
            outputs=[components["input_dirs_display"]],
            show_progress=False,
        )

    # Directory selection
    if "input_dirs_display" in components:
        components["input_dirs_display"].select(
            fn=on_input_select,
            inputs=[components["input_dirs_display"]],
            outputs=[
                components["input_gallery"],
                components["input_details"],
                components["create_prompt_btn"],
                components["selected_dir_path"],
                components["multimodal_json"],
                components["prompt_text"],
                components["run_cosmos_ops"],
                components["source_model"],
                components["num_frames"],
                components["input_metadata"],
                components["prompt_creation_result"],
                components["status_display"],
            ],
        )

    # Filtering events
    if "dir_search" in components:
        components["dir_search"].change(
            fn=filter_dirs_bound,
            inputs=[components["dir_search"]],
            outputs=[components["input_dirs_display"]],
            show_progress=False,
        )

    # Create prompt button
    if "create_prompt_btn" in components:
        components["create_prompt_btn"].click(
            fn=create_prompt,
            inputs=[
                components["create_prompt_text"],
                components["create_video_dir"],
                components["create_name"],
                components["create_negative"],
            ],
            outputs=[components.get("create_progress_area")],
            show_progress="full",
            queue=True,
        )

    # Input gallery selection
    if "input_gallery" in components:
        # Create a wrapper that adds inputs_dir
        def handle_input_select(evt: gr.SelectData, gallery_data):
            return on_input_select(evt, gallery_data, inputs_dir)

        safe_wire(
            components["input_gallery"],
            "select",
            handle_input_select,
            inputs=[components["input_gallery"]],
            outputs=[
                components.get("selected_dir_path"),
                components.get("preview_group"),
                components.get("input_tabs_group"),
                components.get("input_name"),
                components.get("input_path"),
                components.get("input_created"),
                components.get("input_resolution"),
                components.get("input_duration"),
                components.get("input_fps"),
                components.get("input_codec"),
                components.get("input_files"),
                components.get("video_preview_gallery"),
                components.get("create_video_dir"),
            ],
        )

    # Input filtering events
    if "inputs_search" in components:
        components["inputs_search"].change(
            fn=filter_dirs_bound,
            inputs=[components["inputs_search"]],
            outputs=[components.get("input_gallery")],
            show_progress=False,
        )

    if "inputs_date_filter" in components:
        components["inputs_date_filter"].change(
            fn=filter_dirs_bound,
            inputs=[components["inputs_search"], components["inputs_date_filter"]],
            outputs=[components.get("input_gallery")],
            show_progress=False,
        )

    if "inputs_sort" in components:
        safe_wire(
            components["inputs_sort"],
            "change",
            lambda search, date_f, sort: load_input_gallery(inputs_dir, search, date_f, sort),
            inputs=[
                components.get("inputs_search"),
                components.get("inputs_date_filter"),
                components.get("inputs_sort"),
            ],
            outputs=[
                components.get("input_gallery"),
                components.get("inputs_results_count"),
            ],
        )
