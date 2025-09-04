"""Unit tests for WorkflowOrchestrator.

Tests the main orchestration logic without requiring external dependencies.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_config_manager():
    """Mock ConfigManager with test configurations."""
    manager = MagicMock()
    manager.get_remote_config.return_value = MagicMock(
        remote_dir="/remote/cosmos", host="192.168.1.100", docker_image="cosmos:latest"
    )
    manager.get_local_config.return_value = MagicMock(notes_dir=Path("test_notes"))
    manager.get_ssh_options.return_value = {
        "hostname": "192.168.1.100",
        "username": "ubuntu",
        "key_filename": "test_key.pem",
    }
    return manager


@pytest.fixture
def mock_ssh_manager():
    """Mock SSHManager with context manager support."""
    ssh = MagicMock()
    ssh.__enter__ = MagicMock(return_value=ssh)
    ssh.__exit__ = MagicMock(return_value=None)
    return ssh


@pytest.fixture
def mock_file_transfer():
    """Mock FileTransferService."""
    transfer = MagicMock()
    transfer.upload_prompt_and_videos = MagicMock()
    transfer.download_results = MagicMock()
    transfer.file_exists_remote = MagicMock(return_value=True)
    return transfer


@pytest.fixture
def mock_docker_executor():
    """Mock DockerExecutor."""
    docker = MagicMock()
    docker.run_inference = MagicMock()
    docker.run_upscaling = MagicMock()
    docker.get_docker_status = MagicMock(return_value="running")
    return docker


@pytest.fixture
def sample_prompt_file(tmp_path):
    """Create a sample prompt file."""
    prompt_file = tmp_path / "test_prompt.json"
    prompt_file.write_text('{"prompt": "test"}')
    return prompt_file


# ============================================================================
# Test Classes
# ============================================================================


class TestWorkflowOrchestratorInit:
    """Test initialization and service creation."""

    def test_init_with_default_config(self):
        """Test initialization with default config file."""
        orchestrator = WorkflowOrchestrator()

        assert orchestrator.config_manager is not None
        assert orchestrator.ssh_manager is None
        assert orchestrator.file_transfer is None
        assert orchestrator.docker_executor is None

    def test_init_with_custom_config_file(self):
        """Test initialization with custom config file path."""
        custom_path = "custom/config.toml"
        with patch("cosmos_workflow.workflows.workflow_orchestrator.ConfigManager") as mock_cm:
            orchestrator = WorkflowOrchestrator(config_file=custom_path)
            mock_cm.assert_called_once_with(custom_path)
            assert orchestrator.config_manager is not None

    def test_initialize_services_creates_all_services(self, mock_config_manager):
        """Test that _initialize_services creates all required services."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch("cosmos_workflow.workflows.workflow_orchestrator.SSHManager") as mock_ssh:
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService"
                ) as mock_ft:
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor"
                    ) as mock_de:
                        orchestrator = WorkflowOrchestrator()
                        orchestrator._initialize_services()

                        # Verify all services were created
                        mock_ssh.assert_called_once()
                        mock_ft.assert_called_once()
                        mock_de.assert_called_once()

                        assert orchestrator.ssh_manager is not None
                        assert orchestrator.file_transfer is not None
                        assert orchestrator.docker_executor is not None

    def test_initialize_services_reuses_existing(self, mock_config_manager, mock_ssh_manager):
        """Test that _initialize_services doesn't recreate existing services."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            orchestrator = WorkflowOrchestrator()

            # Set existing services
            orchestrator.ssh_manager = mock_ssh_manager
            orchestrator.file_transfer = MagicMock()
            orchestrator.docker_executor = MagicMock()

            # Store references
            original_ssh = orchestrator.ssh_manager
            original_ft = orchestrator.file_transfer
            original_docker = orchestrator.docker_executor

            # Call initialize - should not replace existing
            orchestrator._initialize_services()

            assert orchestrator.ssh_manager is original_ssh
            assert orchestrator.file_transfer is original_ft
            assert orchestrator.docker_executor is original_docker


class TestWorkflowOrchestratorHelpers:
    """Test helper methods."""

    def test_get_workflow_type_full_cycle(self):
        """Test workflow type detection for full cycle."""
        orchestrator = WorkflowOrchestrator()

        workflow_type = orchestrator._get_workflow_type(
            inference=True, upscale=True, upload=True, download=True
        )
        assert workflow_type == "full cycle"

    def test_get_workflow_type_inference_only(self):
        """Test workflow type detection for inference only."""
        orchestrator = WorkflowOrchestrator()

        workflow_type = orchestrator._get_workflow_type(
            inference=True, upscale=False, upload=True, download=True
        )
        assert workflow_type == "inference only"

    def test_get_workflow_type_upscaling_only(self):
        """Test workflow type detection for upscaling only."""
        orchestrator = WorkflowOrchestrator()

        workflow_type = orchestrator._get_workflow_type(
            inference=False, upscale=True, upload=False, download=True
        )
        assert workflow_type == "upscaling only"

    def test_get_workflow_type_custom(self):
        """Test workflow type detection for custom workflow."""
        orchestrator = WorkflowOrchestrator()

        workflow_type = orchestrator._get_workflow_type(
            inference=False, upscale=False, upload=True, download=True
        )
        assert workflow_type == "custom"

    def test_get_video_directories_with_override(self):
        """Test getting video directories with explicit override."""
        orchestrator = WorkflowOrchestrator()
        prompt_file = Path("test_prompt.json")

        dirs = orchestrator._get_video_directories(prompt_file, "custom_videos")

        assert len(dirs) == 1
        assert dirs[0] == Path("inputs/videos/custom_videos")

    def test_get_video_directories_default(self):
        """Test getting video directories with default behavior."""
        orchestrator = WorkflowOrchestrator()
        prompt_file = Path("test_prompt.json")

        dirs = orchestrator._get_video_directories(prompt_file, None)

        assert len(dirs) == 1
        assert dirs[0] == Path("inputs/videos/test_prompt")

    def test_get_video_directories_from_run_spec(self, tmp_path):
        """Test getting video directories from RunSpec file."""
        # Create mock RunSpec file
        run_spec_file = tmp_path / "test_rs_abc123.json"

        # Mock the RunSpec and PromptSpec loading (imported inside the method)
        with patch("cosmos_workflow.prompts.schemas.RunSpec") as mock_rs:
            with patch("cosmos_workflow.prompts.schemas.PromptSpec") as mock_ps:
                mock_run_spec = MagicMock()
                mock_run_spec.prompt_id = "ps_123"
                mock_rs.load.return_value = mock_run_spec

                mock_prompt_spec = MagicMock()
                mock_prompt_spec.input_video_path = "/videos/test_video/video.mp4"
                mock_ps.load.return_value = mock_prompt_spec

                # Mock Path.rglob to find prompt spec
                with patch.object(Path, "rglob") as mock_rglob:
                    mock_rglob.return_value = [Path("inputs/prompts/test_123.json")]

                    # Mock Path.parent.exists() for the video path
                    with patch.object(Path, "exists", return_value=True):
                        orchestrator = WorkflowOrchestrator()
                        dirs = orchestrator._get_video_directories(run_spec_file, None)

                        # Should extract parent directory from video path
                        assert len(dirs) == 1


class TestWorkflowOrchestratorStatus:
    """Test status checking functionality."""

    def test_check_remote_status_success(
        self, mock_config_manager, mock_ssh_manager, mock_file_transfer, mock_docker_executor
    ):
        """Test successful remote status check."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()
                        status = orchestrator.check_remote_status()

                        assert status["ssh_status"] == "connected"
                        assert status["docker_status"] == "running"
                        assert status["remote_directory_exists"] is True
                        assert status["remote_directory"] == "/remote/cosmos"

    def test_check_remote_status_connection_failure(self, mock_config_manager):
        """Test remote status check with connection failure."""
        mock_ssh = MagicMock()
        mock_ssh.__enter__.side_effect = Exception("Connection failed")

        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager", return_value=mock_ssh
            ):
                orchestrator = WorkflowOrchestrator()
                status = orchestrator.check_remote_status()

                assert status["ssh_status"] == "failed"
                assert "error" in status
                assert "Connection failed" in status["error"]


class TestWorkflowOrchestratorEdgeCases:
    """Test edge cases and error handling."""

    def test_get_video_directories_from_run_spec_error_handling(self, mock_config_manager):
        """Test video directory handling when RunSpec loading fails."""
        # Create orchestrator
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            orchestrator = WorkflowOrchestrator()

            # Create a RunSpec-like filename
            run_spec_file = Path("inputs/prompts/test_rs_12345.json")

            # Mock RunSpec.load to raise an exception
            with patch("cosmos_workflow.prompts.schemas.RunSpec") as mock_run_spec:
                mock_run_spec.load.side_effect = Exception("Failed to load RunSpec")

                # Should fall back to default behavior
                result = orchestrator._get_video_directories(run_spec_file, None)

                # Should return default based on filename stem
                assert len(result) == 1
                assert result[0] == Path("inputs/videos/test_rs_12345")


class TestWorkflowOrchestratorLogging:
    """Test logging functionality."""

    def test_log_workflow_completion_creates_file(self, mock_config_manager, tmp_path):
        """Test that workflow completion creates log file."""
        # Set up mock config to use temp directory
        mock_config_manager.get_local_config.return_value = MagicMock(notes_dir=tmp_path / "notes")

        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            orchestrator = WorkflowOrchestrator()

            prompt_file = Path("test_prompt.json")
            orchestrator._log_workflow_completion(
                prompt_file, upscaled=True, upscale_weight=0.5, num_gpu=2
            )

            # Check log file was created
            log_file = tmp_path / "notes" / "run_history.log"
            assert log_file.exists()

            # Check log content
            content = log_file.read_text()
            assert "test_prompt.json" in content
            assert "upscaled=True" in content
            assert "upscale_weight=0.5" in content
            assert "num_gpu=2" in content

    def test_log_workflow_failure_creates_file(self, mock_config_manager, tmp_path):
        """Test that workflow failure creates log file."""
        # Set up mock config to use temp directory
        mock_config_manager.get_local_config.return_value = MagicMock(notes_dir=tmp_path / "notes")

        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            orchestrator = WorkflowOrchestrator()

            prompt_file = Path("test_prompt.json")
            duration = "00:05:30"
            orchestrator._log_workflow_failure(prompt_file, error="Test error", duration=duration)

            # Check log file was created
            log_file = tmp_path / "notes" / "run_history.log"
            assert log_file.exists()

            # Check log content
            content = log_file.read_text()
            assert "FAILED" in content
            assert "test_prompt.json" in content
            assert "Test error" in content
            assert duration in content

    def test_log_workflow_completion_appends_to_existing(self, mock_config_manager, tmp_path):
        """Test that workflow completion appends to existing log."""
        # Set up mock config to use temp directory
        mock_config_manager.get_local_config.return_value = MagicMock(notes_dir=tmp_path / "notes")

        # Create existing log file
        notes_dir = tmp_path / "notes"
        notes_dir.mkdir(parents=True)
        log_file = notes_dir / "run_history.log"
        log_file.write_text("Existing log entry\n")

        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            orchestrator = WorkflowOrchestrator()

            prompt_file = Path("test_prompt.json")
            orchestrator._log_workflow_completion(
                prompt_file, upscaled=False, upscale_weight=0.0, num_gpu=1
            )

            # Check log was appended
            content = log_file.read_text()
            assert "Existing log entry" in content
            assert "test_prompt.json" in content
            assert content.count("\n") >= 2  # At least 2 lines


class TestWorkflowOrchestratorRun:
    """Test main run() method and workflows."""

    def test_run_full_workflow_success(
        self,
        mock_config_manager,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        sample_prompt_file,
    ):
        """Test successful full workflow execution."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()

                        # Mock Path operations for video directories
                        with patch.object(Path, "exists", return_value=True):
                            result = orchestrator.run(
                                prompt_file=sample_prompt_file,
                                inference=True,
                                upscale=True,
                                upload=True,
                                download=True,
                                num_gpu=2,
                                cuda_devices="0,1",
                            )

                        # Verify result
                        assert result["status"] == "success"
                        assert result["workflow_type"] == "full cycle"
                        assert "upload" in result["steps_performed"]
                        assert "inference" in result["steps_performed"]
                        assert "upscale" in result["steps_performed"]
                        assert "download" in result["steps_performed"]
                        assert result["num_gpu"] == 2
                        assert result["cuda_devices"] == "0,1"

                        # Verify service calls
                        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
                        mock_docker_executor.run_inference.assert_called_once()
                        mock_docker_executor.run_upscaling.assert_called_once()
                        mock_file_transfer.download_results.assert_called_once()

    def test_run_inference_only_workflow(
        self,
        mock_config_manager,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        sample_prompt_file,
    ):
        """Test inference-only workflow."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()

                        with patch.object(Path, "exists", return_value=True):
                            result = orchestrator.run(
                                prompt_file=sample_prompt_file,
                                inference=True,
                                upscale=False,
                                upload=True,
                                download=True,
                            )

                        assert result["status"] == "success"
                        assert result["workflow_type"] == "inference only"
                        assert "inference" in result["steps_performed"]
                        assert "upscale" not in result["steps_performed"]

                        mock_docker_executor.run_inference.assert_called_once()
                        mock_docker_executor.run_upscaling.assert_not_called()

    def test_run_upscale_only_workflow(
        self,
        mock_config_manager,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        sample_prompt_file,
    ):
        """Test upscale-only workflow."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()

                        result = orchestrator.run(
                            prompt_file=sample_prompt_file,
                            inference=False,
                            upscale=True,
                            upload=False,
                            download=True,
                            upscale_weight=0.7,
                        )

                        assert result["status"] == "success"
                        assert result["workflow_type"] == "upscaling only"
                        assert "upscale" in result["steps_performed"]
                        assert "inference" not in result["steps_performed"]
                        assert "upload" not in result["steps_performed"]
                        assert result["upscale_weight"] == 0.7

                        mock_file_transfer.upload_prompt_and_videos.assert_not_called()
                        mock_docker_executor.run_upscaling.assert_called_once()

    def test_run_with_exception_handling(
        self,
        mock_config_manager,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        sample_prompt_file,
    ):
        """Test workflow with exception handling."""
        # Make docker executor raise an exception
        mock_docker_executor.run_inference.side_effect = Exception("Docker failed")

        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()

                        with patch.object(Path, "exists", return_value=True):
                            with pytest.raises(RuntimeError) as exc_info:
                                orchestrator.run(
                                    prompt_file=sample_prompt_file, inference=True, upscale=False
                                )

                            assert "Docker failed" in str(exc_info.value)

    def test_run_custom_workflow_upload_download_only(
        self,
        mock_config_manager,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        sample_prompt_file,
    ):
        """Test custom workflow with only upload and download."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()

                        with patch.object(Path, "exists", return_value=True):
                            result = orchestrator.run(
                                prompt_file=sample_prompt_file,
                                inference=False,
                                upscale=False,
                                upload=True,
                                download=True,
                            )

                        assert result["status"] == "success"
                        assert result["workflow_type"] == "custom"
                        assert result["steps_performed"] == ["upload", "download"]

                        mock_file_transfer.upload_prompt_and_videos.assert_called_once()
                        mock_file_transfer.download_results.assert_called_once()
                        mock_docker_executor.run_inference.assert_not_called()
                        mock_docker_executor.run_upscaling.assert_not_called()


class TestWorkflowOrchestratorLegacy:
    """Test convenience methods that provide specialized workflow APIs."""

    def test_run_full_cycle_delegates_correctly(
        self,
        mock_config_manager,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        sample_prompt_file,
    ):
        """Test that run_full_cycle delegates to run() correctly."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()

                        with patch.object(Path, "exists", return_value=True):
                            result = orchestrator.run_full_cycle(
                                prompt_file=sample_prompt_file,
                                videos_subdir="test_videos",
                                no_upscale=False,
                                upscale_weight=0.5,
                                num_gpu=2,
                                cuda_devices="0,1",
                            )

                        assert result["status"] == "success"
                        assert result["workflow_type"] == "full cycle"
                        assert result["upscaled"] is True
                        assert result["upscale_weight"] == 0.5

    def test_run_inference_only_delegates_correctly(
        self,
        mock_config_manager,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        sample_prompt_file,
    ):
        """Test that run_inference_only delegates to run() correctly."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()

                        with patch.object(Path, "exists", return_value=True):
                            result = orchestrator.run_inference_only(
                                prompt_file=sample_prompt_file,
                                videos_subdir="test_videos",
                                num_gpu=1,
                                cuda_devices="0",
                            )

                        assert result["status"] == "success"
                        assert result["workflow_type"] == "inference only"
                        assert result["upscaled"] is False
                        assert "inference" in result["steps_performed"]
                        assert "upscale" not in result["steps_performed"]

    def test_run_upscaling_only_delegates_correctly(
        self,
        mock_config_manager,
        mock_ssh_manager,
        mock_file_transfer,
        mock_docker_executor,
        sample_prompt_file,
    ):
        """Test that run_upscaling_only delegates to run() correctly."""
        with patch(
            "cosmos_workflow.workflows.workflow_orchestrator.ConfigManager",
            return_value=mock_config_manager,
        ):
            with patch(
                "cosmos_workflow.workflows.workflow_orchestrator.SSHManager",
                return_value=mock_ssh_manager,
            ):
                with patch(
                    "cosmos_workflow.workflows.workflow_orchestrator.FileTransferService",
                    return_value=mock_file_transfer,
                ):
                    with patch(
                        "cosmos_workflow.workflows.workflow_orchestrator.DockerExecutor",
                        return_value=mock_docker_executor,
                    ):
                        orchestrator = WorkflowOrchestrator()

                        result = orchestrator.run_upscaling_only(
                            prompt_file=sample_prompt_file,
                            upscale_weight=0.8,
                            num_gpu=2,
                            cuda_devices="0,1",
                        )

                        assert result["status"] == "success"
                        assert result["workflow_type"] == "upscaling only"
                        assert result["upscaled"] is True
                        assert result["upscale_weight"] == 0.8
                        assert "upscale" in result["steps_performed"]
                        assert "upload" not in result["steps_performed"]
