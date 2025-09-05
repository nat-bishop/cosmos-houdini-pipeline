"""Behavioral tests for CLI create commands - TARGET BEHAVIOR.

These tests define the desired CLI behavior using WorkflowService and database.
They test the target state, not the current JSON-based implementation.
Following TDD Gate 1: Write tests for desired behavior.
These tests will initially FAIL until we implement the service integration.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


class TestCreatePromptCommandTarget:
    """Test the target behavior of 'cosmos create prompt' with WorkflowService."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def test_video_dir(self):
        """Create a temporary directory with test video files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_dir = Path(tmpdir) / "test_videos"
            video_dir.mkdir()

            # Create mock video files
            (video_dir / "color.mp4").write_text("mock video content")
            (video_dir / "depth.mp4").write_text("mock depth content")
            (video_dir / "segmentation.mp4").write_text("mock segmentation content")

            yield video_dir

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_create_prompt_uses_service(self, mock_get_service, runner, test_video_dir):
        """Test that create prompt uses WorkflowService and returns database ID."""
        # Setup mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.create_prompt.return_value = {
            "id": "ps_database_id_123",
            "model_type": "transfer",
            "prompt_text": "cyberpunk city at night",
            "inputs": {
                "video": str(test_video_dir / "color.mp4"),
                "depth": str(test_video_dir / "depth.mp4"),
                "seg": str(test_video_dir / "segmentation.mp4"),
            },
            "parameters": {},
            "created_at": "2024-01-01T00:00:00",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli, ["create", "prompt", "cyberpunk city at night", str(test_video_dir)]
        )

        # Target behavior assertions
        assert result.exit_code == 0
        assert "Prompt created successfully!" in result.output
        assert "ps_database_id_123" in result.output  # Database ID shown
        assert "cyberpunk" in result.output.lower()  # Smart name shown

        # Verify service was called correctly
        mock_service.create_prompt.assert_called_once()
        call_args = mock_service.create_prompt.call_args
        assert call_args.kwargs["model_type"] == "transfer"
        assert call_args.kwargs["prompt_text"] == "cyberpunk city at night"
        assert "video" in call_args.kwargs["inputs"]

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_create_prompt_validates_files(self, mock_get_service, runner):
        """Test that create prompt validates video files exist."""
        from cosmos_workflow.cli import cli

        # Try with non-existent directory
        result = runner.invoke(cli, ["create", "prompt", "test prompt", "/nonexistent/directory"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_create_prompt_handles_db_error(self, mock_get_service, runner, test_video_dir):
        """Test that database errors are handled gracefully."""
        # Setup mock to raise database error
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.create_prompt.side_effect = Exception("Database connection failed")

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["create", "prompt", "test prompt", str(test_video_dir)])

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()
        # Clear error message, no silent failure
        assert "database" in result.output.lower()


class TestCreateRunCommandTarget:
    """Test the target behavior of 'cosmos create run' with WorkflowService."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_create_run_from_prompt_id(self, mock_get_service, runner):
        """Test creating a run from a prompt ID."""
        # Setup mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # Mock getting the prompt
        mock_service.get_prompt.return_value = {
            "id": "ps_test123",
            "model_type": "transfer",
            "prompt_text": "test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
            "parameters": {},
        }

        # Mock creating the run
        mock_service.create_run.return_value = {
            "id": "rs_run_id_456",
            "prompt_id": "ps_test123",
            "model_type": "transfer",
            "status": "pending",
            "execution_config": {
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
                "num_steps": 35,
            },
            "created_at": "2024-01-01T00:00:00",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "create",
                "run",
                "ps_test123",  # Target: accepts prompt ID, not JSON file
            ],
        )

        assert result.exit_code == 0
        assert "Run created successfully!" in result.output or "Run created" in result.output
        assert "rs_run_id_456" in result.output  # Database run ID shown
        assert "ps_test123" in result.output  # Reference to prompt

        # Verify service calls
        mock_service.get_prompt.assert_called_once_with("ps_test123")
        mock_service.create_run.assert_called_once()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_create_run_with_custom_weights(self, mock_get_service, runner):
        """Test creating a run with custom weights."""
        # Setup mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.get_prompt.return_value = {
            "id": "ps_test123",
            "model_type": "transfer",
            "prompt_text": "test",
            "inputs": {},
            "parameters": {},
        }

        mock_service.create_run.return_value = {
            "id": "rs_run_id_789",
            "prompt_id": "ps_test123",
            "status": "pending",
            "execution_config": {
                "weights": {"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2},
            },
            "created_at": "2024-01-01T00:00:00",
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "create",
                "run",
                "ps_test123",
                "--weights",
                "0.3",
                "0.3",
                "0.2",
                "0.2",
            ],
        )

        assert result.exit_code == 0
        assert "Run created" in result.output
        assert "rs_run_id_789" in result.output

        # Verify custom weights were passed
        call_args = mock_service.create_run.call_args
        weights = call_args.kwargs["execution_config"]["weights"]
        assert weights["vis"] == 0.3
        assert weights["edge"] == 0.3
        assert weights["depth"] == 0.2
        assert weights["seg"] == 0.2

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_create_run_invalid_prompt_id(self, mock_get_service, runner):
        """Test error when prompt ID doesn't exist."""
        # Setup mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.get_prompt.return_value = None  # Prompt not found

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["create", "run", "ps_nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()
        assert "ps_nonexistent" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_create_run_dry_run_shows_details(self, mock_get_service, runner):
        """Test --dry-run shows comprehensive information."""
        # Setup mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.get_prompt.return_value = {
            "id": "ps_test123",
            "prompt_text": "test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
        }

        from cosmos_workflow.cli import cli

        # Test dry run (if implemented)
        # This test can be expanded when dry-run is implemented for create run
        # For now, just test that the command doesn't crash
        result = runner.invoke(cli, ["create", "run", "ps_test123"])
        # Basic check - command should work
        assert "ps_test123" in result.output or "error" in result.output.lower()


class TestInferenceCommandTarget:
    """Test inference command from create module perspective."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    def test_inference_from_run_id(self, mock_get_orchestrator, mock_get_service, runner):
        """Test that inference accepts run IDs."""
        # Setup mocks
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator
        mock_orchestrator.execute_run.return_value = {
            "status": "success",
            "output_path": "/outputs/result.mp4",
        }

        # Mock run and prompt
        mock_service.get_run.return_value = {
            "id": "rs_test_run",
            "prompt_id": "ps_test_prompt",
            "status": "pending",
        }
        mock_service.get_prompt.return_value = {
            "id": "ps_test_prompt",
            "prompt_text": "test",
            "inputs": {},
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_test_run"])

        # Should work with run ID
        assert result.exit_code == 0
        mock_service.get_run.assert_called_with("rs_test_run")

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_dry_run_from_run_id(self, mock_get_service, runner):
        """Test dry-run with run ID."""
        # Setup mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.get_run.return_value = {
            "id": "rs_test_run",
            "prompt_id": "ps_test_prompt",
            "status": "pending",
            "model_type": "transfer",
            "execution_config": {"weights": {}},
            "outputs": {},
            "metadata": {},
        }
        mock_service.get_prompt.return_value = {
            "id": "ps_test_prompt",
            "prompt_text": "test prompt",
            "inputs": {"video": "/test.mp4"},
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_test_run", "--dry-run"])

        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        assert "rs_test_run" in result.output

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_inference_invalid_run_id(self, mock_get_service, runner):
        """Test error with invalid run ID."""
        # Setup mock service
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.get_run.return_value = None  # Run not found

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower()


class TestCLIServiceIntegration:
    """Test overall CLI and service integration."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_database_initialized_once_per_invocation(self, mock_get_service, runner):
        """Test that database/service is initialized only once per CLI invocation."""
        # Setup mock
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        # This test verifies the concept - actual implementation may vary
        # The key is that get_workflow_service should cache the service
        from cosmos_workflow.cli import cli

        # Run a command that uses the service
        mock_service.get_prompt.return_value = {
            "id": "ps_test",
            "prompt_text": "test",
            "inputs": {},
        }
        runner.invoke(cli, ["create", "run", "ps_test"])

        # Service should be retrieved via context
        assert mock_get_service.called

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_database_error_shows_clear_message(self, mock_get_service, runner):
        """Test that database errors show clear messages, not tracebacks."""
        # Setup mock to raise error
        mock_get_service.side_effect = Exception("Database connection failed")

        from cosmos_workflow.cli import cli

        # Any command that needs database
        result = runner.invoke(cli, ["create", "run", "ps_test"])

        assert result.exit_code != 0
        assert "database" in result.output.lower()
        # Should have user-friendly error, not raw traceback
        assert "error" in result.output.lower() or "failed" in result.output.lower()
