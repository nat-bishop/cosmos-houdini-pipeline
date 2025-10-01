"""Event wiring modules for Gradio components.

This package contains modular event wiring for different UI tabs,
extracted from the monolithic builder.py to improve maintainability.
"""

from .inputs import wire_inputs_events
from .jobs import wire_jobs_control_events, wire_jobs_events, wire_queue_timers
from .navigation import wire_cross_tab_navigation
from .prompts import wire_prompts_events
from .runs import wire_runs_events

__all__ = [
    "wire_cross_tab_navigation",
    "wire_inputs_events",
    "wire_jobs_control_events",
    "wire_jobs_events",
    "wire_prompts_events",
    "wire_queue_timers",
    "wire_runs_events",
]
