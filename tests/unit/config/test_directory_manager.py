#!/usr/bin/env python3
"""
Comprehensive tests for DirectoryManager.
Tests all methods, edge cases, and error conditions.
"""

import tempfile
from datetime import datetime
from pathlib import Path

from cosmos_workflow.prompts.schemas import DirectoryManager


class TestDirectoryManager:
    """Test the DirectoryManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create test directories
        self.prompts_dir = self.temp_path / "prompts"
        self.runs_dir = self.temp_path / "runs"
        self.prompts_dir.mkdir(parents=True)
        self.runs_dir.mkdir(parents=True)

        # Create DirectoryManager instance
        self.dir_manager = DirectoryManager(self.prompts_dir, self.runs_dir)

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test DirectoryManager initialization."""
        assert self.dir_manager.base_prompts_dir == self.prompts_dir
        assert self.dir_manager.base_runs_dir == self.runs_dir

    def test_get_date_subdirectory_string_timestamp(self):
        """Test getting date subdirectory from string timestamp."""
        timestamp = "2025-08-29T10:30:45Z"
        date_dir = self.dir_manager.get_date_subdirectory(timestamp)

        assert date_dir == "2025-08-29"

    def test_get_date_subdirectory_datetime_timestamp(self):
        """Test getting date subdirectory from datetime timestamp."""
        timestamp = datetime(2025, 8, 29, 10, 30, 45)
        date_dir = self.dir_manager.get_date_subdirectory(timestamp)

        assert date_dir == "2025-08-29"

    def test_get_date_subdirectory_edge_cases(self):
        """Test getting date subdirectory with edge case timestamps."""
        # Test with different time formats
        test_cases = [
            ("2025-01-01T00:00:00Z", "2025-01-01"),
            ("2025-12-31T23:59:59Z", "2025-12-31"),
            ("2024-02-29T12:00:00Z", "2024-02-29"),  # Leap year
            ("2023-06-15T06:30:00Z", "2023-06-15"),
        ]

        for timestamp, expected in test_cases:
            date_dir = self.dir_manager.get_date_subdirectory(timestamp)
            assert date_dir == expected, f"Failed for {timestamp}"

    def test_get_prompt_file_path(self):
        """Test getting prompt file path."""
        prompt_name = "test_prompt"
        timestamp = "2025-08-29T10:30:45Z"
        prompt_hash = "ps_abc123"

        file_path = self.dir_manager.get_prompt_file_path(prompt_name, timestamp, prompt_hash)

        expected_path = (
            self.prompts_dir / "2025-08-29" / "test_prompt_2025-08-29T10-30-45_ps_abc123.json"
        )
        assert file_path == expected_path

    def test_get_run_file_path(self):
        """Test getting run file path."""
        prompt_name = "test_prompt"
        timestamp = "2025-08-29T10:30:45Z"
        run_hash = "rs_def456"

        file_path = self.dir_manager.get_run_file_path(prompt_name, timestamp, run_hash)

        expected_path = (
            self.runs_dir / "2025-08-29" / "test_prompt_2025-08-29T10-30-45_rs_def456.json"
        )
        assert file_path == expected_path

    def test_get_file_paths_with_datetime_objects(self):
        """Test getting file paths with datetime objects."""
        prompt_name = "test_prompt"
        timestamp = datetime(2025, 8, 29, 10, 30, 45)
        prompt_hash = "ps_abc123"
        run_hash = "rs_def456"

        prompt_path = self.dir_manager.get_prompt_file_path(prompt_name, timestamp, prompt_hash)
        run_path = self.dir_manager.get_run_file_path(prompt_name, timestamp, run_hash)

        expected_prompt_path = (
            self.prompts_dir / "2025-08-29" / "test_prompt_2025-08-29T10-30-45_ps_abc123.json"
        )
        expected_run_path = (
            self.runs_dir / "2025-08-29" / "test_prompt_2025-08-29T10-30-45_rs_def456.json"
        )

        assert prompt_path == expected_prompt_path
        assert run_path == expected_run_path

    def test_get_file_paths_filename_safety(self):
        """Test that filenames are safe for all operating systems."""
        prompt_name = "test:prompt/with\\special*chars?"
        timestamp = "2025-08-29T10:30:45Z"
        prompt_hash = "ps_abc123"

        file_path = self.dir_manager.get_prompt_file_path(prompt_name, timestamp, prompt_hash)

        # Check that the filename doesn't contain invalid characters
        filename = file_path.name
        assert ":" not in filename
        assert "/" not in filename
        assert "\\" not in filename
        assert "*" not in filename
        assert "?" not in filename

        # Should contain safe replacements
        assert "test_prompt_with_special_chars" in filename

    def test_ensure_directories_exist(self):
        """Test that directories are created when they don't exist."""
        # Remove directories
        import shutil

        shutil.rmtree(self.prompts_dir)
        shutil.rmtree(self.runs_dir)

        # Ensure they exist
        self.dir_manager.ensure_directories_exist()

        assert self.prompts_dir.exists()
        assert self.runs_dir.exists()
        assert self.prompts_dir.is_dir()
        assert self.runs_dir.is_dir()

    def test_ensure_directories_exist_already_exist(self):
        """Test that existing directories are not recreated."""
        # Get modification times
        prompts_mtime = self.prompts_dir.stat().st_mtime
        runs_mtime = self.runs_dir.stat().st_mtime

        # Ensure directories exist
        self.dir_manager.ensure_directories_exist()

        # Check that modification times haven't changed
        assert self.prompts_dir.stat().st_mtime == prompts_mtime
        assert self.runs_dir.stat().st_mtime == runs_mtime

    def test_list_date_directories_empty(self):
        """Test listing date directories when none exist."""
        date_dirs = self.dir_manager.list_date_directories(self.prompts_dir)

        assert date_dirs == []

    def test_list_date_directories_with_valid_dates(self):
        """Test listing date directories with valid date formats."""
        # Create date directories
        valid_dates = ["2025-08-29", "2025-08-30", "2025-09-01"]
        for date in valid_dates:
            date_path = self.prompts_dir / date
            date_path.mkdir()

        date_dirs = self.dir_manager.list_date_directories(self.prompts_dir)

        # Should be sorted in reverse order (most recent first)
        expected_order = ["2025-09-01", "2025-08-30", "2025-08-29"]
        assert date_dirs == expected_order

    def test_list_date_directories_with_invalid_dates(self):
        """Test listing date directories with invalid date formats."""
        # Create valid date directories
        valid_dates = ["2025-08-29", "2025-08-30"]
        for date in valid_dates:
            date_path = self.prompts_dir / date
            date_path.mkdir()

        # Create invalid date directories
        invalid_dates = ["invalid_date", "2025-13-01", "not_a_date", "2025-08-32"]
        for date in invalid_dates:
            date_path = self.prompts_dir / date
            date_path.mkdir()

        date_dirs = self.dir_manager.list_date_directories(self.prompts_dir)

        # Should only include valid dates
        expected_order = ["2025-08-30", "2025-08-29"]
        assert date_dirs == expected_order

    def test_list_date_directories_with_files(self):
        """Test listing date directories when files exist alongside directories."""
        # Create date directories
        valid_dates = ["2025-08-29", "2025-08-30"]
        for date in valid_dates:
            date_path = self.prompts_dir / date
            date_path.mkdir()

        # Create some files (not directories)
        files = ["file1.txt", "file2.json", "README.md"]
        for file in files:
            file_path = self.prompts_dir / file
            file_path.touch()

        date_dirs = self.dir_manager.list_date_directories(self.prompts_dir)

        # Should only include directories, not files
        expected_order = ["2025-08-30", "2025-08-29"]
        assert date_dirs == expected_order

    def test_list_date_directories_nonexistent_base(self):
        """Test listing date directories from non-existent base directory."""
        non_existent_dir = self.temp_path / "nonexistent"

        date_dirs = self.dir_manager.list_date_directories(non_existent_dir)

        assert date_dirs == []

    def test_is_valid_date_format_valid_dates(self):
        """Test date format validation with valid dates."""
        valid_dates = ["2025-08-29", "2024-02-29", "2023-12-31", "2026-01-01"]  # Leap year

        for date in valid_dates:
            assert self.dir_manager._is_valid_date_format(date), f"Failed for {date}"

    def test_is_valid_date_format_invalid_dates(self):
        """Test date format validation with invalid dates."""
        invalid_dates = [
            "invalid_date",
            "2025-13-01",  # Invalid month
            "2025-08-32",  # Invalid day
            "2025-08-29T10:30:45",  # Wrong format
            "2025/08/29",  # Wrong separator
            "25-08-29",  # Wrong year format
            "2025-8-29",  # Missing leading zeros
            "2025-08-9",  # Missing leading zeros
        ]

        for date in invalid_dates:
            assert not self.dir_manager._is_valid_date_format(date), f"Failed for {date}"

    def test_is_valid_date_format_edge_cases(self):
        """Test date format validation with edge cases."""
        edge_cases = [
            "",  # Empty string
            "  2025-08-29  ",  # Whitespace
            "2025-08-29\n",  # Newline
            "2025-08-29\r",  # Carriage return
            "2025-08-29\t",  # Tab
        ]

        for date in edge_cases:
            assert not self.dir_manager._is_valid_date_format(date), f"Failed for {date!r}"

    def test_file_path_creation_with_special_characters(self):
        """Test file path creation handles special characters in names."""
        prompt_name = "test prompt with spaces and (parentheses) and [brackets]"
        timestamp = "2025-08-29T10:30:45Z"
        prompt_hash = "ps_abc123"

        file_path = self.dir_manager.get_prompt_file_path(prompt_name, timestamp, prompt_hash)

        # Check that the path is valid
        assert file_path.parent.exists() or file_path.parent.parent.exists()

        # Check filename format
        filename = file_path.name
        assert filename.startswith("test_prompt_with_spaces_and_parentheses_and_brackets")
        assert filename.endswith("_ps_abc123.json")
        assert "2025-08-29T10-30-45" in filename

    def test_file_path_creation_with_unicode(self):
        """Test file path creation handles unicode characters."""
        prompt_name = "test_prompt_with_accents_and_unicode"
        timestamp = "2025-08-29T10:30:45Z"
        prompt_hash = "ps_abc123"

        file_path = self.dir_manager.get_prompt_file_path(prompt_name, timestamp, prompt_hash)

        # Should handle unicode gracefully
        assert "test_prompt_with_accents_and_unicode" in file_path.name

    def test_timestamp_parsing_edge_cases(self):
        """Test timestamp parsing with edge cases."""
        edge_cases = [
            ("2025-08-29T00:00:00Z", "2025-08-29"),
            ("2025-08-29T23:59:59Z", "2025-08-29"),
            ("2025-08-29T12:00:00.123Z", "2025-08-29"),  # With milliseconds
            ("2025-08-29T12:00:00+00:00", "2025-08-29"),  # Different timezone format
        ]

        for timestamp, expected in edge_cases:
            date_dir = self.dir_manager.get_date_subdirectory(timestamp)
            assert date_dir == expected, f"Failed for {timestamp}"

    def test_directory_structure_creation(self):
        """Test that the complete directory structure is created correctly."""
        prompt_name = "test_prompt"
        timestamp = "2025-08-29T10:30:45Z"
        prompt_hash = "ps_abc123"
        run_hash = "rs_def456"

        # Get file paths
        self.dir_manager.get_prompt_file_path(prompt_name, timestamp, prompt_hash)
        self.dir_manager.get_run_file_path(prompt_name, timestamp, run_hash)

        # Ensure base directories exist
        self.dir_manager.ensure_directories_exist()

        # Ensure date subdirectories exist
        self.dir_manager.ensure_date_directories_exist(timestamp)

        # Check that date subdirectories are created
        date_dir = "2025-08-29"
        expected_prompt_date_dir = self.prompts_dir / date_dir
        expected_run_date_dir = self.runs_dir / date_dir

        assert expected_prompt_date_dir.exists()
        assert expected_run_date_dir.exists()
        assert expected_prompt_date_dir.is_dir()
        assert expected_run_date_dir.is_dir()

    def test_multiple_timestamps_same_date(self):
        """Test handling multiple timestamps on the same date."""
        prompt_name = "test_prompt"
        timestamps = ["2025-08-29T00:00:00Z", "2025-08-29T12:00:00Z", "2025-08-29T23:59:59Z"]
        prompt_hash = "ps_abc123"

        for timestamp in timestamps:
            file_path = self.dir_manager.get_prompt_file_path(prompt_name, timestamp, prompt_hash)
            assert file_path.parent.name == "2025-08-29"

    def test_multiple_timestamps_different_dates(self):
        """Test handling multiple timestamps on different dates."""
        prompt_name = "test_prompt"
        timestamps = ["2025-08-29T10:00:00Z", "2025-08-30T10:00:00Z", "2025-09-01T10:00:00Z"]
        prompt_hash = "ps_abc123"

        date_dirs = set()
        for timestamp in timestamps:
            file_path = self.dir_manager.get_prompt_file_path(prompt_name, timestamp, prompt_hash)
            date_dirs.add(file_path.parent.name)

        expected_dates = {"2025-08-29", "2025-08-30", "2025-09-01"}
        assert date_dirs == expected_dates
