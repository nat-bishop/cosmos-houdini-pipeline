"""
Simplified integration tests that focus on testing behavior without mocking internals.
"""

from datetime import datetime

import pytest

# Import from test stubs temporarily until full migration
from tests.test_stubs import ExecutionStatus, PromptSpec, RunSpec


class TestWorkflowOrchestrationSimple:
    """Simplified workflow tests focusing on behavior."""

    @pytest.mark.integration
    def test_schemas_work_together(self, sample_prompt_spec, sample_run_spec, temp_dir):
        """Test that PromptSpec and RunSpec schemas work correctly together."""
        # Save specs to files
        prompt_file = temp_dir / "prompt.json"
        sample_prompt_spec.save(prompt_file)

        run_file = temp_dir / "run.json"
        sample_run_spec.save(run_file)

        # Load them back
        loaded_prompt = PromptSpec.load(prompt_file)
        loaded_run = RunSpec.load(run_file)

        # Verify relationship
        assert loaded_run.prompt_id == loaded_prompt.id
        assert loaded_run.execution_status == ExecutionStatus.PENDING

    @pytest.mark.integration
    def test_runspec_with_parameters(self, temp_dir):
        """Test RunSpec with complete parameters."""
        run_spec = RunSpec(
            id="test_rs_complete",
            prompt_id="test_ps_123",
            name="complete_test_run",
            control_weights={"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25},
            parameters={
                "num_steps": 35,
                "guidance": 8.0,
                "sigma_max": 70.0,
                "blur_strength": "medium",
                "canny_threshold": "medium",
                "fps": 24,
                "seed": 42,
            },
            timestamp=datetime.now().isoformat(),
            execution_status=ExecutionStatus.PENDING,
            output_path=str(temp_dir / "output"),
        )

        # Save and reload
        spec_file = temp_dir / "complete_run.json"
        run_spec.save(spec_file)
        loaded = RunSpec.load(spec_file)

        # Verify all fields preserved
        assert loaded.id == run_spec.id
        assert loaded.name == run_spec.name
        assert loaded.control_weights == run_spec.control_weights
        assert loaded.parameters == run_spec.parameters
        assert loaded.execution_status == ExecutionStatus.PENDING

    @pytest.mark.integration
    def test_batch_spec_creation(self, temp_dir):
        """Test creating multiple specs for batch processing."""
        specs = []

        for i in range(5):
            prompt_spec = PromptSpec(
                id=f"batch_ps_{i:03d}",
                name=f"batch_scene_{i}",
                prompt=f"Scene {i} prompt",
                negative_prompt="",
                input_video_path=str(temp_dir / f"video_{i}.mp4"),
                control_inputs={},
                timestamp=datetime.now().isoformat(),
                is_upsampled=False,
                parent_prompt_text=None,
            )

            run_spec = RunSpec(
                id=f"batch_rs_{i:03d}",
                prompt_id=prompt_spec.id,
                name=f"batch_run_{i}",
                control_weights={"depth": 0.2 + i * 0.1},
                parameters={"num_steps": 30 + i, "guidance": 7.0 + i * 0.5, "seed": 100 + i},
                timestamp=datetime.now().isoformat(),
                execution_status=ExecutionStatus.PENDING,
                output_path=str(temp_dir / f"batch_output_{i}"),
            )

            specs.append((prompt_spec, run_spec))

        # Verify all specs are valid and unique
        assert len(specs) == 5
        ids = set()
        for prompt_spec, run_spec in specs:
            assert prompt_spec.id not in ids
            assert run_spec.id not in ids
            ids.add(prompt_spec.id)
            ids.add(run_spec.id)
            assert run_spec.prompt_id == prompt_spec.id

    @pytest.mark.integration
    def test_execution_status_transitions(self, sample_run_spec, temp_dir):
        """Test execution status transitions."""
        # Start as pending
        assert sample_run_spec.execution_status == ExecutionStatus.PENDING

        # Create new spec with running status
        running_spec = RunSpec(
            id=sample_run_spec.id,
            prompt_id=sample_run_spec.prompt_id,
            name=sample_run_spec.name,
            control_weights=sample_run_spec.control_weights,
            parameters=sample_run_spec.parameters,
            timestamp=sample_run_spec.timestamp,
            execution_status=ExecutionStatus.RUNNING,
            output_path=sample_run_spec.output_path,
        )

        # Save and reload
        spec_file = temp_dir / "status_test.json"
        running_spec.save(spec_file)
        loaded = RunSpec.load(spec_file)

        # Verify status preserved
        assert loaded.execution_status == ExecutionStatus.RUNNING

        # Test all status values
        for status in ExecutionStatus:
            status_spec = RunSpec(
                id=f"status_test_{status.value}",
                prompt_id="test_ps",
                name=f"status_test_{status.value}",
                control_weights={},
                parameters={},
                timestamp=datetime.now().isoformat(),
                execution_status=status,
                output_path=None,
            )

            status_file = temp_dir / f"status_{status.value}.json"
            status_spec.save(status_file)
            loaded_status = RunSpec.load(status_file)
            assert loaded_status.execution_status == status
