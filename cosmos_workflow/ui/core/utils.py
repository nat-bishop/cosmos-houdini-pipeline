"""Utility functions for core UI modules.

This module provides helper functions for safe component handling
and event wiring in the Gradio UI.
"""

from typing import Any


def safe_get_components(components: dict[str, Any], *keys: str) -> list[Any] | None:
    """Safely get multiple components from dictionary.

    Args:
        components: Dictionary of UI components
        *keys: Component keys to retrieve

    Returns:
        List of components if all exist, None otherwise
    """
    result = []
    for key in keys:
        if key not in components or components[key] is None:
            return None
        result.append(components[key])
    return result


def filter_none_components(component_list: list[Any]) -> list[Any]:
    """Filter out None values from component list.

    Args:
        component_list: List of components that may contain None

    Returns:
        List with None values removed
    """
    return [c for c in component_list if c is not None]


def safe_wire_event(component: Any, event_name: str, fn, inputs=None, outputs=None, **kwargs):
    """Safely wire an event to a component.

    Args:
        component: The Gradio component
        event_name: Name of the event (click, change, select, etc.)
        fn: Function to call
        inputs: Input components (will filter None)
        outputs: Output components (will filter None)
        **kwargs: Additional arguments for the event

    Returns:
        The event object if successful, None otherwise
    """
    if component is None:
        return None

    # Filter None from inputs and outputs
    if inputs is not None:
        inputs = filter_none_components(inputs) if isinstance(inputs, list) else inputs
        if not inputs and isinstance(inputs, list):
            return None

    if outputs is not None:
        outputs = filter_none_components(outputs) if isinstance(outputs, list) else outputs
        if not outputs and isinstance(outputs, list):
            return None

    # Get the event method
    event_method = getattr(component, event_name, None)
    if event_method is None:
        return None

    # Wire the event
    return event_method(fn=fn, inputs=inputs, outputs=outputs, **kwargs)


def collect_components(components: dict[str, Any], keys: list[str]) -> list[Any]:
    """Collect components by keys, returning only those that exist.

    Args:
        components: Dictionary of UI components
        keys: List of component keys

    Returns:
        List of existing components (non-None)
    """
    return [components[k] for k in keys if k in components and components[k] is not None]
