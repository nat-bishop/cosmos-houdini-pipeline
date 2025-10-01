"""Unified data loading and filtering logic for runs.

This module eliminates code duplication by providing a single, configurable
loader for all run data fetching scenarios.
"""

from typing import Any

import gradio as gr

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.ui.tabs.runs.display_builders import (
    build_gallery_data,
    build_runs_table_data,
    calculate_runs_statistics,
)
from cosmos_workflow.ui.tabs.runs.filters import apply_date_filter, apply_run_filters
from cosmos_workflow.utils.logging import logger


class RunFilters:
    """Encapsulates all filtering parameters for run queries."""

    def __init__(
        self,
        status_filter: str = "all",
        date_filter: str = "all",
        type_filter: str = "all",
        search_text: str = "",
        limit: int = 50,
        rating_filter: str | None = None,
        version_filter: str | None = None,
        prompt_ids: list[str] | None = None,
    ):
        self.status_filter = status_filter
        self.date_filter = date_filter
        self.type_filter = type_filter
        self.search_text = search_text
        self.limit = limit
        self.rating_filter = rating_filter
        self.version_filter = version_filter
        self.prompt_ids = prompt_ids


class RunsLoader:
    """Unified loader for all run data fetching scenarios.

    This class eliminates code duplication between the three load_runs_* functions
    by providing a single, configurable implementation.
    """

    def __init__(self):
        self.api = CosmosAPI()
        self.max_search_limit = 500

    def load_runs(self, filters: RunFilters) -> tuple[list, list, str]:
        """Load runs with the given filters.

        This is the single implementation that replaces all three load_runs_* functions.

        Args:
            filters: RunFilters object containing all filter parameters

        Returns:
            Tuple of (gallery_data, table_data, stats_text)
        """
        try:
            # Validate API
            if not self.api:
                logger.warning("CosmosAPI not initialized")
                return [], [], "No data available"

            # Fetch runs based on filter configuration
            all_runs = self._fetch_runs(filters)

            # Enrich runs with additional data
            self._enrich_runs(all_runs)

            # Apply filtering
            filtered_runs = self._apply_filters(all_runs, filters)

            # Store total count before limiting display
            total_filtered = len(filtered_runs)

            # Limit to display size
            display_limit = int(filters.limit)
            filtered_runs = filtered_runs[:display_limit]

            # Build output data
            gallery_data = build_gallery_data(filtered_runs, limit=50)
            table_data = build_runs_table_data(filtered_runs)
            stats = calculate_runs_statistics(filtered_runs, total_filtered)

            logger.info(
                "Runs data loaded: {} total, {} shown, {} gallery items",
                total_filtered,
                len(filtered_runs),
                len(gallery_data),
            )

            return gallery_data, table_data, stats

        except Exception as e:
            logger.error("Error loading runs data: {}", e, exc_info=True)
            return [], [], "Error loading data"

    def load_runs_with_prompt_names(self, filters: RunFilters) -> tuple[list, list, str, list]:
        """Load runs with prompt names (for multi-prompt filtering).

        Args:
            filters: RunFilters object with prompt_ids set

        Returns:
            Tuple of (gallery_data, table_data, stats_text, prompt_names)
        """
        if not filters.prompt_ids:
            logger.info("No prompt IDs provided for filtering - returning empty results")
            return [], [], "No prompts selected for filtering", []

        # Get prompt names
        prompt_names = self._get_prompt_names(filters.prompt_ids[:20])  # Cap at 20

        # Load runs using standard method
        gallery_data, table_data, stats = self.load_runs(filters)

        return gallery_data, table_data, stats, prompt_names

    def _fetch_runs(self, filters: RunFilters) -> list[dict[str, Any]]:
        """Fetch runs from the API based on filter configuration."""
        if filters.prompt_ids:
            # Fetch runs for specific prompts
            return self._fetch_runs_for_prompts(filters.prompt_ids)
        else:
            # Standard fetch with optional version filter
            status = None if filters.status_filter == "all" else filters.status_filter
            return self.api.list_runs(
                status=status,
                limit=self.max_search_limit,
                version_filter=filters.version_filter,
            )

    def _fetch_runs_for_prompts(self, prompt_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch runs for specific prompt IDs."""
        all_runs = []
        # Cap at 20 prompts for performance
        for prompt_id in prompt_ids[:20]:
            try:
                runs = self.api.list_runs(prompt_id=prompt_id)
                if runs:
                    all_runs.extend(runs)
            except Exception as e:
                logger.warning("Failed to get runs for prompt {}: {}", prompt_id, e)
        return all_runs

    def _enrich_runs(self, runs: list[dict[str, Any]]) -> None:
        """Enrich runs with additional data like prompt text."""
        for run in runs:
            # Add prompt text if missing
            if not run.get("prompt_text") and run.get("prompt_id"):
                prompt = self.api.get_prompt(run["prompt_id"])
                if prompt:
                    run["prompt_text"] = prompt.get("prompt_text", "")

            # Check for upscaled versions of transfer runs
            if run.get("model_type") == "transfer":
                # Get upscaled run using the dedicated method
                upscaled_run = self.api.get_upscaled_run(run["id"])
                if upscaled_run:
                    run["has_upscaled"] = True
                    run["upscaled_run"] = upscaled_run

    def _apply_filters(
        self, runs: list[dict[str, Any]], filters: RunFilters
    ) -> list[dict[str, Any]]:
        """Apply all filters to the runs list."""
        filtered = apply_date_filter(runs, filters.date_filter)
        filtered = apply_run_filters(
            filtered, filters.type_filter, filters.search_text, filters.rating_filter
        )
        return filtered

    def _get_prompt_names(self, prompt_ids: list[str]) -> list[str]:
        """Get prompt names for the given IDs."""
        prompt_names = []
        for prompt_id in prompt_ids:
            prompt = self.api.get_prompt(prompt_id)
            if prompt:
                name = prompt.get("prompt_text", "")[:50]
                if name:
                    prompt_names.append(f"{name}... ({prompt_id[:8]})")
                else:
                    prompt_names.append(prompt_id[:16])
        return prompt_names


# Main function for loading runs with all filters
def load_runs_data(
    status_filter="all",
    date_filter="all",
    type_filter="all",
    search_text="",
    limit=50,
    rating_filter=None,
):
    """Load runs data for table with filtering and populate video grid.

    Args:
        status_filter: Filter by run status
        date_filter: Filter by date range
        type_filter: Filter by run type
        search_text: Search text for filtering
        limit: Maximum number of runs to display
        rating_filter: Filter by rating

    Returns:
        Tuple of (gallery_data, table_data, stats_text)
    """
    loader = RunsLoader()
    filters = RunFilters(
        status_filter=status_filter,
        date_filter=date_filter,
        type_filter=type_filter,
        search_text=search_text,
        limit=limit,
        rating_filter=rating_filter,
    )
    return loader.load_runs(filters)


def load_runs_for_multiple_prompts(
    prompt_ids,
    status_filter="all",
    date_filter="all",
    type_filter="all",
    search_text="",
    limit="50",
    rating_filter=None,
):
    """Load runs data for multiple prompt IDs.

    Args:
        prompt_ids: List of prompt IDs to filter by
        status_filter: Filter by run status
        date_filter: Filter by date range
        type_filter: Filter by run type
        search_text: Search text for filtering
        limit: Maximum number of runs to display
        rating_filter: Filter by rating

    Returns:
        Tuple of (gallery_data, table_data, stats_text, prompt_names)
    """
    loader = RunsLoader()
    filters = RunFilters(
        status_filter=status_filter,
        date_filter=date_filter,
        type_filter=type_filter,
        search_text=search_text,
        limit=limit,
        rating_filter=rating_filter,
        prompt_ids=prompt_ids,
    )
    return loader.load_runs_with_prompt_names(filters)


def load_runs_with_filters(
    status_filter,
    date_filter,
    type_filter,
    search_text,
    limit,
    rating_filter,
    version_filter,
    nav_state,
):
    """Load runs data with all filters, including persistent prompt filter from navigation state.

    This is the main entry point for loading runs with full filter support including
    navigation state for cross-tab filtering.

    Args:
        status_filter: Filter by run status
        date_filter: Filter by date range
        type_filter: Filter by run type
        search_text: Search text for filtering
        limit: Maximum number of runs to display
        rating_filter: Filter by rating
        version_filter: Filter by version (all/not upscaled/upscaled)
        nav_state: Navigation state containing cross-tab filter info

    Returns:
        Tuple of (gallery, table, stats, nav_state, filter_row_visibility, filter_text)
    """
    # Check if we have active prompt filtering from navigation
    if (
        nav_state
        and nav_state.get("filter_type") in ["prompt_ids", "input"]
        and nav_state.get("filter_values")
    ):
        prompt_ids = nav_state.get("filter_values", [])
        filter_type = nav_state.get("filter_type")
        logger.info("Loading runs with {} filter for {} prompts", filter_type, len(prompt_ids))

        # Load with prompt filter
        gallery, table, stats, prompt_names = load_runs_for_multiple_prompts(
            prompt_ids,
            status_filter,
            date_filter,
            type_filter,
            search_text,
            limit,
            rating_filter,
        )

        # Format filter display based on type
        filter_display = ""
        if filter_type == "input" and nav_state.get("source_tab") == "inputs":
            # For input-based filtering, show the input context
            filter_display = "**Filtering by input directory**\n"
            filter_display += f"Found {len(prompt_names)} prompt(s) using this input\n"
        elif prompt_names:
            filter_display = f"**Filtering by {len(prompt_names)} prompt(s):**\n"

        # Add prompt names
        if prompt_names:
            for name in prompt_names[:3]:
                filter_display += f"• {name}\n"
            if len(prompt_names) > 3:
                filter_display += f"• ... and {len(prompt_names) - 3} more"

        return (
            gallery,
            table,
            stats,
            nav_state,  # Keep navigation state unchanged
            gr.update(visible=True),  # Show filter indicator
            gr.update(value=filter_display),  # Update filter text
        )
    else:
        # No navigation filtering, use regular loader
        logger.info("Loading runs with standard filters")
        loader = RunsLoader()
        filters = RunFilters(
            status_filter=status_filter,
            date_filter=date_filter,
            type_filter=type_filter,
            search_text=search_text,
            limit=limit,
            rating_filter=rating_filter,
            version_filter=version_filter,
        )
        gallery, table, stats = loader.load_runs(filters)

        return (
            gallery,
            table,
            stats,
            nav_state,  # Keep navigation state unchanged
            gr.update(visible=False),  # Hide filter indicator
            gr.update(value=""),  # Clear filter text
        )
