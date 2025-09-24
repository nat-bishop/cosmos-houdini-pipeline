"""Event wiring for Runs tab components."""

import functools

import gradio as gr

from cosmos_workflow.ui.tabs.runs import (
    cancel_delete_run,
    cancel_upscale,
    confirm_delete_run,
    execute_upscale,
    load_run_logs,
    load_runs_data_with_version_filter,
    load_runs_with_filters,
    on_runs_gallery_select,
    on_runs_table_select,
    preview_delete_run,
    show_upscale_dialog,
    update_runs_selection_info,
)
from cosmos_workflow.utils.logging import logger


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
        # Common elements
        "runs_info_id",
        "runs_info_status",
        "runs_info_type",
        "runs_info_timestamp",
        "runs_info_prompt_id",
        "runs_info_prompt_name",
        "runs_info_duration",
        "runs_info_seed",
        "runs_info_gpu",
        "runs_info_rating",
        "runs_model_version_display",
        "runs_log_path",
        "runs_log_output",
        "runs_detail_main_video",
        "runs_detail_thumb_video",
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
                components.get("runs_delete_dialog"),  # Hide dialog (1st return value)
                components.get("runs_selected_id"),  # Clear selected ID (2nd return value)
                components.get("runs_selected_info"),  # Status message (3rd return value)
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
                components.get("runs_delete_dialog"),  # Hide dialog (only return value)
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
