"""Tab navigation and cross-tab communication handlers for runs.

This module handles navigation to the runs tab from other tabs,
including filtering and state management.
"""

import gradio as gr

from cosmos_workflow.ui.tabs.runs.data_loading import (
    load_runs_data,
    load_runs_for_multiple_prompts,
)
from cosmos_workflow.utils.logging import logger


def handle_runs_tab_with_pending_data(pending_data):
    """Handle Runs tab with pending navigation data.

    Args:
        pending_data: Dictionary with gallery, table, stats, and prompt_names

    Returns:
        Tuple of updates for runs components
    """
    logger.info("Using pending navigation data for Runs tab")

    gallery_data = pending_data.get("gallery", [])
    table_data = pending_data.get("table", [])
    stats = pending_data.get("stats", "No data")
    prompt_names = pending_data.get("prompt_names", [])

    # Format prompt filter display
    filter_display = ""
    if prompt_names:
        filter_display = f"**Filtering by {len(prompt_names)} prompt(s):**\n"
        display_names = [f"• {name}" for name in prompt_names[:3]]
        filter_display += "\n".join(display_names)
        if len(prompt_names) > 3:
            filter_display += f"\n• ... and {len(prompt_names) - 3} more"

    return (
        gallery_data,
        table_data,
        stats,
        gr.update(visible=bool(prompt_names)),
        gr.update(value=filter_display),
        gr.update(),
        gr.update(),
        gr.update(),
    )


def handle_runs_tab_with_filter(nav_state):
    """Handle Runs tab with prompt filter.

    Args:
        nav_state: Navigation state dictionary with filter_type and filter_values

    Returns:
        Tuple of updates for runs components
    """
    prompt_ids = nav_state.get("filter_values", [])
    logger.info("Switching to Runs tab with filter for prompts: {}", prompt_ids)

    if not prompt_ids:
        return (gr.update(),) * 8

    gallery_data, table_data, stats, prompt_names = load_runs_for_multiple_prompts(
        prompt_ids, "all", "all", "all", "", 50
    )

    # Ensure table_data is properly formatted
    if table_data is None:
        table_data = []
    elif isinstance(table_data, dict):
        table_data = table_data.get("data", [])

    logger.info("Loaded {} runs for filtered prompts", len(table_data) if table_data else 0)

    # Format prompt filter display
    filter_display = ""
    if prompt_names:
        filter_display = f"**Filtering by {len(prompt_names)} prompt(s):**\n"
        display_names = [f"• {name}" for name in prompt_names[:3]]
        filter_display += "\n".join(display_names)
        if len(prompt_names) > 3:
            filter_display += f"\n• ... and {len(prompt_names) - 3} more"

    return (
        gallery_data if gallery_data else [],
        table_data,
        stats if stats else "No data",
        gr.update(visible=True),
        gr.update(value=filter_display),
        gr.update(),
        gr.update(),
        gr.update(),
    )


def handle_runs_tab_default():
    """Handle Runs tab without filter - load default data.

    Returns:
        Tuple of updates for runs components
    """
    logger.info("Switching to Runs tab without filter - loading default data")

    gallery_data, table_data, stats = load_runs_data("all", "all", "all", "", 50, "all")

    if table_data is None:
        table_data = []
    elif isinstance(table_data, dict):
        table_data = table_data.get("data", [])

    return (
        gallery_data if gallery_data else [],
        table_data,
        stats if stats else "No data",
        gr.update(visible=False),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
    )
