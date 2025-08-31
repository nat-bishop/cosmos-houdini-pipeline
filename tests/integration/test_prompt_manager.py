#!/usr/bin/env python3
"""
Tests for the prompt management system.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cosmos_workflow.prompts import PromptManager
from cosmos_workflow.prompts.schemas import ExecutionStatus, PromptSpec, RunSpec


class TestPromptManager:
    """Test the PromptManager class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary directories for testing
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create mock config
        self.mock_config = Mock()
        self.mock_config.prompts_dir = self.temp_path / "prompts"
        self.mock_config.runs_dir = self.temp_path / "runs"
        self.mock_config.outputs_dir = self.temp_path / "outputs"
        self.mock_config.videos_dir = self.temp_path / "videos"

        # Mock the ConfigManager
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config
            self.prompt_manager = PromptManager("dummy_config.toml")

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()

    def test_create_prompt_spec(self):
        """Test creating a new PromptSpec."""
        prompt_spec = self.prompt_manager.create_prompt_spec(
            "test_shot", "A beautiful sunset over the ocean"
        )

        assert isinstance(prompt_spec, PromptSpec)
        assert prompt_spec.name == "test_shot"
        assert prompt_spec.prompt == "A beautiful sunset over the ocean"
        assert prompt_spec.input_video_path == "inputs/videos/test_shot/color.mp4"
        assert "depth" in prompt_spec.control_inputs
        assert "seg" in prompt_spec.control_inputs
        assert prompt_spec.id.startswith("ps_")

    def test_create_prompt_spec_with_custom_paths(self):
        """Test creating a PromptSpec with custom video and control input paths."""
        custom_control_inputs = {"depth": "custom/depth.mp4", "seg": "custom/seg.mp4"}

        prompt_spec = self.prompt_manager.create_prompt_spec(
            "test_shot",
            "Test prompt",
            input_video_path="custom/video.mp4",
            control_inputs=custom_control_inputs,
        )

        assert prompt_spec.input_video_path == "custom/video.mp4"
        assert prompt_spec.control_inputs["depth"] == "custom/depth.mp4"
        assert prompt_spec.control_inputs["seg"] == "custom/seg.mp4"

    def test_create_prompt_spec_upsampled(self):
        """Test creating an upsampled PromptSpec."""
        prompt_spec = self.prompt_manager.create_prompt_spec(
            "test_shot", "Upsampled prompt", is_upsampled=True, parent_prompt_text="Original prompt"
        )

        assert prompt_spec.is_upsampled is True
        assert prompt_spec.parent_prompt_text == "Original prompt"

    def test_create_run_spec(self):
        """Test creating a new RunSpec."""
        # First create a PromptSpec
        prompt_spec = self.prompt_manager.create_prompt_spec("test_shot", "Test prompt")

        # Create RunSpec with custom parameters
        custom_weights = {"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1}
        custom_params = {
            "num_steps": 50,
            "guidance": 10.0,
            "sigma_max": 70.0,
            "blur_strength": "medium",
            "canny_threshold": "medium",
            "fps": 30,
            "seed": 1,
        }

        run_spec = self.prompt_manager.create_run_spec(
            prompt_spec=prompt_spec, control_weights=custom_weights, parameters=custom_params
        )

        assert isinstance(run_spec, RunSpec)
        assert run_spec.prompt_id == prompt_spec.id
        assert run_spec.control_weights == custom_weights
        assert run_spec.parameters["num_steps"] == 50
        assert run_spec.parameters["guidance"] == 10.0
        assert run_spec.parameters["fps"] == 30
        assert run_spec.execution_status == ExecutionStatus.PENDING
        assert run_spec.id.startswith("rs_")

    def test_create_run_spec_with_defaults(self):
        """Test creating a RunSpec with default parameters."""
        prompt_spec = self.prompt_manager.create_prompt_spec("test_shot", "Test prompt")

        run_spec = self.prompt_manager.create_run_spec(prompt_spec)

        assert run_spec.control_weights["vis"] == 0.25
        assert run_spec.control_weights["edge"] == 0.25
        assert run_spec.control_weights["depth"] == 0.25
        assert run_spec.control_weights["seg"] == 0.25
        assert run_spec.parameters["num_steps"] == 35
        assert run_spec.parameters["guidance"] == 7.0

    def test_validate_prompt_spec(self):
        """Test validating a PromptSpec."""
        # Create a valid PromptSpec
        prompt_spec = self.prompt_manager.create_prompt_spec("test_shot", "Test prompt")

        # Test validation
        assert (
            self.prompt_manager.validate_prompt_spec(prompt_spec.id) is False
        )  # ID is not a file path

        # Test with file path
        prompt_files = list(self.prompt_manager.prompts_dir.rglob("*.json"))
        if prompt_files:
            assert self.prompt_manager.validate_prompt_spec(prompt_files[0]) is True

    def test_list_prompts(self):
        """Test listing available prompts."""
        # Create some PromptSpecs
        self.prompt_manager.create_prompt_spec("shot1", "Prompt 1")
        self.prompt_manager.create_prompt_spec("shot2", "Prompt 2")

        # List all prompts
        prompts = self.prompt_manager.list_prompts()
        assert len(prompts) >= 2

        # List with pattern
        filtered_prompts = self.prompt_manager.list_prompts("shot1")
        assert len(filtered_prompts) >= 1
        assert any("shot1" in str(p) for p in filtered_prompts)

    def test_get_prompt_info(self):
        """Test getting prompt information."""
        # Create a PromptSpec
        self.prompt_manager.create_prompt_spec("test_shot", "Test prompt")

        # Get info from the created file
        prompt_files = list(self.prompt_manager.prompts_dir.rglob("*.json"))
        if prompt_files:
            info = self.prompt_manager.get_prompt_info(prompt_files[0])

            assert info["name"] == "test_shot"
            assert info["prompt_text"] == "Test prompt"
            assert info["id"].startswith("ps_")
            assert "depth" in info["control_inputs"]
            assert "seg" in info["control_inputs"]

    def test_invalid_control_weights(self):
        """Test validation of invalid control weights."""
        prompt_spec = self.prompt_manager.create_prompt_spec("test_shot", "Test prompt")

        # This should raise an error with invalid weights
        with pytest.raises(ValueError, match="Invalid control weights"):
            self.prompt_manager.create_run_spec(
                prompt_spec=prompt_spec,
                control_weights={"vis": -0.1, "edge": 0.5, "depth": 0.3, "seg": 0.3},
            )

    def test_invalid_parameters(self):
        """Test validation of invalid parameters."""
        prompt_spec = self.prompt_manager.create_prompt_spec("test_shot", "Test prompt")

        # This should raise an error with invalid parameters
        with pytest.raises(ValueError, match="Invalid parameters"):
            self.prompt_manager.create_run_spec(
                prompt_spec=prompt_spec,
                parameters={
                    "num_steps": 0,
                    "guidance": 7.0,
                    "sigma_max": 70.0,
                    "blur_strength": "medium",
                    "canny_threshold": "medium",
                    "fps": 24,
                    "seed": 1,
                },
            )

    def test_validate_run_spec(self):
        """Test validating a RunSpec."""
        # Create a PromptSpec and RunSpec
        prompt_spec = self.prompt_manager.create_prompt_spec("test_shot", "Test prompt")
        self.prompt_manager.create_run_spec(prompt_spec)

        # Test validation with non-existent file
        assert self.prompt_manager.validate_run_spec("non_existent.json") is False

        # Test with actual file path
        run_files = list(self.prompt_manager.runs_dir.rglob("*.json"))
        if run_files:
            assert self.prompt_manager.validate_run_spec(run_files[0]) is True

    def test_list_runs(self):
        """Test listing available runs."""
        # Create some PromptSpecs and RunSpecs
        prompt_spec1 = self.prompt_manager.create_prompt_spec("shot1", "Prompt 1")
        prompt_spec2 = self.prompt_manager.create_prompt_spec("shot2", "Prompt 2")

        self.prompt_manager.create_run_spec(prompt_spec1)
        self.prompt_manager.create_run_spec(prompt_spec2)

        # List all runs
        runs = self.prompt_manager.list_runs()
        assert len(runs) >= 2

        # List with pattern
        filtered_runs = self.prompt_manager.list_runs("shot1")
        assert len(filtered_runs) >= 1
        assert any("shot1" in str(r) for r in filtered_runs)

    def test_get_run_info(self):
        """Test getting run information."""
        # Create a PromptSpec and RunSpec
        prompt_spec = self.prompt_manager.create_prompt_spec("test_shot", "Test prompt")
        self.prompt_manager.create_run_spec(
            prompt_spec=prompt_spec,
            control_weights={"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2},
        )

        # Get info from the created file
        run_files = list(self.prompt_manager.runs_dir.rglob("*.json"))
        if run_files:
            info = self.prompt_manager.get_run_info(run_files[0])

            assert info["name"] == "test_shot"
            assert info["prompt_id"] == prompt_spec.id
            assert info["id"].startswith("rs_")
            assert info["control_weights"]["vis"] == 0.3
            assert info["control_weights"]["edge"] == 0.3
            assert info["execution_status"] == "pending"


if __name__ == "__main__":
    pytest.main([__file__])
