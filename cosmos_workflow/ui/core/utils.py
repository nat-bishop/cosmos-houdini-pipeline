"""Utility functions for core UI modules.

This module provides helper functions for safe component handling
in the Gradio UI.
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


def collect_components(components: dict[str, Any], keys: list[str]) -> list[Any]:
    """Collect components by keys, returning only those that exist.

    Args:
        components: Dictionary of UI components
        keys: List of component keys

    Returns:
        List of existing components (non-None)
    """
    return [components[k] for k in keys if k in components and components[k] is not None]
