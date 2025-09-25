"""UI builder and event wiring orchestrator for the Gradio application.

This module coordinates the building of UI components and wiring of events
by delegating to specialized modules for each tab.
"""

from typing import Any

import gradio as gr

from cosmos_workflow.ui.core.state import create_ui_states
from cosmos_workflow.ui.core.wiring import (
    wire_cross_tab_navigation,
    wire_inputs_events,
    wire_jobs_events,
    wire_prompts_events,
    wire_runs_events,
)
from cosmos_workflow.ui.styles_simple import get_custom_css
from cosmos_workflow.ui.tabs.inputs_ui import create_inputs_tab_ui
from cosmos_workflow.ui.tabs.jobs_ui import create_jobs_tab_ui
from cosmos_workflow.ui.tabs.prompts_ui import create_prompts_tab_ui
from cosmos_workflow.ui.tabs.runs_ui import create_runs_tab_ui
from cosmos_workflow.utils.logging import logger


def build_ui_components(config: Any) -> tuple[gr.Blocks, dict[str, Any]]:
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


def wire_header_events(components: dict[str, Any], api: Any, config: Any) -> None:
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

            # Refresh runs
            from cosmos_workflow.ui.tabs.runs.data_loading import load_runs_data

            gallery_data, table_data, stats = load_runs_data()

            return (
                gr.update(value="**Status:** ✅ Data refreshed"),
                prompts_data,  # Using load_ops_prompts which returns the right format
                gallery_data,
                table_data,
                stats,
            )
        except Exception as e:
            logger.error("Error refreshing data - Type: %s, Message: %s", type(e).__name__, str(e))
            return (
                gr.update(value=f"**Status:** ❌ Error refreshing: {e!s}"),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
            )

    if "manual_refresh" in components:
        # Updated to use ops_prompts_table
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


def wire_all_events(
    app: gr.Blocks, components: dict[str, Any], config: Any, api: Any, simple_queue_service: Any
) -> None:
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
    wire_header_events(components, api, config)
    wire_inputs_events(components, config, api)
    wire_prompts_events(components, api, simple_queue_service)
    wire_runs_events(components, api)
    wire_jobs_events(components, api, simple_queue_service)

    # Wire cross-tab navigation events
    wire_cross_tab_navigation(components)

    # Load initial data
    wire_initial_data_load(app, components, config, api, simple_queue_service)

    logger.info(
        "All events wired successfully - Components: %d, Config: %s",
        len(components),
        type(config).__name__,
    )


def wire_initial_data_load(
    app: gr.Blocks, components: dict[str, Any], config: Any, api: Any, simple_queue_service: Any
) -> None:
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
        if "ops_limit" in components:
            # Also initialize the selection count and state on load
            outputs = [components["ops_prompts_table"]]
            if "selection_count" in components:
                outputs.append(components["selection_count"])
            if "selected_prompt_ids_state" in components:
                outputs.append(components["selected_prompt_ids_state"])

            def load_initial_prompts_with_state(limit, search, enhanced, runs, date):
                """Load prompts and initialize selection state."""
                table_data = load_ops_prompts(limit, search, enhanced, runs, date)
                # Initialize with empty selection
                if len(outputs) == 3:
                    return table_data, "No Prompts Selected", []
                elif len(outputs) == 2:
                    return table_data, "No Prompts Selected"
                else:
                    return table_data

            # Wire the initial load to use the actual limit component's default value
            app.load(
                fn=load_initial_prompts_with_state,
                inputs=[
                    components.get("ops_limit", gr.Number(value=50, visible=False)),
                    components.get("prompts_search", gr.Textbox(value="", visible=False)),
                    components.get(
                        "prompts_enhanced_filter", gr.Dropdown(value="all", visible=False)
                    ),
                    components.get("prompts_runs_filter", gr.Dropdown(value="all", visible=False)),
                    components.get("prompts_date_filter", gr.Dropdown(value="all", visible=False)),
                ],
                outputs=outputs,
            )
        else:
            # Fallback if components don't exist
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
    if all(k in components for k in ["runs_gallery", "runs_table", "runs_stats"]):
        app.load(
            fn=load_runs_data,
            outputs=[
                components["runs_gallery"],
                components["runs_table"],
                components["runs_stats"],
            ],
        )

    # Load initial data for jobs/queue tab
    if "queue_table" in components:
        queue_handlers = QueueHandlers(simple_queue_service)

        app.load(
            fn=queue_handlers.get_queue_display,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    initialized_count = sum(
        1
        for k in ["input_gallery", "ops_prompts_table", "runs_gallery", "queue_table"]
        if k in components
    )
    logger.info(
        "Initial data loading configured - %d components initialized",
        initialized_count,
    )
