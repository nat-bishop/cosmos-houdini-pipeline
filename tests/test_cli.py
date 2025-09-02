"""
Tests for the Cosmos CLI interface.

This module provides comprehensive testing for all CLI commands using Click's
CliRunner. Tests focus on user-visible behavior: outputs, exit codes, and
file operations.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cosmos_workflow.cli import cli

# =============================================================================
# CLI-SPECIFIC TEST FIXTURES
# =============================================================================
# Note: Using shared fixtures from conftest.py for common mocks
# Only CLI-specific fixtures are defined here


@pytest.fixture
def cli_runner():
    """Provide a CliRunner instance for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_orchestrator():
    """Mock WorkflowOrchestrator to avoid real SSH/Docker operations."""
    # The new CLI imports WorkflowOrchestrator differently
    with patch(
        "cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator"
    ) as mock_class:
        orchestrator = MagicMock()
        mock_class.return_value = orchestrator

        # Setup default successful responses
        orchestrator.check_remote_status.return_value = {
            "ssh_status": "connected",
            "remote_directory": "/remote/cosmos",
            "remote_directory_exists": True,
            "docker_status": {
                "docker_running": True,
                "available_images": ["cosmos:latest"],
                "running_containers": 0,
            },
        }

        orchestrator.run_full_cycle.return_value = {
            "success": True,
            "inference_output": "Inference complete",
            "upscale_output": "Upscaling complete",
        }

        orchestrator.run_inference_only.return_value = {
            "success": True,
            "output": "Inference complete",
        }

        yield orchestrator


@pytest.fixture
def sample_prompt_spec_file(temp_dir, sample_prompt_spec):
    """Create a sample PromptSpec JSON file for CLI testing.

    Uses the sample_prompt_spec from conftest.py and saves it as a JSON file.
    """
    spec_file = temp_dir / "test_prompt.json"
    spec_file.write_text(json.dumps(sample_prompt_spec.to_dict(), indent=2))
    return spec_file


# =============================================================================
# TEST HELPERS
# =============================================================================


def assert_success(result, expected_output=None):
    """Assert that a CLI command succeeded."""
    assert result.exit_code == 0, f"Command failed: {result.output}"
    if expected_output:
        assert expected_output.lower() in result.output.lower()


def assert_failure(result, expected_error=None):
    """Assert that a CLI command failed with expected error."""
    assert result.exit_code != 0, f"Command should have failed: {result.output}"
    if expected_error:
        assert expected_error.lower() in result.output.lower()


def extract_json_path(output):
    """Extract JSON file path from CLI output."""
    import re

    # Look for paths ending in .json
    match = re.search(r"([\w/\\]+\.json)", output)
    if match:
        return Path(match.group(1))
    return None


# =============================================================================
# BASIC CLI TESTS
# =============================================================================


class TestCLIBasics:
    """Test core CLI functionality."""

    def test_cli_help(self, cli_runner):
        """Test that help text is displayed."""
        result = cli_runner.invoke(cli, ["--help"])
        assert_success(result)
        assert "Cosmos-Transfer1 Workflow Orchestrator" in result.output
        assert "Commands:" in result.output

    def test_cli_version(self, cli_runner):
        """Test version display."""
        result = cli_runner.invoke(cli, ["--version"])
        assert_success(result)
        assert "version" in result.output.lower()
        assert "0.1.0" in result.output

    def test_cli_verbose_mode(self, cli_runner):
        """Test verbose flag is accepted."""
        result = cli_runner.invoke(cli, ["--verbose", "--help"])
        assert_success(result)

    def test_invalid_command(self, cli_runner):
        """Test error handling for invalid commands."""
        result = cli_runner.invoke(cli, ["invalid-command"])
        assert_failure(result)
        assert "No such command" in result.output


# =============================================================================
# CREATE COMMAND TESTS
# =============================================================================


class TestCreateCommands:
    """Test 'create' command group."""

    def test_create_help(self, cli_runner):
        """Test create command help."""
        result = cli_runner.invoke(cli, ["create", "--help"])
        assert_success(result)
        assert "Create prompts and run specifications" in result.output

    @patch("cosmos_workflow.utils.smart_naming.generate_smart_name")
    @patch("cosmos_workflow.prompts.schemas.DirectoryManager")
    def test_create_prompt_minimal(self, mock_dir_manager, mock_smart_name, cli_runner, temp_dir):
        """Test creating prompt with minimal arguments."""
        # Setup mocks
        mock_smart_name.return_value = "futuristic_city"
        mock_dir_instance = MagicMock()
        mock_dir_manager.return_value = mock_dir_instance

        # Create prompt file path that will be "saved"
        prompt_file = temp_dir / "test.json"
        mock_dir_instance.get_prompt_file_path.return_value = prompt_file

        # Run command
        result = cli_runner.invoke(cli, ["create", "prompt", "A futuristic city"])

        # Verify success
        assert_success(result, "Prompt created successfully")
        # The new CLI might reverse the word order in names
        assert "futuristic" in result.output and "city" in result.output

        # Verify smart name was called
        mock_smart_name.assert_called_once_with("A futuristic city", max_length=30)

    @patch("cosmos_workflow.prompts.schemas.DirectoryManager")
    def test_create_prompt_with_name(self, mock_dir_manager, cli_runner, temp_dir):
        """Test creating prompt with explicit name."""
        # Setup mocks
        mock_dir_instance = MagicMock()
        mock_dir_manager.return_value = mock_dir_instance
        prompt_file = temp_dir / "my_scene.json"
        mock_dir_instance.get_prompt_file_path.return_value = prompt_file

        # Run command
        result = cli_runner.invoke(
            cli,
            ["create", "prompt", "Test prompt", "--name", "my_scene"],
        )

        # Verify success
        assert_success(result, "Prompt created successfully")
        assert "my_scene" in result.output

    @patch("cosmos_workflow.prompts.schemas.DirectoryManager")
    def test_create_prompt_with_video(self, mock_dir_manager, cli_runner, temp_dir):
        """Test creating prompt with custom video path."""
        # Setup mocks
        mock_dir_instance = MagicMock()
        mock_dir_manager.return_value = mock_dir_instance
        prompt_file = temp_dir / "test.json"
        mock_dir_instance.get_prompt_file_path.return_value = prompt_file

        # Run command
        result = cli_runner.invoke(
            cli,
            ["create", "prompt", "Test", "--video", "custom/video.mp4"],
        )

        # Verify success
        assert_success(result, "Prompt created successfully")
        assert "custom/video.mp4" in result.output

    def test_create_prompt_missing_text(self, cli_runner):
        """Test error when prompt text is missing."""
        result = cli_runner.invoke(cli, ["create", "prompt"])
        assert_failure(result, "Missing argument")


# =============================================================================
# STATUS COMMAND TESTS
# =============================================================================


class TestStatusCommand:
    """Test 'status' command."""

    def test_status_connected(self, cli_runner, mock_orchestrator):
        """Test status command when remote is connected."""
        result = cli_runner.invoke(cli, ["status"])

        assert_success(result)
        assert "Remote Instance Status" in result.output
        assert "Connected" in result.output
        assert "Docker Running" in result.output

        # Verify orchestrator was called
        mock_orchestrator.check_remote_status.assert_called_once()

    def test_status_disconnected(self, cli_runner, mock_orchestrator):
        """Test status command when remote is disconnected."""
        # Setup disconnected status
        mock_orchestrator.check_remote_status.return_value = {
            "ssh_status": "disconnected",
            "error": "Connection refused",
        }

        result = cli_runner.invoke(cli, ["status"])

        assert_success(result)  # Command itself succeeds even if connection fails
        assert "Disconnected" in result.output
        assert "Connection refused" in result.output

    def test_status_with_verbose(self, cli_runner, mock_orchestrator):
        """Test status command in verbose mode shows more details."""
        result = cli_runner.invoke(cli, ["--verbose", "status"])

        assert_success(result)
        assert "Docker Images" in result.output
        assert "Running Containers" in result.output


# =============================================================================
# INFERENCE COMMAND TESTS
# =============================================================================


class TestInferenceCommand:
    """Test 'inference' command."""

    def test_inference_with_file(self, cli_runner, mock_orchestrator, sample_prompt_spec_file):
        """Test basic inference command with prompt file."""
        result = cli_runner.invoke(cli, ["inference", str(sample_prompt_spec_file)])

        assert_success(result, "completed")

        # Verify orchestrator was called with correct method
        mock_orchestrator.run_full_cycle.assert_called_once()

    def test_inference_no_upscale(self, cli_runner, mock_orchestrator, sample_prompt_spec_file):
        """Test inference without upscaling."""
        result = cli_runner.invoke(
            cli,
            ["inference", str(sample_prompt_spec_file), "--no-upscale"],
        )

        assert_success(result, "completed")

        # Verify inference-only method was called
        mock_orchestrator.run_inference_only.assert_called_once()
        mock_orchestrator.run_full_cycle.assert_not_called()

    def test_inference_missing_file(self, cli_runner):
        """Test error when spec file doesn't exist."""
        result = cli_runner.invoke(cli, ["inference", "nonexistent.json"])
        assert_failure(result)
        # Click handles file validation

    def test_inference_with_custom_weight(
        self, cli_runner, mock_orchestrator, sample_prompt_spec_file
    ):
        """Test inference with custom upscale weight."""
        result = cli_runner.invoke(
            cli,
            ["inference", str(sample_prompt_spec_file), "--upscale-weight", "0.7"],
        )

        assert_success(result)

        # Check the weight was passed correctly
        call_args = mock_orchestrator.run_full_cycle.call_args
        assert call_args.kwargs["upscale_weight"] == 0.7

    # --dry-run tests (TDD - these will fail initially)
    def test_inference_dry_run_prevents_execution(
        self, cli_runner, mock_orchestrator, sample_prompt_spec_file
    ):
        """Test that --dry-run prevents actual execution."""
        result = cli_runner.invoke(
            cli,
            ["inference", str(sample_prompt_spec_file), "--dry-run"],
        )

        assert_success(result)

        # Should show dry run mode
        assert "DRY RUN" in result.output or "dry run" in result.output.lower()

        # Should NOT execute actual operations
        mock_orchestrator.run_full_cycle.assert_not_called()
        mock_orchestrator.run_inference_only.assert_not_called()

    def test_inference_dry_run_shows_plan(
        self, cli_runner, mock_orchestrator, sample_prompt_spec_file
    ):
        """Test that --dry-run shows what would happen."""
        result = cli_runner.invoke(
            cli,
            ["inference", str(sample_prompt_spec_file), "--dry-run"],
        )

        assert_success(result)

        # Should describe what would happen
        output_lower = result.output.lower()
        assert any(word in output_lower for word in ["would", "will", "plan", "preview"])
        assert "upload" in output_lower or "transfer" in output_lower
        assert "inference" in output_lower or "execute" in output_lower

    def test_inference_dry_run_with_no_upscale(
        self, cli_runner, mock_orchestrator, sample_prompt_spec_file
    ):
        """Test --dry-run combined with --no-upscale."""
        result = cli_runner.invoke(
            cli,
            ["inference", str(sample_prompt_spec_file), "--dry-run", "--no-upscale"],
        )

        assert_success(result)

        # Should indicate no upscaling in dry run
        output_lower = result.output.lower()
        assert "dry run" in output_lower
        assert "no upscaling" in output_lower or "inference only" in output_lower

        # Should not execute
        mock_orchestrator.run_full_cycle.assert_not_called()
        mock_orchestrator.run_inference_only.assert_not_called()


# =============================================================================
# PREPARE COMMAND TESTS
# =============================================================================


class TestPrepareCommand:
    """Test 'prepare' command."""

    @patch("cosmos_workflow.local_ai.cosmos_sequence.CosmosSequenceValidator")
    @patch("cosmos_workflow.local_ai.cosmos_sequence.CosmosVideoConverter")
    def test_prepare_basic(self, mock_converter, mock_validator, cli_runner, temp_dir):
        """Test basic prepare command."""
        # Setup mocks
        mock_validator_instance = MagicMock()
        mock_validator.return_value = mock_validator_instance

        # Mock valid sequence
        sequence_info = MagicMock()
        sequence_info.valid = True
        sequence_info.issues = []
        mock_validator_instance.validate.return_value = sequence_info

        mock_converter_instance = MagicMock()
        mock_converter.return_value = mock_converter_instance
        mock_converter_instance.convert_sequence.return_value = {
            "success": True,
            "output_dir": str(temp_dir / "videos" / "test"),
        }

        # Mock metadata generation (needed to avoid MagicMock rendering error)
        metadata = MagicMock()
        metadata.name = "test_scene"
        metadata.frame_count = 10
        metadata.resolution = (1920, 1080)
        metadata.fps = 24
        metadata.control_inputs = {"color": "color.mp4"}
        metadata.video_path = "color.mp4"
        metadata.description = "Test description"
        mock_converter_instance.generate_metadata.return_value = metadata

        # Create a dummy input directory
        input_dir = temp_dir / "renders"
        input_dir.mkdir()

        result = cli_runner.invoke(cli, ["prepare", str(input_dir)])

        # Should succeed without dry-run
        assert_success(result, "Inference inputs prepared")
        mock_converter_instance.convert_sequence.assert_called_once()

    @patch("cosmos_workflow.local_ai.cosmos_sequence.CosmosSequenceValidator")
    def test_prepare_dry_run_prevents_conversion(self, mock_validator, cli_runner, temp_dir):
        """Test that --dry-run prevents actual video conversion."""
        # Setup validator mock
        mock_validator_instance = MagicMock()
        mock_validator.return_value = mock_validator_instance

        # Mock valid sequence with details
        sequence_info = MagicMock()
        sequence_info.valid = True
        sequence_info.issues = []
        sequence_info.sequences = {
            "color": {"count": 10, "pattern": "color.####.png"},
            "depth": {"count": 10, "pattern": "depth.####.png"},
        }
        sequence_info.frame_count = 10
        sequence_info.resolution = (1920, 1080)
        mock_validator_instance.validate.return_value = sequence_info

        # Create input directory
        input_dir = temp_dir / "renders"
        input_dir.mkdir()

        result = cli_runner.invoke(cli, ["prepare", str(input_dir), "--dry-run"])

        assert_success(result)

        # Should show dry run mode
        assert "DRY RUN" in result.output or "dry run" in result.output.lower()

        # Should validate but not convert
        mock_validator_instance.validate.assert_called_once()

        # Should describe what would happen
        output_lower = result.output.lower()
        assert "would" in output_lower
        # Check for output files mentioned (*.mp4 files)
        assert ".mp4" in output_lower or "frames" in output_lower

    @patch("cosmos_workflow.local_ai.cosmos_sequence.CosmosSequenceValidator")
    def test_prepare_dry_run_shows_details(self, mock_validator, cli_runner, temp_dir):
        """Test that --dry-run shows conversion details."""
        # Setup validator mock with detailed sequence info
        mock_validator_instance = MagicMock()
        mock_validator.return_value = mock_validator_instance

        sequence_info = MagicMock()
        sequence_info.valid = True
        sequence_info.issues = []
        sequence_info.sequences = {
            "color": {"count": 120, "pattern": "color.####.png"},
            "depth": {"count": 120, "pattern": "depth.####.png"},
            "segmentation": {"count": 120, "pattern": "seg.####.png"},
        }
        sequence_info.frame_count = 120
        sequence_info.resolution = (1920, 1080)
        mock_validator_instance.validate.return_value = sequence_info

        input_dir = temp_dir / "renders"
        input_dir.mkdir()

        result = cli_runner.invoke(
            cli, ["prepare", str(input_dir), "--dry-run", "--fps", "30", "--name", "test_scene"]
        )

        assert_success(result)

        # Should show sequence details
        assert "120" in result.output  # frame count
        assert "1920" in result.output or "1080" in result.output  # resolution
        assert "color" in result.output.lower()
        assert "depth" in result.output.lower()


# =============================================================================
# PROMPT-ENHANCE COMMAND TESTS
# =============================================================================


class TestPromptEnhanceCommand:
    """Test 'prompt-enhance' command."""

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    def test_prompt_enhance_dry_run(
        self, mock_orchestrator_class, cli_runner, sample_prompt_spec_file
    ):
        """Test that --dry-run prevents AI API calls."""
        # Setup mock
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        result = cli_runner.invoke(
            cli,
            ["prompt-enhance", str(sample_prompt_spec_file), "--dry-run"],
        )

        assert_success(result)

        # Should show dry run mode
        assert "DRY RUN" in result.output or "dry run" in result.output.lower()

        # Should NOT call the upsampling method
        mock_orchestrator.run_single_prompt_upsampling.assert_not_called()

        # Should describe what would happen
        output_lower = result.output.lower()
        assert "would" in output_lower
        assert "enhance" in output_lower or "upsample" in output_lower


# =============================================================================
# RUN WITH PYTEST
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
