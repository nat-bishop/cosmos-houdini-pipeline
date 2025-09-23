"""Runs tab functionality split into focused modules.

This package contains:
- data_loading: Unified data loading and filtering logic
- display_handlers: Gallery and table selection handlers
- run_details: Run details display and information
- run_actions: Actions like delete, upscale, transfer
- navigation: Tab navigation and cross-tab communication
"""

# Re-export main functions for backward compatibility
from cosmos_workflow.ui.tabs.runs.data_loading import (
    load_runs_data,
    load_runs_data_with_version_filter,
    load_runs_for_multiple_prompts,
    load_runs_with_filters,
)
from cosmos_workflow.ui.tabs.runs.display_handlers import (
    on_runs_gallery_select,
    on_runs_table_select,
    update_runs_selection_info,
)
from cosmos_workflow.ui.tabs.runs.navigation import (
    handle_runs_tab_default,
    handle_runs_tab_with_filter,
    handle_runs_tab_with_pending_data,
)
from cosmos_workflow.ui.tabs.runs.run_actions import (
    cancel_delete_run,
    cancel_upscale,
    confirm_delete_run,
    execute_upscale,
    load_run_logs,
    preview_delete_run,
    show_upscale_dialog,
)

__all__ = [
    "cancel_delete_run",
    "cancel_upscale",
    "confirm_delete_run",
    "execute_upscale",
    "handle_runs_tab_default",
    "handle_runs_tab_with_filter",
    "handle_runs_tab_with_pending_data",
    "load_run_logs",
    "load_runs_data",
    "load_runs_data_with_version_filter",
    "load_runs_for_multiple_prompts",
    "load_runs_with_filters",
    "on_runs_gallery_select",
    "on_runs_table_select",
    "preview_delete_run",
    "show_upscale_dialog",
    "update_runs_selection_info",
]
