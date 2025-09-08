"""Tests for unified status tracking (Phase 4).

Tests get_active_operations and enhanced check_status functionality.
"""

from unittest.mock import MagicMock, patch

from cosmos_workflow.api import CosmosAPI


class TestActiveOperations:
    """Test get_active_operations functionality."""

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_basic(self, mock_executor, mock_repo, mock_db):
        """Test basic get_active_operations functionality."""
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
            "name": "cosmos_transfer_abc123",
            "status": "Up 5 minutes",
        }
        mock_executor_instance.get_containers.return_value = [container]

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance

        result = api.get_active_operations()

        # Check structure
        assert "active_runs" in result
        assert "orphaned_containers" in result
        assert "issues" in result

        # Check matching worked
        assert len(result["active_runs"]) == 1
        assert result["active_runs"][0]["id"] == "run_abc123"
        assert result["active_runs"][0]["container"] is not None
        assert result["active_runs"][0]["container"]["id"] == "container_111aaa"

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_multiple_runs(self, mock_executor, mock_repo, mock_db):
        """Test with multiple active operations."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Multiple active runs
        active_runs = [
            {
                "id": "run_transfer",
                "model_type": "transfer",
                "status": "running",
                "execution_config": {"container_id": "container_aaa"},
                "prompt_id": "ps_12345",
            },
            {
                "id": "run_upscale",
                "model_type": "upscale",
                "status": "running",
                "execution_config": {"container_id": "container_bbb"},
                "prompt_id": "ps_12345",
            },
            {
                "id": "run_enhance",
                "model_type": "enhance",
                "status": "running",
                "execution_config": {"container_id": "container_ccc"},
                "prompt_id": "ps_67890",
            },
        ]
        mock_repo_instance.list_runs.return_value = active_runs

        # Matching containers
        containers = [
            {"id": "container_aaa111", "name": "cosmos_transfer_xxx"},
            {"id": "container_bbb222", "name": "cosmos_upscale_yyy"},
            {"id": "container_ccc333", "name": "cosmos_enhance_zzz"},
        ]
        mock_executor_instance.get_containers.return_value = containers

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance

        result = api.get_active_operations()

        # All runs should be matched
        assert len(result["active_runs"]) == 3
        for run in result["active_runs"]:
            assert run["container"] is not None

        # No orphaned containers
        assert len(result["orphaned_containers"]) == 0

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_orphaned_containers(self, mock_executor, mock_repo, mock_db):
        """Test detection of orphaned containers."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # One active run
        active_run = {
            "id": "run_known",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"container_id": "container_known"},
            "prompt_id": "ps_12345",
        }
        mock_repo_instance.list_runs.return_value = [active_run]

        # Multiple containers including orphans
        containers = [
            {"id": "container_known123", "name": "cosmos_transfer_known"},
            {"id": "container_orphan1", "name": "manual_container"},
            {"id": "container_orphan2", "name": "cosmos_old_run"},
        ]
        mock_executor_instance.get_containers.return_value = containers

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance

        result = api.get_active_operations()

        # One matched run
        assert len(result["active_runs"]) == 1
        assert result["active_runs"][0]["container"] is not None

        # Two orphaned containers
        assert len(result["orphaned_containers"]) == 2
        orphan_ids = [c["id"] for c in result["orphaned_containers"]]
        assert "container_orphan1" in orphan_ids
        assert "container_orphan2" in orphan_ids

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_zombie_runs(self, mock_executor, mock_repo, mock_db):
        """Test detection of zombie runs (runs without containers)."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Runs marked as running
        zombie_runs = [
            {
                "id": "run_zombie1",
                "model_type": "transfer",
                "status": "running",
                "execution_config": {"container_id": "container_gone1"},
                "prompt_id": "ps_11111",
            },
            {
                "id": "run_zombie2",
                "model_type": "upscale",
                "status": "running",
                "execution_config": {"container_id": "container_gone2"},
                "prompt_id": "ps_22222",
            },
        ]
        mock_repo_instance.list_runs.return_value = zombie_runs

        # No containers running
        mock_executor_instance.get_containers.return_value = []

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance

        result = api.get_active_operations()

        # Runs should be returned but with no container
        assert len(result["active_runs"]) == 2
        for run in result["active_runs"]:
            assert run["container"] is None

        # Issues should be reported
        assert len(result["issues"]) > 0
        assert any(
            "zombie" in issue.lower() or "no container" in issue.lower()
            for issue in result["issues"]
        )

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_get_active_operations_no_container_id(self, mock_executor, mock_repo, mock_db):
        """Test handling runs without container_id in execution_config."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Run without container_id (legacy run)
        legacy_run = {
            "id": "run_legacy",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {},  # No container_id
            "prompt_id": "ps_legacy",
        }
        mock_repo_instance.list_runs.return_value = [legacy_run]

        # Container exists
        container = {"id": "container_abc", "name": "cosmos_transfer_legacy"}
        mock_executor_instance.get_containers.return_value = [container]

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance

        result = api.get_active_operations()

        # Legacy run should have no container matched
        assert len(result["active_runs"]) == 1
        assert result["active_runs"][0]["container"] is None

        # Container becomes orphaned
        assert len(result["orphaned_containers"]) == 1


class TestEnhancedCheckStatus:
    """Test enhanced check_status functionality."""

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_check_status_includes_active_operations(self, mock_executor, mock_repo, mock_db):
        """Test that check_status includes active operations when Docker is running."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Mock base status from orchestrator
        base_status = {
            "ssh_status": "connected",
            "docker_status": {"docker_running": True},
            "gpu_info": {"name": "NVIDIA A100", "memory_total": "40GB"},
        }
        mock_executor_instance.check_remote_status.return_value = base_status

        # Mock active run
        active_run = {
            "id": "run_test",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"container_id": "container_test"},
            "prompt_id": "ps_test",
        }
        mock_repo_instance.list_runs.return_value = [active_run]

        # Mock container
        container = {"id": "container_test123", "name": "cosmos_transfer_test"}
        mock_executor_instance.get_containers.return_value = [container]

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance

        result = api.check_status()

        # Should include base status
        assert result["ssh_status"] == "connected"
        assert result["docker_status"]["docker_running"] is True

        # Should include active operations
        assert "active_operations" in result
        assert len(result["active_operations"]) == 1
        assert result["active_operations"][0]["id"] == "run_test"

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_check_status_no_operations_when_docker_down(self, mock_executor, mock_repo, mock_db):
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

        result = api.check_status()

        # Should not include active operations
        assert "active_operations" not in result
        # Should not have called list_runs (Docker is down)
        mock_repo_instance.list_runs.assert_not_called()

    @patch("cosmos_workflow.api.cosmos_api.init_database")
    @patch("cosmos_workflow.api.cosmos_api.DataRepository")
    @patch("cosmos_workflow.api.cosmos_api.GPUExecutor")
    def test_check_status_includes_issues(self, mock_executor, mock_repo, mock_db):
        """Test that check_status includes issues when detected."""
        mock_repo_instance = MagicMock()
        mock_repo.return_value = mock_repo_instance
        mock_executor_instance = MagicMock()
        mock_executor.return_value = mock_executor_instance

        # Mock base status
        base_status = {"ssh_status": "connected", "docker_status": {"docker_running": True}}
        mock_executor_instance.check_remote_status.return_value = base_status

        # Mock zombie run (no matching container)
        zombie_run = {
            "id": "run_zombie",
            "model_type": "transfer",
            "status": "running",
            "execution_config": {"container_id": "container_gone"},
            "prompt_id": "ps_zombie",
        }
        mock_repo_instance.list_runs.return_value = [zombie_run]

        # No containers
        mock_executor_instance.get_containers.return_value = []

        api = CosmosAPI()
        api.service = mock_repo_instance
        api.orchestrator = mock_executor_instance

        result = api.check_status()

        # Should include issues
        assert "issues" in result
        assert len(result["issues"]) > 0

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
