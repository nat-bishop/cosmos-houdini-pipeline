"""UI utility modules for Gradio interface.

This package contains utility functions extracted from the main UI code
to reduce duplication and improve maintainability.
"""

# Import all utilities for easy access
from .dataframe import (
    clear_selection,
    count_selected,
    get_cell_value,
    get_row_by_index,
    get_selected_ids,
    get_selected_rows,
    is_dataframe,
    select_all,
    update_selection_status,
)
from .formatting import (
    format_duration,
    format_file_size,
    format_number,
    format_percentage,
    format_run_status,
    format_time_ago,
    format_timestamp,
    truncate_text,
)
from .video import (
    extract_video_metadata,
    generate_thumbnail_fast,
    get_multimodal_inputs,
    get_video_duration_seconds,
    get_video_files,
    validate_video_directory,
)

__all__ = [
    "clear_selection",
    "count_selected",
    # Video utilities
    "extract_video_metadata",
    "format_duration",
    "format_file_size",
    "format_number",
    "format_percentage",
    "format_run_status",
    "format_time_ago",
    # Formatting utilities
    "format_timestamp",
    "generate_thumbnail_fast",
    "get_cell_value",
    "get_multimodal_inputs",
    "get_row_by_index",
    "get_selected_ids",
    "get_selected_rows",
    "get_video_duration_seconds",
    "get_video_files",
    # DataFrame utilities
    "is_dataframe",
    "select_all",
    "truncate_text",
    "update_selection_status",
    "validate_video_directory",
]
