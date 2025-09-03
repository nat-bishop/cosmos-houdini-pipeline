#!/usr/bin/env python3
"""Integration tests for upsampling workflow with MINIMAL mocking.

Only mocks external boundaries (SSH, Docker, SFTP).
Everything else uses real code to ensure robustness.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, mock_open, patch

import pytest

from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.schemas import DirectoryManager, PromptSpec
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator


class TestUpsamplingWithMinimalMocks:
    """Test upsampling workflow with only external service mocks."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a real temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            input_dir = workspace / "inputs"
            output_dir = workspace / "outputs"
            input_dir.mkdir()
            output_dir.mkdir()

            yield {
                "workspace": workspace,
                "input_dir": input_dir,
                "output_dir": output_dir,
                "dir_manager": DirectoryManager(str(input_dir), str(output_dir)),
            }

    def test_upsampling_with_smart_naming_success(self, temp_workspace, monkeypatch):
        """Test successful upsampling with smart name generation."""

        # Only mock the external service initialization
        def mock_initialize_services(self):
            self.ssh_manager = Mock()
            self.file_transfer = Mock()
            self.docker_executor = Mock()
            # Use REAL config manager, prompt manager, etc.
            from cosmos_workflow.config.config_manager import ConfigManager

            self.config_manager = ConfigManager()
            self.prompt_spec_manager = PromptSpecManager(temp_workspace["dir_manager"])

        monkeypatch.setattr(
            "cosmos_workflow.workflows.upsample_integration.UpsampleWorkflowMixin._initialize_services",
            mock_initialize_services,
        )

        # Create REAL orchestrator
        orchestrator = WorkflowOrchestrator()

        # Mock only external calls
        orchestrator.file_transfer.download_file = Mock(return_value=True)
        orchestrator.docker_executor.run_command = Mock(return_value=(0, "Success", ""))

        # Create test prompts using REAL PromptSpecManager
        spec_manager = PromptSpecManager(temp_workspace["dir_manager"])
        test_specs = [
            spec_manager.create_prompt_spec("A foggy morning in the mountains"),
            spec_manager.create_prompt_spec("Cyberpunk city at night"),
        ]

        # Simulate upsampling results
        test_results = [
            {
                "spec_id": test_specs[0].id,
                "upsampled_prompt": "A serene misty morning with fog rolling through ancient mountain paths",
                "name": test_specs[0].name,
            },
            {
                "spec_id": test_specs[1].id,
                "upsampled_prompt": "Neon-lit cyberpunk metropolis with flying cars and holographic billboards",
                "name": test_specs[1].name,
            },
        ]

        # Mock the file download to return our test results
        def mock_download(*args, **kwargs):
            # Write results to the expected location
            result_file = temp_workspace["workspace"] / "upsampling_results.json"
            with open(result_file, "w") as f:
                json.dump(test_results, f)
            return True

        orchestrator.file_transfer.download_file = mock_download

        # Mock reading the result file
        with patch("builtins.open", mock_open(read_data=json.dumps(test_results))):
            result = orchestrator.run_prompt_upsampling(test_specs)

        # Verify smart naming worked
        assert result["success"]
        assert len(result["updated_specs"]) == 2

        # Check first spec got smart name from enhanced prompt
        spec1 = result["updated_specs"][0]
        assert (
            "misty" in spec1.name.lower()
            or "fog" in spec1.name.lower()
            or "morning" in spec1.name.lower()
        )
        assert "_enhanced" not in spec1.name

        # Check second spec
        spec2 = result["updated_specs"][1]
        assert (
            "neon" in spec2.name.lower()
            or "cyberpunk" in spec2.name.lower()
            or "metropolis" in spec2.name.lower()
        )

    def test_upsampling_handles_missing_spec_id(self, temp_workspace, monkeypatch):
        """Test fallback to name matching when spec_id is missing."""

        def mock_initialize_services(self):
            self.ssh_manager = Mock()
            self.file_transfer = Mock()
            self.docker_executor = Mock()
            from cosmos_workflow.config.config_manager import ConfigManager

            self.config_manager = ConfigManager()
            self.prompt_spec_manager = PromptSpecManager(temp_workspace["dir_manager"])

        monkeypatch.setattr(
            "cosmos_workflow.workflows.upsample_integration.UpsampleWorkflowMixin._initialize_services",
            mock_initialize_services,
        )

        orchestrator = WorkflowOrchestrator()

        # Create test spec
        spec_manager = PromptSpecManager(temp_workspace["dir_manager"])
        test_spec = spec_manager.create_prompt_spec("Original prompt")

        # Result with missing spec_id (should fall back to name matching)
        test_results = [
            {
                # NO spec_id field
                "upsampled_prompt": "Enhanced version of the original prompt with more details",
                "name": test_spec.name,  # Match by name instead
            }
        ]

        def mock_download(*args, **kwargs):
            result_file = temp_workspace["workspace"] / "upsampling_results.json"
            with open(result_file, "w") as f:
                json.dump(test_results, f)
            return True

        orchestrator.file_transfer.download_file = mock_download
        orchestrator.docker_executor.run_command = Mock(return_value=(0, "Success", ""))

        with patch("builtins.open", mock_open(read_data=json.dumps(test_results))):
            result = orchestrator.run_prompt_upsampling([test_spec])

        # Should still succeed by matching on name
        assert result["success"]
        assert len(result["updated_specs"]) == 1
        assert (
            "enhanced" in result["updated_specs"][0].name.lower()
            or "version" in result["updated_specs"][0].name.lower()
        )

    def test_upsampling_handles_docker_failure(self, temp_workspace, monkeypatch):
        """Test proper error handling when Docker command fails."""

        def mock_initialize_services(self):
            self.ssh_manager = Mock()
            self.file_transfer = Mock()
            self.docker_executor = Mock()
            from cosmos_workflow.config.config_manager import ConfigManager

            self.config_manager = ConfigManager()
            self.prompt_spec_manager = PromptSpecManager(temp_workspace["dir_manager"])

        monkeypatch.setattr(
            "cosmos_workflow.workflows.upsample_integration.UpsampleWorkflowMixin._initialize_services",
            mock_initialize_services,
        )

        orchestrator = WorkflowOrchestrator()

        # Docker command fails
        orchestrator.docker_executor.run_command = Mock(
            return_value=(1, "", "Error: Container failed to start")
        )

        spec_manager = PromptSpecManager(temp_workspace["dir_manager"])
        test_spec = spec_manager.create_prompt_spec("Test prompt")

        result = orchestrator.run_prompt_upsampling([test_spec])

        # Should handle the error gracefully
        assert not result["success"]
        assert "error" in result or "message" in result

    def test_upsampling_handles_empty_results(self, temp_workspace, monkeypatch):
        """Test handling when upsampling returns empty results."""

        def mock_initialize_services(self):
            self.ssh_manager = Mock()
            self.file_transfer = Mock()
            self.docker_executor = Mock()
            from cosmos_workflow.config.config_manager import ConfigManager

            self.config_manager = ConfigManager()
            self.prompt_spec_manager = PromptSpecManager(temp_workspace["dir_manager"])

        monkeypatch.setattr(
            "cosmos_workflow.workflows.upsample_integration.UpsampleWorkflowMixin._initialize_services",
            mock_initialize_services,
        )

        orchestrator = WorkflowOrchestrator()

        # Return empty results
        test_results = []

        def mock_download(*args, **kwargs):
            result_file = temp_workspace["workspace"] / "upsampling_results.json"
            with open(result_file, "w") as f:
                json.dump(test_results, f)
            return True

        orchestrator.file_transfer.download_file = mock_download
        orchestrator.docker_executor.run_command = Mock(return_value=(0, "Success", ""))

        spec_manager = PromptSpecManager(temp_workspace["dir_manager"])
        test_spec = spec_manager.create_prompt_spec("Test prompt")

        with patch("builtins.open", mock_open(read_data=json.dumps(test_results))):
            result = orchestrator.run_prompt_upsampling([test_spec])

        # Should handle empty results gracefully
        assert result["success"] or "updated_specs" in result
        assert len(result.get("updated_specs", [])) == 0

    def test_upsampling_preserves_metadata(self, temp_workspace, monkeypatch):
        """Test that upsampling preserves important metadata."""

        def mock_initialize_services(self):
            self.ssh_manager = Mock()
            self.file_transfer = Mock()
            self.docker_executor = Mock()
            from cosmos_workflow.config.config_manager import ConfigManager

            self.config_manager = ConfigManager()
            self.prompt_spec_manager = PromptSpecManager(temp_workspace["dir_manager"])

        monkeypatch.setattr(
            "cosmos_workflow.workflows.upsample_integration.UpsampleWorkflowMixin._initialize_services",
            mock_initialize_services,
        )

        orchestrator = WorkflowOrchestrator()

        # Create spec with specific metadata
        spec_manager = PromptSpecManager(temp_workspace["dir_manager"])
        original_spec = spec_manager.create_prompt_spec(
            prompt_text="Original prompt", video_dir="custom/video/path"
        )

        test_results = [
            {
                "spec_id": original_spec.id,
                "upsampled_prompt": "Enhanced prompt with more vivid details",
                "name": original_spec.name,
            }
        ]

        def mock_download(*args, **kwargs):
            result_file = temp_workspace["workspace"] / "upsampling_results.json"
            with open(result_file, "w") as f:
                json.dump(test_results, f)
            return True

        orchestrator.file_transfer.download_file = mock_download
        orchestrator.docker_executor.run_command = Mock(return_value=(0, "Success", ""))

        with patch("builtins.open", mock_open(read_data=json.dumps(test_results))):
            result = orchestrator.run_prompt_upsampling([original_spec])

        assert result["success"]
        updated_spec = result["updated_specs"][0]

        # Should preserve video paths
        assert updated_spec.input_video_path == original_spec.input_video_path
        assert updated_spec.control_inputs == original_spec.control_inputs

        # Should mark as upsampled
        assert updated_spec.is_upsampled

        # Should track parent
        assert updated_spec.parent_prompt_text == "Original prompt"


class TestErrorRecovery:
    """Test error recovery and edge cases."""

    def test_handles_malformed_json(self, monkeypatch):
        """Test handling of malformed JSON responses."""

        def mock_initialize_services(self):
            self.ssh_manager = Mock()
            self.file_transfer = Mock()
            self.docker_executor = Mock()
            from cosmos_workflow.config.config_manager import ConfigManager

            self.config_manager = ConfigManager()

        monkeypatch.setattr(
            "cosmos_workflow.workflows.upsample_integration.UpsampleWorkflowMixin._initialize_services",
            mock_initialize_services,
        )

        orchestrator = WorkflowOrchestrator()
        orchestrator.docker_executor.run_command = Mock(return_value=(0, "Success", ""))

        # Mock reading malformed JSON
        with patch("builtins.open", mock_open(read_data="{ malformed json")):
            with tempfile.TemporaryDirectory() as tmpdir:
                dm = DirectoryManager(tmpdir, tmpdir)
                spec_manager = PromptSpecManager(dm)
                test_spec = spec_manager.create_prompt_spec("Test")

                result = orchestrator.run_prompt_upsampling([test_spec])

        # Should handle JSON error gracefully
        assert not result.get("success", False) or "error" in result

    def test_handles_network_timeout(self, monkeypatch):
        """Test handling of network timeouts."""

        def mock_initialize_services(self):
            self.ssh_manager = Mock()
            self.file_transfer = Mock()
            self.docker_executor = Mock()
            from cosmos_workflow.config.config_manager import ConfigManager

            self.config_manager = ConfigManager()

        monkeypatch.setattr(
            "cosmos_workflow.workflows.upsample_integration.UpsampleWorkflowMixin._initialize_services",
            mock_initialize_services,
        )

        orchestrator = WorkflowOrchestrator()

        # Simulate timeout
        orchestrator.docker_executor.run_command = Mock(
            side_effect=TimeoutError("Command timed out")
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            dm = DirectoryManager(tmpdir, tmpdir)
            spec_manager = PromptSpecManager(dm)
            test_spec = spec_manager.create_prompt_spec("Test")

            # Should not crash on timeout
            result = orchestrator.run_prompt_upsampling([test_spec])
            assert not result.get("success", False)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
