"""UI Constants and Configuration.

Central location for UI constants to eliminate magic numbers
and document component relationships. These are structural constants
that define the application, not user-configurable settings.
"""

from enum import IntEnum
from typing import Final


# Tab indices - These are hardcoded in the UI structure and must not change
class TabIndex(IntEnum):
    """Tab indices for navigation using IntEnum for type safety.

    These indices correspond to the order tabs are created in the UI.
    Changing these values will break tab navigation.
    """

    INPUTS = 0
    PROMPTS = 1
    RUNS = 2
    JOBS = 3

    @classmethod
    def from_name(cls, name: str) -> "TabIndex":
        """Get tab index from tab name string.

        Args:
            name: Tab name (case-insensitive)

        Returns:
            TabIndex enum value

        Raises:
            KeyError: If name doesn't match any tab
        """
        return cls[name.upper()]


# Document fragile positional returns that frequently cause bugs
# These map the order of gr.update() returns to their component names
OUTPUT_POSITIONS: Final[dict[str, list[int] | dict[str, int]]] = {
    # Prompt deletion - adjusted after prompts_table was removed
    "prompt_delete": {
        "ops_table": 0,
        "dialog": 1,  # Now at position 1 instead of 2
        # prompts_table was removed, causing mismatch bugs
    },
    # Run deletion dialog
    "run_delete": {"dialog": 0, "selected_id": 1, "status_message": 2},
    # The infamous 43-field run selection return
    # This is why we needed NamedTuple in Phase 1
    "run_select": list(range(43)),
    # Job control outputs
    "job_kill": {"dialog": 0, "status": 1},
}


# UI Performance defaults - These could be overridden by config.toml
DEFAULT_TIMEOUT_MS: Final[int] = 120000
QUEUE_CHECK_INTERVAL: Final[int] = 2
AUTO_REFRESH_SECONDS: Final[int] = 5
MAX_CONCURRENT_THUMBNAILS: Final[int] = 4

# Display defaults - These could be overridden by config.toml
MAX_GALLERY_ITEMS: Final[int] = 50
MAX_TABLE_ROWS: Final[int] = 100
THUMBNAIL_SIZE: Final[tuple[int, int]] = (384, 216)
THUMBNAIL_QUALITY: Final[int] = 85

# Component group names for related UI elements
# Useful for debugging when components are missing
COMPONENT_GROUPS: Final[dict[str, list[str]]] = {
    "prompt_management": [
        "create_prompt_btn",
        "delete_prompt_btn",
        "prompts_table",
        "ops_prompts_table",
    ],
    "run_actions": ["delete_run_btn", "upscale_btn", "transfer_btn", "enhance_btn"],
    "job_control": ["kill_job_btn", "cancel_job_btn", "queue_table", "active_job_display"],
    "navigation": ["tabs", "selected_tab", "status_display"],
}
