"""
Comprehensive tests for prompt_manager.py to improve coverage from 12.90% to 85%+
Tests the PromptManager orchestrator class.
"""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest

from cosmos_workflow.prompts.prompt_manager import PromptManager
from cosmos_workflow.prompts.schemas import ExecutionStatus, PromptSpec, RunSpec


class TestPromptManager:
    """Test the PromptManager orchestrator class."""

    @pytest.fixture
    def temp_config_file(self, temp_dir):
        """Create a temporary config file."""
        # Use forward slashes for TOML compatibility on Windows
        prompts_dir = str(temp_dir / "prompts").replace("\\", "/")
        runs_dir = str(temp_dir / "runs").replace("\\", "/")
        outputs_dir = str(temp_dir / "outputs").replace("\\", "/")
        videos_dir = str(temp_dir / "videos").replace("\\", "/")
        notes_dir = str(temp_dir / "notes").replace("\\", "/")
        ssh_key = str(temp_dir / "key.pem").replace("\\", "/")

        config_content = f"""
[local]
prompts_dir = "{prompts_dir}"
runs_dir = "{runs_dir}"
outputs_dir = "{outputs_dir}"
videos_dir = "{videos_dir}"
notes_dir = "{notes_dir}"

[remote]
host = "test-host"
port = 22
user = "test-user"
ssh_key = "{ssh_key}"
remote_dir = "/remote/test"
docker_image = "test-image"
"""
        config_file = temp_dir / "test_config.toml"
        config_file.write_text(config_content)
        return str(config_file)

    @pytest.fixture
    def prompt_manager(self, temp_config_file):
        """Create a PromptManager instance with test config."""
        return PromptManager(temp_config_file)

    def test_initialization(self, prompt_manager, temp_dir):
        """Test PromptManager initialization."""
        # Check that managers are initialized
        assert prompt_manager.config_manager is not None
        assert prompt_manager.prompt_spec_manager is not None
        assert prompt_manager.run_spec_manager is not None
        assert prompt_manager.validator is not None
        assert prompt_manager.dir_manager is not None

        # Check directories were created
        assert (temp_dir / "prompts").exists()
        assert (temp_dir / "runs").exists()
        assert (temp_dir / "outputs").exists()

    def test_create_prompt_spec_minimal(self, prompt_manager):
        """Test creating a minimal PromptSpec."""
        prompt_spec = prompt_manager.create_prompt_spec(prompt_text="A beautiful sunset")

        assert prompt_spec is not None
        assert prompt_spec.prompt == "A beautiful sunset"
        assert prompt_spec.negative_prompt == "bad quality, blurry, low resolution, cartoonish"
        assert prompt_spec.id.startswith("ps_")

    def test_create_prompt_spec_full(self, prompt_manager, temp_dir):
        """Test creating a PromptSpec with all parameters."""
        video_path = temp_dir / "test_video.mp4"
        video_path.touch()

        control_inputs = {"depth": str(temp_dir / "depth.mp4"), "edge": str(temp_dir / "edge.mp4")}

        # Create the control files
        for path in control_inputs.values():
            Path(path).touch()

        prompt_spec = prompt_manager.create_prompt_spec(
            name="sunset_scene",
            prompt_text="A beautiful sunset over mountains",
            negative_prompt="dark, gloomy",
            input_video_path=str(video_path),
            control_inputs=control_inputs,
            is_upsampled=True,
            parent_prompt_text="Original prompt",
        )

        assert prompt_spec.name == "sunset_scene"
        assert prompt_spec.prompt == "A beautiful sunset over mountains"
        assert prompt_spec.negative_prompt == "dark, gloomy"
        assert prompt_spec.input_video_path == str(video_path)
        assert prompt_spec.control_inputs == control_inputs
        assert prompt_spec.is_upsampled is True
        assert prompt_spec.parent_prompt_text == "Original prompt"

    def test_create_run_spec(self, prompt_manager):
        """Test creating a RunSpec from a PromptSpec."""
        # First create a prompt spec
        prompt_spec = prompt_manager.create_prompt_spec(
            name="test_prompt", prompt_text="Test prompt text"
        )

        # Create run spec
        run_spec = prompt_manager.create_run_spec(
            prompt_spec=prompt_spec,
            control_weights={"depth": 0.5, "edge": 0.3},
            parameters={"num_steps": 50, "seed": 42},
        )

        assert run_spec is not None
        assert run_spec.prompt_id == prompt_spec.id
        assert run_spec.name == prompt_spec.name
        assert run_spec.control_weights == {"depth": 0.5, "edge": 0.3}
        assert run_spec.parameters["num_steps"] == 50
        assert run_spec.parameters["seed"] == 42

    def test_create_run_spec_with_custom_output(self, prompt_manager, temp_dir):
        """Test creating a RunSpec with custom output path."""
        prompt_spec = prompt_manager.create_prompt_spec(prompt_text="Test prompt")

        custom_output = str(temp_dir / "custom_output")
        run_spec = prompt_manager.create_run_spec(
            prompt_spec=prompt_spec, custom_output_path=custom_output
        )

        assert run_spec.output_path == custom_output

    def test_validate_prompt_spec_valid(self, prompt_manager, temp_dir):
        """Test validating a valid PromptSpec file."""
        # Create a valid prompt spec file
        prompt_spec = PromptSpec(
            id="test_ps_123",
            name="test",
            prompt="Test prompt",
            negative_prompt="",
            input_video_path="test.mp4",
            control_inputs={},
            timestamp="2025-01-01T00:00:00Z",
        )

        spec_file = temp_dir / "test_prompt.json"
        spec_file.write_text(json.dumps(prompt_spec.to_dict()))

        # Validate
        is_valid = prompt_manager.validate_prompt_spec(spec_file)
        assert is_valid is True

    def test_validate_prompt_spec_invalid(self, prompt_manager, temp_dir):
        """Test validating an invalid PromptSpec file."""
        # Create an invalid spec file (missing required fields)
        invalid_spec = {
            "id": "test_ps_123",
            # Missing required fields like 'name', 'prompt', etc.
        }

        spec_file = temp_dir / "invalid_prompt.json"
        spec_file.write_text(json.dumps(invalid_spec))

        # Validate
        is_valid = prompt_manager.validate_prompt_spec(spec_file)
        assert is_valid is False

    def test_validate_run_spec_valid(self, prompt_manager, temp_dir):
        """Test validating a valid RunSpec file."""
        run_spec = RunSpec(
            id="test_rs_456",
            prompt_id="test_ps_123",
            name="test_run",
            control_weights={},
            parameters={},
            timestamp="2025-01-01T00:00:00Z",
            execution_status=ExecutionStatus.PENDING,
        )

        spec_file = temp_dir / "test_run.json"
        spec_file.write_text(json.dumps(run_spec.to_dict()))

        is_valid = prompt_manager.validate_run_spec(spec_file)
        assert is_valid is True

    def test_validate_run_spec_invalid(self, prompt_manager, temp_dir):
        """Test validating an invalid RunSpec file."""
        invalid_spec = {
            "id": "test_rs_456",
            # Missing required fields
        }

        spec_file = temp_dir / "invalid_run.json"
        spec_file.write_text(json.dumps(invalid_spec))

        is_valid = prompt_manager.validate_run_spec(spec_file)
        assert is_valid is False

    def test_list_prompts(self, prompt_manager, temp_dir):
        """Test listing prompt files."""
        # Create some prompt files
        prompts_dir = temp_dir / "prompts" / "2025-01-01"
        prompts_dir.mkdir(parents=True)

        for i in range(3):
            prompt_file = prompts_dir / f"prompt_{i}.json"
            prompt_file.write_text("{}")

        # List prompts
        prompts = prompt_manager.list_prompts()
        assert len(prompts) >= 3

    def test_list_prompts_with_pattern(self, prompt_manager, temp_dir):
        """Test listing prompts with a pattern."""
        prompts_dir = temp_dir / "prompts" / "2025-01-01"
        prompts_dir.mkdir(parents=True)

        # Create files with different patterns
        (prompts_dir / "test_prompt_1.json").write_text("{}")
        (prompts_dir / "test_prompt_2.json").write_text("{}")
        (prompts_dir / "other_prompt.json").write_text("{}")

        # List with pattern
        prompts = prompt_manager.list_prompts(pattern="**/test_*.json")
        test_prompts = [p for p in prompts if "test_" in p.name]
        assert len(test_prompts) >= 2

    def test_list_runs(self, prompt_manager, temp_dir):
        """Test listing run files."""
        runs_dir = temp_dir / "runs" / "2025-01-01"
        runs_dir.mkdir(parents=True)

        for i in range(3):
            run_file = runs_dir / f"run_{i}.json"
            run_file.write_text("{}")

        runs = prompt_manager.list_runs()
        assert len(runs) >= 3

    def test_list_runs_with_pattern(self, prompt_manager, temp_dir):
        """Test listing runs with a pattern."""
        runs_dir = temp_dir / "runs" / "2025-01-01"
        runs_dir.mkdir(parents=True)

        (runs_dir / "test_run_1.json").write_text("{}")
        (runs_dir / "test_run_2.json").write_text("{}")
        (runs_dir / "other_run.json").write_text("{}")

        runs = prompt_manager.list_runs(pattern="**/test_*.json")
        test_runs = [r for r in runs if "test_" in r.name]
        assert len(test_runs) >= 2

    def test_directory_creation(self, temp_dir):
        """Test that all required directories are created."""
        config_file = temp_dir / "config.toml"
        # Use forward slashes for TOML compatibility
        prompts_dir = str(temp_dir / "new_prompts").replace("\\", "/")
        runs_dir = str(temp_dir / "new_runs").replace("\\", "/")
        outputs_dir = str(temp_dir / "new_outputs").replace("\\", "/")
        videos_dir = str(temp_dir / "new_videos").replace("\\", "/")
        notes_dir = str(temp_dir / "new_notes").replace("\\", "/")

        config_content = f"""
[local]
prompts_dir = "{prompts_dir}"
runs_dir = "{runs_dir}"
outputs_dir = "{outputs_dir}"
videos_dir = "{videos_dir}"
notes_dir = "{notes_dir}"

[remote]
host = "test"
port = 22
user = "test"
ssh_key = "test.pem"
remote_dir = "/test"
docker_image = "test"
"""
        config_file.write_text(config_content)

        # Create manager - should create directories
        PromptManager(str(config_file))

        assert (temp_dir / "new_prompts").exists()
        assert (temp_dir / "new_runs").exists()
        assert (temp_dir / "new_outputs").exists()

    def test_manager_delegation(self, prompt_manager):
        """Test that methods properly delegate to specialized managers."""
        # Mock the specialized managers
        prompt_manager.prompt_spec_manager = Mock()
        prompt_manager.run_spec_manager = Mock()
        prompt_manager.validator = Mock()

        # Test delegation
        prompt_manager.create_prompt_spec(prompt_text="test")
        prompt_manager.prompt_spec_manager.create_prompt_spec.assert_called_once()

        mock_prompt_spec = Mock(id="test_id", name="test")
        prompt_manager.create_run_spec(mock_prompt_spec)
        prompt_manager.run_spec_manager.create_run_spec.assert_called_once()

        prompt_manager.validate_prompt_spec("test.json")
        prompt_manager.validator.validate_prompt_spec.assert_called_once()

        prompt_manager.validate_run_spec("test.json")
        prompt_manager.validator.validate_run_spec.assert_called_once()

    def test_config_loading_error(self, temp_dir):
        """Test handling of config loading errors."""
        # Try to load non-existent config
        with pytest.raises(FileNotFoundError):
            PromptManager("non_existent_config.toml")

    def test_invalid_config_format(self, temp_dir):
        """Test handling of invalid config format."""
        config_file = temp_dir / "bad_config.toml"
        config_file.write_text("invalid toml content{")

        with pytest.raises(Exception):  # Should raise some parsing error
            PromptManager(str(config_file))


class TestPromptManagerIntegration:
    """Integration tests for PromptManager with real components."""

    @pytest.fixture
    def integration_manager(self, temp_dir):
        """Create a PromptManager with real components."""
        # Use forward slashes for TOML compatibility
        prompts_dir = str(temp_dir / "prompts").replace("\\", "/")
        runs_dir = str(temp_dir / "runs").replace("\\", "/")
        outputs_dir = str(temp_dir / "outputs").replace("\\", "/")
        videos_dir = str(temp_dir / "videos").replace("\\", "/")
        notes_dir = str(temp_dir / "notes").replace("\\", "/")

        config_content = f"""
[local]
prompts_dir = "{prompts_dir}"
runs_dir = "{runs_dir}"
outputs_dir = "{outputs_dir}"
videos_dir = "{videos_dir}"
notes_dir = "{notes_dir}"

[remote]
host = "test"
port = 22
user = "test"
ssh_key = "test.pem"
remote_dir = "/test"
docker_image = "test"
"""
        config_file = temp_dir / "config.toml"
        config_file.write_text(config_content)
        return PromptManager(str(config_file))

    def test_full_workflow(self, integration_manager, temp_dir):
        """Test complete workflow from prompt to run spec."""
        # Create video file
        video_file = temp_dir / "videos" / "test.mp4"
        video_file.parent.mkdir(parents=True, exist_ok=True)
        video_file.touch()

        # Create prompt spec
        prompt_spec = integration_manager.create_prompt_spec(
            name="workflow_test",
            prompt_text="Test workflow prompt",
            input_video_path=str(video_file),
        )

        # Verify it was saved
        prompt_files = integration_manager.list_prompts()
        assert any("workflow_test" in str(p) for p in prompt_files)

        # Create run spec
        integration_manager.create_run_spec(
            prompt_spec=prompt_spec, control_weights={"depth": 0.5}, parameters={"num_steps": 30}
        )

        # Verify it was saved
        run_files = integration_manager.list_runs()
        assert any("workflow_test" in str(r) for r in run_files)

        # Validate both specs
        prompt_file = next(p for p in prompt_files if "workflow_test" in str(p))
        assert integration_manager.validate_prompt_spec(prompt_file) is True

        run_file = next(r for r in run_files if "workflow_test" in str(r))
        assert integration_manager.validate_run_spec(run_file) is True
