"""Behavioral tests for CLI prompt-enhance command - TARGET BEHAVIOR.

These tests define the desired behavior of prompt-enhance with WorkflowService.
Enhancement is treated as a run with model_type="enhancement".
Following TDD Gate 1: Write tests for desired behavior.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


class TestPromptEnhanceCommandTarget:
    """Test target behavior of 'cosmos prompt-enhance' with database integration."""

    @pytest.fixture
    def runner(self):
        """Create a CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_service(self):
        """Create a mock WorkflowService with common responses."""
        service = MagicMock()

        # Default prompt response
        service.get_prompt.return_value = {
            "id": "ps_original_123",
            "model_type": "transfer",
            "prompt_text": "simple description",
            "inputs": {
                "video": "/path/to/video.mp4",
                "depth": "/path/to/depth.mp4",
                "seg": "/path/to/seg.mp4",
            },
            "parameters": {"fps": 24},
        }

        # Enhancement run creation response
        service.create_run.return_value = {
            "id": "rs_enhance_run_456",
            "prompt_id": "ps_original_123",
            "model_type": "enhancement",
            "status": "pending",
            "execution_config": {
                "model": "pixtral",
                "type": "enhancement",
                "temperature": 0.7,
            },
            "outputs": {},
            "metadata": {},
            "created_at": "2024-01-01T00:00:00",
        }

        # Enhanced prompt creation response
        service.create_prompt.return_value = {
            "id": "ps_enhanced_789",
            "model_type": "transfer",
            "prompt_text": "A cinematic masterpiece showing...",  # Enhanced text
            "inputs": {
                "video": "/path/to/video.mp4",
                "depth": "/path/to/depth.mp4",
                "seg": "/path/to/seg.mp4",
            },
            "parameters": {"fps": 24, "enhanced": True},
            "created_at": "2024-01-01T00:01:00",
        }

        # Update run with outputs
        service.update_run.return_value = {
            "id": "rs_enhance_run_456",
            "outputs": {"enhanced_prompt_id": "ps_enhanced_789"},
        }

        return service

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_prompt_enhance_creates_enhancement_run(
        self, mock_get_service, mock_get_orchestrator, runner, mock_service
    ):
        """Test that prompt-enhance creates an enhancement run and new prompt."""
        # Setup mocks
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator
        mock_orchestrator.run_prompt_upsampling.return_value = (
            "A cinematic masterpiece showing..."  # Enhanced text
        )

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "prompt-enhance",
                "ps_original_123",  # Uses prompt ID from database
            ],
        )

        # Assertions
        assert result.exit_code == 0
        assert "enhanced" in result.output.lower() or "upsampled" in result.output.lower()
        assert "ps_enhanced_789" in result.output  # New enhanced prompt ID
        assert "rs_enhance_run_456" in result.output  # Enhancement run ID

        # Verify service interactions
        mock_service.get_prompt.assert_called_with("ps_original_123")

        # Should create enhancement run
        create_run_calls = mock_service.create_run.call_args_list
        assert len(create_run_calls) == 1
        run_call = create_run_calls[0]
        assert run_call.kwargs["prompt_id"] == "ps_original_123"
        assert run_call.kwargs["execution_config"]["type"] == "enhancement"

        # Should run upsampling
        mock_orchestrator.run_prompt_upsampling.assert_called_once()

        # Should create enhanced prompt
        create_prompt_calls = mock_service.create_prompt.call_args_list
        assert len(create_prompt_calls) == 1
        prompt_call = create_prompt_calls[0]
        assert "cinematic" in prompt_call.kwargs["prompt_text"].lower()
        assert prompt_call.kwargs["model_type"] == "transfer"
        assert prompt_call.kwargs["inputs"] == mock_service.get_prompt.return_value["inputs"]

        # Should update run with enhanced prompt ID
        mock_service.update_run.assert_called_once()
        update_call = mock_service.update_run.call_args
        assert update_call[0][0] == "rs_enhance_run_456"
        assert "enhanced_prompt_id" in update_call.kwargs["outputs"]

        # Should update run status
        status_calls = [args[0][1] for args in mock_service.update_run_status.call_args_list]
        assert "completed" in status_calls or "success" in status_calls

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_prompt_enhance_with_custom_model(
        self, mock_get_service, mock_get_orchestrator, runner, mock_service
    ):
        """Test prompt-enhance with custom AI model selection."""
        # Setup mock
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator
        mock_orchestrator.run_prompt_upsampling.return_value = "Enhanced text with custom model"

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "prompt-enhance",
                "ps_original_123",
                "--model",
                "gpt-4",  # Custom model
            ],
        )

        assert result.exit_code == 0

        # Check that custom model was used
        create_run_calls = mock_service.create_run.call_args_list
        assert len(create_run_calls) == 1
        run_call = create_run_calls[0]
        assert run_call.kwargs["execution_config"]["model"] == "gpt-4"

    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_prompt_enhance_dry_run(self, mock_get_service, runner, mock_service):
        """Test --dry-run shows preview without executing."""
        # Setup mock
        mock_get_service.return_value = mock_service

        from cosmos_workflow.cli import cli

        result = runner.invoke(
            cli,
            [
                "prompt-enhance",
                "ps_original_123",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0
        assert "dry" in result.output.lower() or "preview" in result.output.lower()
        assert "ps_original_123" in result.output
        assert "simple description" in result.output  # Original prompt shown

        # Should NOT create run or enhanced prompt
        mock_service.create_run.assert_not_called()
        mock_service.create_prompt.assert_not_called()
        mock_service.update_run.assert_not_called()

    @patch("cosmos_workflow.cli.enhance.WorkflowService")
    @patch("cosmos_workflow.cli.enhance.init_database")
    def test_prompt_enhance_not_found(self, mock_init_db, mock_service_class, runner):
        """Test error when prompt ID doesn't exist."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db

        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        mock_service.get_prompt.return_value = None  # Prompt not found

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["prompt-enhance", "ps_nonexistent"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()
        assert "ps_nonexistent" in result.output

    @patch("cosmos_workflow.workflows.workflow_orchestrator.WorkflowOrchestrator")
    @patch("cosmos_workflow.cli.enhance.WorkflowService")
    @patch("cosmos_workflow.cli.enhance.init_database")
    def test_prompt_enhance_handles_upsampling_failure(
        self, mock_init_db, mock_service_class, mock_orchestrator_class, runner, mock_service
    ):
        """Test that enhancement handles AI model failures gracefully."""
        # Setup mocks
        mock_db = MagicMock()
        mock_init_db.return_value = mock_db
        mock_service_class.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator
        mock_orchestrator.run_prompt_upsampling.side_effect = Exception("AI model failed")

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["prompt-enhance", "ps_original_123"])

        assert result.exit_code != 0
        assert "error" in result.output.lower() or "failed" in result.output.lower()

        # Should update run status to failed
        status_calls = mock_service.update_run_status.call_args_list
        if status_calls:
            last_status = status_calls[-1][0][1]
            assert last_status == "failed"

    @patch("cosmos_workflow.cli.base.CLIContext.get_orchestrator")
    @patch("cosmos_workflow.cli.base.CLIContext.get_workflow_service")
    def test_prompt_enhance_tracks_parent_relationship(
        self, mock_get_service, mock_get_orchestrator, runner, mock_service
    ):
        """Test that enhanced prompts track their parent prompt."""
        # Setup mocks
        mock_get_service.return_value = mock_service

        mock_orchestrator = MagicMock()
        mock_get_orchestrator.return_value = mock_orchestrator
        mock_orchestrator.run_prompt_upsampling.return_value = "Enhanced text"

        from cosmos_workflow.cli import cli

        result = runner.invoke(cli, ["prompt-enhance", "ps_original_123"])

        assert result.exit_code == 0

        # Check that parent relationship is tracked
        create_prompt_calls = mock_service.create_prompt.call_args_list
        assert len(create_prompt_calls) == 1
        prompt_call = create_prompt_calls[0]

        # Should include parent reference in parameters or metadata
        params = prompt_call.kwargs.get("parameters", {})
        assert params.get("parent_prompt_id") == "ps_original_123" or params.get("enhanced")
