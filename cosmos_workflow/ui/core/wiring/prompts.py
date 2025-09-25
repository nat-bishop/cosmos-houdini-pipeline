"""Event wiring for Prompts tab components."""

import functools
from typing import Any

import gradio as gr

from cosmos_workflow.ui.core.safe_wiring import safe_wire
from cosmos_workflow.ui.tabs.prompts_handlers import (
    cancel_delete_prompts,
    clear_selection,
    confirm_delete_prompts,
    load_ops_prompts,
    on_prompt_row_select,
    preview_delete_prompts,
    run_enhance_on_selected,
    run_inference_on_selected,
    select_all_prompts,
)


def wire_prompts_events(components: dict[str, Any], api: Any, simple_queue_service: Any) -> None:
    """Wire events for the Prompts tab.

    Args:
        components: Dictionary of UI components
        api: CosmosAPI instance
        simple_queue_service: SimplifiedQueueService instance
    """
    # Bind services to handlers
    run_inference_bound = functools.partial(
        run_inference_on_selected,
        queue_service=simple_queue_service,
    )
    run_enhance_bound = functools.partial(
        run_enhance_on_selected,
        queue_service=simple_queue_service,
    )

    # Refresh button - removed as prompts_table doesn't exist anymore
    # The ops_prompts_table is refreshed via filter changes instead

    # Wire filtering events for ops_prompts_table
    filter_components = [
        "prompts_search",
        "prompts_enhanced_filter",
        "prompts_runs_filter",
        "prompts_date_filter",
        "ops_limit",
    ]

    # Check if all filter components exist
    if all(comp in components for comp in filter_components):
        filter_inputs = [
            components["ops_limit"],
            components["prompts_search"],
            components["prompts_enhanced_filter"],
            components["prompts_runs_filter"],
            components["prompts_date_filter"],
        ]

        # Wire each filter component to reload the table
        for filter_comp_name in filter_components:
            components[filter_comp_name].change(
                fn=load_ops_prompts,
                inputs=filter_inputs,
                outputs=[components["ops_prompts_table"]],
                show_progress=False,
            )

    # Old prompts_table selection removed - using ops_prompts_table now

    # Inference and enhance buttons
    if "run_inference_btn" in components and "ops_prompts_table" in components:
        # Inference needs all weight sliders and parameters
        inference_inputs = [
            components.get("ops_prompts_table"),
            components.get("weight_vis"),
            components.get("weight_edge"),
            components.get("weight_depth"),
            components.get("weight_seg"),
            components.get("inf_steps"),
            components.get("inf_guidance"),
            components.get("inf_seed"),
            components.get("inf_fps"),
            components.get("inf_sigma_max"),
            components.get("inf_blur_strength"),
            components.get("inf_canny_threshold"),
        ]

        inference_inputs = [i for i in inference_inputs if i is not None]
        if inference_inputs:
            safe_wire(
                components["run_inference_btn"],
                "click",
                run_inference_bound,
                inputs=inference_inputs,
                outputs=[
                    components.get("queue_table"),
                    components.get("inference_status"),
                    components.get("status_display"),
                ],
                show_progress=True,
            )

    if "run_enhance_btn" in components and "ops_prompts_table" in components:
        # Enhance needs dataframe, create_new, and force_overwrite
        enhance_inputs = [
            components.get("ops_prompts_table"),
            components.get("enhance_create_new"),
            components.get("enhance_force"),
        ]
        enhance_inputs = [i for i in enhance_inputs if i is not None]

        if enhance_inputs:
            safe_wire(
                components["run_enhance_btn"],
                "click",
                run_enhance_bound,
                inputs=enhance_inputs,
                outputs=[
                    components.get("queue_table"),
                    components.get("enhance_status"),
                    components.get("status_display"),
                ],
                show_progress=True,
            )

    # Selection controls
    if "select_all_btn" in components and "ops_prompts_table" in components:
        outputs = [
            components.get("ops_prompts_table"),
            components.get("selection_count"),
        ]
        if "selected_prompt_ids_state" in components:
            outputs.append(components.get("selected_prompt_ids_state"))

        safe_wire(
            components["select_all_btn"],
            "click",
            select_all_prompts,
            inputs=[components["ops_prompts_table"]],
            outputs=outputs,
        )

    if "clear_selection_btn" in components and "ops_prompts_table" in components:
        outputs = [
            components.get("ops_prompts_table"),
            components.get("selection_count"),
        ]
        if "selected_prompt_ids_state" in components:
            outputs.append(components.get("selected_prompt_ids_state"))

        safe_wire(
            components["clear_selection_btn"],
            "click",
            clear_selection,
            inputs=[components["ops_prompts_table"]],
            outputs=outputs,
        )

    # Delete operations
    if "delete_selected_btn" in components and "ops_prompts_table" in components:
        safe_wire(
            components["delete_selected_btn"],
            "click",
            preview_delete_prompts,
            inputs=[components["ops_prompts_table"]],
            outputs=[
                components.get("prompts_delete_dialog"),
                components.get("prompts_delete_preview"),
                components.get("prompts_delete_outputs_checkbox"),
                components.get("prompts_delete_ids_hidden"),
            ],
            scroll_to_output=True,  # Scroll to delete confirmation dialog
        )

    if "prompts_confirm_delete_btn" in components and "prompts_delete_ids_hidden" in components:
        # Clean outputs - only ops_prompts_table and dialog exist
        filtered_outputs = [
            components.get("ops_prompts_table"),
            components.get("prompts_delete_dialog"),
        ]
        filtered_outputs = [o for o in filtered_outputs if o is not None]

        components["prompts_confirm_delete_btn"].click(
            fn=confirm_delete_prompts,
            inputs=[
                components["prompts_delete_ids_hidden"],
                components.get("prompts_delete_outputs_checkbox"),
            ],
            outputs=filtered_outputs,
        ).then(
            fn=load_ops_prompts,
            inputs=[
                components.get("prompts_limit_slider", gr.Number(value=50, visible=False)),
                components.get("prompts_search", gr.Textbox(value="", visible=False)),
                components.get("prompts_enhanced_filter", gr.Dropdown(value="all", visible=False)),
                components.get("prompts_runs_filter", gr.Dropdown(value="all", visible=False)),
                components.get("prompts_date_filter", gr.Dropdown(value="all", visible=False)),
            ],
            outputs=[components.get("ops_prompts_table")],
        )

    if "prompts_cancel_delete_btn" in components:
        components["prompts_cancel_delete_btn"].click(
            fn=cancel_delete_prompts,
            outputs=[components.get("prompts_delete_dialog")],
        )

    # Ops prompts table selection and checkbox changes
    if "ops_prompts_table" in components:
        # Wire selection event for row details
        outputs = [
            components.get("selected_prompt_id"),
            components.get("selected_prompt_name"),
            components.get("selected_prompt_text"),
            components.get("selected_prompt_negative"),
            components.get("selected_prompt_created"),
            components.get("selected_prompt_video_dir"),
            components.get("selected_prompt_enhanced"),
            components.get("selected_prompt_runs_stats"),
            components.get("selected_prompt_rating"),
            components.get("selected_prompt_video_thumb"),
        ]
        outputs = [o for o in outputs if o is not None]
        if outputs:
            components["ops_prompts_table"].select(
                fn=on_prompt_row_select,
                inputs=[components["ops_prompts_table"]],
                outputs=outputs,
            )

        # Wire change event to update selection count and IDs when checkboxes are clicked
        if "selection_count" in components:
            from cosmos_workflow.ui.tabs.prompts_handlers import update_selection_count

            # Include the state component in outputs if it exists
            outputs = [components["selection_count"]]
            if "selected_prompt_ids_state" in components:
                outputs.append(components["selected_prompt_ids_state"])

            components["ops_prompts_table"].change(
                fn=update_selection_count,
                inputs=[components["ops_prompts_table"]],
                outputs=outputs,
                show_progress=False,
            )
