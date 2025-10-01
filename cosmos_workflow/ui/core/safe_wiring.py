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
        logger.warning(
            "Event method not found - Component: %s, Event: %s", type(component).__name__, event
        )
        return None

    try:
        # Call the event method with filtered inputs/outputs
        return event_method(fn=handler, inputs=inputs, outputs=outputs, **kwargs)
    except Exception as e:
        logger.error(
            "Event wiring failed - Event: %s, Handler: %s, Error: %s",
            event,
            handler.__name__ if hasattr(handler, "__name__") else str(handler),
            str(e),
        )
        return None
