"""Event wiring for Runs tab components."""

import functools
from typing import Any

import gradio as gr

from cosmos_workflow.ui.tabs.runs import (
    cancel_delete_run,
    cancel_upscale,
    confirm_delete_run,
    execute_upscale,
    load_run_logs,
    load_runs_data,
    load_runs_with_filters,
    on_runs_gallery_select,
    on_runs_table_select,
    preview_delete_run,
    show_upscale_dialog,
    update_runs_selection_info,
)
from cosmos_workflow.utils.logging import logger


def wire_runs_events(components: dict[str, Any], api: Any) -> None:
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


def wire_runs_filtering_events(components: dict[str, Any]) -> None:
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
        # Create inputs list for the load function - includes navigation_state for reading
        load_inputs = [components[k] for k in filter_keys]
        load_inputs.append(components.get("navigation_state"))

        filter_outputs = [
            components.get("runs_gallery"),
            components.get("runs_table"),
            components.get("runs_stats"),
            components.get("navigation_state"),
            components.get("runs_nav_filter_row"),
            components.get("runs_prompt_filter"),
        ]

        # Wire change events for all filter components
        # IMPORTANT: We pass the same inputs but the change event only triggers
        # when the specific filter component changes, not when navigation_state changes
        for filter_key in filter_keys:
            if filter_key in components:
                components[filter_key].change(
                    fn=load_runs_with_filters,
                    inputs=load_inputs,
                    outputs=filter_outputs,
                )

        # Wire clear filter button
        if "clear_nav_filter_btn" in components:

            def clear_navigation_filter(*args):
                """Clear the navigation filter and reload all runs."""
                # Return cleared navigation state and hide filter display
                return (
                    gr.update(),  # runs_gallery - will be refreshed
                    gr.update(),  # runs_table - will be refreshed
                    gr.update(),  # runs_stats - will be refreshed
                    {
                        "filter_type": None,
                        "filter_values": [],
                        "source_tab": None,
                    },  # Clear navigation_state
                    gr.update(visible=False),  # Hide runs_nav_filter_row
                    gr.update(value=""),  # Clear runs_prompt_filter text
                )

            components["clear_nav_filter_btn"].click(
                fn=clear_navigation_filter,
                inputs=load_inputs,  # Pass same inputs for consistency
                outputs=filter_outputs,
            ).then(
                # Reload data after clearing filter
                fn=load_runs_with_filters,
                inputs=load_inputs,
                outputs=filter_outputs,
            )


def wire_runs_selection_events(components: dict[str, Any]) -> None:
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
        "runs_upscaled_tab",  # Tab visibility for upscaled output
        "runs_output_video_upscaled",  # Upscaled video in tab
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
        "runs_info_duration",
        "runs_info_prompt_id",
        "runs_info_created",
        "runs_info_completed",
        "runs_info_output_path",
        "runs_info_input_paths",
        # Star rating buttons
        "star_1",
        "star_2",
        "star_3",
        "star_4",
        "star_5",
        # Additional fields
        "runs_params_json",
        "runs_log_path",
        "runs_log_output",
        "runs_upscale_selected_btn",
    ]

    # Wire table selection
    if "runs_table" in components:
        outputs = [components.get(k) for k in runs_output_keys if k in components]
        if outputs:
            # Track which components are actually present for the handler
            present_keys = [k for k in runs_output_keys if k in components]

            def on_table_select_filtered(table_data, evt: gr.SelectData) -> list[Any]:
                result = on_runs_table_select(table_data, evt)
                # Filter result to only include values for present components
                return [result[runs_output_keys.index(k)] for k in present_keys]

            components["runs_table"].select(
                fn=on_table_select_filtered,
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

            # Track which components are actually present for the handler
            present_keys = [k for k in runs_output_keys if k in components]

            def on_gallery_select_with_index(evt: gr.SelectData) -> list[Any]:
                result = on_runs_gallery_select(evt)
                # Filter result to only include values for present components
                filtered_result = [result[runs_output_keys.index(k)] for k in present_keys]
                return [*filtered_result, evt.index if evt else 0]

            components["runs_gallery"].select(
                fn=on_gallery_select_with_index,
                inputs=[],
                outputs=outputs_with_index,
            )

        # Update selection info for gallery too
        if "runs_selected_info" in components and "runs_selected_id" in components:

            def update_gallery_selection_info(evt: gr.SelectData) -> tuple[Any, str]:
                """Update selection info when gallery item is selected."""
                if evt is None:
                    return gr.update(value="No run selected"), ""

                # Extract run ID from gallery selection
                result = on_runs_gallery_select(evt)
                if result and len(result) > 1:
                    run_id = result[1]  # runs_detail_id is at index 1
                    if run_id:
                        return gr.update(value=f"**Selected:** {run_id[:8]}..."), run_id

                return gr.update(value="No run selected"), ""

            components["runs_gallery"].select(
                fn=update_gallery_selection_info,
                inputs=[],
                outputs=[components["runs_selected_info"], components["runs_selected_id"]],
            )


def wire_runs_navigation_events(components: dict[str, Any]) -> None:
    """Wire gallery navigation buttons."""
    if all(k in components for k in ["runs_prev_btn", "runs_next_btn", "runs_selected_index"]):

        def navigate_gallery_prev(current_index: int) -> tuple[Any, int]:
            new_index = max(0, current_index - 1)
            return gr.update(selected_index=new_index), new_index

        def navigate_gallery_next(current_index: int) -> tuple[Any, int]:
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


def wire_runs_action_events(components: dict[str, Any], api: Any) -> None:
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


def wire_runs_rating_events(components: dict[str, Any], api: Any) -> None:
    """Wire star rating button events."""

    def handle_star_click(star_value: int, run_id: str | None, *filter_args) -> list[Any]:
        """Handle star button click and save rating."""
        if not run_id:
            # No run selected, return unchanged
            return [gr.update()] * 10

        # Save the rating
        if api:
            api.set_run_rating(run_id, star_value)
            logger.info(
                "Run rating updated - Run ID: %s, Rating: %d/5, Source: UI", run_id, star_value
            )

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
        # Use load_runs_data which now handles all filtering internally
        gallery_data, table_data, stats = load_runs_data(
            status_filter,
            date_filter,
            type_filter,
            search_text,
            limit,
            rating_filter,
        )

        # Return updated star states with filled/empty stars
        return [
            gr.update(
                value="★" if i <= star_value else "☆",
                variant="primary" if i <= star_value else "secondary",
            )
            for i in range(1, 6)
        ] + [
            gr.update(value=star_value),  # runs_info_rating expects a number, not a string
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
