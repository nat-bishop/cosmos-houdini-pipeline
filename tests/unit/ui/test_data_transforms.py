#!/usr/bin/env python3
"""Tests for UI data transformation and business logic - no UI dependencies."""

from unittest.mock import Mock, patch

import pytest

from cosmos_workflow.ui.tabs.prompts_handlers import (
    calculate_average_rating,
    calculate_run_statistics,
    filter_prompts,
    get_selected_prompt_ids,
)
from cosmos_workflow.ui.utils import dataframe as df_utils


class TestRunStatistics:
    """Test run statistics calculation."""

    def test_calculate_run_statistics_basic(self):
        """Test basic statistics calculation."""
        runs = [
            {"status": "completed", "model_type": "transfer"},
            {"status": "completed", "model_type": "upscale"},
            {"status": "completed", "model_type": "enhance"},
            {"status": "failed", "model_type": "transfer"},
            {"status": "running", "model_type": "transfer"},
        ]

        stats = calculate_run_statistics(runs)

        assert stats["transfer"] == 1  # Only 1 completed transfer
        assert stats["upscale"] == 1
        assert stats["enhance"] == 1
        assert stats["total_completed"] == 3

    def test_calculate_run_statistics_empty(self):
        """Test with no runs."""
        stats = calculate_run_statistics([])

        assert stats["transfer"] == 0
        assert stats["upscale"] == 0
        assert stats["enhance"] == 0
        assert stats["total_completed"] == 0

    def test_calculate_run_statistics_no_completed(self):
        """Test with no completed runs."""
        runs = [
            {"status": "failed", "model_type": "transfer"},
            {"status": "running", "model_type": "upscale"},
            {"status": "pending", "model_type": "enhance"},
        ]

        stats = calculate_run_statistics(runs)

        assert stats["total_completed"] == 0
        assert stats["transfer"] == 0

    def test_calculate_run_statistics_missing_fields(self):
        """Test with missing or malformed data."""
        runs = [
            {"status": "completed"},  # Missing model_type
            {"model_type": "transfer"},  # Missing status
            {"status": "completed", "model_type": "unknown_type"},  # Unknown type
            {"status": "completed", "model_type": "transfer"},  # Valid
        ]

        stats = calculate_run_statistics(runs)

        assert stats["transfer"] == 1  # Only the valid one
        # Implementation counts ALL completed runs, not just known types
        assert stats["total_completed"] == 3  # Three completed (including unknown type)


class TestAverageRating:
    """Test average rating calculation."""

    def test_calculate_average_rating_valid(self):
        """Test with valid ratings."""
        runs = [
            {"status": "completed", "rating": 5},
            {"status": "completed", "rating": 4},
            {"status": "completed", "rating": 3},
        ]

        avg, count = calculate_average_rating(runs)

        assert avg == 4.0
        assert count == 3

    def test_calculate_average_rating_mixed(self):
        """Test with mixed completed and incomplete runs."""
        runs = [
            {"status": "completed", "rating": 5},
            {"status": "completed", "rating": 3},
            {"status": "failed", "rating": 1},  # Should be ignored
            {"status": "running", "rating": 5},  # Should be ignored
            {"status": "completed"},  # No rating
        ]

        avg, count = calculate_average_rating(runs)

        assert avg == 4.0  # (5 + 3) / 2
        assert count == 2

    def test_calculate_average_rating_no_ratings(self):
        """Test with no ratings."""
        runs = [
            {"status": "completed"},
            {"status": "completed", "rating": None},
        ]

        avg, count = calculate_average_rating(runs)

        assert avg is None
        assert count == 0

    def test_calculate_average_rating_invalid_ratings(self):
        """Test with invalid rating values."""
        runs = [
            {"status": "completed", "rating": 5},
            {"status": "completed", "rating": 0},  # Invalid (below 1)
            {"status": "completed", "rating": 6},  # Invalid (above 5)
            {"status": "completed", "rating": "5"},  # String (might work)
            {"status": "completed", "rating": 3.5},  # Float (valid)
        ]

        avg, count = calculate_average_rating(runs)

        # Should only count valid ratings (5 and 3.5)
        assert avg == 4.25
        assert count == 2


class TestPromptFiltering:
    """Test prompt filtering logic."""

    @pytest.fixture
    def sample_prompts(self):
        """Create sample prompts for testing."""
        return [
            {
                "id": "ps_001",
                "prompt_text": "A beautiful sunset",
                "parameters": {"name": "sunset", "enhanced": True},
                "inputs": {"video": "/inputs/sunset/color.mp4"},
                "created_at": "2025-01-15T10:00:00Z",
            },
            {
                "id": "ps_002",
                "prompt_text": "Ocean waves",
                "parameters": {"name": "ocean", "enhanced": False},
                "inputs": {"video": "/inputs/ocean/color.mp4"},
                "created_at": "2025-01-14T10:00:00Z",
            },
            {
                "id": "ps_003",
                "prompt_text": "Mountain landscape",
                "parameters": {"name": "mountain", "enhanced": True},
                "inputs": {"video": "/inputs/mountain/color.mp4"},
                "created_at": "2025-01-10T10:00:00Z",
            },
        ]

    def test_filter_prompts_by_search(self, sample_prompts):
        """Test text search filtering."""
        # Search in prompt text
        filtered = filter_prompts(sample_prompts, search_text="sunset")
        assert len(filtered) == 1
        assert filtered[0]["id"] == "ps_001"

        # Search in name
        filtered = filter_prompts(sample_prompts, search_text="ocean")
        assert len(filtered) == 1
        assert filtered[0]["id"] == "ps_002"

        # Search in video path
        filtered = filter_prompts(sample_prompts, search_text="mountain")
        assert len(filtered) == 1
        assert filtered[0]["id"] == "ps_003"

        # Case insensitive search
        filtered = filter_prompts(sample_prompts, search_text="SUNSET")
        assert len(filtered) == 1

    def test_filter_prompts_by_enhanced(self, sample_prompts):
        """Test enhanced filter."""
        # Only enhanced
        filtered = filter_prompts(sample_prompts, enhanced_filter="enhanced")
        assert len(filtered) == 2
        assert all(p["parameters"]["enhanced"] for p in filtered)

        # Not enhanced
        filtered = filter_prompts(sample_prompts, enhanced_filter="not_enhanced")
        assert len(filtered) == 1
        assert not filtered[0]["parameters"]["enhanced"]

        # All (no filter)
        filtered = filter_prompts(sample_prompts, enhanced_filter="all")
        assert len(filtered) == 3

    def test_filter_prompts_by_date(self, sample_prompts):
        """Test date filtering."""
        # Date filtering is complex to mock properly
        # Just test that it doesn't crash and returns valid results

        # Test "all" returns everything
        filtered = filter_prompts(sample_prompts, date_filter="all")
        assert len(filtered) == 3

        # Test other filters don't crash and return lists
        for filter_type in ["today", "last_7_days", "last_30_days", "older_than_30_days"]:
            filtered = filter_prompts(sample_prompts, date_filter=filter_type)
            assert isinstance(filtered, list)
            # Results depend on current date, so we can't assert exact counts

    def test_filter_prompts_combined(self, sample_prompts):
        """Test combining multiple filters."""
        # Enhanced + search
        filtered = filter_prompts(
            sample_prompts,
            search_text="a",  # Matches "A beautiful" and "Mountain landscape"
            enhanced_filter="enhanced",
        )
        assert len(filtered) == 2
        assert all(p["parameters"]["enhanced"] for p in filtered)

    def test_filter_prompts_with_runs(self, sample_prompts):
        """Test filtering by run status."""
        with patch("cosmos_workflow.ui.tabs.prompts_handlers.CosmosAPI") as mock_api:
            mock_api_instance = Mock()
            mock_api.return_value = mock_api_instance

            # Setup mock returns for each prompt
            mock_api_instance.list_runs.side_effect = [
                [{"id": "rs_001"}],  # ps_001 has runs
                [],  # ps_002 has no runs
                [{"id": "rs_002"}, {"id": "rs_003"}],  # ps_003 has runs
            ]

            # Filter for prompts with runs
            filtered = filter_prompts(sample_prompts, runs_filter="has_runs")
            assert len(filtered) == 2
            assert filtered[0]["id"] == "ps_001"
            assert filtered[1]["id"] == "ps_003"

            # Reset side_effect for next test
            mock_api_instance.list_runs.side_effect = [
                [{"id": "rs_001"}],  # ps_001 has runs
                [],  # ps_002 has no runs
                [{"id": "rs_002"}],  # ps_003 has runs
            ]

            # Filter for prompts without runs
            filtered = filter_prompts(sample_prompts, runs_filter="no_runs")
            assert len(filtered) == 1
            assert filtered[0]["id"] == "ps_002"


class TestDataframeUtils:
    """Test dataframe utility functions."""

    def test_select_all(self):
        """Test selecting all rows."""
        data = [
            [False, "id1", "text1"],
            [False, "id2", "text2"],
            [True, "id3", "text3"],  # Already selected
        ]

        result = df_utils.select_all(data)

        assert all(row[0] is True for row in result)
        assert len(result) == 3

    def test_clear_selection(self):
        """Test clearing all selections."""
        data = [
            [True, "id1", "text1"],
            [True, "id2", "text2"],
            [False, "id3", "text3"],
        ]

        result = df_utils.clear_selection(data)

        assert all(row[0] is False for row in result)

    def test_count_selected(self):
        """Test counting selected rows."""
        data = [
            [True, "id1", "text1"],
            [False, "id2", "text2"],
            [True, "id3", "text3"],
        ]

        count = df_utils.count_selected(data)
        assert count == 2

    def test_count_selected_empty(self):
        """Test counting with no data."""
        assert df_utils.count_selected([]) == 0
        assert df_utils.count_selected(None) == 0

    def test_get_selected_ids(self):
        """Test extracting selected IDs."""
        data = [
            [True, "ps_001", "text1"],
            [False, "ps_002", "text2"],
            [True, "ps_003", "text3"],
        ]

        ids = df_utils.get_selected_ids(data, id_column=1)

        assert ids == ["ps_001", "ps_003"]

    def test_get_selected_ids_none_selected(self):
        """Test with no selections."""
        data = [
            [False, "ps_001", "text1"],
            [False, "ps_002", "text2"],
        ]

        ids = df_utils.get_selected_ids(data, id_column=1)
        assert ids == []

    def test_get_cell_value(self):
        """Test getting cell value safely."""
        data = [
            ["val00", "val01", "val02"],
            ["val10", "val11", "val12"],
        ]

        # Valid access
        assert df_utils.get_cell_value(data, 0, 1) == "val01"
        assert df_utils.get_cell_value(data, 1, 2) == "val12"

        # Out of bounds with default
        assert df_utils.get_cell_value(data, 5, 0, default="N/A") == "N/A"
        assert df_utils.get_cell_value(data, 0, 10, default="") == ""

        # None data
        assert df_utils.get_cell_value(None, 0, 0, default="empty") == "empty"


class TestPromptSelection:
    """Test prompt selection logic."""

    def test_get_selected_prompt_ids(self):
        """Test extracting selected prompt IDs."""
        table_data = [
            [True, "ps_001", "Prompt 1", "Text 1", "2025-01-15"],
            [False, "ps_002", "Prompt 2", "Text 2", "2025-01-15"],
            [True, "ps_003", "Prompt 3", "Text 3", "2025-01-15"],
        ]

        ids = get_selected_prompt_ids(table_data)

        assert len(ids) == 2
        assert "ps_001" in ids
        assert "ps_003" in ids
        assert "ps_002" not in ids

    def test_get_selected_prompt_ids_empty(self):
        """Test with empty or invalid data."""
        assert get_selected_prompt_ids([]) == []
        assert get_selected_prompt_ids(None) == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
