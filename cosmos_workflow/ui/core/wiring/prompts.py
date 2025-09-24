"""Event wiring for Prompts tab components."""

import functools
from typing import Any

import gradio as gr

from cosmos_workflow.ui.core.safe_wiring import safe_wire
from cosmos_workflow.ui.tabs.prompts_handlers import (
    cancel_delete_prompts,
    clear_selection,
    confirm_delete_prompts,
    filter_prompts,
    list_prompts,
    load_ops_prompts,
    on_prompt_row_select,
    preview_delete_prompts,
    run_enhance_on_selected,
    run_inference_on_selected,
    select_all_prompts,
)
from cosmos_workflow.utils.logging import logger


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

    # Refresh button
    if "refresh_prompts_btn" in components:
        components["refresh_prompts_btn"].click(
            fn=list_prompts,
            outputs=[components.get("prompts_table")],
            show_progress=False,
        )

    # Filtering events
    if "prompt_search" in components:
        safe_wire(
            components["prompt_search"],
            "change",
            filter_prompts,
            inputs=[
                components.get("prompt_search"),
                components.get("prompt_status_filter"),
                components.get("prompts_table"),
            ],
            outputs=[components.get("prompts_table")],
            show_progress=False,
        )

    if "prompt_status_filter" in components:
        safe_wire(
            components["prompt_status_filter"],
            "change",
            filter_prompts,
            inputs=[
                components.get("prompt_search"),
                components.get("prompt_status_filter"),
                components.get("prompts_table"),
            ],
            outputs=[components.get("prompts_table")],
            show_progress=False,
        )

    # Table selection
    if "prompts_table" in components:
        safe_wire(
            components["prompts_table"],
            "select",
            on_prompt_row_select,
            inputs=[components["prompts_table"]],
            outputs=[
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
            ],
            show_progress=True,
        )

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
        safe_wire(
            components["select_all_btn"],
            "click",
            select_all_prompts,
            inputs=[components["ops_prompts_table"]],
            outputs=[
                components.get("ops_prompts_table"),
                components.get("selection_count"),
            ],
        )

    if "clear_selection_btn" in components and "ops_prompts_table" in components:
        safe_wire(
            components["clear_selection_btn"],
            "click",
            clear_selection,
            inputs=[components["ops_prompts_table"]],
            outputs=[
                components.get("ops_prompts_table"),
                components.get("selection_count"),
            ],
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
        # Debug: Check which components exist
        outputs_list = [
            components.get("ops_prompts_table"),
            components.get("prompts_table"),
            components.get("prompts_delete_dialog"),
            components.get("selection_count"),
        ]
        logger.debug(
            f"confirm_delete_prompts outputs before filtering: {[c is not None for c in outputs_list]}"
        )
        filtered_outputs = [o for o in outputs_list if o is not None]
        logger.debug(
            f"confirm_delete_prompts outputs after filtering: {len(filtered_outputs)} components"
        )
        # Since prompts_table doesn't exist, we need to adjust the outputs
        # The function returns 3 values but only 2 components exist: ops_prompts_table and prompts_delete_dialog
        # So we need to remove the middle return value
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

    # Ops prompts table selection
    if "ops_prompts_table" in components:
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
