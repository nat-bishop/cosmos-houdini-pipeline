"""Unified data loading and filtering logic for runs.

This module eliminates code duplication by providing a single, configurable
loader for all run data fetching scenarios.
"""

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import gradio as gr

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.utils.logging import logger

# Thread pool for parallel thumbnail generation
THUMBNAIL_EXECUTOR = ThreadPoolExecutor(max_workers=4)


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
            gallery_data = _build_gallery_data(filtered_runs, limit=50)
            table_data = _build_runs_table_data(filtered_runs)
            stats = _calculate_runs_statistics(filtered_runs, total_filtered)

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
        filtered = _apply_date_filter(runs, filters.date_filter)
        filtered = _apply_run_filters(
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


# Legacy function signatures for backward compatibility
def load_runs_data(status_filter, date_filter, type_filter, search_text, limit, rating_filter=None):
    """Load runs data for table with filtering and populate video grid.

    Legacy function maintained for backward compatibility.
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


def load_runs_data_with_version_filter(
    status_filter, date_filter, type_filter, search_text, limit, rating_filter, version_filter
):
    """Load runs data with version filtering support.

    Legacy function maintained for backward compatibility.
    """
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
    return loader.load_runs(filters)


def load_runs_for_multiple_prompts(
    prompt_ids, status_filter, date_filter, type_filter, search_text, limit, rating_filter=None
):
    """Load runs data for multiple prompt IDs.

    Legacy function maintained for backward compatibility.
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

    Legacy function maintained for backward compatibility.
    """
    # Check if we have active prompt filtering
    if (
        nav_state
        and nav_state.get("filter_type") == "prompt_ids"
        and nav_state.get("filter_values")
    ):
        prompt_ids = nav_state.get("filter_values", [])
        logger.info(f"Loading runs with prompt filter for {len(prompt_ids)} prompts")

        # Use the multi-prompt loader with all filters
        gallery, table, stats, prompt_names = load_runs_for_multiple_prompts(
            prompt_ids,
            status_filter,
            date_filter,
            type_filter,
            search_text,
            limit,
            rating_filter,
        )

        # Format prompt names for display
        if prompt_names:
            filter_display = f"**Filtering by {len(prompt_names)} prompt(s):**\n"
            display_names = []
            for name in prompt_names[:3]:
                display_names.append(f"• {name}")
            filter_display += "\n".join(display_names)
            if len(prompt_names) > 3:
                filter_display += f"\n• ... and {len(prompt_names) - 3} more"
        else:
            filter_display = ""

        return (
            gallery,
            table,
            stats,
            nav_state,  # Keep navigation state unchanged
            gr.update(visible=True),  # Show filter indicator
            gr.update(value=filter_display),  # Update filter text
        )
    else:
        # No prompt filtering, use regular loader with version filter
        logger.info("Loading runs with version filter: {}", version_filter)
        gallery, table, stats = load_runs_data_with_version_filter(
            status_filter,
            date_filter,
            type_filter,
            search_text,
            limit,
            rating_filter,
            version_filter,
        )

        return (
            gallery,
            table,
            stats,
            nav_state,  # Keep navigation state unchanged
            gr.update(visible=False),  # Hide filter indicator
            gr.update(value=""),  # Clear filter text
        )


# Import helper functions from the new specialized modules
from cosmos_workflow.ui.tabs.runs.display_builders import (
    build_gallery_data as _build_gallery_data,
)
from cosmos_workflow.ui.tabs.runs.display_builders import (
    build_runs_table_data as _build_runs_table_data,
)
from cosmos_workflow.ui.tabs.runs.display_builders import (
    calculate_runs_statistics as _calculate_runs_statistics,
)
from cosmos_workflow.ui.tabs.runs.filters import (
    apply_date_filter as _apply_date_filter,
)
from cosmos_workflow.ui.tabs.runs.filters import (
    apply_run_filters as _apply_run_filters,
)
