#!/usr/bin/env python3
"""
Test workflow utilities module.
"""

from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from cosmos_workflow.utils.workflow_utils import (
    ensure_path_exists,
    format_duration,
    log_workflow_event,
    validate_gpu_configuration,
)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_ensure_path_exists(self, tmp_path):
        """Test ensure_path_exists creates directory."""
        test_dir = tmp_path / "test_dir" / "sub_dir"
        result = ensure_path_exists(test_dir)

        assert test_dir.exists()
        assert test_dir.is_dir()
        assert result == test_dir

    def test_ensure_path_exists_with_file(self, tmp_path):
        """Test ensure_path_exists with file path."""
        test_file = tmp_path / "test_dir" / "file.txt"
        result = ensure_path_exists(test_file)

        assert result.exists()
        assert result.is_dir()
        assert result == test_file.parent

    def test_ensure_path_exists_already_exists(self, tmp_path):
        """Test ensure_path_exists with existing directory."""
        test_dir = tmp_path / "existing"
        test_dir.mkdir()

        result = ensure_path_exists(test_dir)
        assert result == test_dir

    def test_format_duration_seconds(self):
        """Test format_duration for seconds only."""
        assert format_duration(45) == "45s"
        assert format_duration(59) == "59s"

    def test_format_duration_minutes(self):
        """Test format_duration for minutes and seconds."""
        assert format_duration(65) == "1m 5s"
        assert format_duration(125) == "2m 5s"
        assert format_duration(3599) == "59m 59s"

    def test_format_duration_hours(self):
        """Test format_duration for hours, minutes and seconds."""
        assert format_duration(3600) == "1h 0m 0s"
        assert format_duration(3665) == "1h 1m 5s"
        assert format_duration(7325) == "2h 2m 5s"

    @patch("cosmos_workflow.utils.workflow_utils.ensure_path_exists")
    def test_log_workflow_event(self, mock_ensure_path):
        """Test log_workflow_event function."""
        mock_file = mock_open()
        with patch("builtins.open", mock_file):
            log_workflow_event(
                "SUCCESS",
                "test_workflow",
                {"duration": "10s", "status": "completed"},
                Path("test_logs"),
            )

        mock_ensure_path.assert_called_once_with(Path("test_logs"))
        mock_file.assert_called_once_with(Path("test_logs") / "run_history.log", "a")

        # Check that something was written
        handle = mock_file()
        handle.write.assert_called()

    def test_validate_gpu_configuration_valid(self):
        """Test validate_gpu_configuration with valid config."""
        assert validate_gpu_configuration(1, "0") is True
        assert validate_gpu_configuration(2, "0,1") is True
        assert validate_gpu_configuration(4, "0,1,2,3") is True

    def test_validate_gpu_configuration_invalid(self):
        """Test validate_gpu_configuration with invalid config."""
        assert validate_gpu_configuration(0, "0") is False  # Invalid num_gpu
        assert validate_gpu_configuration(-1, "0") is False  # Negative num_gpu
        assert validate_gpu_configuration(2, "0") is False  # Mismatch count
        assert validate_gpu_configuration(1, "abc") is False  # Non-numeric device
        assert validate_gpu_configuration(1, "-1") is False  # Negative device ID
