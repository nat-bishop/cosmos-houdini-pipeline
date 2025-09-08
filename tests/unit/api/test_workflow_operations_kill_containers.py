#!/usr/bin/env python3
"""Tests for WorkflowOperations.kill_containers method."""

import unittest
from unittest.mock import MagicMock, patch

from cosmos_workflow.api.cosmos_api import CosmosAPI


class TestWorkflowOperationsKillContainers(unittest.TestCase):
    """Test the kill_containers method follows the established pattern."""

    def setUp(self):
        """Set up test fixtures."""
        # Create WorkflowOperations with mocked dependencies
        with patch("cosmos_workflow.api.cosmos_api.ConfigManager"):
            with patch("cosmos_workflow.api.cosmos_api.init_database"):
                with patch("cosmos_workflow.api.cosmos_api.DataRepository"):
                    with patch("cosmos_workflow.api.cosmos_api.GPUExecutor") as MockOrchestrator:
                        # Set up the orchestrator mock
                        self.mock_orchestrator = MagicMock()
                        MockOrchestrator.return_value = self.mock_orchestrator

                        # Set up nested mocks for ssh_manager and docker_executor
                        self.mock_ssh_manager = MagicMock()
                        self.mock_docker_executor = MagicMock()
                        self.mock_orchestrator.ssh_manager = self.mock_ssh_manager
                        self.mock_orchestrator.docker_executor = self.mock_docker_executor

                        # Create the WorkflowOperations instance
                        self.ops = CosmosAPI()

    def test_kill_containers_follows_established_pattern(self):
        """Test that kill_containers uses orchestrator pattern correctly."""
        # Set up the mock to return a successful result
        self.mock_docker_executor.kill_containers.return_value = {
            "status": "success",
            "killed_count": 2,
            "killed_containers": ["abc123", "def456"],
        }

        # Call the method
        result = self.ops.kill_containers()

        # Verify it follows the pattern:
        # 1. Initializes services through orchestrator
        self.mock_orchestrator._initialize_services.assert_called_once()

        # 2. Uses orchestrator's ssh_manager as context manager
        self.mock_ssh_manager.__enter__.assert_called_once()
        self.mock_ssh_manager.__exit__.assert_called_once()

        # 3. Uses orchestrator's docker_executor
        self.mock_docker_executor.kill_containers.assert_called_once()

        # 4. Returns the correct result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["killed_count"], 2)
        self.assertEqual(result["killed_containers"], ["abc123", "def456"])

    def test_kill_containers_handles_no_containers(self):
        """Test kill_containers when no containers are running."""
        # Set up the mock to return no containers
        self.mock_docker_executor.kill_containers.return_value = {
            "status": "success",
            "killed_count": 0,
            "killed_containers": [],
        }

        # Call the method
        result = self.ops.kill_containers()

        # Verify correct handling
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["killed_count"], 0)
        self.assertEqual(result["killed_containers"], [])

    def test_kill_containers_handles_docker_executor_failure(self):
        """Test kill_containers when docker executor fails."""
        # Set up the mock to return a failure
        self.mock_docker_executor.kill_containers.return_value = {
            "status": "failed",
            "error": "Docker daemon not responding",
            "killed_count": 0,
            "killed_containers": [],
        }

        # Call the method
        result = self.ops.kill_containers()

        # Verify it handles the failure correctly
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"], "Docker daemon not responding")
        self.assertEqual(result["killed_count"], 0)

    def test_kill_containers_handles_exception(self):
        """Test kill_containers handles exceptions gracefully."""
        # Set up the mock to raise an exception
        self.mock_orchestrator._initialize_services.side_effect = ConnectionError(
            "SSH connection failed"
        )

        # Call the method
        result = self.ops.kill_containers()

        # Verify it returns a proper error response
        self.assertEqual(result["status"], "failed")
        self.assertIn("SSH connection failed", result["error"])
        self.assertEqual(result["killed_count"], 0)
        self.assertEqual(result["killed_containers"], [])

    def test_kill_containers_uses_context_manager_properly(self):
        """Test that SSH context manager is used even if kill_containers raises."""
        # Set up the mock to raise an exception inside the context
        self.mock_docker_executor.kill_containers.side_effect = RuntimeError(
            "Container kill failed"
        )

        # Call the method
        result = self.ops.kill_containers()

        # Verify context manager was still properly used
        self.mock_ssh_manager.__enter__.assert_called_once()
        self.mock_ssh_manager.__exit__.assert_called_once()

        # Verify error is handled
        self.assertEqual(result["status"], "failed")
        self.assertIn("Container kill failed", result["error"])


if __name__ == "__main__":
    unittest.main()
