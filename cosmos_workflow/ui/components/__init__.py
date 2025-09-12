"""UI components for Cosmos Workflow Manager."""

from .global_controls import create_global_controls
from .history_tab import create_history_tab
from .inputs_tab import create_inputs_tab
from .jobs_tab import create_jobs_tab
from .outputs_tab import create_outputs_tab
from .prompts_tab import create_prompts_tab

__all__ = [
    "create_global_controls",
    "create_history_tab",
    "create_inputs_tab",
    "create_jobs_tab",
    "create_outputs_tab",
    "create_prompts_tab",
]
