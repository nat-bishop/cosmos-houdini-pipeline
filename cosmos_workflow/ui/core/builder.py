"""UI builder and event wiring for the Gradio application.

This module contains functions to build the main UI and wire up all event
handlers in a modular way, breaking down the monolithic create_ui function.
"""

import functools

import gradio as gr

from cosmos_workflow.ui.core.state import create_ui_states
from cosmos_workflow.ui.core.utils import filter_none_components
from cosmos_workflow.ui.styles_simple import get_custom_css
from cosmos_workflow.ui.tabs.inputs_ui import create_inputs_tab_ui
from cosmos_workflow.ui.tabs.jobs_ui import create_jobs_tab_ui
from cosmos_workflow.ui.tabs.prompts_ui import create_prompts_tab_ui
from cosmos_workflow.ui.tabs.runs_ui import create_runs_tab_ui
from cosmos_workflow.utils.logging import logger


def build_ui_components(config):
    """Build all UI components and tabs.

    Args:
        config: Application configuration

    Returns:
        tuple: (app, components) - The Gradio app and component dict
    """
    components = {}

    custom_css = get_custom_css()

    with gr.Blocks(title="Cosmos Workflow Manager", css=custom_css) as app:
        # Header
        gr.Markdown("# 🌌 Cosmos Workflow Manager")

        with gr.Row():
            status_display = gr.Markdown("**Status:** Initializing...")
            manual_refresh = gr.Button("🔄 Refresh All Data", scale=0, size="sm")

        components["status_display"] = status_display
        components["manual_refresh"] = manual_refresh

        # Create tabs
        with gr.Tabs() as tabs:
            # Create each tab UI
            inputs_components = create_inputs_tab_ui(config)
            components.update(inputs_components)

            prompts_components = create_prompts_tab_ui()
            components.update(prompts_components)

            runs_components = create_runs_tab_ui()
            components.update(runs_components)

            jobs_components = create_jobs_tab_ui()
            components.update(jobs_components)

        components["tabs"] = tabs

        # Create UI states
        states = create_ui_states()
        components.update(states)

        # Track selected tab
        selected_tab = gr.Number(value=0, visible=False, precision=0)
        components["selected_tab"] = selected_tab

    return app, components


def wire_navigation_events(components):
    """Wire tab navigation events.

    Args:
        components: Dictionary of UI components
    """
    # Tab navigation handler - Tabs component cannot be used as input
    # Instead, we'll handle tab navigation through button clicks and other events


def wire_header_events(components, api, config):
    """Wire header and manual refresh events.

    Args:
        components: Dictionary of UI components
        api: CosmosAPI instance
        config: Configuration instance
    """
    from cosmos_workflow.ui.tabs.prompts_handlers import load_ops_prompts

    # Manual refresh button
    def refresh_all_data():
        """Refresh data in all tabs."""
        try:
            # Refresh prompts using load_ops_prompts which returns the right format
            prompts_data = load_ops_prompts(
                limit=50,
                search_text="",
                enhanced_filter="all",
                runs_filter="all",
                date_filter="all",
            )

            # For runs, return empty/minimal data to avoid hanging on thumbnail generation
            # The runs tab will load its own data when accessed
            gallery = []
            table = []
            stats = "Runs data will refresh when you visit the Runs tab"

            return (
                "**Status:** ✅ All data refreshed",
                prompts_data,
                gallery,
                table,
                stats,
            )
        except Exception as e:
            logger.error("Error refreshing data: {}", e)
            return (
                f"**Status:** ❌ Error: {e!s}",
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
            )

    if "manual_refresh" in components:
        outputs = [
            components.get("status_display"),
            components.get("ops_prompts_table"),  # Fixed: was "prompts_table"
            components.get("runs_gallery"),
            components.get("runs_table"),
            components.get("runs_stats"),
        ]
        # Filter out None values
        outputs = [o for o in outputs if o is not None]

        if outputs:
            components["manual_refresh"].click(
                fn=refresh_all_data,
                inputs=[],
                outputs=outputs,
                show_progress=True,
            )


def wire_inputs_events(components, config, api):
    """Wire events for the Inputs tab.

    Args:
        components: Dictionary of UI components
        config: Application configuration
        api: CosmosAPI instance
    """
    import functools

    # Bind with inputs_dir parameter
    from pathlib import Path

    from cosmos_workflow.ui.tabs.inputs_handlers import (
        create_prompt,
        filter_input_directories,
        get_input_directories,
        load_input_gallery,
        on_input_select,
    )

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
        import gradio as gr

        from cosmos_workflow.ui.tabs.inputs_handlers import on_input_select

        # Create a wrapper that adds inputs_dir
        def handle_input_select(evt: gr.SelectData, gallery_data):
            return on_input_select(evt, gallery_data, inputs_dir)

        components["input_gallery"].select(
            fn=handle_input_select,
            inputs=[components["input_gallery"]],
            outputs=filter_none_components(
                [
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
                ]
            ),
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
        components["inputs_sort"].change(
            fn=lambda search, date_f, sort: load_input_gallery(inputs_dir, search, date_f, sort),
            inputs=filter_none_components(
                [
                    components.get("inputs_search"),
                    components.get("inputs_date_filter"),
                    components.get("inputs_sort"),
                ]
            ),
            outputs=filter_none_components(
                [
                    components.get("input_gallery"),
                    components.get("inputs_results_count"),
                ]
            ),
        )


def wire_prompts_events(components, api, simple_queue_service):
    """Wire events for the Prompts tab.

    Args:
        components: Dictionary of UI components
        api: CosmosAPI instance
        simple_queue_service: SimplifiedQueueService instance
    """
    from cosmos_workflow.ui.tabs.prompts_handlers import (
        cancel_delete_prompts,
        clear_selection,
        confirm_delete_prompts,
        filter_prompts,
        list_prompts,
        on_prompt_row_select,
        preview_delete_prompts,
        run_enhance_on_selected,
        run_inference_on_selected,
        select_all_prompts,
    )

    # Bind services to handlers
    run_inference_bound = functools.partial(
        run_inference_on_selected,
        api=api,
        simple_queue_service=simple_queue_service,
    )
    run_enhance_bound = functools.partial(
        run_enhance_on_selected,
        api=api,
        simple_queue_service=simple_queue_service,
    )

    # Refresh button
    if "refresh_prompts_btn" in components:
        components["refresh_prompts_btn"].click(
            fn=list_prompts,
            outputs=filter_none_components([components.get("prompts_table")]),
            show_progress=False,
        )

    # Filtering events
    if "prompt_search" in components:
        components["prompt_search"].change(
            fn=filter_prompts,
            inputs=filter_none_components(
                [
                    components.get("prompt_search"),
                    components.get("prompt_status_filter"),
                    components.get("prompts_table"),
                ]
            ),
            outputs=filter_none_components([components.get("prompts_table")]),
            show_progress=False,
        )

    if "prompt_status_filter" in components:
        components["prompt_status_filter"].change(
            fn=filter_prompts,
            inputs=filter_none_components(
                [
                    components.get("prompt_search"),
                    components.get("prompt_status_filter"),
                    components.get("prompts_table"),
                ]
            ),
            outputs=filter_none_components([components.get("prompts_table")]),
            show_progress=False,
        )

    # Table selection
    if "prompts_table" in components:
        components["prompts_table"].select(
            fn=on_prompt_row_select,
            inputs=[components["prompts_table"]],
            outputs=filter_none_components(
                [
                    components.get("selected_prompt_id"),
                    components.get("prompt_details"),
                    components.get("prompt_video_gallery"),
                    components.get("run_inference_btn"),
                    components.get("run_enhance_btn"),
                    components.get("prompt_run_stats"),
                    components.get("runs_for_prompt"),
                    components.get("view_runs_for_prompt_btn"),
                    components.get("prompt_action_result"),
                    components.get("status_display"),
                ]
            ),
            show_progress=True,
        )

    # Inference and enhance buttons
    if "run_inference_btn" in components and "prompts_table" in components:
        components["run_inference_btn"].click(
            fn=run_inference_bound,
            inputs=[components["prompts_table"]],
            outputs=[
                components["queue_table"],
                components["prompt_action_result"],
                components["status_display"],
            ],
            show_progress=True,
        )

    if "run_enhance_btn" in components and "prompts_table" in components:
        components["run_enhance_btn"].click(
            fn=run_enhance_bound,
            inputs=[components["prompts_table"]],
            outputs=filter_none_components(
                [
                    components.get("queue_table"),
                    components.get("prompt_action_result"),
                    components.get("status_display"),
                ]
            ),
            show_progress=True,
        )

    # Selection controls
    if "select_all_btn" in components and "ops_prompts_table" in components:
        components["select_all_btn"].click(
            fn=select_all_prompts,
            inputs=[components["ops_prompts_table"]],
            outputs=filter_none_components(
                [
                    components.get("ops_prompts_table"),
                    components.get("selection_count"),
                ]
            ),
        )

    if "clear_selection_btn" in components and "ops_prompts_table" in components:
        components["clear_selection_btn"].click(
            fn=clear_selection,
            inputs=[components["ops_prompts_table"]],
            outputs=filter_none_components(
                [
                    components.get("ops_prompts_table"),
                    components.get("selection_count"),
                ]
            ),
        )

    # Delete operations
    if "delete_selected_btn" in components and "ops_prompts_table" in components:
        components["delete_selected_btn"].click(
            fn=preview_delete_prompts,
            inputs=[components["ops_prompts_table"]],
            outputs=filter_none_components(
                [
                    components.get("delete_dialog"),
                    components.get("delete_preview"),
                    components.get("delete_selected_ids"),
                ]
            ),
        )

    if "prompts_confirm_delete_btn" in components and "delete_selected_ids" in components:
        components["prompts_confirm_delete_btn"].click(
            fn=confirm_delete_prompts,
            inputs=[components["delete_selected_ids"]],
            outputs=filter_none_components(
                [
                    components.get("ops_prompts_table"),
                    components.get("prompts_table"),
                    components.get("delete_dialog"),
                    components.get("selection_count"),
                ]
            ),
        )

    if "prompts_cancel_delete_btn" in components:
        components["prompts_cancel_delete_btn"].click(
            fn=cancel_delete_prompts,
            outputs=filter_none_components([components.get("delete_dialog")]),
        )

    # Ops prompts table selection
    if "ops_prompts_table" in components:
        outputs = filter_none_components(
            [
                components.get("selected_prompt_id"),
                components.get("prompt_details"),
                components.get("prompt_video_gallery"),
                components.get("run_inference_btn"),
                components.get("run_enhance_btn"),
                components.get("prompt_run_stats"),
                components.get("runs_for_prompt"),
                components.get("view_runs_for_prompt_btn"),
                components.get("prompt_action_result"),
                components.get("status_display"),
            ]
        )
        if outputs:
            components["ops_prompts_table"].select(
                fn=on_prompt_row_select,
                inputs=[components["ops_prompts_table"]],
                outputs=outputs,
            )


def wire_runs_events(components, api):
    """Wire events for the Runs tab.

    This handles all runs-related events including filtering, selection,
    navigation, ratings, and actions.

    Args:
        components: Dictionary of UI components
        api: CosmosAPI instance
    """
    wire_runs_filtering_events(components)
    wire_runs_selection_events(components)
    wire_runs_navigation_events(components)
    wire_runs_action_events(components, api)
    wire_runs_rating_events(components, api)


def wire_runs_filtering_events(components):
    """Wire runs filtering events."""
    from cosmos_workflow.ui.tabs.runs import load_runs_with_filters

    # Check if all filter components exist
    filter_keys = [
        "runs_status_filter",
        "runs_date_filter",
        "runs_type_filter",
        "runs_search",
        "runs_limit",
        "runs_rating_filter",
        "runs_version_filter",
    ]

    if all(k in components for k in filter_keys):
        filter_inputs = [components[k] for k in filter_keys]
        filter_inputs.append(components.get("navigation_state"))

        filter_outputs = [
            components.get("runs_gallery"),
            components.get("runs_table"),
            components.get("runs_stats"),
            components.get("navigation_state"),
            components.get("runs_nav_filter_row"),
            components.get("runs_prompt_filter"),
        ]

        # Wire change events for all filter components
        for filter_key in filter_keys:
            if filter_key in components:
                components[filter_key].change(
                    fn=load_runs_with_filters,
                    inputs=filter_inputs,
                    outputs=filter_outputs,
                )


def wire_runs_selection_events(components):
    """Wire runs table and gallery selection events."""
    from cosmos_workflow.ui.tabs.runs import (
        on_runs_gallery_select,
        on_runs_table_select,
        update_runs_selection_info,
    )

    # Define the output keys for run details
    runs_output_keys = [
        "runs_details_group",
        "runs_detail_id",
        "runs_detail_status",
        # Content visibility
        "runs_main_content_transfer",
        "runs_main_content_enhance",
        "runs_main_content_upscale",
        # Transfer content
        "runs_input_video_1",
        "runs_input_video_2",
        "runs_input_video_3",
        "runs_input_video_4",
        "runs_output_video",
        "runs_prompt_text",
        # Enhancement content
        "runs_original_prompt_enhance",
        "runs_enhanced_prompt_enhance",
        "runs_enhance_stats",
        # Upscale content
        "runs_output_video_upscale",
        "runs_original_video_upscale",
        "runs_upscale_stats",
        "runs_upscale_prompt",
        # Info tab
        "runs_info_id",
        "runs_info_prompt_id",
        "runs_info_status",
        "runs_info_duration",
        "runs_info_type",
        "runs_info_prompt_name",
        # Star ratings
        "star_1",
        "star_2",
        "star_3",
        "star_4",
        "star_5",
        "runs_info_rating",
        "runs_info_created",
        "runs_info_completed",
        "runs_info_output_path",
        "runs_info_input_paths",
        # Parameters and logs
        "runs_params_json",
        "runs_log_path",
        "runs_log_output",
        # Selection tracking
        "runs_upscale_selected_btn",
        "runs_selected_id",
        "runs_selected_info",
        # Upscaled output
        "runs_output_video_upscaled",
        "runs_upscaled_tab",
    ]

    # Wire table selection
    if "runs_table" in components:
        outputs = [components.get(k) for k in runs_output_keys if k in components]
        if outputs:
            components["runs_table"].select(
                fn=on_runs_table_select,
                inputs=[components["runs_table"]],
                outputs=outputs,
            )

        # Update selection info
        if "runs_selected_info" in components and "runs_selected_id" in components:
            components["runs_table"].select(
                fn=update_runs_selection_info,
                inputs=[components["runs_table"]],
                outputs=[components["runs_selected_info"], components["runs_selected_id"]],
            )

    # Wire gallery selection
    if "runs_gallery" in components:
        outputs = [components.get(k) for k in runs_output_keys if k in components]
        if outputs:
            # Add index tracking
            outputs_with_index = [*outputs, components.get("runs_selected_index")]

            def on_gallery_select_with_index(evt: gr.SelectData):
                result = on_runs_gallery_select(evt)
                return [*result, evt.index if evt else 0]

            components["runs_gallery"].select(
                fn=on_gallery_select_with_index,
                inputs=[],
                outputs=outputs_with_index,
            )


def wire_runs_navigation_events(components):
    """Wire gallery navigation buttons."""
    if all(k in components for k in ["runs_prev_btn", "runs_next_btn", "runs_selected_index"]):

        def navigate_gallery_prev(current_index):
            new_index = max(0, current_index - 1)
            return gr.update(selected_index=new_index), new_index

        def navigate_gallery_next(current_index):
            new_index = current_index + 1
            return gr.update(selected_index=new_index), new_index

        components["runs_prev_btn"].click(
            fn=navigate_gallery_prev,
            inputs=[components["runs_selected_index"]],
            outputs=[components["runs_gallery"], components["runs_selected_index"]],
        )

        components["runs_next_btn"].click(
            fn=navigate_gallery_next,
            inputs=[components["runs_selected_index"]],
            outputs=[components["runs_gallery"], components["runs_selected_index"]],
        )


def wire_runs_action_events(components, api):
    """Wire run action events (delete, upscale, etc)."""
    from cosmos_workflow.ui.tabs.runs import (
        cancel_delete_run,
        cancel_upscale,
        confirm_delete_run,
        execute_upscale,
        load_run_logs,
        load_runs_with_filters,
        preview_delete_run,
        show_upscale_dialog,
    )

    # Delete operations
    if "runs_delete_selected_btn" in components:
        components["runs_delete_selected_btn"].click(
            fn=preview_delete_run,
            inputs=[components.get("runs_selected_id")],
            outputs=[
                components.get("runs_delete_dialog"),
                components.get("runs_delete_preview"),
                components.get("runs_delete_outputs_checkbox"),
                components.get("runs_delete_id_hidden"),
            ],
        )

    if "runs_confirm_delete_btn" in components:
        components["runs_confirm_delete_btn"].click(
            fn=confirm_delete_run,
            inputs=[
                components.get("runs_delete_id_hidden"),
                components.get("runs_delete_outputs_checkbox"),
            ],
            outputs=[
                components.get("runs_selected_info"),
                components.get("runs_delete_dialog"),
            ],
        ).then(
            fn=load_runs_with_filters,
            inputs=[
                components.get("runs_status_filter"),
                components.get("runs_date_filter"),
                components.get("runs_type_filter"),
                components.get("runs_search"),
                components.get("runs_limit"),
                components.get("runs_rating_filter"),
                components.get("runs_version_filter"),
                components.get("navigation_state"),
            ],
            outputs=[
                components.get("runs_gallery"),
                components.get("runs_table"),
                components.get("runs_stats"),
                components.get("navigation_state"),
                components.get("runs_nav_filter_row"),
                components.get("runs_prompt_filter"),
            ],
        )

    if "runs_cancel_delete_btn" in components:
        components["runs_cancel_delete_btn"].click(
            fn=cancel_delete_run,
            outputs=[
                components.get("runs_selected_info"),
                components.get("runs_delete_dialog"),
            ],
        )

    # Upscale operations
    if "runs_upscale_selected_btn" in components:
        components["runs_upscale_selected_btn"].click(
            fn=show_upscale_dialog,
            inputs=[components.get("runs_selected_id")],
            outputs=[
                components.get("runs_upscale_dialog"),
                components.get("runs_upscale_preview"),
                components.get("runs_upscale_id_hidden"),
            ],
        )

    if "runs_confirm_upscale_btn" in components:
        components["runs_confirm_upscale_btn"].click(
            fn=execute_upscale,
            inputs=[
                components.get("runs_upscale_id_hidden"),
                components.get("runs_upscale_weight"),
                components.get("runs_upscale_prompt_input"),
            ],
            outputs=[
                components.get("runs_upscale_dialog"),
                components.get("runs_selected_info"),
            ],
        )

    if "runs_cancel_upscale_btn" in components:
        components["runs_cancel_upscale_btn"].click(
            fn=cancel_upscale,
            outputs=[components.get("runs_upscale_dialog")],
        )

    # Load logs button
    if "runs_load_logs_btn" in components:
        components["runs_load_logs_btn"].click(
            fn=load_run_logs,
            inputs=[components.get("runs_log_path")],
            outputs=[components.get("runs_log_output")],
        )


def wire_runs_rating_events(components, api):
    """Wire star rating button events."""
    from cosmos_workflow.ui.tabs.runs import load_runs_data_with_version_filter

    def handle_star_click(star_value, run_id, *filter_args):
        """Handle star button click and save rating."""
        if not run_id:
            # No run selected, return unchanged
            return [gr.update()] * 10

        # Save the rating
        if api:
            api.set_run_rating(run_id, star_value)
            logger.info("Set rating {} for run {}", star_value, run_id)

        # Refresh the runs display
        (
            status_filter,
            date_filter,
            type_filter,
            search_text,
            limit,
            rating_filter,
            version_filter,
        ) = filter_args
        gallery_data, table_data, stats = load_runs_data_with_version_filter(
            status_filter,
            date_filter,
            type_filter,
            search_text,
            limit,
            rating_filter,
            version_filter,
        )

        # Return updated star states
        return [
            gr.update(variant="primary" if i <= star_value else "secondary") for i in range(1, 6)
        ] + [
            gr.update(value=f"**Current Rating:** {star_value}/5"),
            gallery_data,
            table_data,
            stats,
        ]

    # Wire star rating buttons
    for i in range(1, 6):
        star_key = f"star_{i}"
        if star_key in components:
            # Collect all required inputs for the handler
            inputs = [
                components.get("runs_info_id"),  # run_id
                components.get("runs_status_filter"),
                components.get("runs_date_filter"),
                components.get("runs_type_filter"),
                components.get("runs_search"),
                components.get("runs_limit"),
                components.get("runs_rating_filter"),
                components.get("runs_version_filter"),
            ]

            outputs = [
                components.get("star_1"),
                components.get("star_2"),
                components.get("star_3"),
                components.get("star_4"),
                components.get("star_5"),
                components.get("runs_info_rating"),
                components.get("runs_gallery"),
                components.get("runs_table"),
                components.get("runs_stats"),
            ]

            components[star_key].click(
                fn=functools.partial(handle_star_click, i),
                inputs=inputs,
                outputs=outputs,
            )


def wire_jobs_events(components, api, simple_queue_service):
    """Wire events for the Jobs tab.

    Args:
        components: Dictionary of UI components
        api: CosmosAPI instance
        simple_queue_service: SimplifiedQueueService instance
    """
    wire_jobs_control_events(components)
    wire_queue_control_events(components, simple_queue_service)
    wire_queue_selection_events(components, simple_queue_service)


def wire_jobs_control_events(components):
    """Wire job control events (stream, kill, etc)."""
    from cosmos_workflow.ui.tabs.jobs_handlers import (
        cancel_kill_confirmation,
        execute_kill_job,
        refresh_and_stream,
        show_kill_confirmation,
    )

    # Stream button
    if "stream_btn" in components:
        components["stream_btn"].click(
            fn=refresh_and_stream,
            inputs=None,  # refresh_and_stream doesn't take any inputs
            outputs=filter_none_components(
                [
                    components.get("running_jobs_display"),
                    components.get("job_status"),
                    components.get("active_job_card"),
                    components.get("jobs_log_display"),
                ]
            ),
        )

    # Kill job operations
    if "kill_job_btn" in components:
        components["kill_job_btn"].click(
            fn=show_kill_confirmation,
            outputs=filter_none_components(
                [
                    components.get("kill_confirm_row"),
                    components.get("kill_job_btn"),
                ]
            ),
        )

    if "confirm_kill_btn" in components:
        components["confirm_kill_btn"].click(
            fn=execute_kill_job,
            outputs=filter_none_components(
                [
                    components.get("running_jobs_display"),
                    components.get("job_status"),
                    components.get("active_job_card"),
                    components.get("kill_confirm_row"),
                    components.get("kill_job_btn"),
                ]
            ),
        )

    if "cancel_kill_btn" in components:
        components["cancel_kill_btn"].click(
            fn=cancel_kill_confirmation,
            outputs=filter_none_components(
                [
                    components.get("kill_confirm_row"),
                    components.get("kill_job_btn"),
                ]
            ),
        )

    # Additional job control events
    if "clear_logs_btn" in components:

        def clear_logs():
            """Clear the job logs display."""
            return gr.update(value="")

        components["clear_logs_btn"].click(
            fn=clear_logs,
            outputs=filter_none_components([components.get("jobs_log_display")]),
        )

    if "auto_advance_toggle" in components:

        def toggle_auto_advance(enabled):
            """Toggle auto-advance for job logs."""
            return gr.update(value=f"Auto-advance: {'Enabled' if enabled else 'Disabled'}")

        components["auto_advance_toggle"].change(
            fn=toggle_auto_advance,
            inputs=[components["auto_advance_toggle"]],
            outputs=[components.get("auto_advance_status")],
        )

    if "batch_size" in components:

        def update_batch_size(size):
            """Update batch processing size."""
            logger.info(f"Batch size updated to: {size}")
            # Don't return anything if no output is expected

        if "batch_size" in components:
            components["batch_size"].change(
                fn=update_batch_size,
                inputs=[components["batch_size"]],
                outputs=None,  # No output expected
            )

    if "cancel_job_btn" in components:
        from cosmos_workflow.ui.tabs.jobs_handlers import cancel_selected_job

        components["cancel_job_btn"].click(
            fn=cancel_selected_job,
            inputs=[components.get("selected_job_id")],
            outputs=filter_none_components(
                [
                    components.get("job_status"),
                    components.get("queue_status"),
                    components.get("queue_table"),
                ]
            ),
        )


def wire_queue_control_events(components, simple_queue_service):
    """Wire queue control events (pause, resume, clear, etc)."""
    from cosmos_workflow.ui.queue_handlers import QueueHandlers

    queue_handlers = QueueHandlers(simple_queue_service)

    # Queue control buttons
    if "pause_queue_btn" in components:
        components["pause_queue_btn"].click(
            fn=queue_handlers.pause_queue,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    if "resume_queue_btn" in components:
        components["resume_queue_btn"].click(
            fn=queue_handlers.resume_queue,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    if "clear_failed_btn" in components:
        components["clear_failed_btn"].click(
            fn=queue_handlers.clear_failed,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    if "retry_failed_btn" in components:
        components["retry_failed_btn"].click(
            fn=queue_handlers.retry_failed,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    # Queue refresh
    if "refresh_queue_btn" in components:
        components["refresh_queue_btn"].click(
            fn=queue_handlers.get_queue_display,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )


def wire_queue_selection_events(components, simple_queue_service):
    """Wire queue table selection events."""
    from cosmos_workflow.ui.queue_handlers import QueueHandlers

    queue_handlers = QueueHandlers(simple_queue_service)

    # Queue table selection
    if "queue_table" in components:
        components["queue_table"].select(
            fn=queue_handlers.on_queue_select,
            inputs=[components["queue_table"]],
            outputs=filter_none_components(
                [
                    components.get("queue_selected_info"),
                    components.get("queue_actions_row"),
                    components.get("queue_selected_id"),
                ]
            ),
        )

    # Queue item actions
    if "remove_queue_item_btn" in components:
        components["remove_queue_item_btn"].click(
            fn=queue_handlers.remove_item,
            inputs=[components.get("queue_selected_id")],
            outputs=filter_none_components(
                [
                    components.get("queue_status"),
                    components.get("queue_table"),
                    components.get("queue_selected_info"),
                    components.get("queue_actions_row"),
                ]
            ),
        )

    if "prioritize_queue_item_btn" in components:
        components["prioritize_queue_item_btn"].click(
            fn=queue_handlers.prioritize_item,
            inputs=[components.get("queue_selected_id")],
            outputs=filter_none_components(
                [
                    components.get("queue_status"),
                    components.get("queue_table"),
                    components.get("queue_selected_info"),
                ]
            ),
        )


def wire_all_events(app, components, config, api, simple_queue_service):
    """Wire all event handlers for the application.

    This is the main orchestrator that calls all specialized event wiring functions.

    Args:
        app: The Gradio Blocks app
        components: Dictionary of all UI components
        config: Application configuration
        api: CosmosAPI instance
        simple_queue_service: SimplifiedQueueService instance
    """
    # Wire events in logical groups
    wire_navigation_events(components)
    wire_header_events(components, api, config)
    wire_inputs_events(components, config, api)
    wire_prompts_events(components, api, simple_queue_service)
    wire_runs_events(components, api)
    wire_jobs_events(components, api, simple_queue_service)

    # Wire cross-tab navigation events
    wire_cross_tab_navigation(components)

    # Load initial data
    wire_initial_data_load(app, components, config, api, simple_queue_service)

    logger.info("All events wired successfully")


def wire_initial_data_load(app, components, config, api, simple_queue_service):
    """Wire initial data loading events when the app starts.

    Args:
        app: The Gradio Blocks app
        components: Dictionary of all UI components
        config: Application configuration
        api: CosmosAPI instance
        simple_queue_service: SimplifiedQueueService instance
    """
    from pathlib import Path

    from cosmos_workflow.ui.queue_handlers import QueueHandlers
    from cosmos_workflow.ui.tabs.inputs_handlers import load_input_gallery
    from cosmos_workflow.ui.tabs.prompts_handlers import load_ops_prompts
    from cosmos_workflow.ui.tabs.runs.data_loading import load_runs_data

    # Load initial data for inputs tab
    if "input_gallery" in components and "inputs_results_count" in components:

        def load_initial_inputs():
            local_config = config.get_local_config()
            inputs_dir = Path(local_config.videos_dir)
            gallery_items, results_text = load_input_gallery(inputs_dir)
            return gallery_items, results_text

        app.load(
            fn=load_initial_inputs,
            outputs=[components["input_gallery"], components["inputs_results_count"]],
        )

    # Load initial data for prompts tab - fixed to use ops_prompts_table
    if "ops_prompts_table" in components:

        def load_initial_prompts():
            return load_ops_prompts(
                limit=50,
                search_text="",
                enhanced_filter="all",
                runs_filter="all",
                date_filter="all",
            )

        app.load(
            fn=load_initial_prompts,
            outputs=[components["ops_prompts_table"]],
        )

    # Load initial data for runs tab
    if "runs_gallery" in components:

        def load_initial_runs():
            # Use the legacy load_runs_data function signature
            return load_runs_data(
                status_filter="all",
                date_filter="all",
                type_filter="all",
                search_text="",
                limit=50,
                rating_filter="all",
            )

        runs_outputs = [
            components.get("runs_gallery"),
            components.get("runs_table"),
            components.get("runs_stats"),
            components.get("runs_results_count"),
        ]

        app.load(
            fn=load_initial_runs,
            outputs=filter_none_components(runs_outputs),
        )

    # Load initial data for jobs/queue tab
    if "queue_table" in components:
        queue_handlers = QueueHandlers(simple_queue_service)

        app.load(
            fn=queue_handlers.get_queue_display,
            outputs=filter_none_components(
                [
                    components.get("queue_status"),
                    components.get("queue_table"),
                ]
            ),
        )

    logger.info("Initial data loading configured")


def wire_cross_tab_navigation(components):
    """Wire cross-tab navigation events."""
    from cosmos_workflow.ui.tabs.runs import load_runs_for_multiple_prompts

    # View runs button from prompts tab - this needs the full navigation
    if "view_runs_btn" in components:

        def prepare_runs_navigation(selected_prompt_ids):
            """Navigate to runs tab with prompt filter and load data."""
            if not selected_prompt_ids:
                return (
                    {"filter_type": None, "filter_values": [], "source_tab": None},
                    None,
                    "No prompts selected",
                    2,  # Runs tab index
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=False),
                    gr.update(value=""),
                )

            logger.info(f"Navigating to runs with {len(selected_prompt_ids)} prompts")

            # Load filtered runs data
            gallery, table, stats, prompt_names = load_runs_for_multiple_prompts(
                selected_prompt_ids, "all", "all", "all", "", "50", None
            )

            # Format filter display
            filter_display = ""
            if prompt_names:
                filter_display = f"**Filtering by {len(prompt_names)} prompt(s):**\n"
                for name in prompt_names[:3]:
                    filter_display += f"• {name}\n"
                if len(prompt_names) > 3:
                    filter_display += f"• ... and {len(prompt_names) - 3} more"

            return (
                {
                    "filter_type": "prompt_ids",
                    "filter_values": selected_prompt_ids,
                    "source_tab": "prompts",
                },
                None,
                f"Viewing runs for {len(selected_prompt_ids)} prompt(s)",
                2,  # Runs tab index
                gallery,
                table,
                stats,
                gr.update(visible=True),
                gr.update(value=filter_display),
            )

        outputs = filter_none_components(
            [
                components.get("navigation_state"),
                components.get("pending_nav_data"),
                components.get("selection_count"),
                components.get("selected_tab"),  # Hidden number component for tab index
                components.get("runs_gallery"),
                components.get("runs_table"),
                components.get("runs_stats"),
                components.get("runs_nav_filter_row"),
                components.get("runs_prompt_filter"),
            ]
        )

        if outputs:
            components["view_runs_btn"].click(
                fn=prepare_runs_navigation,
                inputs=[components.get("selected_prompt_ids_state")],
                outputs=outputs,
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[2]?.click(); }, 100); return []; }",
                queue=False,
            )

    # View runs button from inputs tab
    if "view_runs_for_input_btn" in components:

        def navigate_to_runs_for_input(selected_dir, nav_state):
            """Navigate to runs tab for input directory."""
            if not selected_dir:
                return gr.update(), nav_state, None

            # Prepare navigation data
            pending_data = {
                "filter_type": "input",
                "filter_value": selected_dir,
                "source_tab": "inputs",
            }

            return gr.update(selected=2), nav_state, pending_data

        if "view_runs_for_input_btn" in components:
            components["view_runs_for_input_btn"].click(
                fn=navigate_to_runs_for_input,
                inputs=filter_none_components(
                    [
                        components.get("selected_dir_path"),  # Fixed: using correct component name
                        components.get("navigation_state"),
                    ]
                ),
                outputs=filter_none_components(
                    [
                        components.get("tabs"),
                        components.get("navigation_state"),
                        components.get("pending_nav_data"),
                    ]
                ),
            )

    # Navigate from inputs to prompts
    if "view_prompts_for_input_btn" in components:

        def prepare_prompts_navigation_from_input(input_name):
            """Navigate to Prompts tab with search filter for input directory."""
            if not input_name:
                return gr.update(), gr.update(), 1

            logger.info(f"Navigating to prompts with search: {input_name}")

            # Extract just the directory name (remove any path prefixes)
            search_term = input_name.split("/")[-1] if "/" in input_name else input_name
            search_term = search_term.split("\\")[-1] if "\\" in search_term else search_term

            # Load prompts with search filter
            from cosmos_workflow.ui.tabs.prompts_handlers import load_ops_prompts

            filtered_table = load_ops_prompts(
                limit=50,
                search_text=search_term,
                enhanced_filter="all",
                runs_filter="all",
                date_filter="all",
            )

            return (
                gr.update(value=search_term),  # Update search box with directory name only
                filtered_table,  # Update table
                1,  # Prompts tab index
            )

        outputs = filter_none_components(
            [
                components.get("prompt_search"),
                components.get("ops_prompts_table"),  # Fixed: was "prompts_table"
                components.get("selected_tab"),
            ]
        )

        if outputs:
            components["view_prompts_for_input_btn"].click(
                fn=prepare_prompts_navigation_from_input,
                inputs=[components.get("selected_dir_path")],
                outputs=outputs,
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[1]?.click(); }, 100); return []; }",
                queue=False,
            )
