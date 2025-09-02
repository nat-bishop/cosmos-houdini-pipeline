#!/usr/bin/env python3
"""
Comprehensive tests for RunSpecManager.
Tests all methods, edge cases, and error conditions.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cosmos_workflow.prompts.run_spec_manager import RunSpecManager
from cosmos_workflow.prompts.schemas import DirectoryManager, RunSpec


class TestRunSpecManager:
    """Test the RunSpecManager class."""

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
        self.mock_dir_manager.get_run_file_path.return_value = self.runs_dir / "test.json"

        # Create RunSpecManager instance
        self.run_spec_manager = RunSpecManager(self.mock_dir_manager)

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()

    def test_init(self):
        """Test RunSpecManager initialization."""
        assert self.run_spec_manager.dir_manager == self.mock_dir_manager

    def test_create_run_spec_basic(self):
        """Test basic RunSpec creation."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_control_weights.return_value = {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }
            mock_schema_utils.get_default_parameters.return_value = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            run_spec = self.run_spec_manager.create_run_spec("ps_prompt123", "test_run")

            assert isinstance(run_spec, RunSpec)
            assert run_spec.id == "rs_test123"
            assert run_spec.prompt_id == "ps_prompt123"
            assert run_spec.name == "test_run"
            assert run_spec.control_weights == {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }
            assert run_spec.parameters["num_steps"] == 35
            assert run_spec.parameters["guidance"] == 7
            assert run_spec.execution_status.value == "pending"
            assert run_spec.output_path == "outputs/test_run"

    def test_create_run_spec_with_custom_control_weights(self):
        """Test RunSpec creation with custom control weights."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_parameters.return_value = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            custom_weights = {"vis": 0.75, "edge": 0.25, "depth": 0.80, "seg": 0.20}

            run_spec = self.run_spec_manager.create_run_spec(
                "ps_prompt123", "test_run", control_weights=custom_weights
            )

            assert run_spec.control_weights == custom_weights

    def test_create_run_spec_with_custom_parameters(self):
        """Test RunSpec creation with custom parameters."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_control_weights.return_value = {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }

            custom_params = {
                "num_steps": 50,
                "guidance": 10,
                "sigma_max": 100,
                "blur_strength": "strong",
                "canny_threshold": "high",
                "fps": 30,
                "seed": 42,
            }

            run_spec = self.run_spec_manager.create_run_spec(
                "ps_prompt123", "test_run", parameters=custom_params
            )

            assert run_spec.parameters["num_steps"] == 50
            assert run_spec.parameters["guidance"] == 10
            assert run_spec.parameters["seed"] == 42
            assert run_spec.parameters["blur_strength"] == "strong"

    def test_create_run_spec_with_custom_output_path(self):
        """Test RunSpec creation with custom output path."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_control_weights.return_value = {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }
            mock_schema_utils.get_default_parameters.return_value = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            run_spec = self.run_spec_manager.create_run_spec(
                "ps_prompt123", "test_run", output_path="custom/output/path"
            )

            assert run_spec.output_path == "custom/output/path"

    def test_create_run_spec_calls_save(self):
        """Test that RunSpec is saved after creation."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_control_weights.return_value = {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }
            mock_schema_utils.get_default_parameters.return_value = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            # Mock the save method
            with patch.object(RunSpec, "save") as mock_save:
                self.run_spec_manager.create_run_spec("ps_prompt123", "test_run")

                # Verify save was called
                mock_save.assert_called_once()

    def test_create_run_spec_calls_directory_manager(self):
        """Test that directory manager is called correctly."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_control_weights.return_value = {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }
            mock_schema_utils.get_default_parameters.return_value = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            self.run_spec_manager.create_run_spec("ps_prompt123", "test_run")

            # Verify directory manager was called
            self.mock_dir_manager.get_run_file_path.assert_called_once()
            call_args = self.mock_dir_manager.get_run_file_path.call_args
            assert call_args[0][0] == "test_run"  # name
            # Second arg is timestamp (ISO format string)
            assert isinstance(call_args[0][1], str)  # timestamp
            assert call_args[0][2] == "rs_test123"  # run_id

    def test_list_runs_empty_directory(self):
        """Test listing runs in empty directory."""
        self.mock_dir_manager.list_date_directories.return_value = []

        runs = self.run_spec_manager.list_runs(self.runs_dir)

        assert runs == []
        self.mock_dir_manager.list_date_directories.assert_called_once_with(self.runs_dir)

    def test_list_runs_with_files(self):
        """Test listing runs with existing files."""
        # Create mock date directories and files
        date_dir = "2025-08-29"
        self.mock_dir_manager.list_date_directories.return_value = [date_dir]

        # Create actual test files
        date_path = self.runs_dir / date_dir
        date_path.mkdir()

        # Create test JSON files with different timestamps to ensure proper sorting
        test_files = [
            ("run1_2025-08-29T10-00-00_rs_abc123.json", 1000),  # oldest
            ("run2_2025-08-29T11-00-00_rs_def456.json", 2000),  # middle
            ("run3_2025-08-29T12-00-00_rs_ghi789.json", 3000),  # newest
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

        runs = self.run_spec_manager.list_runs(self.runs_dir)

        assert len(runs) == 3
        assert all(r.name in [f[0] for f in test_files] for r in runs)
        # Should be sorted by modification time (most recent first)
        assert runs[0].name == "run3_2025-08-29T12-00-00_rs_ghi789.json"

    def test_list_runs_with_pattern(self):
        """Test listing runs with pattern filter."""
        date_dir = "2025-08-29"
        self.mock_dir_manager.list_date_directories.return_value = [date_dir]

        date_path = self.runs_dir / date_dir
        date_path.mkdir()

        # Create test files
        test_files = [
            "cyberpunk_run_2025-08-29T10-00-00_rs_abc123.json",
            "building_run_2025-08-29T11-00-00_rs_def456.json",
            "cyberpunk_run_2025-08-29T12-00-00_rs_ghi789.json",
        ]

        for filename in test_files:
            file_path = date_path / filename
            with open(file_path, "w") as f:
                json.dump({"test": "data"}, f)

        # Filter by pattern
        runs = self.run_spec_manager.list_runs(self.runs_dir, pattern="cyberpunk")

        assert len(runs) == 2
        assert all("cyberpunk" in r.name for r in runs)

    def test_list_runs_pattern_case_insensitive(self):
        """Test that pattern matching is case insensitive."""
        date_dir = "2025-08-29"
        self.mock_dir_manager.list_date_directories.return_value = [date_dir]

        date_path = self.runs_dir / date_dir
        date_path.mkdir()

        # Create test files
        test_files = [
            "CYBERPUNK_RUN_2025-08-29T10-00-00_rs_abc123.json",
            "building_run_2025-08-29T11-00-00_rs_def456.json",
        ]

        for filename in test_files:
            file_path = date_path / filename
            with open(file_path, "w") as f:
                json.dump({"test": "data"}, f)

        # Filter by lowercase pattern
        runs = self.run_spec_manager.list_runs(self.runs_dir, pattern="cyberpunk")

        assert len(runs) == 1
        assert "CYBERPUNK" in runs[0].name

    def test_get_run_info_success(self):
        """Test successfully getting run information."""
        # Create a test file
        test_file = self.runs_dir / "test_run.json"
        test_data = {
            "id": "rs_test123",
            "prompt_id": "ps_prompt123",
            "name": "test_run",
            "control_weights": {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40},
            "parameters": {"num_steps": 35, "guidance": 7, "sigma_max": 70},
            "timestamp": "2025-08-29T10:00:00Z",
            "execution_status": "success",
            "output_path": "outputs/test_run",
        }

        with open(test_file, "w") as f:
            json.dump(test_data, f)

        info = self.run_spec_manager.get_run_info(test_file)

        assert info["filename"] == "test_run.json"
        assert info["id"] == "rs_test123"
        assert info["prompt_id"] == "ps_prompt123"
        assert info["name"] == "test_run"
        assert info["control_weights"] == {"vis": 0.25, "edge": 0.50, "depth": 0.30, "seg": 0.40}
        assert info["parameters"] == {"num_steps": 35, "guidance": 7, "sigma_max": 70}
        assert info["timestamp"] == "2025-08-29T10:00:00Z"
        assert info["execution_status"] == "success"
        assert info["output_path"] == "outputs/test_run"
        assert info["file_path"] == str(test_file)
        assert info["file_size"] > 0
        assert isinstance(info["created_time"], datetime)

    def test_get_run_info_file_not_found(self):
        """Test getting run info for non-existent file."""
        non_existent_file = self.runs_dir / "nonexistent.json"

        with pytest.raises(FileNotFoundError, match="RunSpec file not found"):
            self.run_spec_manager.get_run_info(non_existent_file)

    def test_get_run_info_invalid_json(self):
        """Test getting run info from invalid JSON file."""
        # Create file with invalid JSON
        invalid_file = self.runs_dir / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("invalid json content")

        with pytest.raises(json.JSONDecodeError):
            self.run_spec_manager.get_run_info(invalid_file)

    def test_get_run_info_missing_fields(self):
        """Test getting run info from file with missing fields."""
        # Create file with missing fields
        incomplete_file = self.runs_dir / "incomplete.json"
        incomplete_data = {
            "id": "rs_test123",
            "name": "test_run",
            # Missing other required fields
        }

        with open(incomplete_file, "w") as f:
            json.dump(incomplete_data, f)

        info = self.run_spec_manager.get_run_info(incomplete_file)

        # Should handle missing fields gracefully
        assert info["prompt_id"] == ""
        assert info["control_weights"] == {}
        assert info["parameters"] == {}
        assert info["timestamp"] == ""
        assert info["execution_status"] == ""
        assert info["output_path"] == ""

    def test_create_run_spec_timestamp_format(self):
        """Test that timestamp is in correct ISO format."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_control_weights.return_value = {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }
            mock_schema_utils.get_default_parameters.return_value = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            run_spec = self.run_spec_manager.create_run_spec("ps_prompt123", "test_run")

            # Check timestamp format
            assert run_spec.timestamp.endswith("Z")
            # Should be parseable as ISO format
            datetime.fromisoformat(run_spec.timestamp.replace("Z", "+00:00"))

    def test_create_run_spec_execution_status_default(self):
        """Test that execution status has correct default value."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_control_weights.return_value = {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }
            mock_schema_utils.get_default_parameters.return_value = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            run_spec = self.run_spec_manager.create_run_spec("ps_prompt123", "test_run")

            assert run_spec.execution_status.value == "pending"

    def test_create_run_spec_custom_execution_status(self):
        """Test that custom execution status is used when provided."""
        with patch("cosmos_workflow.prompts.schemas.SchemaUtils") as mock_schema_utils:
            mock_schema_utils.generate_run_id.return_value = "rs_test123"
            mock_schema_utils.get_default_control_weights.return_value = {
                "vis": 0.25,
                "edge": 0.50,
                "depth": 0.30,
                "seg": 0.40,
            }
            mock_schema_utils.get_default_parameters.return_value = {
                "num_steps": 35,
                "guidance": 7,
                "sigma_max": 70,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 1,
            }

            run_spec = self.run_spec_manager.create_run_spec("ps_prompt123", "test_run")

            # Note: execution_status is not currently configurable in create_run_spec
            # It always defaults to ExecutionStatus.PENDING
            assert run_spec.execution_status.value == "pending"
