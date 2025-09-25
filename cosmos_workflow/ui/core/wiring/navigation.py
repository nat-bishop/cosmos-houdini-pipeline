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
            selected_dir: str | None,
        ) -> tuple[Any, ...]:
            """Navigate to runs tab for input directory with filtering."""
            if not selected_dir:
                return (
                    {"filter_type": None, "filter_values": [], "source_tab": None},
                    None,
                    "No input directory selected",
                    2,  # Runs tab index
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=False),
                    gr.update(value=""),
                )

            logger.info(
                "Cross-tab navigation - Target: runs, Filter: input, Value: %s",
                selected_dir,
            )

            # Extract just the directory name
            dir_name = selected_dir.split("/")[-1] if "/" in selected_dir else selected_dir
            dir_name = dir_name.split("\\")[-1] if "\\" in dir_name else dir_name

            # Import here to avoid circular dependency
            from cosmos_workflow.api.cosmos_api import CosmosAPI

            # Find prompts that use this input
            api = CosmosAPI()
            prompts = api.list_prompts(limit=100)
            matching_prompt_ids = []
            matching_prompt_names = []

            for prompt in prompts:
                inputs = prompt.get("inputs", {})
                video_path = inputs.get("video", "")
                if dir_name in video_path:
                    matching_prompt_ids.append(prompt.get("id"))
                    matching_prompt_names.append(
                        prompt.get("parameters", {}).get("name", "unnamed")
                    )

            if not matching_prompt_ids:
                return (
                    {"filter_type": None, "filter_values": [], "source_tab": None},
                    None,
                    f"No prompts found using input '{dir_name}'",
                    2,  # Runs tab index
                    gr.update(),
                    gr.update(),
                    gr.update(),
                    gr.update(visible=False),
                    gr.update(value=""),
                )

            # Load filtered runs data
            gallery, table, stats, _ = load_runs_for_multiple_prompts(
                matching_prompt_ids, "all", "all", "all", "", "50", None
            )

            # Format filter display
            filter_display = f"**Filtering by input: {dir_name}**\n"
            filter_display += f"Found {len(matching_prompt_names)} prompt(s) using this input\n"
            for name in matching_prompt_names[:3]:
                filter_display += f"• {name}\n"
            if len(matching_prompt_names) > 3:
                filter_display += f"• ... and {len(matching_prompt_names) - 3} more"

            return (
                {
                    "filter_type": "input",
                    "filter_values": matching_prompt_ids,
                    "source_tab": "inputs",
                },
                None,
                f"Viewing runs for input '{dir_name}'",
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
            components.get("selected_tab"),
            components.get("runs_gallery"),
            components.get("runs_table"),
            components.get("runs_stats"),
            components.get("runs_nav_filter_row"),
            components.get("runs_prompt_filter"),
        ]
        outputs = [o for o in outputs if o is not None]

        if outputs:
            components["view_runs_for_input_btn"].click(
                fn=navigate_to_runs_for_input,
                inputs=[components.get("selected_dir_path")],
                outputs=outputs,
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[2]?.click(); }, 100); return []; }",
                queue=False,
            )

    # Navigate from inputs to prompts
    if "view_prompts_for_input_btn" in components:

        def prepare_prompts_navigation_from_input(
            input_name: str | None,
        ) -> tuple[Any, Any]:
            """Navigate to Prompts tab with search filter for input directory."""
            if not input_name:
                return gr.update(), gr.update()

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
            )

        outputs = [
            components.get("prompts_search"),  # Fixed: was "prompt_search"
            components.get("ops_prompts_table"),
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
