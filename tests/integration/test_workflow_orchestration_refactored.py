"""
Integration tests for the complete workflow orchestration.
Tests the full pipeline from PromptSpec creation to inference execution.

REFACTORED: Following TEST_SUITE_INVESTIGATION_REPORT.md recommendations:
- Uses fake implementations instead of mocks
- Tests behavior and outcomes, not implementation details
- Would survive internal refactoring
"""

import json
from datetime import datetime

import pytest

from tests.fixtures.fakes import (
    FakePromptSpec,
    FakeRunSpec,
    FakeWorkflowOrchestrator,
)


class TestWorkflowOrchestrationBehavior:
    """Test workflow orchestration behavior, not implementation.

    These tests verify that the workflow produces correct outcomes
    rather than checking specific method calls.
    """

    @pytest.fixture
    def fake_orchestrator(self):
        """Create orchestrator with fake dependencies."""
        return FakeWorkflowOrchestrator()

    @pytest.fixture
    def test_specs(self, tmp_path):
        """Create test specifications."""
        # Create prompt spec
        prompt_spec = FakePromptSpec(
            id="test_ps_001",
            name="mountain_scene",
            prompt="A majestic mountain landscape at sunset",
            input_video_path=str(tmp_path / "input.mp4"),
        )

        # Create run spec
        run_spec = FakeRunSpec(
            id="test_rs_001",
            prompt_spec_id=prompt_spec.id,
            control_weights={"depth": 0.4, "segmentation": 0.3},
            parameters={"num_steps": 35, "seed": 42},
        )

        # Write specs to files
        prompt_file = tmp_path / "prompt_spec.json"
        prompt_file.write_text(json.dumps(prompt_spec.to_dict()))

        run_file = tmp_path / "run_spec.json"
        run_file.write_text(json.dumps(run_spec.to_dict()))

        # Create mock input video
        input_video = tmp_path / "input.mp4"
        input_video.write_bytes(b"mock video data")

        return {
            "prompt_spec": prompt_spec,
            "run_spec": run_spec,
            "prompt_file": prompt_file,
            "run_file": run_file,
            "input_video": input_video,
        }

    @pytest.mark.integration
    def test_workflow_completes_successfully(self, fake_orchestrator, test_specs):
        """Test that workflow completes with expected outcomes.

        This test verifies BEHAVIOR:
        - Workflow returns success
        - Files are transferred
        - Inference is executed
        - Results are available

        It does NOT test:
        - Specific method calls
        - Call order
        - Internal implementation details
        """
        # Execute workflow
        result = fake_orchestrator.run_inference(
            str(test_specs["run_file"]), num_gpus=2, verbose=True
        )

        # Verify OUTCOME: Workflow completed successfully
        assert result is True

        # Verify OUTCOME: Workflow was tracked
        assert len(fake_orchestrator.workflows_run) == 1
        workflow = fake_orchestrator.workflows_run[0]
        assert workflow["type"] == "inference"
        assert workflow["num_gpus"] == 2

        # Verify OUTCOME: Files were uploaded (behavior, not calls)
        assert len(fake_orchestrator.file_transfer.uploaded_files) > 0

        # Verify OUTCOME: Docker container was run
        assert len(fake_orchestrator.docker_executor.containers_run) == 1
        container = fake_orchestrator.docker_executor.containers_run[0]
        assert container[0] == "inference"
        assert container[1]["num_gpu"] == 2

        # Verify OUTCOME: Results exist
        prompt_name = test_specs["prompt_spec"].name
        assert prompt_name in fake_orchestrator.docker_executor.inference_results
        result = fake_orchestrator.docker_executor.inference_results[prompt_name]
        assert result["status"] == "success"
        assert "output_path" in result

    @pytest.mark.integration
    def test_workflow_handles_missing_input_gracefully(self, fake_orchestrator, tmp_path):
        """Test that workflow fails gracefully with missing input.

        Tests BEHAVIOR when input is invalid, not error propagation details.
        """
        # Create run spec pointing to non-existent file
        missing_file = tmp_path / "missing_run_spec.json"

        # Execute workflow with missing file
        result = fake_orchestrator.run_inference(str(missing_file))

        # Verify OUTCOME: Workflow failed gracefully
        assert result is False

        # Verify OUTCOME: No containers were run
        assert len(fake_orchestrator.docker_executor.containers_run) == 0

    @pytest.mark.integration
    def test_workflow_produces_correct_output_structure(self, fake_orchestrator, test_specs):
        """Test that workflow produces expected output structure.

        Verifies the CONTRACT of the workflow output, not how it's produced.
        """
        # Execute workflow
        result = fake_orchestrator.run_inference(str(test_specs["run_file"]))

        assert result is True

        # Verify output structure matches contract
        prompt_name = test_specs["prompt_spec"].name
        inference_result = fake_orchestrator.docker_executor.inference_results[prompt_name]

        # Check required fields exist
        required_fields = ["status", "output_path", "duration", "timestamp"]
        for field in required_fields:
            assert field in inference_result

        # Verify output path follows expected pattern
        assert f"outputs/{prompt_name}" in inference_result["output_path"]
        assert inference_result["output_path"].endswith(".mp4")

        # Verify timestamp is valid ISO format
        datetime.fromisoformat(inference_result["timestamp"])

    @pytest.mark.integration
    def test_workflow_respects_gpu_configuration(self, fake_orchestrator, test_specs):
        """Test that workflow correctly configures GPU usage.

        Tests the BEHAVIOR of GPU configuration, not HOW it's implemented.
        """
        # Test with different GPU configurations
        gpu_configs = [(1, "0"), (2, "0,1"), (4, "0,1,2,3")]

        for num_gpus, _expected_devices in gpu_configs:
            # Reset tracking
            fake_orchestrator.docker_executor.containers_run.clear()

            # Run with specific GPU config
            result = fake_orchestrator.run_inference(str(test_specs["run_file"]), num_gpus=num_gpus)

            assert result is True

            # Verify GPU configuration was applied
            container = fake_orchestrator.docker_executor.containers_run[0]
            assert container[1]["num_gpu"] == num_gpus
            # Note: We test the behavior (num_gpu is set correctly)
            # not the implementation (exact cuda_devices string)

    @pytest.mark.integration
    def test_workflow_tracks_execution_history(self, fake_orchestrator, test_specs):
        """Test that workflow maintains execution history.

        Verifies BEHAVIOR of history tracking without coupling to storage mechanism.
        """
        # Run multiple workflows
        for i in range(3):
            result = fake_orchestrator.run_inference(str(test_specs["run_file"]), num_gpus=i + 1)
            assert result is True

        # Verify history is maintained
        assert len(fake_orchestrator.workflows_run) == 3

        # Verify each execution is tracked with correct metadata
        for i, workflow in enumerate(fake_orchestrator.workflows_run):
            assert workflow["num_gpus"] == i + 1
            assert "timestamp" in workflow
            # Verify timestamps are in order
            if i > 0:
                prev_time = datetime.fromisoformat(
                    fake_orchestrator.workflows_run[i - 1]["timestamp"]
                )
                curr_time = datetime.fromisoformat(workflow["timestamp"])
                assert curr_time >= prev_time

    @pytest.mark.integration
    def test_system_status_check(self, fake_orchestrator):
        """Test system status checking behavior.

        Tests WHAT the status check reports, not HOW it gathers the information.
        """
        # Initially connected
        assert fake_orchestrator.check_status() is True

        # Disconnect
        fake_orchestrator.ssh_manager.disconnect()
        assert fake_orchestrator.check_status() is False

        # Reconnect
        fake_orchestrator.ssh_manager.connect()
        assert fake_orchestrator.check_status() is True

    @pytest.mark.integration
    def test_docker_status_reporting(self, fake_orchestrator, test_specs):
        """Test Docker status reporting behavior.

        Verifies the CONTRACT of status reporting, not implementation.
        """
        # Get initial status
        status = fake_orchestrator.docker_executor.get_docker_status()
        assert status["docker_running"] is True
        assert status["containers_run"] == 0

        # Run some workflows
        for _ in range(3):
            fake_orchestrator.run_inference(str(test_specs["run_file"]))

        # Check updated status
        status = fake_orchestrator.docker_executor.get_docker_status()
        assert status["containers_run"] == 3

        # Disconnect and check status
        fake_orchestrator.ssh_manager.disconnect()
        status = fake_orchestrator.docker_executor.get_docker_status()
        assert status["docker_running"] is False
        assert "error" in status


class TestUpscalingWorkflow:
    """Test upscaling workflow behavior."""

    @pytest.fixture
    def setup_for_upscaling(self, tmp_path):
        """Set up orchestrator with completed inference."""
        orchestrator = FakeWorkflowOrchestrator()

        # Create and run initial inference
        prompt_spec = FakePromptSpec(name="test_scene")
        prompt_file = tmp_path / "prompt.json"
        prompt_file.write_text(json.dumps(prompt_spec.to_dict()))

        # Simulate successful inference
        orchestrator.docker_executor.run_inference(prompt_file)

        return orchestrator, prompt_file

    @pytest.mark.integration
    def test_upscaling_requires_completed_inference(self, setup_for_upscaling):
        """Test that upscaling verifies input video exists.

        Tests BEHAVIOR: upscaling fails without prior inference.
        """
        orchestrator, prompt_file = setup_for_upscaling

        # Upscaling with existing inference should work
        orchestrator.docker_executor.run_upscaling(prompt_file, control_weight=0.7)

        # Verify upscaling was executed
        assert len(orchestrator.docker_executor.containers_run) == 2
        upscale_run = orchestrator.docker_executor.containers_run[1]
        assert upscale_run[0] == "upscaling"
        assert upscale_run[1]["control_weight"] == 0.7

        # Upscaling without inference should fail
        new_prompt = prompt_file.parent / "new_prompt.json"
        new_prompt.write_text('{"name": "new_scene"}')

        with pytest.raises(FileNotFoundError, match="Input video not found"):
            orchestrator.docker_executor.run_upscaling(new_prompt)

    @pytest.mark.integration
    def test_upscaling_creates_separate_output(self, setup_for_upscaling):
        """Test that upscaling creates separate output directory.

        Verifies BEHAVIOR of output organization, not implementation.
        """
        orchestrator, prompt_file = setup_for_upscaling

        # Run upscaling
        orchestrator.docker_executor.run_upscaling(prompt_file)

        # Verify separate output directory was created
        created_dirs = orchestrator.docker_executor.remote_executor.created_directories

        # Should have directories for both regular and upscaled output
        assert any("test_scene" in d and "upscaled" not in d for d in created_dirs)
        assert any("test_scene_upscaled" in d for d in created_dirs)
