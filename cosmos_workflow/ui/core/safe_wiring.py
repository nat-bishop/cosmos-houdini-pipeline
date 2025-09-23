"""Safe event wiring utilities for Gradio components.

This module provides utilities to safely wire events to components,
handling missing components and None values gracefully.
"""

from collections.abc import Callable
from typing import Any

from cosmos_workflow.utils.logging import logger


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
