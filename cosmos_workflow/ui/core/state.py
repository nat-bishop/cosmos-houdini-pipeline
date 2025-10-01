"""State management for Gradio UI.

This module defines and initializes all shared state components used across
the UI tabs for navigation, filtering, and cross-tab communication.
"""

import gradio as gr


def create_ui_states():
    """Create and return all UI state components.

    Returns:
        dict: Dictionary of state components with descriptive keys
    """
    states = {}

    # Cross-tab navigation and filtering state
    states["navigation_state"] = gr.State(
        value={
            "filter_type": None,  # "prompt_ids" or None
            "filter_values": [],  # List of IDs being filtered
            "source_tab": None,  # Where navigation originated from
        }
    )

    # Store selected prompt IDs (avoids dataframe preprocessing issues)
    states["selected_prompt_ids_state"] = gr.State(value=[])

    # Hold pending navigation data (prevents race condition)
    states["pending_nav_data"] = gr.State(value=None)

    # Track last selected run ID to avoid unnecessary scrolling
    states["last_selected_run_id"] = gr.State(value=None)

    return states


def get_initial_navigation_state():
    """Get the initial navigation state structure.

    Returns:
        dict: Initial navigation state
    """
    return {
        "filter_type": None,
        "filter_values": [],
        "source_tab": None,
    }


def update_navigation_state(current_state, filter_type=None, filter_values=None, source_tab=None):
    """Update navigation state with new values.

    Args:
        current_state: Current navigation state dict
        filter_type: Type of filter ("prompt_ids" or None)
        filter_values: List of filter values
        source_tab: Source tab name

    Returns:
        dict: Updated navigation state
    """
    if current_state is None:
        current_state = get_initial_navigation_state()

    new_state = current_state.copy()

    if filter_type is not None:
        new_state["filter_type"] = filter_type
    if filter_values is not None:
        new_state["filter_values"] = filter_values
    if source_tab is not None:
        new_state["source_tab"] = source_tab

    return new_state


def clear_navigation_state():
    """Clear/reset the navigation state.

    Returns:
        dict: Empty navigation state
    """
    return get_initial_navigation_state()
