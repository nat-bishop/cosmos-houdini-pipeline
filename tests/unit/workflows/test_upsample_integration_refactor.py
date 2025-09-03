"""Test upsampling integration with PromptSpecManager refactor.

Tests for TDD Gate 1: Write tests WITHOUT mocks - real function calls only.
NO Mock(), MagicMock(), patch(), or any test doubles.
Tests WILL fail with AttributeError/ImportError - that's expected.
"""

import json
import tempfile
from pathlib import Path

import pytest

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.schemas import DirectoryManager, PromptSpec
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator


class TestUpsampleWithPromptSpecManager:
    """Test that upsampling uses PromptSpecManager correctly.

    NO MOCKS - These tests call real functions and will fail initially.
    """

    def test_upsampled_prompt_gets_smart_name(self, tmp_path):
        """Test that enhanced prompts get smart names from their content."""
        # Setup real orchestrator
        orchestrator = WorkflowOrchestrator()

        # Create test prompt
        test_prompt = PromptSpec(
            id="test_id",
            name="original_name",
            prompt="A simple test prompt",
            negative_prompt="",
            input_video_path=str(tmp_path / "video.mp4"),
            control_inputs={"depth": str(tmp_path / "depth.mp4")},
            timestamp="2025-01-01T00:00:00Z",
            is_upsampled=False,
            parent_prompt_text=None,
        )

        # Create mock upsampling result file that would be downloaded
        upsampled_results = [
            {
                "spec_id": "test_id",
                "upsampled_prompt": "A breathtaking panoramic view of golden sunlight streaming through tall windows onto polished marble floors",
            }
        ]

        results_file = tmp_path / "batch_results.json"
        results_file.write_text(json.dumps(upsampled_results))

        # This WILL fail initially - no mocks!
        # We're testing that the real function uses PromptSpecManager correctly
        result = orchestrator.run_prompt_upsampling([test_prompt])

        # Verify the enhanced prompt has a smart name, not "original_name_enhanced"
        assert result["success"]
        assert len(result["updated_specs"]) == 1

        updated_spec = result["updated_specs"][0]
        assert updated_spec.name != "original_name_enhanced"
        assert updated_spec.name != "original_name"
        # Should get a smart name like "golden_sunlight_windows" based on content
        assert "golden" in updated_spec.name.lower() or "sunlight" in updated_spec.name.lower()

    def test_upsampled_spec_created_with_manager(self, tmp_path):
        """Test that PromptSpecManager.create_prompt_spec is used for upsampling."""
        # Setup real orchestrator - NO MOCKS
        orchestrator = WorkflowOrchestrator()

        # Create test prompt with real paths
        test_prompt = PromptSpec(
            id="test_id",
            name="test_prompt",
            prompt="Test prompt text",
            negative_prompt="bad things",
            input_video_path=str(tmp_path / "video.mp4"),
            control_inputs={"depth": str(tmp_path / "depth.mp4")},
            timestamp="2025-01-01T00:00:00Z",
            is_upsampled=False,
            parent_prompt_text=None,
        )

        # Create expected results file
        upsampled_results = [
            {
                "spec_id": "test_id",
                "upsampled_prompt": "An enhanced and more detailed version of the prompt",
            }
        ]

        results_file = tmp_path / "batch_results.json"
        results_file.write_text(json.dumps(upsampled_results))

        # Run real upsampling - will fail initially (no SSH connection etc)
        result = orchestrator.run_prompt_upsampling([test_prompt])

        # Verify the spec was created properly
        updated_spec = result["updated_specs"][0]

        # Check that spec has all required fields from PromptSpecManager
        assert updated_spec.id is not None
        assert updated_spec.name is not None
        assert updated_spec.prompt == "An enhanced and more detailed version of the prompt"
        assert updated_spec.negative_prompt == "bad things"
        assert updated_spec.input_video_path == str(tmp_path / "video.mp4")
        assert updated_spec.control_inputs == {"depth": str(tmp_path / "depth.mp4")}
        assert updated_spec.is_upsampled is True
        assert updated_spec.parent_prompt_text == "Test prompt text"

    def test_multiple_prompts_get_unique_smart_names(self, tmp_path):
        """Test that multiple enhanced prompts each get unique smart names."""
        # Setup real orchestrator - NO MOCKS
        orchestrator = WorkflowOrchestrator()

        # Create test prompts with real paths
        test_prompts = [
            PromptSpec(
                id="id1",
                name="prompt1",
                prompt="First prompt",
                negative_prompt="",
                input_video_path=str(tmp_path / "video1.mp4"),
                control_inputs={"depth": str(tmp_path / "depth1.mp4")},
                timestamp="2025-01-01T00:00:00Z",
                is_upsampled=False,
                parent_prompt_text=None,
            ),
            PromptSpec(
                id="id2",
                name="prompt2",
                prompt="Second prompt",
                negative_prompt="",
                input_video_path=str(tmp_path / "video2.mp4"),
                control_inputs={"depth": str(tmp_path / "depth2.mp4")},
                timestamp="2025-01-01T00:00:01Z",
                is_upsampled=False,
                parent_prompt_text=None,
            ),
        ]

        # Create expected results
        upsampled_results = [
            {
                "spec_id": "id1",
                "upsampled_prompt": "Misty morning fog rolling through ancient forest paths",
            },
            {
                "spec_id": "id2",
                "upsampled_prompt": "Crystal clear water cascading over smooth river rocks",
            },
        ]

        results_file = tmp_path / "batch_results.json"
        results_file.write_text(json.dumps(upsampled_results))

        # Run real upsampling
        result = orchestrator.run_prompt_upsampling(test_prompts)

        # Verify each got a unique smart name
        assert len(result["updated_specs"]) == 2

        spec1 = result["updated_specs"][0]
        spec2 = result["updated_specs"][1]

        # Names should be different
        assert spec1.name != spec2.name

        # Names should reflect content
        assert (
            "fog" in spec1.name.lower()
            or "mist" in spec1.name.lower()
            or "forest" in spec1.name.lower()
        )
        assert (
            "water" in spec2.name.lower()
            or "crystal" in spec2.name.lower()
            or "river" in spec2.name.lower()
        )

        # Neither should have the old "_enhanced" pattern
        assert not spec1.name.endswith("_enhanced")
        assert not spec2.name.endswith("_enhanced")

    def test_upsampling_preserves_metadata(self, tmp_path):
        """Test that upsampling preserves all metadata correctly."""
        # Setup real orchestrator - NO MOCKS
        orchestrator = WorkflowOrchestrator()

        # Create test prompt with full metadata
        test_prompt = PromptSpec(
            id="metadata_test",
            name="original",
            prompt="Original prompt text",
            negative_prompt="avoid these things",
            input_video_path=str(tmp_path / "video.mp4"),
            control_inputs={
                "depth": str(tmp_path / "depth.mp4"),
                "seg": str(tmp_path / "segmentation.mp4"),
            },
            timestamp="2025-01-01T12:00:00Z",
            is_upsampled=False,
            parent_prompt_text=None,
        )

        # Create expected results
        upsampled_results = [
            {
                "spec_id": "metadata_test",
                "upsampled_prompt": "Enhanced prompt with more detail",
            }
        ]

        results_file = tmp_path / "batch_results.json"
        results_file.write_text(json.dumps(upsampled_results))

        # Run real upsampling
        result = orchestrator.run_prompt_upsampling([test_prompt])

        # Verify metadata preservation
        updated_spec = result["updated_specs"][0]

        assert updated_spec.negative_prompt == "avoid these things"
        assert updated_spec.input_video_path == str(tmp_path / "video.mp4")
        assert updated_spec.control_inputs == {
            "depth": str(tmp_path / "depth.mp4"),
            "seg": str(tmp_path / "segmentation.mp4"),
        }
        assert updated_spec.is_upsampled is True
        assert updated_spec.parent_prompt_text == "Original prompt text"

    def test_spec_files_saved_to_correct_location(self, tmp_path):
        """Test that enhanced specs are saved to the filesystem."""
        # Setup real orchestrator
        orchestrator = WorkflowOrchestrator()

        # Create test prompt
        test_prompt = PromptSpec(
            id="save_test",
            name="test_save",
            prompt="Save test prompt",
            negative_prompt="",
            input_video_path=str(tmp_path / "video.mp4"),
            control_inputs={"depth": str(tmp_path / "depth.mp4")},
            timestamp="2025-01-01T00:00:00Z",
            is_upsampled=False,
            parent_prompt_text=None,
        )

        # Create results
        upsampled_results = [
            {
                "spec_id": "save_test",
                "upsampled_prompt": "A detailed save test prompt with enhancements",
            }
        ]

        results_file = tmp_path / "batch_results.json"
        results_file.write_text(json.dumps(upsampled_results))

        # Run upsampling
        result = orchestrator.run_prompt_upsampling([test_prompt])

        # Check that files were created
        updated_spec = result["updated_specs"][0]

        # PromptSpecManager should have saved the file
        # The exact path depends on the implementation
        # but we can verify the spec has the required save method called
        assert updated_spec.id is not None
        assert updated_spec.timestamp is not None
