"""Tests for refactored WorkflowOperations methods.

Following TDD Gate 1: Write tests first for the refactored quick_inference
and batch_inference methods that accept prompt IDs directly.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.config.config_manager import ConfigManager


class TestQuickInferenceRefactored:
    """Test the refactored quick_inference method that accepts prompt_id directly."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config manager."""
        config = MagicMock(spec=ConfigManager)
        config.get_local_config.return_value = MagicMock(outputs_dir=Path("/tmp/outputs"))
        return config

    @pytest.fixture
    def mock_service(self):
        """Create mock workflow service."""
        service = MagicMock()
        return service

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock workflow orchestrator."""
        orchestrator = MagicMock()
        return orchestrator

    @pytest.fixture
    def ops(self, mock_config, mock_service, mock_orchestrator):
        """Create WorkflowOperations instance with mocked dependencies."""
        with patch("cosmos_workflow.api.cosmos_api.init_database"):
            with patch("cosmos_workflow.api.cosmos_api.DataRepository", return_value=mock_service):
                with patch(
                    "cosmos_workflow.api.cosmos_api.GPUExecutor",
                    return_value=mock_orchestrator,
                ):
                    ops = CosmosAPI(mock_config)
                    ops.service = mock_service
                    ops.orchestrator = mock_orchestrator
                    return ops

    def test_quick_inference_accepts_prompt_id_directly(self, ops, mock_service, mock_orchestrator):
        """Test that quick_inference is the primary method accepting prompt_id directly."""
        # Setup mock prompt
        mock_prompt = {
            "id": "ps_test123",
            "prompt_text": "A beautiful sunset",
            "model_type": "transfer",
            "inputs": {"video": "test.mp4"},
            "parameters": {},
        }
        mock_service.get_prompt.return_value = mock_prompt

        # Setup mock run creation
        mock_run = {
            "id": "rs_auto123",
            "prompt_id": "ps_test123",
            "status": "pending",
            "execution_config": {
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}
            },
        }
        mock_service.create_run.return_value = mock_run

        # Setup mock execution result
        mock_result = {
            "output_path": "/outputs/result.mp4",
            "duration_seconds": 120,
            "status": "completed",
        }
        mock_orchestrator.execute_run.return_value = mock_result

        # Call quick_inference with prompt_id directly (no run_id needed)
        result = ops.quick_inference("ps_test123")

        # Verify it creates a run internally
        mock_service.create_run.assert_called_once_with(
            prompt_id="ps_test123",
            execution_config={
                "weights": {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
                "num_steps": 35,
                "guidance": 5.0,
                "seed": 1,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
            },
            model_type="transfer",
        )

        # Verify it executes the run
        mock_orchestrator.execute_run.assert_called_once()

        # Verify it returns run_id in results for tracking
        assert "run_id" in result
        assert result["run_id"] == "rs_auto123"
        assert result["output_path"] == "/outputs/result.mp4"
        assert result["status"] == "completed"

    def test_quick_inference_with_custom_weights(self, ops, mock_service, mock_orchestrator):
        """Test quick_inference with custom weights."""
        mock_prompt = {"id": "ps_test123", "prompt_text": "Test", "inputs": {}, "parameters": {}}
        mock_service.get_prompt.return_value = mock_prompt
        mock_run = {"id": "rs_auto456", "prompt_id": "ps_test123"}
        mock_service.create_run.return_value = mock_run
        mock_orchestrator.execute_run.return_value = {
            "output_path": "test.mp4",
            "duration_seconds": 60,
        }

        # Custom weights
        weights = {"vis": 0.4, "edge": 0.3, "depth": 0.2, "seg": 0.1}

        result = ops.quick_inference("ps_test123", weights=weights)

        # Verify custom weights are passed
        call_args = mock_service.create_run.call_args
        assert call_args[1]["execution_config"]["weights"] == weights
        assert result["run_id"] == "rs_auto456"

    def test_quick_inference_with_additional_params(self, ops, mock_service, mock_orchestrator):
        """Test quick_inference with additional execution parameters."""
        mock_prompt = {"id": "ps_test123", "prompt_text": "Test", "inputs": {}, "parameters": {}}
        mock_service.get_prompt.return_value = mock_prompt
        mock_run = {"id": "rs_auto789", "prompt_id": "ps_test123"}
        mock_service.create_run.return_value = mock_run
        mock_orchestrator.execute_run.return_value = {
            "output_path": "test.mp4",
            "duration_seconds": 90,
        }

        ops.quick_inference("ps_test123", num_steps=50, guidance=8.5, seed=42)

        # Verify additional params are passed
        call_args = mock_service.create_run.call_args
        assert call_args[1]["execution_config"]["num_steps"] == 50
        assert call_args[1]["execution_config"]["guidance"] == 8.5
        assert call_args[1]["execution_config"]["seed"] == 42

    def test_quick_inference_invalid_prompt_id(self, ops, mock_service):
        """Test quick_inference with invalid prompt_id."""
        mock_service.get_prompt.return_value = None

        with pytest.raises(ValueError, match="Prompt not found: ps_invalid"):
            ops.quick_inference("ps_invalid")

    def test_quick_inference_docstring_indicates_primary_method(self, ops):
        """Test that quick_inference docstring emphasizes it's the recommended method."""
        docstring = ops.quick_inference.__doc__
        assert "recommended method" in docstring
        assert "internally" in docstring.lower()


class TestBatchInferenceRefactored:
    """Test the refactored batch_inference method that accepts prompt_ids directly."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config manager."""
        config = MagicMock(spec=ConfigManager)
        config.get_local_config.return_value = MagicMock(outputs_dir=Path("/tmp/outputs"))
        return config

    @pytest.fixture
    def mock_service(self):
        """Create mock workflow service."""
        service = MagicMock()
        return service

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock workflow orchestrator."""
        orchestrator = MagicMock()
        return orchestrator

    @pytest.fixture
    def ops(self, mock_config, mock_service, mock_orchestrator):
        """Create WorkflowOperations instance with mocked dependencies."""
        with patch("cosmos_workflow.api.cosmos_api.init_database"):
            with patch("cosmos_workflow.api.cosmos_api.DataRepository", return_value=mock_service):
                with patch(
                    "cosmos_workflow.api.cosmos_api.GPUExecutor",
                    return_value=mock_orchestrator,
                ):
                    ops = CosmosAPI(mock_config)
                    ops.service = mock_service
                    ops.orchestrator = mock_orchestrator
                    return ops

    def test_batch_inference_accepts_list_of_prompt_ids(self, ops, mock_service, mock_orchestrator):
        """Test that batch_inference accepts list of prompt_ids and creates runs internally."""
        # Setup mock prompts
        mock_prompts = [
            {"id": "ps_test1", "prompt_text": "Sunset", "inputs": {}, "parameters": {}},
            {"id": "ps_test2", "prompt_text": "Sunrise", "inputs": {}, "parameters": {}},
            {"id": "ps_test3", "prompt_text": "Night", "inputs": {}, "parameters": {}},
        ]

        def get_prompt_side_effect(prompt_id):
            for p in mock_prompts:
                if p["id"] == prompt_id:
                    return p
            return None

        mock_service.get_prompt.side_effect = get_prompt_side_effect

        # Setup mock run creation
        mock_runs = [
            {"id": "rs_auto1", "prompt_id": "ps_test1", "status": "pending"},
            {"id": "rs_auto2", "prompt_id": "ps_test2", "status": "pending"},
            {"id": "rs_auto3", "prompt_id": "ps_test3", "status": "pending"},
        ]
        mock_service.create_run.side_effect = mock_runs

        # Setup mock batch execution result
        mock_batch_result = {
            "output_mapping": {
                "rs_auto1": "/outputs/result1.mp4",
                "rs_auto2": "/outputs/result2.mp4",
                "rs_auto3": "/outputs/result3.mp4",
            },
            "total_duration": 360,
            "successful": 3,
            "failed": 0,
        }
        mock_orchestrator.execute_batch_runs.return_value = mock_batch_result

        # Call batch_inference with list of prompt_ids
        prompt_ids = ["ps_test1", "ps_test2", "ps_test3"]
        result = ops.batch_inference(prompt_ids)

        # Verify it creates runs for all prompts
        assert mock_service.create_run.call_count == 3

        # Verify it calls batch execution
        mock_orchestrator.execute_batch_runs.assert_called_once()
        batch_call_args = mock_orchestrator.execute_batch_runs.call_args[0][0]
        assert len(batch_call_args) == 3

        # Note: Run statuses are now updated internally by execute_batch_runs,
        # not by the API layer

        # Verify result structure
        assert "output_mapping" in result
        assert len(result["output_mapping"]) == 3
        assert result["successful"] == 3

    def test_batch_inference_with_shared_weights(self, ops, mock_service, mock_orchestrator):
        """Test batch_inference with shared weights for all prompts."""
        mock_prompts = [
            {"id": "ps_test1", "prompt_text": "Test1", "inputs": {}, "parameters": {}},
            {"id": "ps_test2", "prompt_text": "Test2", "inputs": {}, "parameters": {}},
        ]

        mock_service.get_prompt.side_effect = lambda pid: next(
            (p for p in mock_prompts if p["id"] == pid), None
        )
        mock_service.create_run.side_effect = [
            {"id": "rs_auto1", "prompt_id": "ps_test1"},
            {"id": "rs_auto2", "prompt_id": "ps_test2"},
        ]
        mock_orchestrator.execute_batch_runs.return_value = {
            "output_mapping": {"rs_auto1": "out1.mp4", "rs_auto2": "out2.mp4"}
        }

        shared_weights = {"vis": 0.5, "edge": 0.2, "depth": 0.2, "seg": 0.1}

        ops.batch_inference(["ps_test1", "ps_test2"], shared_weights=shared_weights)

        # Verify shared weights are used for all runs
        for call_args in mock_service.create_run.call_args_list:
            assert call_args[1]["execution_config"]["weights"] == shared_weights

    def test_batch_inference_skips_missing_prompts(self, ops, mock_service, mock_orchestrator):
        """Test batch_inference gracefully handles missing prompts."""
        # Only ps_test2 exists
        mock_service.get_prompt.side_effect = lambda pid: (
            {"id": "ps_test2", "prompt_text": "Test2", "inputs": {}, "parameters": {}}
            if pid == "ps_test2"
            else None
        )

        mock_service.create_run.return_value = {"id": "rs_auto2", "prompt_id": "ps_test2"}
        mock_orchestrator.execute_batch_runs.return_value = {
            "output_mapping": {"rs_auto2": "out2.mp4"}
        }

        # Try to process 3 prompts, but only 1 exists
        ops.batch_inference(["ps_missing1", "ps_test2", "ps_missing3"])

        # Verify only 1 run was created (for the existing prompt)
        assert mock_service.create_run.call_count == 1
        # Verify it was called with ps_test2
        call_args = mock_service.create_run.call_args
        assert call_args[1]["prompt_id"] == "ps_test2"

    def test_batch_inference_handles_failed_runs(self, ops, mock_service, mock_orchestrator):
        """Test batch_inference properly marks failed runs."""
        mock_prompts = [
            {"id": "ps_test1", "prompt_text": "Test1", "inputs": {}, "parameters": {}},
            {"id": "ps_test2", "prompt_text": "Test2", "inputs": {}, "parameters": {}},
        ]

        mock_service.get_prompt.side_effect = lambda pid: next(
            (p for p in mock_prompts if p["id"] == pid), None
        )
        mock_service.create_run.side_effect = [
            {"id": "rs_auto1", "prompt_id": "ps_test1"},
            {"id": "rs_auto2", "prompt_id": "ps_test2"},
        ]

        # Only rs_auto1 succeeded
        mock_orchestrator.execute_batch_runs.return_value = {
            "output_mapping": {"rs_auto1": "out1.mp4"},
            "successful": 1,
            "failed": 1,
        }

        result = ops.batch_inference(["ps_test1", "ps_test2"])

        # Note: Status updates are now handled internally by execute_batch_runs
        # Verify result structure shows correct success/failure counts
        assert result["successful"] == 1
        assert result["failed"] == 1

    def test_batch_inference_with_additional_params(self, ops, mock_service, mock_orchestrator):
        """Test batch_inference with additional execution parameters."""
        mock_prompt = {"id": "ps_test1", "prompt_text": "Test", "inputs": {}, "parameters": {}}
        mock_service.get_prompt.return_value = mock_prompt
        mock_service.create_run.return_value = {"id": "rs_auto1", "prompt_id": "ps_test1"}
        mock_orchestrator.execute_batch_runs.return_value = {
            "output_mapping": {"rs_auto1": "out.mp4"}
        }

        ops.batch_inference(["ps_test1"], num_steps=50, guidance=8.5, seed=42)

        # Verify additional params are passed to run creation
        call_args = mock_service.create_run.call_args
        assert call_args[1]["execution_config"]["num_steps"] == 50
        assert call_args[1]["execution_config"]["guidance"] == 8.5
        assert call_args[1]["execution_config"]["seed"] == 42

    def test_batch_inference_empty_list(self, ops, mock_orchestrator):
        """Test batch_inference with empty prompt list."""
        ops.batch_inference([])

        # Should handle gracefully
        mock_orchestrator.execute_batch_runs.assert_called_once_with([])


class TestCreateAndExecuteMethods:
    """Test that create_run and execute_run remain as low-level methods."""

    @pytest.fixture
    def mock_config(self):
        """Create mock config manager."""
        config = MagicMock(spec=ConfigManager)
        config.get_local_config.return_value = MagicMock(outputs_dir=Path("/tmp/outputs"))
        return config

    @pytest.fixture
    def ops(self, mock_config):
        """Create WorkflowOperations instance."""
        with patch("cosmos_workflow.api.cosmos_api.init_database"):
            with patch("cosmos_workflow.api.cosmos_api.DataRepository"):
                with patch("cosmos_workflow.api.cosmos_api.GPUExecutor"):
                    return CosmosAPI(mock_config)

    def test_quick_inference_replaces_create_and_execute(self, ops):
        """Test that quick_inference is the new primary method."""
        assert hasattr(ops, "quick_inference")
        assert callable(ops.quick_inference)
        # Verify it's documented as the primary method
        docstring = ops.quick_inference.__doc__ or ""
        assert "execute inference" in docstring.lower() or "run inference" in docstring.lower()

    def test_batch_inference_available(self, ops):
        """Test that batch_inference method exists."""
        assert hasattr(ops, "batch_inference")
        assert callable(ops.batch_inference)
        # Verify it handles multiple prompts
        docstring = ops.batch_inference.__doc__ or ""
        assert "batch" in docstring.lower() or "multiple" in docstring.lower()
