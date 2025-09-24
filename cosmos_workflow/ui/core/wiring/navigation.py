"""Cross-tab navigation event wiring."""

from typing import Any

import gradio as gr

from cosmos_workflow.ui.tabs.prompts_handlers import load_ops_prompts
from cosmos_workflow.ui.tabs.runs import load_runs_for_multiple_prompts
from cosmos_workflow.utils.logging import logger


def wire_cross_tab_navigation(components: dict[str, Any]) -> None:
    """Wire cross-tab navigation events.

    Handles navigation between tabs with data filtering and loading.
    """
    # View runs button from prompts tab - this needs the full navigation
    if "view_runs_btn" in components:

        def prepare_runs_navigation(selected_prompt_ids: list[str] | None) -> tuple[Any, ...]:
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

            logger.info(
                "Cross-tab navigation - Target: runs, Filter: prompts, Count: %d",
                len(selected_prompt_ids),
            )

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

        outputs = [
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
        outputs = [o for o in outputs if o is not None]

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

        def navigate_to_runs_for_input(
            selected_dir: str | None, nav_state: Any
        ) -> tuple[Any, Any, dict | None]:
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
                inputs=[
                    components.get("selected_dir_path"),  # Fixed: using correct component name
                    components.get("navigation_state"),
                ],
                outputs=[
                    components.get("tabs"),
                    components.get("navigation_state"),
                    components.get("pending_nav_data"),
                ],
            )

    # Navigate from inputs to prompts
    if "view_prompts_for_input_btn" in components:

        def prepare_prompts_navigation_from_input(
            input_name: str | None,
        ) -> tuple[Any, Any, int]:
            """Navigate to Prompts tab with search filter for input directory."""
            if not input_name:
                return gr.update(), gr.update(), 1

            logger.info(
                "Cross-tab navigation - Target: prompts, Filter: input, Value: %s", input_name
            )

            # Extract just the directory name (remove any path prefixes)
            search_term = input_name.split("/")[-1] if "/" in input_name else input_name
            search_term = search_term.split("\\")[-1] if "\\" in search_term else search_term

            # Load prompts with search filter
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

        outputs = [
            components.get("prompt_search"),
            components.get("ops_prompts_table"),  # Fixed: was "prompts_table"
            components.get("selected_tab"),
        ]
        outputs = [o for o in outputs if o is not None]

        if outputs:
            components["view_prompts_for_input_btn"].click(
                fn=prepare_prompts_navigation_from_input,
                inputs=[components.get("selected_dir_path")],
                outputs=outputs,
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[1]?.click(); }, 100); return []; }",
                queue=False,
            )
