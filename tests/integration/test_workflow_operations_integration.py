"""Integration tests for CosmosAPI.

Tests actual SSH and Docker interactions when test environment is available.
Skip tests if TEST_GPU_HOST environment variable is not set.
"""

import os
from unittest.mock import patch

import pytest

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.connection import SSHManager


@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("TEST_GPU_HOST"), reason="No test environment configured")
class TestCosmosAPIIntegration:
    """Integration tests for CosmosAPI with real SSH/Docker."""

    @pytest.fixture
    def test_config(self):
        """Create test configuration from environment variables."""
        # Load environment variables for test configuration
        config = {
            "gpu_host": os.getenv("TEST_GPU_HOST"),
            "gpu_username": os.getenv("TEST_GPU_USERNAME", "ubuntu"),
            "ssh_key_path": os.getenv("TEST_SSH_KEY_PATH", "~/.ssh/id_rsa"),
            "ssh_passphrase": os.getenv("TEST_SSH_PASSPHRASE", ""),
            "remote_base_dir": os.getenv("TEST_REMOTE_DIR", "/tmp/cosmos-test"),
            "transfer1_docker_image": os.getenv("TEST_DOCKER_IMAGE", "busybox:latest"),
        }
        return config

    @pytest.fixture
    def workflow_ops(self, test_config):
        """Create CosmosAPI instance with test configuration."""
        # Mock ConfigManager to use test configuration
        with patch("cosmos_workflow.api.cosmos_api.ConfigManager") as mock_config:
            mock_config.return_value.get.side_effect = lambda key: test_config.get(key)
            ops = CosmosAPI()
            yield ops
            # Cleanup: close SSH connections
            if hasattr(ops, "orchestrator") and hasattr(ops.orchestrator, "ssh_manager"):
                ops.orchestrator.ssh_manager.close()

    def test_kill_containers_with_no_containers(self, workflow_ops):
        """Test kill_containers when no containers are running."""
        # This should not fail even if no containers exist
        result = workflow_ops.kill_containers()

        assert result["status"] in ["success", "no_containers"]
        assert result["killed_count"] == 0
        assert result["killed_containers"] == []

    def test_kill_containers_with_running_container(self, workflow_ops):
        """Test kill_containers with an actual running container."""
        # Start a test container using busybox (lightweight image)
        try:
            # Create a long-running container for testing
            ssh_manager = workflow_ops.orchestrator.ssh_manager

            # Start a simple container that sleeps
            start_cmd = "sudo docker run -d --name cosmos-test-container busybox:latest sleep 3600"
            ssh_manager.execute_command_success(start_cmd, stream_output=False)

            # Now kill it using our API
            result = workflow_ops.kill_containers()

            assert result["status"] == "success"
            assert result["killed_count"] >= 1
            assert len(result["killed_containers"]) >= 1

            # Verify container is no longer running
            ps_cmd = "sudo docker ps --filter name=cosmos-test-container --format '{{.Names}}'"
            output = ssh_manager.execute_command_success(ps_cmd, stream_output=False)
            assert "cosmos-test-container" not in output

        finally:
            # Cleanup: ensure test container is removed
            try:
                ssh_manager.execute_command_success(
                    "sudo docker rm -f cosmos-test-container 2>/dev/null || true",
                    stream_output=False,
                )
            except Exception:
                pass  # Ignore cleanup errors

    def test_docker_status_integration(self, workflow_ops):
        """Test getting Docker status from remote server."""
        # This tests the docker info and docker images commands
        status = workflow_ops.get_docker_status()

        assert "docker_running" in status
        if status["docker_running"]:
            assert "docker_info" in status
            assert "available_images" in status
            # Docker info should return some output
            assert len(status["docker_info"]) > 0
        else:
            assert "error" in status

    def test_ssh_connection_lifecycle(self, test_config):
        """Test SSH connection management lifecycle."""
        # Test that SSH connections are properly opened and closed
        ssh_manager = SSHManager(
            hostname=test_config["gpu_host"],
            username=test_config["gpu_username"],
            key_path=test_config["ssh_key_path"],
            passphrase=test_config["ssh_passphrase"],
        )

        # Test connection
        with ssh_manager:
            # Should be able to execute a simple command
            output = ssh_manager.execute_command_success("echo 'test'", stream_output=False)
            assert "test" in output

        # After context exit, connection should be closed
        assert ssh_manager.client is None or not ssh_manager.client.get_transport().is_active()

    def test_multiple_container_kill(self, workflow_ops):
        """Test killing multiple containers at once."""
        ssh_manager = workflow_ops.orchestrator.ssh_manager

        try:
            # Start multiple test containers
            for i in range(3):
                cmd = f"sudo docker run -d --name cosmos-test-{i} busybox:latest sleep 3600"
                ssh_manager.execute_command_success(cmd, stream_output=False)

            # Kill all containers
            result = workflow_ops.kill_containers()

            assert result["status"] == "success"
            assert result["killed_count"] >= 3

            # Verify all test containers are gone
            for i in range(3):
                ps_cmd = f"sudo docker ps --filter name=cosmos-test-{i} --format '{{{{.Names}}}}'"
                output = ssh_manager.execute_command_success(ps_cmd, stream_output=False)
                assert f"cosmos-test-{i}" not in output

        finally:
            # Cleanup
            for i in range(3):
                try:
                    ssh_manager.execute_command_success(
                        f"sudo docker rm -f cosmos-test-{i} 2>/dev/null || true",
                        stream_output=False,
                    )
                except Exception:
                    pass
