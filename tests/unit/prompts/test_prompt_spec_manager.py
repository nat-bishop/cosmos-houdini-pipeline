#!/usr/bin/env python3
"""
Comprehensive tests for PromptSpecManager.
Tests all methods, edge cases, and error conditions.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.schemas import DirectoryManager, PromptSpec


class TestPromptSpecManager:
    """Test the PromptSpecManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create test directories
        self.prompts_dir = self.temp_path / "prompts"
        self.runs_dir = self.temp_path / "runs"
        self.prompts_dir.mkdir(parents=True)
        self.runs_dir.mkdir(parents=True)

        # Create mock directory manager
        self.mock_dir_manager = Mock(spec=DirectoryManager)
        self.mock_dir_manager.get_prompt_file_path.return_value = self.prompts_dir / "test.json"

        # Create PromptSpecManager instance
        self.prompt_spec_manager = PromptSpecManager(self.mock_dir_manager)

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test PromptSpecManager initialization."""
        assert self.prompt_spec_manager.dir_manager == self.mock_dir_manager

    def test_create_prompt_spec_basic(self):
        """Test basic PromptSpec creation."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            prompt_spec = self.prompt_spec_manager.create_prompt_spec(
                "test_prompt", "A beautiful sunset over the ocean"
            )

            assert isinstance(prompt_spec, PromptSpec)
            assert prompt_spec.id == "ps_test123"
            assert prompt_spec.name == "test_prompt"
            assert prompt_spec.prompt == "A beautiful sunset over the ocean"
            assert prompt_spec.negative_prompt == "bad quality, blurry, low resolution, cartoonish"
            assert prompt_spec.input_video_path == "inputs/videos/test_prompt/color.mp4"
            assert prompt_spec.is_upsampled is False
            assert prompt_spec.parent_prompt_text is None

    def test_create_prompt_spec_with_custom_video_path(self):
        """Test PromptSpec creation with custom video path."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            prompt_spec = self.prompt_spec_manager.create_prompt_spec(
                "test_prompt", "Test prompt", input_video_path="custom/path/video.mp4"
            )

            assert prompt_spec.input_video_path == "custom/path/video.mp4"

    def test_create_prompt_spec_with_custom_control_inputs(self):
        """Test PromptSpec creation with custom control inputs."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            custom_control_inputs = {
                "depth": "custom/depth.mp4",
                "seg": "custom/seg.mp4",
                "edge": "custom/edge.mp4",
            }

            prompt_spec = self.prompt_spec_manager.create_prompt_spec(
                "test_prompt", "Test prompt", control_inputs=custom_control_inputs
            )

            assert prompt_spec.control_inputs == custom_control_inputs

    def test_create_prompt_spec_with_default_control_inputs(self):
        """Test PromptSpec creation with default control inputs."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            prompt_spec = self.prompt_spec_manager.create_prompt_spec("test_prompt", "Test prompt")

            expected_control_inputs = {
                "depth": "inputs/videos/test_prompt/depth.mp4",
                "seg": "inputs/videos/test_prompt/segmentation.mp4",
            }
            assert prompt_spec.control_inputs == expected_control_inputs

    def test_create_prompt_spec_upsampled(self):
        """Test PromptSpec creation for upsampled prompts."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            prompt_spec = self.prompt_spec_manager.create_prompt_spec(
                "test_prompt",
                "Upsampled prompt",
                is_upsampled=True,
                parent_prompt_text="Original prompt text",
            )

            assert prompt_spec.is_upsampled is True
            assert prompt_spec.parent_prompt_text == "Original prompt text"

    def test_create_prompt_spec_calls_save(self):
        """Test that PromptSpec is saved after creation."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            # Mock the save method
            with patch.object(PromptSpec, "save") as mock_save:
                prompt_spec = self.prompt_spec_manager.create_prompt_spec(
                    "test_prompt", "Test prompt"
                )

                # Verify save was called
                mock_save.assert_called_once()

    def test_create_prompt_spec_calls_directory_manager(self):
        """Test that directory manager is called correctly."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            prompt_spec = self.prompt_spec_manager.create_prompt_spec("test_prompt", "Test prompt")

            # Verify directory manager was called
            self.mock_dir_manager.get_prompt_file_path.assert_called_once()
            call_args = self.mock_dir_manager.get_prompt_file_path.call_args
            assert call_args[0][0] == "test_prompt"  # name
            assert call_args[0][2] == "ps_test123"  # prompt_id

    def test_list_prompts_empty_directory(self):
        """Test listing prompts in empty directory."""
        self.mock_dir_manager.list_date_directories.return_value = []

        prompts = self.prompt_spec_manager.list_prompts(self.prompts_dir)

        assert prompts == []
        self.mock_dir_manager.list_date_directories.assert_called_once_with(self.prompts_dir)

    def test_list_prompts_with_files(self):
        """Test listing prompts with existing files."""
        # Create mock date directories and files
        date_dir = "2025-08-29"
        self.mock_dir_manager.list_date_directories.return_value = [date_dir]

        # Create actual test files
        date_path = self.prompts_dir / date_dir
        date_path.mkdir()

        # Create test JSON files with different timestamps to ensure proper sorting
        test_files = [
            ("prompt1_2025-08-29T10-00-00_ps_abc123.json", 1000),  # oldest
            ("prompt2_2025-08-29T11-00-00_ps_def456.json", 2000),  # middle
            ("prompt3_2025-08-29T12-00-00_ps_ghi789.json", 3000),  # newest
        ]

        for filename, timestamp in test_files:
            file_path = date_path / filename
            with open(file_path, "w") as f:
                json.dump({"test": "data"}, f)
            # Set modification time
            file_path.touch()
            # Simulate different modification times
            import os

            os.utime(file_path, (timestamp, timestamp))

        prompts = self.prompt_spec_manager.list_prompts(self.prompts_dir)

        assert len(prompts) == 3
        assert all(p.name in [f[0] for f in test_files] for p in prompts)
        # Should be sorted by modification time (most recent first)
        assert prompts[0].name == "prompt3_2025-08-29T12-00-00_ps_ghi789.json"

    def test_list_prompts_with_pattern(self):
        """Test listing prompts with pattern filter."""
        date_dir = "2025-08-29"
        self.mock_dir_manager.list_date_directories.return_value = [date_dir]

        date_path = self.prompts_dir / date_dir
        date_path.mkdir()

        # Create test files
        test_files = [
            "cyberpunk_2025-08-29T10-00-00_ps_abc123.json",
            "building_2025-08-29T11-00-00_ps_def456.json",
            "cyberpunk_2025-08-29T12-00-00_ps_ghi789.json",
        ]

        for filename in test_files:
            file_path = date_path / filename
            with open(file_path, "w") as f:
                json.dump({"test": "data"}, f)

        # Filter by pattern
        prompts = self.prompt_spec_manager.list_prompts(self.prompts_dir, pattern="cyberpunk")

        assert len(prompts) == 2
        assert all("cyberpunk" in p.name for p in prompts)

    def test_list_prompts_pattern_case_insensitive(self):
        """Test that pattern matching is case insensitive."""
        date_dir = "2025-08-29"
        self.mock_dir_manager.list_date_directories.return_value = [date_dir]

        date_path = self.prompts_dir / date_dir
        date_path.mkdir()

        # Create test files
        test_files = [
            "CYBERPUNK_2025-08-29T10-00-00_ps_abc123.json",
            "building_2025-08-29T11-00-00_ps_def456.json",
        ]

        for filename in test_files:
            file_path = date_path / filename
            with open(file_path, "w") as f:
                json.dump({"test": "data"}, f)

        # Filter by lowercase pattern
        prompts = self.prompt_spec_manager.list_prompts(self.prompts_dir, pattern="cyberpunk")

        assert len(prompts) == 1
        assert "CYBERPUNK" in prompts[0].name

    def test_get_prompt_info_success(self):
        """Test successfully getting prompt information."""
        # Create a test file
        test_file = self.prompts_dir / "test_prompt.json"
        test_data = {
            "id": "ps_test123",
            "name": "test_prompt",
            "prompt": "Test prompt text",
            "negative_prompt": "Bad quality",
            "input_video_path": "inputs/videos/test.mp4",
            "control_inputs": {"depth": "depth.mp4", "seg": "seg.mp4"},
            "timestamp": "2025-08-29T10:00:00Z",
            "is_upsampled": False,
            "parent_prompt_text": None,
        }

        with open(test_file, "w") as f:
            json.dump(test_data, f)

        info = self.prompt_spec_manager.get_prompt_info(test_file)

        assert info["filename"] == "test_prompt.json"
        assert info["id"] == "ps_test123"
        assert info["name"] == "test_prompt"
        assert info["prompt_text"] == "Test prompt text"
        assert info["negative_prompt"] == "Bad quality"
        assert info["input_video_path"] == "inputs/videos/test.mp4"
        assert info["control_inputs"] == {"depth": "depth.mp4", "seg": "seg.mp4"}
        assert info["timestamp"] == "2025-08-29T10:00:00Z"
        assert info["is_upsampled"] is False
        assert info["parent_prompt_text"] is None  # None values are preserved
        assert info["file_path"] == str(test_file)
        assert info["file_size"] > 0
        assert isinstance(info["created_time"], datetime)

    def test_get_prompt_info_file_not_found(self):
        """Test getting prompt info for non-existent file."""
        non_existent_file = self.prompts_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="PromptSpec file not found"):
            self.prompt_spec_manager.get_prompt_info(non_existent_file)

    def test_get_prompt_info_invalid_json(self):
        """Test getting prompt info from invalid JSON file."""
        # Create file with invalid JSON
        invalid_file = self.prompts_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        with pytest.raises(json.JSONDecodeError):
            self.prompt_spec_manager.get_prompt_info(invalid_file)

    def test_get_prompt_info_missing_fields(self):
        """Test getting prompt info from file with missing fields."""
        # Create file with missing fields
        incomplete_file = self.prompts_dir / "incomplete.json"
        incomplete_data = {
            "id": "ps_test123",
            "name": "test_prompt"
            # Missing other required fields
        }

        with open(incomplete_file, "w") as f:
            json.dump(incomplete_data, f)

        info = self.prompt_spec_manager.get_prompt_info(incomplete_file)

        # Should handle missing fields gracefully
        assert info["prompt_text"] == ""
        assert info["negative_prompt"] == ""
        assert info["input_video_path"] == ""
        assert info["control_inputs"] == {}
        assert info["timestamp"] == ""
        assert info["is_upsampled"] is False
        assert info["parent_prompt_text"] == ""

    def test_create_prompt_spec_timestamp_format(self):
        """Test that timestamp is in correct ISO format."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            prompt_spec = self.prompt_spec_manager.create_prompt_spec("test_prompt", "Test prompt")

            # Check timestamp format
            assert prompt_spec.timestamp.endswith("Z")
            # Should be parseable as ISO format
            datetime.fromisoformat(prompt_spec.timestamp.replace("Z", "+00:00"))

    def test_create_prompt_spec_negative_prompt_default(self):
        """Test that negative prompt has correct default value."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            prompt_spec = self.prompt_spec_manager.create_prompt_spec("test_prompt", "Test prompt")

            expected_negative = "bad quality, blurry, low resolution, cartoonish"
            assert prompt_spec.negative_prompt == expected_negative

    def test_create_prompt_spec_custom_negative_prompt(self):
        """Test that custom negative prompt is used when provided."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_prompt_id.return_value = "ps_test123"

            custom_negative = "Custom negative prompt"
            prompt_spec = self.prompt_spec_manager.create_prompt_spec(
                "test_prompt", "Test prompt", negative_prompt=custom_negative
            )

            assert prompt_spec.negative_prompt == custom_negative
