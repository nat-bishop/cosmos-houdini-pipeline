"""Safe event wiring utilities for Gradio components.

This module provides utilities to safely wire events to components,
handling missing components and None values gracefully.
"""

from collections.abc import Callable
from typing import Any

from cosmos_workflow.utils.logging import logger


def safe_wire(
    component: Any,
    event: str,
    handler: Callable,
    inputs: list[Any] | Any | None = None,
    outputs: list[Any] | Any | None = None,
    **kwargs,
) -> Any | None:
    """Universal safe event wiring - replaces filter_none_components pattern.

    This is the primary function to use for all event wiring. It handles:
    - Missing components gracefully (returns None)
    - Automatic filtering of None values from lists
    - Any Gradio event type (click, change, select, submit, etc.)
    - Error handling with logging

    Args:
        component: Gradio component or None
        event: Event name (click, change, select, submit, blur, etc.)
        handler: Event handler function
        inputs: Input components (auto-filtered for None)
        outputs: Output components (auto-filtered for None)
        **kwargs: Additional event arguments (scroll_to_output, etc.)

    Returns:
        Event object if successful, None if component missing

    Example:
        # Instead of:
        component.click(
            fn=handler,
            inputs=filter_none_components([text, None, slider]),
            outputs=filter_none_components([display])
        )

        # Use:
        safe_wire(component, "click", handler,
                 inputs=[text, None, slider],
                 outputs=[display])
    """
    if component is None:
        # Silently skip - this is expected for optional components
        return None

    # Auto-filter None values from inputs
    if inputs is not None:
        if isinstance(inputs, list):
            inputs = [i for i in inputs if i is not None]
            # If all inputs were None, set to None (not empty list)
            if not inputs:
                inputs = None
        elif inputs is None:
            # Single None input
            inputs = None

    # Auto-filter None values from outputs
    if outputs is not None:
        if isinstance(outputs, list):
            outputs = [o for o in outputs if o is not None]
            # If all outputs were None, set to None (not empty list)
            if not outputs:
                outputs = None
        elif outputs is None:
            # Single None output
            outputs = None

    # Get the event method dynamically
    event_method = getattr(component, event, None)
    if event_method is None:
        logger.warning(f"Component has no '{event}' event method")
        return None

    try:
        # Call the event method with filtered inputs/outputs
        return event_method(fn=handler, inputs=inputs, outputs=outputs, **kwargs)
    except Exception as e:
        logger.error(f"Error wiring {event} event: {e}")
        return None


# Legacy functions - kept for backward compatibility but should migrate to safe_wire()
def safe_click(
    components: dict[str, Any],
    component_name: str,
    fn: Callable,
    inputs: list | Any | None = None,
    outputs: list | Any | None = None,
    **kwargs,
) -> Any | None:
    """Safely wire a click event to a component.

    Args:
        components: Dictionary of UI components
        component_name: Name of the component
        fn: Function to call on click
        inputs: Input components (can be list or single)
        outputs: Output components (can be list or single)
        **kwargs: Additional arguments for click()

    Returns:
        Event object if successful, None otherwise
    """
    if component_name not in components:
        logger.debug(f"Component '{component_name}' not found, skipping click event")
        return None

    component = components[component_name]
    if component is None:
        logger.debug(f"Component '{component_name}' is None, skipping click event")
        return None

    # Process inputs
    if inputs is not None:
        if isinstance(inputs, list):
            inputs = [components.get(i) if isinstance(i, str) else i for i in inputs]
            inputs = [i for i in inputs if i is not None]
            if not inputs:
                inputs = None
        elif isinstance(inputs, str):
            inputs = components.get(inputs)

    # Process outputs
    if outputs is not None:
        if isinstance(outputs, list):
            outputs = [components.get(o) if isinstance(o, str) else o for o in outputs]
            outputs = [o for o in outputs if o is not None]
            if not outputs:
                outputs = None
        elif isinstance(outputs, str):
            outputs = components.get(outputs)

    try:
        return component.click(fn=fn, inputs=inputs, outputs=outputs, **kwargs)
    except Exception as e:
        logger.error(f"Error wiring click event for {component_name}: {e}")
        return None


def safe_change(
    components: dict[str, Any],
    component_name: str,
    fn: Callable,
    inputs: list | Any | None = None,
    outputs: list | Any | None = None,
    **kwargs,
) -> Any | None:
    """Safely wire a change event to a component."""
    if component_name not in components:
        logger.debug(f"Component '{component_name}' not found, skipping change event")
        return None

    component = components[component_name]
    if component is None:
        return None

    # Process inputs and outputs same as click
    if inputs is not None:
        if isinstance(inputs, list):
            inputs = [components.get(i) if isinstance(i, str) else i for i in inputs]
            inputs = [i for i in inputs if i is not None]
        elif isinstance(inputs, str):
            inputs = components.get(inputs)

    if outputs is not None:
        if isinstance(outputs, list):
            outputs = [components.get(o) if isinstance(o, str) else o for o in outputs]
            outputs = [o for o in outputs if o is not None]
        elif isinstance(outputs, str):
            outputs = components.get(outputs)

    try:
        return component.change(fn=fn, inputs=inputs, outputs=outputs, **kwargs)
    except Exception as e:
        logger.error(f"Error wiring change event for {component_name}: {e}")
        return None


def safe_select(
    components: dict[str, Any],
    component_name: str,
    fn: Callable,
    inputs: list | Any | None = None,
    outputs: list | Any | None = None,
    **kwargs,
) -> Any | None:
    """Safely wire a select event to a component."""
    if component_name not in components:
        logger.debug(f"Component '{component_name}' not found, skipping select event")
        return None

    component = components[component_name]
    if component is None:
        return None

    # Process inputs and outputs
    if inputs is not None:
        if isinstance(inputs, list):
            inputs = [components.get(i) if isinstance(i, str) else i for i in inputs]
            inputs = [i for i in inputs if i is not None]
        elif isinstance(inputs, str):
            inputs = components.get(inputs)

    if outputs is not None:
        if isinstance(outputs, list):
            outputs = [components.get(o) if isinstance(o, str) else o for o in outputs]
            outputs = [o for o in outputs if o is not None]
        elif isinstance(outputs, str):
            outputs = components.get(outputs)

    try:
        return component.select(fn=fn, inputs=inputs, outputs=outputs, **kwargs)
    except Exception as e:
        logger.error(f"Error wiring select event for {component_name}: {e}")
        return None


def get_components_safe(components: dict[str, Any], *names: str) -> list[Any]:
    """Safely get multiple components from dictionary.

    Args:
        components: Dictionary of UI components
        *names: Component names to retrieve

    Returns:
        List of components (None values filtered out)
    """
    result = []
    for name in names:
        comp = components.get(name)
        if comp is not None:
            result.append(comp)
    return result if result else None


def wire_event_safe(
    components: dict[str, Any], component_name: str, event_type: str, fn: Callable, **kwargs
):
    """Generic safe event wiring.

    Args:
        components: Component dictionary
        component_name: Name of component
        event_type: Type of event (click, change, select)
        fn: Function to bind
        **kwargs: Event arguments
    """
    if event_type == "click":
        return safe_click(components, component_name, fn, **kwargs)
    elif event_type == "change":
        return safe_change(components, component_name, fn, **kwargs)
    elif event_type == "select":
        return safe_select(components, component_name, fn, **kwargs)
    else:
        logger.warning(f"Unknown event type: {event_type}")
        return None
