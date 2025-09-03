"""Compatibility layer for migrating from PromptManager to PromptSpecManager.

DEPRECATED: This module provides backward compatibility during the migration
from PromptManager to PromptSpecManager. New code should use PromptSpecManager directly.
"""

import warnings
from pathlib import Path
from typing import Any

from cosmos_workflow.config.config_manager import ConfigManager

from .prompt_spec_manager import PromptSpecManager
from .schemas import DirectoryManager, PromptSpec


class PromptManager:
    """DEPRECATED: Use PromptSpecManager directly.

    This is a compatibility shim for tests during migration.
    Will be removed in a future version.
    """

    def __init__(self, config_file: str = "cosmos_workflow/config/config.toml"):
        """Initialize with backward compatibility.

        Args:
            config_file: Path to configuration file
        """
        warnings.warn(
            "PromptManager is deprecated. Use PromptSpecManager directly.",
            DeprecationWarning,
            stacklevel=2,
        )

        # Setup config and directories
        self.config_manager = ConfigManager(config_file)
        self.config_file = config_file
        local_config = self.config_manager.get_local_config()

        # Create directory manager
        dir_manager = DirectoryManager(local_config.prompts_dir, local_config.runs_dir)
        dir_manager.ensure_directories_exist()

        # Create the actual spec manager
        self.prompt_spec_manager = PromptSpecManager(dir_manager)

        # Store commonly accessed paths for compatibility
        self.prompts_dir = Path(local_config.prompts_dir)
        self.runs_dir = Path(local_config.runs_dir)

    def create_prompt_spec(
        self,
        name: str | None = None,
        prompt_text: str = "",
        negative_prompt: str | None = None,
        input_video_path: str | None = None,
        control_inputs: dict[str, str] | None = None,
        is_upsampled: bool = False,
        parent_prompt_text: str | None = None,
    ) -> PromptSpec:
        """Create a PromptSpec (delegates to PromptSpecManager).

        Args:
            name: Optional name for the prompt
            prompt_text: The prompt text
            negative_prompt: Negative prompt text
            input_video_path: Path to input video
            control_inputs: Control input paths
            is_upsampled: Whether this is an upsampled prompt
            parent_prompt_text: Original prompt if upsampled

        Returns:
            Created PromptSpec
        """
        # Use default negative prompt if not provided
        if negative_prompt is None:
            negative_prompt = "The video captures a game playing, with bad crappy graphics and cartoonish frames. It represents a recording of old outdated games. The lighting looks very fake. The textures are very raw and basic. The geometries are very primitive. The images are very pixelated and of poor CG quality. There are many subtitles in the footage. Overall, the video is unrealistic at all."

        return self.prompt_spec_manager.create_prompt_spec(
            name=name,
            prompt_text=prompt_text,
            negative_prompt=negative_prompt,
            input_video_path=input_video_path,
            control_inputs=control_inputs,
            is_upsampled=is_upsampled,
            parent_prompt_text=parent_prompt_text,
        )

    def list_prompts(self, pattern: str | None = None) -> list[Path]:
        """List available PromptSpec files.

        Args:
            pattern: Optional glob pattern to filter files

        Returns:
            List of PromptSpec file paths
        """
        return self.prompt_spec_manager.list_prompts(self.prompts_dir, pattern)

    def load_prompt_spec(self, file_path: Path | str) -> PromptSpec:
        """Load a PromptSpec from file.

        Args:
            file_path: Path to the JSON file

        Returns:
            Loaded PromptSpec object
        """
        return self.prompt_spec_manager.load_prompt_spec(file_path)

    def get_prompts_dir(self) -> Path:
        """Get the prompts directory path.

        Returns:
            Path to prompts directory
        """
        return self.prompts_dir

    def get_runs_dir(self) -> Path:
        """Get the runs directory path.

        Returns:
            Path to runs directory
        """
        return self.runs_dir
