"""Tab navigation logic for the Gradio UI.

This module handles tab switching, cross-tab navigation, and filter application
when moving between different UI tabs.
"""

import gradio as gr

from cosmos_workflow.ui.constants import TabIndex
from cosmos_workflow.ui.tabs.jobs_handlers import check_running_jobs
from cosmos_workflow.ui.tabs.runs.navigation import (
    handle_runs_tab_default,
    handle_runs_tab_with_filter,
    handle_runs_tab_with_pending_data,
)
from cosmos_workflow.utils.logging import logger


def handle_jobs_tab_refresh():
    """Handle Jobs tab refresh when switching to it.

    Returns:
        tuple: Updates for all components
    """
    logger.info("Switching to Jobs tab - refreshing status")
    jobs_result = check_running_jobs()

    if "Ready to stream" in jobs_result[1]:
        logger.info("Active container detected - starting log stream")

    return (
        gr.update(),  # runs_gallery - no update
        gr.update(),  # runs_table - no update
        gr.update(),  # runs_stats - no update
        gr.update(),  # runs_nav_filter_row - no update
        gr.update(),  # runs_prompt_filter - no update
        jobs_result[0],  # Update container details
        jobs_result[1],  # Update job status
        jobs_result[2],  # Update active job card
    )


def handle_tab_select(tab_index, nav_state, pending_data):
    """Handle tab selection and apply navigation filters.

    This is the main navigation orchestrator that routes tab switches
    and manages cross-tab data flow.

    Args:
        tab_index: Index of selected tab (TabIndex enum value)
        nav_state: Navigation state dict with filter info
        pending_data: Pending navigation data from cross-tab actions

    Returns:
        tuple: (nav_state, pending_data, ...component updates)
    """
    logger.info(
        "handle_tab_select called: tab={}, nav_state={}, has_pending={}",
        tab_index,
        nav_state,
        pending_data is not None,
    )

    # Auto-refresh Jobs tab when switching to it
    if tab_index == TabIndex.JOBS:
        updates = handle_jobs_tab_refresh()
        return (nav_state, pending_data, *updates)

    # Check if there's pending navigation data (from View Runs button)
    if tab_index == TabIndex.RUNS and pending_data is not None:
        updates = handle_runs_tab_with_pending_data(pending_data)
        return (nav_state, None, *updates)

    # Check if we're navigating to Runs tab with pending filter
    elif tab_index == TabIndex.RUNS and nav_state and nav_state.get("filter_type") == "prompt_ids":
        updates = handle_runs_tab_with_filter(nav_state)
        return (nav_state, None, *updates)

    # Check if we're navigating to Runs tab without filter - load default data
    elif tab_index == TabIndex.RUNS and (not nav_state or nav_state.get("filter_type") is None):
        updates = handle_runs_tab_default()
        final_nav_state = (
            nav_state
            if nav_state
            else {
                "filter_type": None,
                "filter_values": [],
                "source_tab": None,
            }
        )
        return (final_nav_state, None, *updates)

    # No navigation action needed for other tabs
    return (
        nav_state,  # Keep current navigation state
        None,  # Clear pending data
        gr.update(),  # Don't change gallery
        gr.update(),  # Don't change table
        gr.update(),  # Don't change stats
        gr.update(),  # Don't change filter indicator
        gr.update(),  # Don't change filter dropdown
        gr.update(),  # Don't change running_jobs_display
        gr.update(),  # Don't change job_status
        gr.update(),  # Don't change active_job_card
    )


def get_tab_index(tab_name: str) -> TabIndex:
    """Convert tab name to TabIndex enum.

    Args:
        tab_name: Name of the tab (case-insensitive)

    Returns:
        TabIndex: Tab index enum value
    """
    try:
        return TabIndex.from_name(tab_name)
    except KeyError:
        logger.warning(f"Unknown tab name: {tab_name}, defaulting to INPUTS")
        return TabIndex.INPUTS


def get_tab_name(tab_index: int | TabIndex) -> str:
    """Convert tab index to name.

    Args:
        tab_index: Index of the tab (int or TabIndex enum)

    Returns:
        str: Tab name with proper capitalization
    """
    if isinstance(tab_index, int):
        # Convert int to TabIndex if valid
        try:
            tab_index = TabIndex(tab_index)
        except ValueError:
            return "Unknown"

    # Return the enum name with proper capitalization
    return tab_index.name.capitalize()
