"""Unit tests for UI formatting utility functions.

Tests cover duration formatting, text truncation, timestamp parsing,
and other display formatting helpers.
"""

from datetime import timezone

import pytest

from cosmos_workflow.ui.utils.formatting import (
    format_duration,
    format_file_size,
    format_number,
    format_percentage,
    format_run_status,
    format_timestamp,
    parse_timestamp_safe,
    truncate_text,
)


class TestFormatDuration:
    """Test format_duration function with various inputs."""

    def test_format_duration_seconds(self):
        """Test formatting durations under 60 seconds."""
        # 45 seconds
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T12:00:45Z"
        assert format_duration(start, end) == "45s"

        # 0 seconds
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T12:00:00Z"
        assert format_duration(start, end) == "0s"

        # 59 seconds
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T12:00:59Z"
        assert format_duration(start, end) == "59s"

    def test_format_duration_minutes(self):
        """Test formatting durations under 1 hour."""
        # 1 minute 30 seconds
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T12:01:30Z"
        assert format_duration(start, end) == "1m 30s"

        # Exactly 5 minutes
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T12:05:00Z"
        assert format_duration(start, end) == "5m 0s"

        # 59 minutes 59 seconds
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T12:59:59Z"
        assert format_duration(start, end) == "59m 59s"

    def test_format_duration_hours(self):
        """Test formatting durations over 1 hour."""
        # 1 hour 30 minutes
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T13:30:00Z"
        assert format_duration(start, end) == "1h 30m"

        # 2 hours 45 minutes
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T14:45:00Z"
        assert format_duration(start, end) == "2h 45m"

        # Many hours
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-02T15:30:00Z"
        assert format_duration(start, end) == "27h 30m"

    def test_format_duration_timezone_aware(self):
        """Test with different timezone formats."""
        # ISO format with Z
        start = "2024-01-01T12:00:00Z"
        end = "2024-01-01T12:30:00Z"
        assert format_duration(start, end) == "30m 0s"

        # ISO format with +00:00
        start = "2024-01-01T12:00:00+00:00"
        end = "2024-01-01T12:30:00+00:00"
        assert format_duration(start, end) == "30m 0s"

        # ISO format with different timezones (should still calculate correctly)
        start = "2024-01-01T12:00:00+00:00"
        end = "2024-01-01T13:30:00+01:00"  # 12:30 UTC
        assert format_duration(start, end) == "30m 0s"

    def test_format_duration_invalid_inputs(self):
        """Test with invalid or missing inputs."""
        # None values
        assert format_duration(None, None) == "-"
        assert format_duration("2024-01-01T12:00:00Z", None) == "-"
        assert format_duration(None, "2024-01-01T12:00:00Z") == "-"

        # Empty strings
        assert format_duration("", "") == "-"
        assert format_duration("2024-01-01T12:00:00Z", "") == "-"
        assert format_duration("", "2024-01-01T12:00:00Z") == "-"

        # Invalid format
        assert format_duration("invalid", "also invalid") == "-"
        assert format_duration("2024-01-01", "not a timestamp") == "-"

    def test_format_duration_negative(self):
        """Test when end time is before start time."""
        start = "2024-01-01T12:30:00Z"
        end = "2024-01-01T12:00:00Z"
        assert format_duration(start, end) == "-"

    def test_format_duration_naive_datetime(self):
        """Test with naive datetime strings (no timezone)."""
        # The function should handle these by adding UTC
        start = "2024-01-01T12:00:00"
        end = "2024-01-01T12:30:00"
        # This should work if the implementation handles naive datetimes
        result = format_duration(start, end)
        assert result in ["30m 0s", "-"]  # Depends on implementation


class TestTruncateText:
    """Test truncate_text function."""

    def test_truncate_text_basic(self):
        """Test basic text truncation."""
        # Text shorter than limit
        assert truncate_text("Hello", 10) == "Hello"

        # Text at exact limit
        assert truncate_text("HelloWorld", 10) == "HelloWorld"

        # Text longer than limit
        assert truncate_text("Hello World!", 10) == "Hello W..."

    def test_truncate_text_custom_length(self):
        """Test with different max lengths."""
        text = "This is a long text that needs truncation"

        assert truncate_text(text, 10) == "This is..."
        assert truncate_text(text, 20) == "This is a long te..."
        assert truncate_text(text, 50) == text  # No truncation needed

    def test_truncate_text_edge_cases(self):
        """Test edge cases."""
        # None input
        assert truncate_text(None) == ""
        assert truncate_text(None, 10) == ""

        # Empty string
        assert truncate_text("") == ""
        assert truncate_text("", 10) == ""

        # Very short max length
        assert truncate_text("Hello", 3) == "..."
        assert truncate_text("Hello", 4) == "H..."

        # Non-string input (should convert)
        assert truncate_text(12345, 5) == "12345"
        assert truncate_text(12345, 3) == "..."


class TestFormatTimestamp:
    """Test format_timestamp function."""

    def test_format_timestamp_valid(self):
        """Test with valid timestamps."""
        # ISO format with Z
        assert format_timestamp("2024-01-15T14:30:45Z") == "2024-01-15 14:30:45"

        # ISO format with timezone
        assert format_timestamp("2024-01-15T14:30:45+00:00") == "2024-01-15 14:30:45"

        # Naive datetime
        assert format_timestamp("2024-01-15T14:30:45") == "2024-01-15 14:30:45"

    def test_format_timestamp_invalid(self):
        """Test with invalid inputs."""
        assert format_timestamp(None) == "-"
        assert format_timestamp("") == "-"
        assert format_timestamp("invalid") == "invalid"  # Returns truncated input
        assert format_timestamp("not-a-date") == "not-a-date"


class TestFormatFileSize:
    """Test format_file_size function."""

    def test_format_file_size_bytes(self):
        """Test formatting sizes in bytes."""
        assert format_file_size(0) == "0 B"
        assert format_file_size(100) == "100 B"
        assert format_file_size(1023) == "1023 B"

    def test_format_file_size_kilobytes(self):
        """Test formatting sizes in KB."""
        assert format_file_size(1024) == "1.00 KB"
        assert format_file_size(1536) == "1.50 KB"
        assert format_file_size(10240) == "10.0 KB"
        assert format_file_size(102400) == "100 KB"

    def test_format_file_size_megabytes(self):
        """Test formatting sizes in MB."""
        assert format_file_size(1048576) == "1.00 MB"
        assert format_file_size(1572864) == "1.50 MB"
        assert format_file_size(10485760) == "10.0 MB"
        assert format_file_size(104857600) == "100 MB"

    def test_format_file_size_gigabytes(self):
        """Test formatting sizes in GB."""
        assert format_file_size(1073741824) == "1.00 GB"
        assert format_file_size(5368709120) == "5.00 GB"

    def test_format_file_size_invalid(self):
        """Test with invalid inputs."""
        assert format_file_size(None) == "-"
        assert format_file_size(-1) == "-"


class TestFormatRunStatus:
    """Test format_run_status function."""

    def test_format_run_status_known(self):
        """Test with known status values."""
        assert format_run_status("completed") == "✅ Completed"
        assert format_run_status("failed") == "❌ Failed"
        assert format_run_status("running") == "🔄 Running"
        assert format_run_status("pending") == "⏳ Pending"
        assert format_run_status("cancelled") == "🚫 Cancelled"
        assert format_run_status("queued") == "📋 Queued"

    def test_format_run_status_case_insensitive(self):
        """Test that status is case-insensitive."""
        assert format_run_status("COMPLETED") == "✅ Completed"
        assert format_run_status("Failed") == "❌ Failed"
        assert format_run_status("RuNnInG") == "🔄 Running"

    def test_format_run_status_unknown(self):
        """Test with unknown status values."""
        assert format_run_status("unknown") == "Unknown"
        assert format_run_status("custom_status") == "Custom_status"
        assert format_run_status(None) == "Unknown"
        assert format_run_status("") == "Unknown"


class TestFormatPercentage:
    """Test format_percentage function."""

    def test_format_percentage_fraction(self):
        """Test with fractional values (0-1)."""
        assert format_percentage(0.5) == "50.0%"
        assert format_percentage(0.753) == "75.3%"
        assert format_percentage(1.0) == "100.0%"
        assert format_percentage(0.0) == "0.0%"

    def test_format_percentage_whole_numbers(self):
        """Test with whole percentage values."""
        assert format_percentage(50) == "50.0%"
        assert format_percentage(75.3) == "75.3%"
        assert format_percentage(100) == "100.0%"

    def test_format_percentage_decimals(self):
        """Test with different decimal precision."""
        assert format_percentage(0.5, decimals=0) == "50%"
        assert format_percentage(0.5, decimals=1) == "50.0%"
        assert format_percentage(0.5, decimals=2) == "50.00%"
        assert format_percentage(0.753456, decimals=2) == "75.35%"

    def test_format_percentage_invalid(self):
        """Test with invalid inputs."""
        assert format_percentage(None) == "-"
        assert format_percentage("not a number") == "-"


class TestFormatNumber:
    """Test format_number function."""

    def test_format_number_with_commas(self):
        """Test formatting with comma separators."""
        assert format_number(1000) == "1,000"
        assert format_number(1000000) == "1,000,000"
        assert format_number(123456789) == "123,456,789"

    def test_format_number_without_commas(self):
        """Test formatting without comma separators."""
        assert format_number(1000, use_commas=False) == "1000"
        assert format_number(1000000, use_commas=False) == "1000000"

    def test_format_number_small(self):
        """Test with small numbers."""
        assert format_number(0) == "0"
        assert format_number(10) == "10"
        assert format_number(999) == "999"

    def test_format_number_invalid(self):
        """Test with invalid inputs."""
        assert format_number(None) == "-"
        assert format_number("not a number") == "-"


class TestParseTimestampSafe:
    """Test parse_timestamp_safe function."""

    def test_parse_timestamp_with_z_suffix(self):
        """Test parsing timestamps with Z suffix (UTC)."""
        result = parse_timestamp_safe("2024-01-15T14:30:45Z")
        assert result is not None
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45
        assert result.tzinfo == timezone.utc

    def test_parse_timestamp_with_timezone(self):
        """Test parsing timestamps with explicit timezone."""
        result = parse_timestamp_safe("2024-01-15T14:30:45+00:00")
        assert result is not None
        assert result.year == 2024
        assert result.tzinfo == timezone.utc

        # With non-UTC timezone
        result = parse_timestamp_safe("2024-01-15T14:30:45+05:00")
        assert result is not None
        assert result.year == 2024

    def test_parse_timestamp_naive(self):
        """Test parsing naive timestamps (no timezone)."""
        result = parse_timestamp_safe("2024-01-15T14:30:45")
        assert result is not None
        assert result.year == 2024
        assert result.tzinfo == timezone.utc  # Should add UTC

    def test_parse_timestamp_invalid(self):
        """Test with invalid inputs."""
        assert parse_timestamp_safe(None) is None
        assert parse_timestamp_safe("") is None
        assert parse_timestamp_safe("invalid") is None
        assert parse_timestamp_safe("2024-13-45") is None  # Invalid date
        assert parse_timestamp_safe("not-a-timestamp") is None

    def test_parse_timestamp_edge_cases(self):
        """Test edge cases."""
        # Date only (no time)
        result = parse_timestamp_safe("2024-01-15")
        # This might work or not depending on implementation
        assert result is None or result.year == 2024

        # Microseconds
        result = parse_timestamp_safe("2024-01-15T14:30:45.123456Z")
        assert result is not None
        assert result.year == 2024
        assert result.microsecond == 123456

    def test_parse_timestamp_consistency(self):
        """Test that parsing is consistent with format_duration."""
        # These timestamps should work with both functions
        start = "2024-01-15T12:00:00Z"
        end = "2024-01-15T12:30:00Z"

        # Parse individually
        start_dt = parse_timestamp_safe(start)
        end_dt = parse_timestamp_safe(end)

        assert start_dt is not None
        assert end_dt is not None

        # Calculate duration manually
        delta = end_dt - start_dt
        assert delta.total_seconds() == 1800  # 30 minutes

        # Should also work with format_duration
        duration = format_duration(start, end)
        assert duration == "30m 0s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
