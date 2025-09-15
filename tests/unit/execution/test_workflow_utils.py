#!/usr/bin/env python3
"""
Test workflow utilities module.
"""

from unittest.mock import patch

from cosmos_workflow.utils.workflow_utils import (
    ensure_directory,
    ensure_path_exists,
    format_duration,
    get_log_path,
    sanitize_remote_path,
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

    def test_ensure_directory(self, tmp_path):
        """Test ensure_directory creates directory."""
        # Test with Path object
        test_dir = tmp_path / "new_dir"
        result = ensure_directory(test_dir)
        assert test_dir.exists()
        assert test_dir.is_dir()
        assert result == test_dir

        # Test with string path
        test_dir2 = tmp_path / "another_dir"
        result2 = ensure_directory(str(test_dir2))
        assert test_dir2.exists()
        assert test_dir2.is_dir()
        assert result2 == test_dir2

        # Test idempotence (calling again on existing dir)
        result3 = ensure_directory(test_dir)
        assert result3 == test_dir

    def test_get_log_path(self, tmp_path):
        """Test get_log_path creates correct log paths."""
        # Mock ensure_directory to use tmp_path
        with patch("cosmos_workflow.utils.workflow_utils.ensure_directory") as mock_ensure:
            mock_ensure.return_value = tmp_path / "outputs/run_run_123/logs"

            # Test with run_id - should return unified log path
            log_path = get_log_path("inference", "test_id", "run_123")
            assert log_path.name == "run_123.log"
            assert "logs" in str(log_path)

            # Test without run_id (should use timestamp)
            log_path2 = get_log_path("batch", "batch_test", None)
            assert log_path2.name.startswith("batch_")
            assert log_path2.name.endswith(".log")

    def test_sanitize_remote_path(self):
        """Test sanitize_remote_path converts backslashes to forward slashes."""
        # Windows path
        assert sanitize_remote_path("C:\\Users\\test\\file.txt") == "C:/Users/test/file.txt"

        # Already POSIX path
        assert sanitize_remote_path("/home/user/file.txt") == "/home/user/file.txt"

        # Mixed slashes
        assert sanitize_remote_path("C:\\Users/test\\file.txt") == "C:/Users/test/file.txt"

        # Empty string
        assert sanitize_remote_path("") == ""
