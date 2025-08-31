#!/usr/bin/env python3
"""
Tests for the new prompt management schemas.

This module tests the PromptSpec, RunSpec, and related utility classes
for the refactored prompt management system.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from cosmos_workflow.prompts.schemas import (
    BlurStrength,
    CannyThreshold,
    DirectoryManager,
    ExecutionStatus,
    PromptSpec,
    RunSpec,
    SchemaUtils,
)


class TestPromptSpec:
    """Test suite for PromptSpec class."""

    def test_prompt_spec_creation(self):
        """Test creating a PromptSpec with all required fields."""
        timestamp = "2024-04-30T12:00:00Z"
        control_inputs = {
            "depth": "inputs/videos/cyberpunk_city_depth.mp4",
            "seg": "inputs/videos/cyberpunk_city_seg.mp4",
        }

        prompt_spec = PromptSpec(
            id="ps_test123",
            name="cyberpunk_city_neon",
            prompt="Cyberpunk city at night with neon lights",
            negative_prompt="bad quality, blurry",
            input_video_path="inputs/videos/cyberpunk_city_video.mp4",
            control_inputs=control_inputs,
            timestamp=timestamp,
            is_upsampled=False,
        )

        assert prompt_spec.id == "ps_test123"
        assert prompt_spec.name == "cyberpunk_city_neon"
        assert prompt_spec.prompt == "Cyberpunk city at night with neon lights"
        assert prompt_spec.negative_prompt == "bad quality, blurry"
        assert prompt_spec.input_video_path == "inputs/videos/cyberpunk_city_video.mp4"
        assert prompt_spec.control_inputs == control_inputs
        assert prompt_spec.timestamp == timestamp
        assert prompt_spec.is_upsampled is False
        assert prompt_spec.parent_prompt_text is None

    def test_prompt_spec_with_upsampling(self):
        """Test creating a PromptSpec with upsampling information."""
        prompt_spec = PromptSpec(
            id="ps_test456",
            name="upsampled_prompt",
            prompt="Enhanced building description",
            negative_prompt="low quality",
            input_video_path="inputs/videos/building.mp4",
            control_inputs={},
            timestamp="2024-04-30T12:00:00Z",
            is_upsampled=True,
            parent_prompt_text="big building",
        )

        assert prompt_spec.is_upsampled is True
        assert prompt_spec.parent_prompt_text == "big building"

    def test_prompt_spec_serialization(self):
        """Test PromptSpec serialization to and from dictionary."""
        original = PromptSpec(
            id="ps_test789",
            name="test_prompt",
            prompt="Test prompt text",
            negative_prompt="Test negative",
            input_video_path="test/video.mp4",
            control_inputs={"depth": "test/depth.mp4"},
            timestamp="2024-04-30T12:00:00Z",
            is_upsampled=False,
        )

        # Convert to dict
        data = original.to_dict()

        # Convert back from dict
        restored = PromptSpec.from_dict(data)

        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.prompt == original.prompt
        assert restored.negative_prompt == original.negative_prompt
        assert restored.input_video_path == original.input_video_path
        assert restored.control_inputs == original.control_inputs
        assert restored.timestamp == original.timestamp
        assert restored.is_upsampled == original.is_upsampled

    def test_prompt_spec_save_load(self):
        """Test saving and loading PromptSpec to/from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            prompt_spec = PromptSpec(
                id="ps_test_save",
                name="save_test",
                prompt="Save test prompt",
                negative_prompt="Save test negative",
                input_video_path="save/test.mp4",
                control_inputs={},
                timestamp="2024-04-30T12:00:00Z",
                is_upsampled=False,
            )

            # Save to file
            file_path = temp_path / "test_prompt.json"
            prompt_spec.save(file_path)

            # Verify file exists
            assert file_path.exists()

            # Load from file
            loaded = PromptSpec.load(file_path)

            # Verify content
            assert loaded.id == prompt_spec.id
            assert loaded.name == prompt_spec.name
            assert loaded.prompt == prompt_spec.prompt


class TestRunSpec:
    """Test suite for RunSpec class."""

    def test_run_spec_creation(self):
        """Test creating a RunSpec with all required fields."""
        control_weights = {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40}

        parameters = {
            "num_steps": 35,
            "guidance": 7.0,
            "sigma_max": 70.0,
            "blur_strength": "medium",
            "canny_threshold": "medium",
            "fps": 24,
            "seed": 1,
        }

        run_spec = RunSpec(
            id="rs_test123",
            prompt_id="ps_cyberpunk_city",
            name="test_run",
            control_weights=control_weights,
            parameters=parameters,
            timestamp="2024-04-30T12:00:00Z",
            execution_status=ExecutionStatus.PENDING,
            output_path="outputs/test_run",
        )

        assert run_spec.id == "rs_test123"
        assert run_spec.prompt_id == "ps_cyberpunk_city"
        assert run_spec.control_weights == control_weights
        assert run_spec.parameters == parameters
        assert run_spec.timestamp == "2024-04-30T12:00:00Z"
        assert run_spec.execution_status == ExecutionStatus.PENDING
        assert run_spec.output_path == "outputs/test_run"

    def test_run_spec_serialization(self):
        """Test RunSpec serialization to and from dictionary."""
        original = RunSpec(
            id="rs_test456",
            prompt_id="ps_test_prompt",
            name="test_run",
            control_weights={"vis": 0.5, "edge": 0.5},
            parameters={"num_steps": 50, "guidance": 10.0},
            timestamp="2024-04-30T12:00:00Z",
            execution_status=ExecutionStatus.SUCCESS,
        )

        # Convert to dict
        data = original.to_dict()

        # Verify execution_status is serialized as string
        assert data["execution_status"] == "success"

        # Convert back from dict
        restored = RunSpec.from_dict(data)

        assert restored.id == original.id
        assert restored.prompt_id == original.prompt_id
        assert restored.control_weights == original.control_weights
        assert restored.parameters == original.parameters
        assert restored.timestamp == original.timestamp
        assert restored.execution_status == original.execution_status

    def test_run_spec_save_load(self):
        """Test saving and loading RunSpec to/from file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            run_spec = RunSpec(
                id="rs_test_save",
                prompt_id="ps_test_prompt",
                name="test_run",
                control_weights={"vis": 0.25, "edge": 0.75},
                parameters={"num_steps": 40, "guidance": 8.0},
                timestamp="2024-04-30T12:00:00Z",
                execution_status=ExecutionStatus.PENDING,
            )

            # Save to file
            file_path = temp_path / "test_run.json"
            run_spec.save(file_path)

            # Verify file exists
            assert file_path.exists()

            # Load from file
            loaded = RunSpec.load(file_path)

            # Verify content
            assert loaded.id == run_spec.id
            assert loaded.prompt_id == run_spec.prompt_id
            assert loaded.control_weights == run_spec.control_weights
            assert loaded.parameters == run_spec.parameters


class TestSchemaUtils:
    """Test suite for SchemaUtils class."""

    def test_generate_prompt_id(self):
        """Test prompt ID generation."""
        prompt_text = "Cyberpunk city at night"
        input_video_path = "inputs/videos/cyberpunk.mp4"
        control_inputs = {
            "depth": "inputs/videos/cyberpunk_depth.mp4",
            "seg": "inputs/videos/cyberpunk_seg.mp4",
        }

        prompt_id = SchemaUtils.generate_prompt_id(prompt_text, input_video_path, control_inputs)

        # Should start with "ps_" and be 15 characters long
        assert prompt_id.startswith("ps_")
        assert len(prompt_id) == 15
        assert prompt_id.count("_") == 1  # Only one underscore separator

        # Should be deterministic
        prompt_id2 = SchemaUtils.generate_prompt_id(prompt_text, input_video_path, control_inputs)
        assert prompt_id == prompt_id2

    def test_generate_run_id(self):
        """Test run ID generation."""
        prompt_id = "ps_test123"
        control_weights = {"vis": 0.25, "edge": 0.75}
        parameters = {"num_steps": 50, "guidance": 10.0}

        run_id = SchemaUtils.generate_run_id(prompt_id, control_weights, parameters)

        # Should start with "rs_" and be 15 characters long
        assert run_id.startswith("rs_")
        assert len(run_id) == 15
        assert run_id.count("_") == 1  # Only one underscore separator

        # Should be deterministic
        run_id2 = SchemaUtils.generate_run_id(prompt_id, control_weights, parameters)
        assert run_id == run_id2

    def test_get_default_parameters(self):
        """Test getting default parameters."""
        defaults = SchemaUtils.get_default_parameters()

        assert "num_steps" in defaults
        assert "guidance" in defaults
        assert "sigma_max" in defaults
        assert "blur_strength" in defaults
        assert "canny_threshold" in defaults
        assert "fps" in defaults
        assert "seed" in defaults

        assert defaults["num_steps"] == 35
        assert defaults["guidance"] == 7.0
        assert defaults["sigma_max"] == 70.0
        assert defaults["blur_strength"] == "medium"
        assert defaults["canny_threshold"] == "medium"
        assert defaults["fps"] == 24
        assert defaults["seed"] == 1

    def test_get_default_control_weights(self):
        """Test getting default control weights."""
        weights = SchemaUtils.get_default_control_weights()

        assert "vis" in weights
        assert "edge" in weights
        assert "depth" in weights
        assert "seg" in weights

        assert weights["vis"] == 0.25
        assert weights["edge"] == 0.25
        assert weights["depth"] == 0.25
        assert weights["seg"] == 0.25

    def test_validate_control_weights(self):
        """Test control weight validation."""
        # Valid weights
        valid_weights = {"vis": 0.25, "edge": 0.75}
        assert SchemaUtils.validate_control_weights(valid_weights) is True

        # Invalid weights (negative)
        invalid_weights = {"vis": -0.25, "edge": 0.75}
        assert SchemaUtils.validate_control_weights(invalid_weights) is False

        # Invalid weights (wrong type)
        invalid_weights2 = {"vis": "0.25", "edge": 0.75}
        assert SchemaUtils.validate_control_weights(invalid_weights2) is False

        # Empty weights
        assert SchemaUtils.validate_control_weights({}) is False

    def test_validate_parameters(self):
        """Test parameter validation."""
        # Valid parameters
        valid_params = SchemaUtils.get_default_parameters()
        assert SchemaUtils.validate_parameters(valid_params) is True

        # Invalid parameters (missing required)
        invalid_params = {"num_steps": 35, "guidance": 7.0}  # Missing others
        assert SchemaUtils.validate_parameters(invalid_params) is False

        # Invalid parameters (out of range)
        invalid_params2 = valid_params.copy()
        invalid_params2["num_steps"] = 150  # Out of range
        assert SchemaUtils.validate_parameters(invalid_params2) is False


class TestDirectoryManager:
    """Test suite for DirectoryManager class."""

    def test_directory_manager_creation(self):
        """Test creating DirectoryManager."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompts_dir = temp_path / "prompts"
            runs_dir = temp_path / "runs"

            dir_manager = DirectoryManager(prompts_dir, runs_dir)

            assert dir_manager.base_prompts_dir == prompts_dir
            assert dir_manager.base_runs_dir == runs_dir

    def test_get_date_subdirectory(self):
        """Test date subdirectory generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dir_manager = DirectoryManager(temp_path / "prompts", temp_path / "runs")

            # Test with ISO string
            iso_timestamp = "2024-04-30T12:00:00Z"
            date_dir = dir_manager.get_date_subdirectory(iso_timestamp)
            assert date_dir == "2024-04-30"

            # Test with datetime object
            dt = datetime(2024, 4, 30, 12, 0, 0)
            date_dir2 = dir_manager.get_date_subdirectory(dt)
            assert date_dir2 == "2024-04-30"

    def test_get_file_paths(self):
        """Test file path generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dir_manager = DirectoryManager(temp_path / "prompts", temp_path / "runs")

            timestamp = "2024-04-30T12:00:00Z"

            # Test prompt file path
            prompt_path = dir_manager.get_prompt_file_path("test_prompt", timestamp, "ps_test123")
            expected_prompt_path = (
                temp_path
                / "prompts"
                / "2024-04-30"
                / "test_prompt_2024-04-30T12-00-00_ps_test123.json"
            )
            assert prompt_path == expected_prompt_path

            # Test run file path
            run_path = dir_manager.get_run_file_path("test_prompt", timestamp, "rs_test123")
            expected_run_path = (
                temp_path
                / "runs"
                / "2024-04-30"
                / "test_prompt_2024-04-30T12-00-00_rs_test123.json"
            )
            assert run_path == expected_run_path

    def test_ensure_directories_exist(self):
        """Test directory creation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompts_dir = temp_path / "prompts"
            runs_dir = temp_path / "runs"

            dir_manager = DirectoryManager(prompts_dir, runs_dir)
            dir_manager.ensure_directories_exist()

            assert prompts_dir.exists()
            assert runs_dir.exists()

    def test_list_date_directories(self):
        """Test listing date directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompts_dir = temp_path / "prompts"
            runs_dir = temp_path / "runs"

            dir_manager = DirectoryManager(prompts_dir, runs_dir)

            # Create some date directories
            (prompts_dir / "2024-04-30").mkdir(parents=True)
            (prompts_dir / "2024-04-29").mkdir(parents=True)
            (prompts_dir / "invalid_dir").mkdir(parents=True)  # Should be ignored

            date_dirs = dir_manager.list_date_directories(prompts_dir)

            # Should only include valid date directories, sorted by date (newest first)
            assert date_dirs == ["2024-04-30", "2024-04-29"]


if __name__ == "__main__":
    pytest.main([__file__])
