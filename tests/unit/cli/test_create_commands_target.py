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

    @patch("cosmos_workflow.cli.create.WorkflowService")
    @patch("cosmos_workflow.cli.create.init_database")
    def test_create_prompt_uses_service(
        self, mock_init_db, mock_service_class, runner, test_video_dir
    ):
        """Test that create prompt uses WorkflowService and returns database ID."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
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

        # Import after mocking to get mocked CLI
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

    @patch("cosmos_workflow.cli.create.WorkflowService")
    @patch("cosmos_workflow.cli.create.init_database")
    def test_create_prompt_validates_files(self, mock_init_db, mock_service_class, runner):
        """Test that create prompt validates video files exist."""
        from cosmos_workflow.cli import cli

        # Try with non-existent directory
        result = runner.invoke(cli, ["create", "prompt", "test prompt", "/nonexistent/directory"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.create.WorkflowService")
    @patch("cosmos_workflow.cli.create.init_database")
    def test_create_prompt_handles_db_error(
        self, mock_init_db, mock_service_class, runner, test_video_dir
    ):
        """Test that database errors are handled gracefully."""
        # Setup mock to raise database error
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
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

    @patch("cosmos_workflow.cli.create.WorkflowService")
    @patch("cosmos_workflow.cli.create.init_database")
    def test_create_run_from_prompt_id(self, mock_init_db, mock_service_class, runner):
        """Test creating a run from a prompt ID."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

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

    @patch("cosmos_workflow.cli.create.WorkflowService")
    @patch("cosmos_workflow.cli.create.init_database")
    def test_create_run_with_custom_weights(self, mock_init_db, mock_service_class, runner):
        """Test creating a run with custom weights."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_service.get_prompt.return_value = {
            "id": "ps_test123",
            "model_type": "transfer",
            "prompt_text": "test",
            "inputs": {},
            "parameters": {},
        }

        mock_service.create_run.return_value = {
            "id": "rs_custom_weights",
            "prompt_id": "ps_test123",
            "execution_config": {"weights": {"vis": 0.3, "edge": 0.3, "depth": 0.2, "seg": 0.2}},
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli, ["create", "run", "ps_test123", "--weights", "0.3", "0.3", "0.2", "0.2"]
        )

        assert result.exit_code == 0

        # Check that custom weights were passed to service
        call_args = mock_service.create_run.call_args
        weights = call_args.kwargs["execution_config"]["weights"]
        assert weights["vis"] == 0.3
        assert weights["edge"] == 0.3

    @patch("cosmos_workflow.cli.create.WorkflowService")
    @patch("cosmos_workflow.cli.create.init_database")
    def test_create_run_invalid_prompt_id(self, mock_init_db, mock_service_class, runner):
        """Test error when prompt ID doesn't exist."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_prompt.return_value = None  # Prompt not found

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["create", "run", "ps_nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    @patch("cosmos_workflow.cli.create.WorkflowService")
    @patch("cosmos_workflow.cli.create.init_database")
    def test_create_run_dry_run_shows_details(self, mock_init_db, mock_service_class, runner):
        """Test that --dry-run shows prompt details without creating run."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_prompt.return_value = {
            "id": "ps_test123",
            "model_type": "transfer",
            "prompt_text": "cyberpunk transformation",
            "inputs": {"video": "/path/to/video.mp4", "depth": "/path/to/depth.mp4"},
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["create", "run", "ps_test123", "--dry-run"])

        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        assert "cyberpunk transformation" in result.output  # Shows prompt text
        assert "ps_test123" in result.output
        assert "/path/to/video.mp4" in result.output  # Shows inputs

        # Should NOT create a run
        mock_service.create_run.assert_not_called()


class TestInferenceCommandTarget:
    """Test the target behavior of 'cosmos inference' with WorkflowService."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_from_run_id(
        self, mock_init_db, mock_service_class, mock_orchestrator_class, runner
    ):
        """Test inference accepts run ID and updates status."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        # Mock get_run to return run details
        mock_service.get_run.return_value = {
            "id": "rs_test_run",
            "prompt_id": "ps_test123",
            "model_type": "transfer",
            "status": "pending",
            "execution_config": {
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
            },
        }

        # Mock get_prompt for full details
        mock_service.get_prompt.return_value = {
            "id": "ps_test123",
            "prompt_text": "test prompt",
            "inputs": {"video": "/path/to/video.mp4"},
        }

        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.run_from_database.return_value = {"status": "success"}

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "inference",
                "rs_test_run",  # Target: accepts run ID
            ],
        )

        assert result.exit_code == 0
        assert "completed" in result.output.lower() or "success" in result.output.lower()

        # Should update run status
        mock_service.update_run_status.assert_called()

        # Orchestrator should be called with database info
        mock_orchestrator.run_from_database.assert_called_once()

    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_dry_run_from_run_id(self, mock_init_db, mock_service_class, runner):
        """Test --dry-run shows run and prompt details."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service

        mock_service.get_run.return_value = {
            "id": "rs_test_run",
            "prompt_id": "ps_test123",
            "status": "pending",
            "execution_config": {"upscale": True, "upscale_weight": 0.7},
        }

        mock_service.get_prompt.return_value = {
            "id": "ps_test123",
            "prompt_text": "epic transformation",
            "inputs": {"video": "/videos/input.mp4"},
        }

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_test_run", "--dry-run"])

        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        assert "epic transformation" in result.output
        assert "rs_test_run" in result.output
        assert "/videos/input.mp4" in result.output
        assert "0.7" in result.output  # upscale weight shown

    @patch("cosmos_workflow.cli.inference.WorkflowService")
    @patch("cosmos_workflow.cli.inference.init_database")
    def test_inference_invalid_run_id(self, mock_init_db, mock_service_class, runner):
        """Test error when run ID doesn't exist."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_run.return_value = None  # Run not found

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["inference", "rs_nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()


class TestCLIServiceIntegration:
    """Test CLI integration with WorkflowService."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @patch("cosmos_workflow.cli.base.init_database")
    def test_database_initialized_once_per_invocation(self, mock_init_db, runner):
        """Test that database is initialized once per CLI invocation."""
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        from cosmos_workflow.cli import cli

        # Single invocation should initialize once
        runner.invoke(cli, ["--help"])

        # Help doesn't need database, so shouldn't initialize
        mock_init_db.assert_not_called()

        # But commands that need database should initialize
        with patch("cosmos_workflow.cli.create.WorkflowService"):
            runner.invoke(cli, ["create", "prompt", "--help"])
            # Help still doesn't initialize
            mock_init_db.assert_not_called()

    @patch("cosmos_workflow.cli.base.init_database")
    def test_database_error_shows_clear_message(self, mock_init_db, runner):
        """Test that database connection errors show clear messages."""
        mock_init_db.side_effect = Exception("Cannot connect to database")

        from cosmos_workflow.cli import cli

        with patch("cosmos_workflow.cli.create.WorkflowService"):
            with tempfile.TemporaryDirectory() as tmpdir:
                video_dir = Path(tmpdir) / "videos"
                video_dir.mkdir()
                (video_dir / "color.mp4").touch()
                (video_dir / "depth.mp4").touch()
                (video_dir / "segmentation.mp4").touch()

                result = runner.invoke(cli, ["create", "prompt", "test", str(video_dir)])

        assert result.exit_code != 0
        assert "database" in result.output.lower()
        assert "error" in result.output.lower() or "failed" in result.output.lower()
        # Clear message, not a traceback
        assert "Cannot connect" in result.output or "connection" in result.output.lower()
