#!/usr/bin/env python3
"""
Tests for SchemaValidator class.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.prompts.schema_validator import SchemaValidator
from cosmos_workflow.prompts.schemas import ExecutionStatus, PromptSpec, RunSpec


class TestSchemaValidator:
    """Test cases for SchemaValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SchemaValidator()
        self.temp_path = Path("temp_test_files")
        self.temp_path.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        if self.temp_path.exists():
            shutil.rmtree(self.temp_path)

    def test_validate_prompt_spec_valid(self):
        """Test validation of valid PromptSpec JSON file."""
        # Create a valid PromptSpec JSON file
        prompt_data = {
            "id": "ps_test123",
            "name": "test_prompt",
            "prompt": "A beautiful sunset over the ocean",
            "negative_prompt": "bad quality, blurry",
            "input_video_path": "inputs/videos/test.mp4",
            "control_inputs": {"depth": "depth.mp4", "seg": "seg.mp4"},
            "timestamp": "2025-08-29T10:00:00Z",
            "is_upsampled": False,
            "parent_prompt_text": None,
        }

        prompt_file = self.temp_path / "test_prompt.json"
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f)

        result = self.validator.validate_prompt_spec(prompt_file)
        assert result is True

    def test_validate_prompt_spec_invalid_id_format(self):
        """Test validation of PromptSpec with invalid ID format."""
        # Create a PromptSpec JSON file with invalid ID
        prompt_data = {
            "id": "invalid_id",  # Missing ps_ prefix
            "name": "test_prompt",
            "prompt": "A beautiful sunset over the ocean",
            "negative_prompt": "bad quality, blurry",
            "input_video_path": "inputs/videos/test.mp4",
            "control_inputs": {"depth": "depth.mp4", "seg": "seg.mp4"},
            "timestamp": "2025-08-29T10:00:00Z",
            "is_upsampled": False,
            "parent_prompt_text": None,
        }

        prompt_file = self.temp_path / "test_prompt_invalid.json"
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f)

        result = self.validator.validate_prompt_spec(prompt_file)
        assert result is False

    def test_validate_prompt_spec_missing_required_fields(self):
        """Test validation of PromptSpec with missing required fields."""
        # Create a PromptSpec JSON file with missing fields
        prompt_data = {
            "id": "ps_test123",
            "name": "test_prompt",
            # Missing prompt field
            "negative_prompt": "bad quality, blurry",
            "input_video_path": "inputs/videos/test.mp4",
            "control_inputs": {"depth": "depth.mp4", "seg": "seg.mp4"},
            "timestamp": "2025-08-29T10:00:00Z",
            "is_upsampled": False,
            "parent_prompt_text": None,
        }

        prompt_file = self.temp_path / "test_prompt_missing.json"
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f)

        result = self.validator.validate_prompt_spec(prompt_file)
        assert result is False

    def test_validate_prompt_spec_invalid_json(self):
        """Test validation of PromptSpec with invalid JSON."""
        # Create an invalid JSON file
        prompt_file = self.temp_path / "test_prompt_invalid.json"
        with open(prompt_file, "w") as f:
            f.write("invalid json content")

        result = self.validator.validate_prompt_spec(prompt_file)
        assert result is False

    def test_validate_run_spec_valid(self):
        """Test validation of valid RunSpec JSON file."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = True

            # Create a valid RunSpec JSON file
            run_data = {
                "id": "rs_test123",
                "prompt_id": "ps_prompt123",
                "name": "test_run",
                "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                "parameters": {
                    "num_steps": 35,
                    "guidance": 7,
                    "sigma_max": 70,
                    "blur_strength": "medium",
                    "canny_threshold": "medium",
                    "fps": 24,
                    "seed": 1,
                },
                "timestamp": "2025-08-29T10:00:00Z",
                "execution_status": "pending",
                "output_path": "outputs/test_run",
            }

            run_file = self.temp_path / "test_run.json"
            with open(run_file, "w") as f:
                json.dump(run_data, f)

            result = self.validator.validate_run_spec(run_file)
            assert result is True

    def test_validate_run_spec_invalid_id_format(self):
        """Test validation of RunSpec with invalid ID format."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = True

            # Create a RunSpec JSON file with invalid ID
            run_data = {
                "id": "invalid_id",  # Missing rs_ prefix
                "prompt_id": "ps_prompt123",
                "name": "test_run",
                "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                "parameters": {
                    "num_steps": 35,
                    "guidance": 7,
                    "sigma_max": 70,
                    "blur_strength": "medium",
                    "canny_threshold": "medium",
                    "fps": 24,
                    "seed": 1,
                },
                "timestamp": "2025-08-29T10:00:00Z",
                "execution_status": "pending",
                "output_path": "outputs/test_run",
            }

            run_file = self.temp_path / "test_run_invalid.json"
            with open(run_file, "w") as f:
                json.dump(run_data, f)

            result = self.validator.validate_run_spec(run_file)
            assert result is False

    def test_validate_run_spec_invalid_prompt_id_format(self):
        """Test validation of RunSpec with invalid prompt ID format."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = True

            # Create a RunSpec JSON file with invalid prompt_id
            run_data = {
                "id": "rs_test123",
                "prompt_id": "invalid_prompt_id",  # Missing ps_ prefix
                "name": "test_run",
                "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                "parameters": {
                    "num_steps": 35,
                    "guidance": 7,
                    "sigma_max": 70,
                    "blur_strength": "medium",
                    "canny_threshold": "medium",
                    "fps": 24,
                    "seed": 1,
                },
                "timestamp": "2025-08-29T10:00:00Z",
                "execution_status": "pending",
                "output_path": "outputs/test_run",
            }

            run_file = self.temp_path / "test_run_invalid_prompt.json"
            with open(run_file, "w") as f:
                json.dump(run_data, f)

            result = self.validator.validate_run_spec(run_file)
            assert result is False

    def test_validate_run_spec_missing_required_fields(self):
        """Test validation of RunSpec with missing required fields."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = True

            # Create a RunSpec JSON file with missing fields
            run_data = {
                "id": "rs_test123",
                "prompt_id": "ps_prompt123",
                # Missing name field
                "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                "parameters": {
                    "num_steps": 35,
                    "guidance": 7,
                    "sigma_max": 70,
                    "blur_strength": "medium",
                    "canny_threshold": "medium",
                    "fps": 24,
                    "seed": 1,
                },
                "timestamp": "2025-08-29T10:00:00Z",
                "execution_status": "pending",
                "output_path": "outputs/test_run",
            }

            run_file = self.temp_path / "test_run_missing.json"
            with open(run_file, "w") as f:
                json.dump(run_data, f)

            result = self.validator.validate_run_spec(run_file)
            assert result is False

    def test_validate_run_spec_invalid_execution_status(self):
        """Test validation of RunSpec with invalid execution status."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = True

            # Create a RunSpec JSON file with invalid execution status
            run_data = {
                "id": "rs_test123",
                "prompt_id": "ps_prompt123",
                "name": "test_run",
                "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                "parameters": {
                    "num_steps": 35,
                    "guidance": 7,
                    "sigma_max": 70,
                    "blur_strength": "medium",
                    "canny_threshold": "medium",
                    "fps": 24,
                    "seed": 1,
                },
                "timestamp": "2025-08-29T10:00:00Z",
                "execution_status": "invalid_status",  # Invalid status
                "output_path": "outputs/test_run",
            }

            run_file = self.temp_path / "test_run_invalid_status.json"
            with open(run_file, "w") as f:
                json.dump(run_data, f)

            result = self.validator.validate_run_spec(run_file)
            assert result is False

    def test_validate_run_spec_valid_execution_statuses(self):
        """Test validation of RunSpec with all valid execution statuses."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = True

            valid_statuses = ["pending", "running", "success", "failed"]

            for status in valid_statuses:
                run_data = {
                    "id": "rs_test123",
                    "prompt_id": "ps_prompt123",
                    "name": "test_run",
                    "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                    "parameters": {
                        "num_steps": 35,
                        "guidance": 7,
                        "sigma_max": 70,
                        "blur_strength": "medium",
                        "canny_threshold": "medium",
                        "fps": 24,
                        "seed": 1,
                    },
                    "timestamp": "2025-08-29T10:00:00Z",
                    "execution_status": status,
                    "output_path": "outputs/test_run",
                }

                run_file = self.temp_path / f"test_run_{status}.json"
                with open(run_file, "w") as f:
                    json.dump(run_data, f)

                result = self.validator.validate_run_spec(run_file)
                assert result is True

    def test_validate_run_spec_calls_schema_utils(self):
        """Test that validation calls SchemaUtils methods."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = True

            run_data = {
                "id": "rs_test123",
                "prompt_id": "ps_prompt123",
                "name": "test_run",
                "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                "parameters": {
                    "num_steps": 35,
                    "guidance": 7,
                    "sigma_max": 70,
                    "blur_strength": "medium",
                    "canny_threshold": "medium",
                    "fps": 24,
                    "seed": 1,
                },
                "timestamp": "2025-08-29T10:00:00Z",
                "execution_status": "pending",
                "output_path": "outputs/test_run",
            }

            run_file = self.temp_path / "test_run_schema_utils.json"
            with open(run_file, "w") as f:
                json.dump(run_data, f)

            self.validator.validate_run_spec(run_file)

            # Verify SchemaUtils methods were called
            mock_schema_utils.validate_control_weights.assert_called_once_with(
                run_data["control_weights"]
            )
            mock_schema_utils.validate_parameters.assert_called_once_with(run_data["parameters"])

    def test_validate_control_weights_valid(self):
        """Test validation of valid control weights."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True

            weights = {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40}

            result = self.validator.validate_control_weights(weights)
            assert result is True

            # Verify SchemaUtils was called
            mock_schema_utils.validate_control_weights.assert_called_once_with(weights)

    def test_validate_control_weights_invalid(self):
        """Test validation of invalid control weights."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = False

            weights = {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40}

            result = self.validator.validate_control_weights(weights)
            assert result is False

    def test_validate_parameters_valid(self):
        """Test validation of valid parameters."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_parameters.return_value = True

            params = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            result = self.validator.validate_parameters(params)
            assert result is True

    def test_validate_parameters_invalid(self):
        """Test validation of invalid parameters."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_parameters.return_value = False

            params = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            result = self.validator.validate_parameters(params)
            assert result is False

    def test_validate_prompt_spec_edge_cases(self):
        """Test validation of PromptSpec edge cases."""
        # Test with very long prompt text
        long_prompt = "A" * 10000  # Very long prompt
        prompt_data = {
            "id": "ps_test123",
            "name": "test_prompt",
            "prompt": long_prompt,
            "negative_prompt": "bad quality, blurry",
            "input_video_path": "inputs/videos/test.mp4",
            "control_inputs": {"depth": "depth.mp4", "seg": "seg.mp4"},
            "timestamp": "2025-08-29T10:00:00Z",
            "is_upsampled": False,
            "parent_prompt_text": None,
        }

        prompt_file = self.temp_path / "test_prompt_long.json"
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f)

        result = self.validator.validate_prompt_spec(prompt_file)
        assert result is True

    def test_validate_run_spec_edge_cases(self):
        """Test validation of RunSpec edge cases."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = True

            # Test with very long name
            long_name = "A" * 1000  # Very long name
            run_data = {
                "id": "rs_test123",
                "prompt_id": "ps_prompt123",
                "name": long_name,
                "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                "parameters": {
                    "num_steps": 35,
                    "guidance": 7,
                    "sigma_max": 70,
                    "blur_strength": "medium",
                    "canny_threshold": "medium",
                    "fps": 24,
                    "seed": 1,
                },
                "timestamp": "2025-08-29T10:00:00Z",
                "execution_status": "pending",
                "output_path": "outputs/test_run",
            }

            run_file = self.temp_path / "test_run_long.json"
            with open(run_file, "w") as f:
                json.dump(run_data, f)

            result = self.validator.validate_run_spec(run_file)
            assert result is True

    def test_validate_prompt_spec_empty_control_inputs(self):
        """Test validation of PromptSpec with empty control inputs."""
        # Create a PromptSpec JSON file with empty control inputs
        prompt_data = {
            "id": "ps_test123",
            "name": "test_prompt",
            "prompt": "A beautiful sunset over the ocean",
            "negative_prompt": "bad quality, blurry",
            "input_video_path": "inputs/videos/test.mp4",
            "control_inputs": {},  # Empty control inputs
            "timestamp": "2025-08-29T10:00:00Z",
            "is_upsampled": False,
            "parent_prompt_text": None,
        }

        prompt_file = self.temp_path / "test_prompt_empty_controls.json"
        with open(prompt_file, "w") as f:
            json.dump(prompt_data, f)

        result = self.validator.validate_prompt_spec(prompt_file)
        assert result is True

    def test_validate_run_spec_empty_parameters(self):
        """Test validation of RunSpec with empty parameters."""
        with patch("cosmos_workflow.prompts.schema_validator.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.validate_control_weights.return_value = True
            mock_schema_utils.validate_parameters.return_value = False  # Should fail validation

            # Create a RunSpec JSON file with empty parameters
            run_data = {
                "id": "rs_test123",
                "prompt_id": "ps_prompt123",
                "name": "test_run",
                "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
                "parameters": {},  # Empty parameters
                "timestamp": "2025-08-29T10:00:00Z",
                "execution_status": "pending",
                "output_path": "outputs/test_run",
            }

            run_file = self.temp_path / "test_run_empty_params.json"
            with open(run_file, "w") as f:
                json.dump(run_data, f)

            result = self.validator.validate_run_spec(run_file)
            assert result is False  # Should fail because parameters validation fails
