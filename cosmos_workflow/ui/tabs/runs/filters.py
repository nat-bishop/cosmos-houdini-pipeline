"""Filtering logic for runs data.

This module contains functions for filtering runs based on various criteria
including date ranges, model types, search text, and ratings.
"""

from datetime import datetime, timedelta, timezone

from cosmos_workflow.utils.logging import logger


def apply_date_filter(runs: list, date_filter: str) -> list:
    """Apply date filter to runs list.

    Args:
        runs: List of run dictionaries
        date_filter: Date filter type (today, yesterday, last_7_days, last_30_days, all)

    Returns:
        Filtered list of runs
    """
    now = datetime.now(timezone.utc)
    filtered_runs = []

    for run in runs:
        # Parse run creation date
        try:
            created_str = run.get("created_at", "")
            if created_str:
                # Handle both timezone-aware and naive dates
                if "Z" in created_str or "+" in created_str or "-" in created_str[-6:]:
                    created = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                else:
                    created = datetime.fromisoformat(created_str).replace(tzinfo=timezone.utc)
            else:
                created = now
        except (ValueError, TypeError) as e:
            logger.debug("Failed to parse created_at timestamp: %s", e)
            created = now

        # Apply date filter
        date_match = False
        if date_filter == "today":
            date_match = created.date() == now.date()
        elif date_filter == "yesterday":
            yesterday = now - timedelta(days=1)
            date_match = created.date() == yesterday.date()
        elif date_filter == "last_7_days":
            seven_days_ago = now - timedelta(days=7)
            date_match = created >= seven_days_ago
        elif date_filter == "last_30_days":
            thirty_days_ago = now - timedelta(days=30)
            date_match = created >= thirty_days_ago
        else:  # all
            date_match = True

        if date_match:
            filtered_runs.append(run)

    return filtered_runs


def apply_run_filters(
    runs: list, type_filter: str, search_text: str, rating_filter: str | None = None
) -> list:
    """Apply type, search, and rating filters to runs.

    Args:
        runs: List of run dictionaries
        type_filter: Model type filter
        search_text: Text to search in run ID and prompt text
        rating_filter: Rating filter (unrated, 5, 4+, 3+, etc.)

    Returns:
        Filtered list of runs
    """
    filtered_runs = runs.copy()

    # Apply type filter
    if type_filter != "all":
        filtered_runs = [
            run for run in filtered_runs if run.get("model_type", "transfer") == type_filter
        ]

    # Apply text search
    if search_text:
        search_lower = search_text.lower()
        filtered_runs = [
            run
            for run in filtered_runs
            if search_lower in run.get("id", "").lower()
            or search_lower in run.get("prompt_text", "").lower()
        ]

    # Apply rating filter
    if rating_filter and rating_filter != "all":
        if rating_filter == "unrated":
            filtered_runs = [run for run in filtered_runs if not run.get("rating")]
        elif rating_filter == "5":
            filtered_runs = [run for run in filtered_runs if run.get("rating") == 5]
        elif isinstance(rating_filter, str) and rating_filter.endswith("+"):
            min_rating = int(rating_filter[0])
            filtered_runs = [
                run
                for run in filtered_runs
                if run.get("rating") and run.get("rating") >= min_rating
            ]

    return filtered_runs


# Maintain backward compatibility with underscore-prefixed names
_apply_date_filter = apply_date_filter
_apply_run_filters = apply_run_filters

__all__ = [
    "apply_date_filter",
    "apply_run_filters",
]
