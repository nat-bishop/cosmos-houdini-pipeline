"""Runs tab functionality split into focused modules.

This package contains:
- data_loading: Unified data loading and filtering logic
- display_handlers: Gallery and table selection handlers
- display_builders: Gallery and table data builders
- filters: Date, type, and rating filters
- run_details: Run details display and information
- model_handlers: Model-specific UI preparation
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
from cosmos_workflow.ui.tabs.runs.display_builders import (
    THUMBNAIL_EXECUTOR,
    build_gallery_data,
    build_runs_table_data,
    calculate_runs_statistics,
)
from cosmos_workflow.ui.tabs.runs.display_handlers import (
    on_runs_gallery_select,
    on_runs_table_select,
    update_runs_selection_info,
)
from cosmos_workflow.ui.tabs.runs.filters import (
    apply_date_filter,
    apply_run_filters,
)
from cosmos_workflow.ui.tabs.runs.model_handlers import (
    prepare_enhance_ui_data,
    prepare_transfer_ui_data,
    prepare_upscale_ui_data,
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
from cosmos_workflow.ui.tabs.runs.run_details import (
    build_input_gallery,
    extract_run_metadata,
    load_spec_and_weights,
    read_log_content,
    resolve_video_paths,
)

__all__ = [
    "THUMBNAIL_EXECUTOR",
    "apply_date_filter",
    "apply_run_filters",
    "build_gallery_data",
    "build_input_gallery",
    "build_runs_table_data",
    "calculate_runs_statistics",
    "cancel_delete_run",
    "cancel_upscale",
    "confirm_delete_run",
    "execute_upscale",
    "extract_run_metadata",
    "handle_runs_tab_default",
    "handle_runs_tab_with_filter",
    "handle_runs_tab_with_pending_data",
    "load_run_logs",
    "load_runs_data",
    "load_runs_data_with_version_filter",
    "load_runs_for_multiple_prompts",
    "load_runs_with_filters",
    "load_spec_and_weights",
    "on_runs_gallery_select",
    "on_runs_table_select",
    "prepare_enhance_ui_data",
    "prepare_transfer_ui_data",
    "prepare_upscale_ui_data",
    "preview_delete_run",
    "read_log_content",
    "resolve_video_paths",
    "show_upscale_dialog",
    "update_runs_selection_info",
]
