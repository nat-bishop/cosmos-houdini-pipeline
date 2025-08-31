#!/usr/bin/env python3
"""
Test smart naming functionality for PromptSpec creation.

Tests that PromptSpecs can auto-generate names from prompt text
using the same smart naming algorithm.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from cosmos_workflow.prompts.prompt_manager import PromptManager
from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.schemas import DirectoryManager
from cosmos_workflow.utils.smart_naming import generate_smart_name, sanitize_name


class TestSmartNamingUtility:
    """Test the centralized smart naming utility."""

    def test_generate_smart_name_from_prompts(self):
        """Test name generation from various prompt texts."""
        test_cases = [
            (
                "Futuristic cyberpunk city with neon lights",
                ["futuristic", "cyberpunk", "city", "neon", "lights"],
            ),
            ("A beautiful sunset over the ocean waves", ["beautiful", "sunset", "ocean", "waves"]),
            (
                "Transform this into an anime style painting",
                ["transform", "anime", "style", "painting"],
            ),
            (
                "Make it look like a Van Gogh masterpiece",
                ["make", "look", "van", "gogh", "masterpiece"],
            ),
            (
                "Abstract geometric patterns with vibrant colors",
                ["abstract", "geometric", "patterns", "vibrant", "colors"],
            ),
        ]

        for prompt, expected_words in test_cases:
            name = generate_smart_name(prompt)

            # Check that at least some expected words appear
            name_parts = name.split("_")
            matches = sum(
                1 for word in expected_words if any(word in part.lower() for part in name_parts)
            )
            assert (
                matches >= 1
            ), f"Expected at least one of {expected_words} in name '{name}' from prompt '{prompt}'"

            # Verify name properties
            assert len(name) <= 20  # Default max length
            assert name.replace("_", "").isalnum()

    def test_sanitize_name(self):
        """Test name sanitization for filesystem safety."""
        test_cases = [
            ("My Cool Name!", "my_cool_name"),
            ("file/with\\slashes", "filewithslashes"),
            ("name@with#special$chars", "namewithspecialchars"),
            ("UPPERCASE NAME", "uppercase_name"),
            ("name   with   spaces", "name___with___spaces"),
        ]

        for input_name, expected in test_cases:
            sanitized = sanitize_name(input_name)
            assert all(
                c.isalnum() or c in "_-" for c in sanitized
            ), f"Sanitized name '{sanitized}' contains invalid characters"


class TestPromptSpecSmartNaming:
    """Test PromptSpec creation with smart naming."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def dir_manager(self, temp_dir):
        """Create a DirectoryManager for testing."""
        prompts_dir = temp_dir / "prompts"
        runs_dir = temp_dir / "runs"
        prompts_dir.mkdir(parents=True, exist_ok=True)
        runs_dir.mkdir(parents=True, exist_ok=True)
        return DirectoryManager(prompts_dir, runs_dir)

    def test_prompt_spec_with_auto_name(self, dir_manager):
        """Test creating a PromptSpec without providing a name."""
        manager = PromptSpecManager(dir_manager)

        # Create PromptSpec without name
        prompt_text = "A futuristic cityscape with flying cars and neon signs"
        spec = manager.create_prompt_spec(
            prompt_text=prompt_text, negative_prompt="blurry, low quality"
        )

        # Verify name was auto-generated
        assert spec.name is not None
        assert spec.name != ""
        assert (
            "futuristic" in spec.name.lower()
            or "cityscape" in spec.name.lower()
            or "flying" in spec.name.lower()
        )

        # Verify other fields
        assert spec.prompt == prompt_text
        assert spec.negative_prompt == "blurry, low quality"

    def test_prompt_spec_with_explicit_name(self, dir_manager):
        """Test creating a PromptSpec with an explicit name."""
        manager = PromptSpecManager(dir_manager)

        # Create PromptSpec with explicit name
        spec = manager.create_prompt_spec(
            name="my_custom_name", prompt_text="A beautiful landscape", negative_prompt="ugly"
        )

        # Verify explicit name was used
        assert spec.name == "my_custom_name"
        assert spec.prompt == "A beautiful landscape"

    def test_prompt_spec_name_generation_consistency(self, dir_manager):
        """Test that the same prompt generates consistent names."""
        manager = PromptSpecManager(dir_manager)

        prompt_text = "A majestic mountain landscape at sunrise"

        # Create multiple specs with the same prompt
        spec1 = manager.create_prompt_spec(prompt_text=prompt_text)
        spec2 = manager.create_prompt_spec(prompt_text=prompt_text)

        # Names should be similar (both derived from same prompt)
        # They may have different IDs but the base name should be similar
        assert spec1.name == spec2.name

    def test_prompt_spec_paths_with_auto_name(self, dir_manager):
        """Test that file paths work correctly with auto-generated names."""
        manager = PromptSpecManager(dir_manager)

        spec = manager.create_prompt_spec(prompt_text="Transform into cyberpunk style")

        # Verify video path uses the auto-generated name
        assert spec.name in spec.input_video_path

        # Verify control inputs use the auto-generated name
        for modality, path in spec.control_inputs.items():
            assert spec.name in path

    def test_upsampled_prompt_with_auto_name(self, dir_manager):
        """Test creating an upsampled prompt with auto-generated name."""
        manager = PromptSpecManager(dir_manager)

        original_prompt = "A simple scene"
        upsampled_prompt = (
            "A highly detailed photorealistic scene with dramatic lighting and intricate textures"
        )

        spec = manager.create_prompt_spec(
            prompt_text=upsampled_prompt, is_upsampled=True, parent_prompt_text=original_prompt
        )

        # Verify name was generated from upsampled prompt
        assert spec.name is not None
        assert any(
            word in spec.name.lower()
            for word in ["detailed", "photorealistic", "dramatic", "lighting"]
        )

        # Verify upsampling fields
        assert spec.is_upsampled is True
        assert spec.parent_prompt_text == original_prompt


class TestPromptManagerIntegration:
    """Test PromptManager with smart naming integration."""

    @pytest.fixture
    def temp_config(self, tmp_path):
        """Create a temporary config file."""
        config_content = """
[paths]
prompts_dir = "./prompts"
runs_dir = "./runs"
videos_dir = "./videos"
"""
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        return config_file

    def test_prompt_manager_auto_naming(self, temp_config, tmp_path):
        """Test PromptManager with auto-naming."""
        # Create necessary directories
        (temp_config.parent / "prompts").mkdir(exist_ok=True)
        (temp_config.parent / "runs").mkdir(exist_ok=True)

        with patch("cosmos_workflow.config.config_manager.ConfigManager") as mock_config:
            mock_config.return_value.get_local_config.return_value.prompts_dir = str(
                temp_config.parent / "prompts"
            )
            mock_config.return_value.get_local_config.return_value.runs_dir = str(
                temp_config.parent / "runs"
            )

            manager = PromptManager()

            # Create prompt without name
            spec = manager.create_prompt_spec(
                prompt_text="An underwater scene with coral reefs and tropical fish"
            )

            # Verify auto-generated name
            assert spec.name is not None
            assert any(
                word in spec.name.lower()
                for word in ["underwater", "coral", "tropical", "fish", "scene"]
            )


class TestCLISmartNaming:
    """Test CLI integration with smart naming."""

    def test_create_spec_command_without_name(self):
        """Test create-spec CLI command without name argument."""
        from cosmos_workflow.cli import create_prompt_spec

        # Mock the file system operations
        with patch("cosmos_workflow.config.config_manager.ConfigManager"), patch(
            "cosmos_workflow.prompts.schemas.DirectoryManager"
        ) as mock_dir_manager, patch("cosmos_workflow.prompts.schemas.PromptSpec.save"):
            # Mock directory manager methods
            mock_dir_instance = Mock()
            mock_dir_instance.get_prompt_file_path.return_value = Path("test.json")
            mock_dir_manager.return_value = mock_dir_instance

            # Call without name - should auto-generate
            create_prompt_spec(
                name=None,  # No name provided
                prompt_text="Create a magical forest scene",
                negative_prompt="boring",
                input_video_path=None,
                control_inputs=None,
                is_upsampled=False,
                parent_prompt_text=None,
                verbose=False,
            )

            # The function should complete without errors
            # Name should be auto-generated from prompt text
            # We can't easily test the exact name, but the function should not fail

    def test_create_spec_command_with_name(self):
        """Test create-spec CLI command with explicit name."""
        from cosmos_workflow.cli import create_prompt_spec

        # Mock the file system operations
        with patch("cosmos_workflow.config.config_manager.ConfigManager"), patch(
            "cosmos_workflow.prompts.schemas.DirectoryManager"
        ) as mock_dir_manager, patch("cosmos_workflow.prompts.schemas.PromptSpec.save"):
            # Mock directory manager methods
            mock_dir_instance = Mock()
            mock_dir_instance.get_prompt_file_path.return_value = Path("test.json")
            mock_dir_manager.return_value = mock_dir_instance

            # Call with explicit name
            create_prompt_spec(
                name="custom_name",
                prompt_text="A test prompt",
                negative_prompt="bad",
                input_video_path=None,
                control_inputs=None,
                is_upsampled=False,
                parent_prompt_text=None,
                verbose=False,
            )

            # The function should use the provided name
            # We can verify by checking the get_prompt_file_path was called with custom_name
            mock_dir_instance.get_prompt_file_path.assert_called()
            call_args = mock_dir_instance.get_prompt_file_path.call_args
            assert call_args[0][0] == "custom_name"  # First positional arg should be the name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
