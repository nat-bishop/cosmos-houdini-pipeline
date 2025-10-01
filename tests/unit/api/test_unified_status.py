"""Tests for unified status tracking (Phase 4).

Tests get_active_operations and enhanced check_status functionality.
"""

from unittest.mock import MagicMock, patch

from cosmos_workflow.api import CosmosAPI


class TestSimplifiedActiveOperations:
    """Test get_active_operations functionality for single-container system."""

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_with_run_and_container(self, mock_executor, mock_repo, mock_db):
        """Test normal case: one run with matching container."""
        # Setup mocks
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Mock a running run from database
        active_run = {
            "id": "run_abc123",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"container_id": "container_111"},
            "prompt_id": "ps_12345",
        }
        mock_repo_instance.list_runs.return_value = [active_run]

        # Mock container from Docker
        container = {
            "id": "container_111aaa",
            "id_short": "container_111",
            "name": "cosmos_transfer_abc123",
            "status": "Up 5 minutes",
        }

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance
        # Mock the nested docker_executor attribute correctly
        api.orchestrator.docker_executor = MagicMock()
        api.orchestrator.docker_executor.get_active_container.return_value = container

        result = api.get_active_operations()

        # Check structure - simplified for single container system
        assert "active_run" in result
        assert "container" in result

        # Check the run details
        assert result["active_run"]["id"] == "run_abc123"

        # Container should be returned
        assert result["container"] is not None
        assert result["container"]["name"] == "cosmos_transfer_abc123"

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_no_run_no_container(self, mock_executor, mock_repo, mock_db):
        """Test idle state: no run, no container."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # No running runs
        mock_repo_instance.list_runs.return_value = []

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance
        # Mock the nested docker_executor attribute - no container
        api.orchestrator.docker_executor = MagicMock()
        api.orchestrator.docker_executor.get_active_container.return_value = None

        result = api.get_active_operations()

        # Should have None for both
        assert result["active_run"] is None
        assert result["container"] is None

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_run_without_container(self, mock_executor, mock_repo, mock_db):
        """Test error case: run exists but no container (zombie run)."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Running run exists
        active_run = {
            "id": "run_zombie",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"container_id": "container_gone"},
            "prompt_id": "ps_11111",
        }
        mock_repo_instance.list_runs.return_value = [active_run]

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance
        # Mock the nested docker_executor attribute - no container
        api.orchestrator.docker_executor = MagicMock()
        api.orchestrator.docker_executor.get_active_container.return_value = None

        result = api.get_active_operations()

        # Run should be returned but container is None
        assert result["active_run"] is not None
        assert result["active_run"]["id"] == "run_zombie"
        assert result["container"] is None

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_container_without_run(self, mock_executor, mock_repo, mock_db):
        """Test error case: container exists but no run (orphaned container)."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # No running runs
        mock_repo_instance.list_runs.return_value = []

        # But container exists
        container = {
            "id": "container_orphan",
            "id_short": "container_or",
            "name": "cosmos_transfer_orphan",
            "status": "Up 10 minutes",
        }

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance
        # Mock the nested docker_executor attribute - container exists
        api.orchestrator.docker_executor = MagicMock()
        api.orchestrator.docker_executor.get_active_container.return_value = container

        result = api.get_active_operations()

        # Container should be returned but run is None
        assert result["active_run"] is None
        assert result["container"] is not None
        assert result["container"]["name"] == "cosmos_transfer_orphan"


class TestEnhancedCheckStatus:
    """Test enhanced check_status functionality."""

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_check_status_includes_active_run(self, mock_executor, mock_repo, mock_db):
        """Test that check_status includes active run details when present."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Mock base status from orchestrator
        base_status = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "gpu_info": {
                "name": "NVIDIA A100",
                "memory_total": "40GB",
                "memory_used": "12GB",
                "memory_percentage": "30%",
                "gpu_utilization": "85%",
            },
        }
        mock_executor_instance.check_remote_status.return_value = base_status

        # Mock active run
        active_run = {
            "id": "run_test",
            "model_type": "transfer",
            "status": "running",
            "prompt_id": "ps_test",
            "started_at": "2024-01-01T10:00:00Z",
        }
        mock_repo_instance.list_runs.return_value = [active_run]

        # Mock container
        container = {"id": "container_test123", "name": "cosmos_transfer_test"}

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance
        # Mock the nested docker_executor attribute
        api.orchestrator.docker_executor = MagicMock()
        api.orchestrator.docker_executor.get_active_container.return_value = container

        result = api.check_status()

        # Should include base status
        assert result["ssh_status"] == "connected"
        assert result["docker_status"]["docker_running"] is True

        # Should include active run details
        assert "active_run" in result
        assert result["active_run"]["id"] == "run_test"

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_check_status_no_run_when_docker_down(self, mock_executor, mock_repo, mock_db):
        """Test that check_status doesn't query operations when Docker is down."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Docker not running
        base_status = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": False},
            "gpu_info": None,
        }
        mock_executor_instance.check_remote_status.return_value = base_status

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance
        # Mock the nested docker_executor attribute
        api.orchestrator.docker_executor = MagicMock()

        result = api.check_status()

        # Should not include active_run when Docker is down
        assert "active_run" not in result
        # Should not have called list_runs (Docker is down)
        mock_repo_instance.list_runs.assert_not_called()

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_generate_container_name(self, mock_executor, mock_repo, mock_db):
        """Test container name generation."""
        api = CosmosAPI()

        # Test different model types and run IDs
        test_cases = [
            ("transfer", "run_abc12345678", "cosmos_transfer_abc12345"),
            ("upscale", "run_def67890123", "cosmos_upscale_def67890"),
            ("enhance", "run_xyz11111111", "cosmos_enhance_xyz11111"),
        ]

        for model_type, run_id, expected in test_cases:
            name = api._generate_container_name(model_type, run_id)
            assert name == expected

        # Test short run_id
        name = api._generate_container_name("transfer", "run_123")
        assert name == "cosmos_transfer_123"
