#!/usr/bin/env python3
"""
Comprehensive tests for PromptManager orchestrator.
Tests how PromptManager coordinates all specialized managers.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cosmos_workflow.prompts.prompt_manager import PromptManager
from cosmos_workflow.prompts.schemas import ExecutionStatus, PromptSpec, RunSpec


class TestPromptManagerOrchestrator:
    """Test the PromptManager orchestrator class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        # Create test directories
        self.prompts_dir = self.temp_path / "prompts"
        self.runs_dir = self.temp_path / "runs"
        self.outputs_dir = self.temp_path / "outputs"
        self.videos_dir = self.temp_path / "videos"

        self.prompts_dir.mkdir(parents=True)
        self.runs_dir.mkdir(parents=True)
        self.outputs_dir.mkdir(parents=True)
        self.videos_dir.mkdir(parents=True)

        # Create mock config
        self.mock_config = Mock()
        self.mock_config.prompts_dir = self.prompts_dir
        self.mock_config.runs_dir = self.runs_dir
        self.mock_config.outputs_dir = self.outputs_dir
        self.mock_config.videos_dir = self.videos_dir

    def teardown_method(self):
        """Clean up test fixtures after each test method."""
        self.temp_dir.cleanup()

    def test_prompt_manager_initialization(self):
        """Test PromptManager initialization and setup."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            # Check that directories were created
            assert self.prompts_dir.exists()
            assert self.runs_dir.exists()
            assert self.outputs_dir.exists()

            # Check that specialized managers were initialized
            assert hasattr(prompt_manager, "prompt_spec_manager")
            assert hasattr(prompt_manager, "run_spec_manager")
            assert hasattr(prompt_manager, "validator")
            assert hasattr(prompt_manager, "dir_manager")

    def test_create_prompt_spec_delegates_to_manager(self):
        """Test that create_prompt_spec delegates to PromptSpecManager."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            # Mock the PromptSpecManager
            mock_prompt_spec = Mock(spec=PromptSpec)
            mock_prompt_spec.id = "ps_test123"
            mock_prompt_spec.name = "test_prompt"

            with patch.object(
                prompt_manager.prompt_spec_manager, "create_prompt_spec"
            ) as mock_create:
                mock_create.return_value = mock_prompt_spec

                result = prompt_manager.create_prompt_spec("test_prompt", "Test prompt text")

                # Verify delegation
                mock_create.assert_called_once_with(
                    name="test_prompt",
                    prompt_text="Test prompt text",
                    negative_prompt="bad quality, blurry, low resolution, cartoonish",
                    input_video_path=None,
                    control_inputs=None,
                    is_upsampled=False,
                    parent_prompt_text=None,
                )

                assert result == mock_prompt_spec

    def test_create_prompt_spec_with_custom_parameters(self):
        """Test create_prompt_spec with custom parameters."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            mock_prompt_spec = Mock(spec=PromptSpec)
            mock_prompt_spec.id = "ps_test123"
            mock_prompt_spec.name = "test_prompt"

            with patch.object(
                prompt_manager.prompt_spec_manager, "create_prompt_spec"
            ) as mock_create:
                mock_create.return_value = mock_prompt_spec

                result = prompt_manager.create_prompt_spec(
                    "test_prompt",
                    "Test prompt text",
                    negative_prompt="Custom negative prompt",
                    input_video_path="custom/video.mp4",
                    control_inputs={"depth": "custom/depth.mp4"},
                    is_upsampled=True,
                    parent_prompt_text="Original prompt",
                )

                # Verify delegation with custom parameters
                mock_create.assert_called_once_with(
                    name="test_prompt",
                    prompt_text="Test prompt text",
                    negative_prompt="Custom negative prompt",
                    input_video_path="custom/video.mp4",
                    control_inputs={"depth": "custom/depth.mp4"},
                    is_upsampled=True,
                    parent_prompt_text="Original prompt",
                )

                assert result == mock_prompt_spec

    def test_create_run_spec_delegates_to_manager(self):
        """Test that create_run_spec delegates to RunSpecManager."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            # Create a mock PromptSpec
            mock_prompt_spec = Mock(spec=PromptSpec)
            mock_prompt_spec.id = "ps_test123"
            mock_prompt_spec.name = "test_prompt"

            # Create a mock RunSpec
            mock_run_spec = Mock(spec=RunSpec)
            mock_run_spec.id = "rs_test456"
            mock_run_spec.prompt_id = "ps_test123"

            with patch.object(prompt_manager.run_spec_manager, "create_run_spec") as mock_create:
                mock_create.return_value = mock_run_spec

                result = prompt_manager.create_run_spec(
                    prompt_spec=mock_prompt_spec,
                    control_weights={"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1},
                    parameters={"num_steps": 50, "guidance": 10.0, "sigma_max": 75.0},
                    custom_output_path="custom/output",
                )

                # Verify delegation
                mock_create.assert_called_once_with(
                    prompt_id="ps_test123",
                    name="test_prompt",
                    control_weights={"vis": 0.5, "edge": 0.3, "depth": 0.1, "seg": 0.1},
                    parameters={"num_steps": 50, "guidance": 10.0, "sigma_max": 75.0},
                    output_path="custom/output",
                )

                assert result == mock_run_spec

    def test_create_run_spec_with_defaults(self):
        """Test create_run_spec with default parameters."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            mock_prompt_spec = Mock(spec=PromptSpec)
            mock_prompt_spec.id = "ps_test123"
            mock_prompt_spec.name = "test_prompt"
            mock_run_spec = Mock(spec=RunSpec)

            with patch.object(prompt_manager.run_spec_manager, "create_run_spec") as mock_create:
                mock_create.return_value = mock_run_spec

                result = prompt_manager.create_run_spec(prompt_spec=mock_prompt_spec)

                # Verify delegation with defaults
                mock_create.assert_called_once_with(
                    prompt_id="ps_test123",
                    name="test_prompt",
                    control_weights=None,
                    parameters=None,
                    output_path=None,
                )

                assert result == mock_run_spec

    def test_validate_prompt_spec_delegates_to_validator(self):
        """Test that validate_prompt_spec delegates to SchemaValidator."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            with patch.object(prompt_manager.validator, "validate_prompt_spec") as mock_validate:
                mock_validate.return_value = True

                result = prompt_manager.validate_prompt_spec("test_prompt.json")

                # Verify delegation
                mock_validate.assert_called_once_with("test_prompt.json")
                assert result is True

    def test_validate_run_spec_delegates_to_validator(self):
        """Test that validate_run_spec delegates to SchemaValidator."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            with patch.object(prompt_manager.validator, "validate_run_spec") as mock_validate:
                mock_validate.return_value = True

                result = prompt_manager.validate_run_spec("test_run.json")

                # Verify delegation
                mock_validate.assert_called_once_with("test_run.json")
                assert result is True

    def test_list_prompts_delegates_to_manager(self):
        """Test that list_prompts delegates to PromptSpecManager."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            mock_prompts = [Path("prompt1.json"), Path("prompt2.json")]

            with patch.object(prompt_manager.prompt_spec_manager, "list_prompts") as mock_list:
                mock_list.return_value = mock_prompts

                result = prompt_manager.list_prompts(pattern="test")

                # Verify delegation
                mock_list.assert_called_once_with(prompt_manager.prompts_dir, "test")
                assert result == mock_prompts

    def test_list_prompts_without_pattern(self):
        """Test list_prompts without pattern."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            mock_prompts = [Path("prompt1.json"), Path("prompt2.json")]

            with patch.object(prompt_manager.prompt_spec_manager, "list_prompts") as mock_list:
                mock_list.return_value = mock_prompts

                result = prompt_manager.list_prompts()

                # Verify delegation without pattern
                mock_list.assert_called_once_with(prompt_manager.prompts_dir, None)
                assert result == mock_prompts

    def test_list_runs_delegates_to_manager(self):
        """Test that list_runs delegates to RunSpecManager."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            mock_runs = [Path("run1.json"), Path("run2.json")]

            with patch.object(prompt_manager.run_spec_manager, "list_runs") as mock_list:
                mock_list.return_value = mock_runs

                result = prompt_manager.list_runs(pattern="test")

                # Verify delegation
                mock_list.assert_called_once_with(prompt_manager.runs_dir, "test")
                assert result == mock_runs

    def test_get_prompt_info_delegates_to_manager(self):
        """Test that get_prompt_info delegates to PromptSpecManager."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            mock_info = {"id": "ps_test123", "name": "test_prompt"}

            with patch.object(
                prompt_manager.prompt_spec_manager, "get_prompt_info"
            ) as mock_get_info:
                mock_get_info.return_value = mock_info

                result = prompt_manager.get_prompt_info("test_prompt.json")

                # Verify delegation
                mock_get_info.assert_called_once_with("test_prompt.json")
                assert result == mock_info

    def test_get_run_info_delegates_to_manager(self):
        """Test that get_run_info delegates to RunSpecManager."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            mock_info = {"id": "rs_test456", "prompt_id": "ps_test123"}

            with patch.object(prompt_manager.run_spec_manager, "get_run_info") as mock_get_info:
                mock_get_info.return_value = mock_info

                result = prompt_manager.get_run_info("test_run.json")

                # Verify delegation
                mock_get_info.assert_called_once_with("test_run.json")
                assert result == mock_info

    def test_prompt_manager_directory_creation(self):
        """Test that PromptManager creates necessary directories."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            # Remove directories to test creation
            import shutil

            shutil.rmtree(self.prompts_dir)
            shutil.rmtree(self.runs_dir)
            shutil.rmtree(self.outputs_dir)

            prompt_manager = PromptManager("dummy_config.toml")

            # Check that directories were created
            assert self.prompts_dir.exists()
            assert self.runs_dir.exists()
            assert self.outputs_dir.exists()
            assert self.prompts_dir.is_dir()
            assert self.runs_dir.is_dir()
            assert self.outputs_dir.is_dir()

    def test_prompt_manager_directory_manager_integration(self):
        """Test that PromptManager properly integrates with DirectoryManager."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            # Check that DirectoryManager was initialized correctly
            assert prompt_manager.dir_manager.base_prompts_dir == self.prompts_dir
            assert prompt_manager.dir_manager.base_runs_dir == self.runs_dir

            # Check that directories were ensured
            assert self.prompts_dir.exists()
            assert self.runs_dir.exists()

    def test_prompt_manager_manager_initialization(self):
        """Test that all specialized managers are properly initialized."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            # Check that all managers exist and have correct types
            assert hasattr(prompt_manager, "prompt_spec_manager")
            assert hasattr(prompt_manager, "run_spec_manager")
            assert hasattr(prompt_manager, "validator")

            # Check that managers have access to the directory manager
            assert prompt_manager.prompt_spec_manager.dir_manager == prompt_manager.dir_manager
            assert prompt_manager.run_spec_manager.dir_manager == prompt_manager.dir_manager

    def test_prompt_manager_error_propagation(self):
        """Test that errors from specialized managers are properly propagated."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            # Test error propagation from PromptSpecManager
            with patch.object(
                prompt_manager.prompt_spec_manager, "create_prompt_spec"
            ) as mock_create:
                mock_create.side_effect = ValueError("Test error")

                with pytest.raises(ValueError, match="Test error"):
                    prompt_manager.create_prompt_spec("test", "test prompt")

            # Test error propagation from RunSpecManager
            mock_prompt_spec = Mock(spec=PromptSpec)
            mock_prompt_spec.id = "ps_test123"
            mock_prompt_spec.name = "test_prompt"
            with patch.object(prompt_manager.run_spec_manager, "create_run_spec") as mock_create:
                mock_create.side_effect = RuntimeError("Test runtime error")

                with pytest.raises(RuntimeError, match="Test runtime error"):
                    prompt_manager.create_run_spec(prompt_spec=mock_prompt_spec)

    def test_prompt_manager_method_chaining(self):
        """Test that PromptManager methods can be chained together."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            # Mock all the necessary methods
            mock_prompt_spec = Mock(spec=PromptSpec)
            mock_prompt_spec.id = "ps_test123"
            mock_prompt_spec.name = "test_prompt"

            mock_run_spec = Mock(spec=RunSpec)
            mock_run_spec.id = "rs_test456"

            with patch.object(
                prompt_manager.prompt_spec_manager, "create_prompt_spec"
            ) as mock_create_prompt:
                with patch.object(
                    prompt_manager.run_spec_manager, "create_run_spec"
                ) as mock_create_run:
                    mock_create_prompt.return_value = mock_prompt_spec
                    mock_create_run.return_value = mock_run_spec

                    # Test method chaining
                    prompt_spec = prompt_manager.create_prompt_spec("test_prompt", "Test prompt")
                    run_spec = prompt_manager.create_run_spec(prompt_spec=prompt_spec)

                    # Verify both methods were called
                    mock_create_prompt.assert_called_once()
                    mock_create_run.assert_called_once()

                    assert prompt_spec == mock_prompt_spec
                    assert run_spec == mock_run_spec

    def test_prompt_manager_config_file_handling(self):
        """Test that PromptManager handles config file paths correctly."""
        config_path = "custom_config.toml"

        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager(config_path)

            # Verify ConfigManager was called with correct path
            mock_config_class.assert_called_once_with(config_path)

    def test_prompt_manager_directory_paths(self):
        """Test that PromptManager correctly sets directory paths."""
        with patch("cosmos_workflow.prompts.prompt_manager.ConfigManager") as mock_config_class:
            mock_config_class.return_value.get_local_config.return_value = self.mock_config

            prompt_manager = PromptManager("dummy_config.toml")

            # Check that paths are correctly set
            assert prompt_manager.prompts_dir == self.prompts_dir
            assert prompt_manager.runs_dir == self.runs_dir
            assert prompt_manager.outputs_dir == self.outputs_dir
            assert prompt_manager.videos_dir == self.videos_dir
