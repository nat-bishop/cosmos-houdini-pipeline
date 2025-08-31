#!/usr/bin/env python3
"""
Comprehensive tests for PromptSpec and RunSpec dataclasses.
Tests all methods, edge cases, and error conditions.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cosmos_workflow.prompts.schemas import (
    BlurStrength,
    CannyThreshold,
    ExecutionStatus,
    PromptSpec,
    RunSpec,
)


class TestPromptSpec:
    """Test the PromptSpec dataclass."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create test data
        self.valid_prompt_data = {
            "id": "ps_test123",
            "name": "test_prompt",
            "prompt": "A beautiful sunset over the ocean",
            "negative_prompt": "Bad quality, blurry",
            "input_video_path": "inputs/videos/test.mp4",
            "control_inputs": {"depth": "depth.mp4", "seg": "seg.mp4"},
            "timestamp": "2025-08-29T10:00:00Z",
            "is_upsampled": False,
            "parent_prompt_text": None,
        }

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()

    def test_prompt_spec_creation(self):
        """Test basic PromptSpec creation."""
        prompt_spec = PromptSpec(**self.valid_prompt_data)

        assert prompt_spec.id == "ps_test123"
        assert prompt_spec.name == "test_prompt"
        assert prompt_spec.prompt == "A beautiful sunset over the ocean"
        assert prompt_spec.negative_prompt == "Bad quality, blurry"
        assert prompt_spec.input_video_path == "inputs/videos/test.mp4"
        assert prompt_spec.control_inputs == {"depth": "depth.mp4", "seg": "seg.mp4"}
        assert prompt_spec.timestamp == "2025-08-29T10:00:00Z"
        assert prompt_spec.is_upsampled is False
        assert prompt_spec.parent_prompt_text is None

    def test_prompt_spec_creation_with_upsampling(self):
        """Test PromptSpec creation with upsampling fields."""
        upsampled_data = self.valid_prompt_data.copy()
        upsampled_data.update({"is_upsampled": True, "parent_prompt_text": "Original prompt text"})

        prompt_spec = PromptSpec(**upsampled_data)

        assert prompt_spec.is_upsampled is True
        assert prompt_spec.parent_prompt_text == "Original prompt text"

    def test_prompt_spec_default_values(self):
        """Test PromptSpec default values."""
        minimal_data = {
            "id": "ps_test123",
            "name": "test_prompt",
            "prompt": "Test prompt",
            "negative_prompt": "Bad quality",
            "input_video_path": "inputs/videos/test.mp4",
            "control_inputs": {"depth": "depth.mp4", "seg": "seg.mp4"},
            "timestamp": "2025-08-29T10:00:00Z",
        }

        prompt_spec = PromptSpec(**minimal_data)

        assert prompt_spec.is_upsampled is False
        assert prompt_spec.parent_prompt_text is None

    def test_prompt_spec_to_dict(self):
        """Test PromptSpec to_dict method."""
        prompt_spec = PromptSpec(**self.valid_prompt_data)
        prompt_dict = prompt_spec.to_dict()

        assert isinstance(prompt_dict, dict)
        assert prompt_dict["id"] == "ps_test123"
        assert prompt_dict["name"] == "test_prompt"
        assert prompt_dict["prompt"] == "A beautiful sunset over the ocean"
        assert prompt_dict["negative_prompt"] == "Bad quality, blurry"
        assert prompt_dict["input_video_path"] == "inputs/videos/test.mp4"
        assert prompt_dict["control_inputs"] == {"depth": "depth.mp4", "seg": "seg.mp4"}
        assert prompt_dict["timestamp"] == "2025-08-29T10:00:00Z"
        assert prompt_dict["is_upsampled"] is False
        assert prompt_dict["parent_prompt_text"] is None

    def test_prompt_spec_from_dict(self):
        """Test PromptSpec from_dict class method."""
        prompt_spec = PromptSpec.from_dict(self.valid_prompt_data)

        assert isinstance(prompt_spec, PromptSpec)
        assert prompt_spec.id == "ps_test123"
        assert prompt_spec.name == "test_prompt"
        assert prompt_spec.prompt == "A beautiful sunset over the ocean"

    def test_prompt_spec_save(self):
        """Test PromptSpec save method."""
        prompt_spec = PromptSpec(**self.valid_prompt_data)
        file_path = self.temp_path / "test_prompt.json"

        prompt_spec.save(file_path)

        assert file_path.exists()
        assert file_path.is_file()

        # Verify content
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["id"] == "ps_test123"
        assert saved_data["name"] == "test_prompt"
        assert saved_data["prompt"] == "A beautiful sunset over the ocean"

    def test_prompt_spec_save_creates_directories(self):
        """Test that save method creates parent directories."""
        prompt_spec = PromptSpec(**self.valid_prompt_data)
        file_path = self.temp_path / "nested" / "deep" / "test_prompt.json"

        prompt_spec.save(file_path)

        assert file_path.exists()
        assert file_path.parent.exists()
        assert file_path.parent.parent.exists()

    def test_prompt_spec_load(self):
        """Test PromptSpec load class method."""
        # Create and save a PromptSpec
        prompt_spec = PromptSpec(**self.valid_prompt_data)
        file_path = self.temp_path / "test_prompt.json"
        prompt_spec.save(file_path)

        # Load it back
        loaded_prompt_spec = PromptSpec.load(file_path)

        assert isinstance(loaded_prompt_spec, PromptSpec)
        assert loaded_prompt_spec.id == prompt_spec.id
        assert loaded_prompt_spec.name == prompt_spec.name
        assert loaded_prompt_spec.prompt == prompt_spec.prompt
        assert loaded_prompt_spec.negative_prompt == prompt_spec.negative_prompt
        assert loaded_prompt_spec.input_video_path == prompt_spec.input_video_path
        assert loaded_prompt_spec.control_inputs == prompt_spec.control_inputs
        assert loaded_prompt_spec.timestamp == prompt_spec.timestamp
        assert loaded_prompt_spec.is_upsampled == prompt_spec.is_upsampled
        assert loaded_prompt_spec.parent_prompt_text == prompt_spec.parent_prompt_text

    def test_prompt_spec_load_file_not_found(self):
        """Test PromptSpec load with non-existent file."""
        non_existent_file = self.temp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            PromptSpec.load(non_existent_file)

    def test_prompt_spec_load_invalid_json(self):
        """Test PromptSpec load with invalid JSON."""
        invalid_file = self.temp_path / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        with pytest.raises(json.JSONDecodeError):
            PromptSpec.load(invalid_file)

    def test_prompt_spec_load_missing_fields(self):
        """Test PromptSpec load with missing fields."""
        incomplete_data = {
            "id": "ps_test123",
            "name": "test_prompt"
            # Missing other required fields
        }

        incomplete_file = self.temp_path / "incomplete.json"
        with open(incomplete_file, "w") as f:
            json.dump(incomplete_data, f)

        with pytest.raises(TypeError):
            PromptSpec.load(incomplete_file)

    def test_prompt_spec_immutability(self):
        """Test that PromptSpec fields cannot be modified after creation."""
        prompt_spec = PromptSpec(**self.valid_prompt_data)

        # Attempt to modify fields (should raise AttributeError)
        with pytest.raises(AttributeError):
            prompt_spec.id = "new_id"

        with pytest.raises(AttributeError):
            prompt_spec.name = "new_name"

        with pytest.raises(AttributeError):
            prompt_spec.prompt = "new prompt"

    def test_prompt_spec_equality(self):
        """Test PromptSpec equality comparison."""
        prompt_spec1 = PromptSpec(**self.valid_prompt_data)
        prompt_spec2 = PromptSpec(**self.valid_prompt_data)

        assert prompt_spec1 == prompt_spec2

        # Different data should create different objects
        different_data = self.valid_prompt_data.copy()
        different_data["prompt"] = "Different prompt"
        prompt_spec3 = PromptSpec(**different_data)

        assert prompt_spec1 != prompt_spec3


class TestRunSpec:
    """Test the RunSpec dataclass."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create test data
        self.valid_run_data = {
            "id": "rs_test456",
            "prompt_id": "ps_test123",
            "name": "test_run",
            "control_weights": {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1},
            "parameters": {
                "num_steps": 50,
                "guidance": 10.0,
                "sigma_max": 75.0,
                "blur_strength": "high",
                "canny_threshold": "low",
                "fps": 30,
                "seed": 42,
            },
            "timestamp": "2025-08-29T10:00:00Z",
            "execution_status": ExecutionStatus.PENDING,
            "output_path": "outputs/test_run",
        }

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()

    def test_run_spec_creation(self):
        """Test basic RunSpec creation."""
        run_spec = RunSpec(**self.valid_run_data)

        assert run_spec.id == "rs_test456"
        assert run_spec.prompt_id == "ps_test123"
        assert run_spec.name == "test_run"
        assert run_spec.control_weights == {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1}
        assert run_spec.parameters["num_steps"] == 50
        assert run_spec.parameters["guidance"] == 10.0
        assert run_spec.parameters["sigma_max"] == 75.0
        assert run_spec.parameters["blur_strength"] == "high"
        assert run_spec.parameters["canny_threshold"] == "low"
        assert run_spec.parameters["fps"] == 30
        assert run_spec.parameters["seed"] == 42
        assert run_spec.timestamp == "2025-08-29T10:00:00Z"
        assert run_spec.execution_status == ExecutionStatus.PENDING
        assert run_spec.output_path == "outputs/test_run"

    def test_run_spec_creation_with_defaults(self):
        """Test RunSpec creation with default values."""
        minimal_data = {
            "id": "rs_test456",
            "prompt_id": "ps_test123",
            "name": "test_run",
            "control_weights": {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1},
            "parameters": {"num_steps": 50, "guidance": 10.0, "sigma_max": 75.0},
            "timestamp": "2025-08-29T10:00:00Z",
        }

        run_spec = RunSpec(**minimal_data)

        assert run_spec.execution_status == ExecutionStatus.PENDING
        assert run_spec.output_path is None

    def test_run_spec_to_dict(self):
        """Test RunSpec to_dict method."""
        run_spec = RunSpec(**self.valid_run_data)
        run_dict = run_spec.to_dict()

        assert isinstance(run_dict, dict)
        assert run_dict["id"] == "rs_test456"
        assert run_dict["prompt_id"] == "ps_test123"
        assert run_dict["name"] == "test_run"
        assert run_dict["control_weights"] == {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1}
        assert run_dict["parameters"]["num_steps"] == 50
        assert run_dict["execution_status"] == "pending"  # Enum value converted to string
        assert run_dict["output_path"] == "outputs/test_run"

    def test_run_spec_from_dict(self):
        """Test RunSpec from_dict class method."""
        run_spec = RunSpec.from_dict(self.valid_run_data)

        assert isinstance(run_spec, RunSpec)
        assert run_spec.id == "rs_test456"
        assert run_spec.prompt_id == "ps_test123"
        assert run_spec.name == "test_run"
        assert run_spec.execution_status == ExecutionStatus.PENDING

    def test_run_spec_from_dict_with_string_status(self):
        """Test RunSpec from_dict with string execution status."""
        string_status_data = self.valid_run_data.copy()
        string_status_data["execution_status"] = "success"

        run_spec = RunSpec.from_dict(string_status_data)

        assert run_spec.execution_status == ExecutionStatus.SUCCESS

    def test_run_spec_save(self):
        """Test RunSpec save method."""
        run_spec = RunSpec(**self.valid_run_data)
        file_path = self.temp_path / "test_run.json"

        run_spec.save(file_path)

        assert file_path.exists()
        assert file_path.is_file()

        # Verify content
        with open(file_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data["id"] == "rs_test456"
        assert saved_data["prompt_id"] == "ps_test123"
        assert saved_data["name"] == "test_run"
        assert saved_data["execution_status"] == "pending"

    def test_run_spec_save_creates_directories(self):
        """Test that save method creates parent directories."""
        run_spec = RunSpec(**self.valid_run_data)
        file_path = self.temp_path / "nested" / "deep" / "test_run.json"

        run_spec.save(file_path)

        assert file_path.exists()
        assert file_path.parent.exists()
        assert file_path.parent.parent.exists()

    def test_run_spec_load(self):
        """Test RunSpec load class method."""
        # Create and save a RunSpec
        run_spec = RunSpec(**self.valid_run_data)
        file_path = self.temp_path / "test_run.json"
        run_spec.save(file_path)

        # Load it back
        loaded_run_spec = RunSpec.load(file_path)

        assert isinstance(loaded_run_spec, RunSpec)
        assert loaded_run_spec.id == run_spec.id
        assert loaded_run_spec.prompt_id == run_spec.prompt_id
        assert loaded_run_spec.name == run_spec.name
        assert loaded_run_spec.control_weights == run_spec.control_weights
        assert loaded_run_spec.parameters == run_spec.parameters
        assert loaded_run_spec.timestamp == run_spec.timestamp
        assert loaded_run_spec.execution_status == run_spec.execution_status
        assert loaded_run_spec.output_path == run_spec.output_path

    def test_run_spec_load_file_not_found(self):
        """Test RunSpec load with non-existent file."""
        non_existent_file = self.temp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            RunSpec.load(non_existent_file)

    def test_run_spec_load_invalid_json(self):
        """Test RunSpec load with invalid JSON."""
        invalid_file = self.temp_path / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        with pytest.raises(json.JSONDecodeError):
            RunSpec.load(invalid_file)

    def test_run_spec_load_missing_fields(self):
        """Test RunSpec load with missing fields."""
        incomplete_data = {
            "id": "rs_test456",
            "prompt_id": "ps_test123",
            "name": "test_run"
            # Missing other required fields
        }

        incomplete_file = self.temp_path / "incomplete.json"
        with open(incomplete_file, "w") as f:
            json.dump(incomplete_data, f)

        with pytest.raises(TypeError):
            RunSpec.load(incomplete_file)

    def test_run_spec_immutability(self):
        """Test that RunSpec fields cannot be modified after creation."""
        run_spec = RunSpec(**self.valid_run_data)

        # Attempt to modify fields (should raise AttributeError)
        with pytest.raises(AttributeError):
            run_spec.id = "new_id"

        with pytest.raises(AttributeError):
            run_spec.prompt_id = "new_prompt_id"

        with pytest.raises(AttributeError):
            run_spec.name = "new_name"

    def test_run_spec_equality(self):
        """Test RunSpec equality comparison."""
        run_spec1 = RunSpec(**self.valid_run_data)
        run_spec2 = RunSpec(**self.valid_run_data)

        assert run_spec1 == run_spec2

        # Different data should create different objects
        different_data = self.valid_run_data.copy()
        different_data["id"] = "rs_different"
        run_spec3 = RunSpec(**different_data)

        assert run_spec1 != run_spec3

    def test_run_spec_execution_status_enum(self):
        """Test RunSpec execution status enum handling."""
        # Test all execution status values
        status_values = [
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.SUCCESS,
            ExecutionStatus.FAILED,
            ExecutionStatus.CANCELLED,
        ]

        for status in status_values:
            status_data = self.valid_run_data.copy()
            status_data["execution_status"] = status

            run_spec = RunSpec(**status_data)
            assert run_spec.execution_status == status

            # Test serialization
            run_dict = run_spec.to_dict()
            assert run_dict["execution_status"] == status.value

    def test_run_spec_parameters_validation(self):
        """Test RunSpec parameters validation through serialization."""
        # Test with various parameter types
        test_parameters = {
            "num_steps": 50,
            "guidance": 10.0,
            "sigma_max": 75.0,
            "blur_strength": "high",
            "canny_threshold": "low",
            "fps": 30,
            "seed": 42,
            "custom_param": "custom_value",
        }

        test_data = self.valid_run_data.copy()
        test_data["parameters"] = test_parameters

        run_spec = RunSpec(**test_data)

        # Should serialize and deserialize correctly
        run_dict = run_spec.to_dict()
        assert run_dict["parameters"] == test_parameters

        # Test round-trip
        file_path = self.temp_path / "test_roundtrip.json"
        run_spec.save(file_path)
        loaded_run_spec = RunSpec.load(file_path)

        assert loaded_run_spec.parameters == test_parameters
