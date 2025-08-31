#!/usr/bin/env python3
"""PromptSpec management system for Cosmos-Transfer1 workflow.
Handles PromptSpec creation, validation, and file operations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from cosmos_workflow.utils.smart_naming import generate_smart_name

from .schemas import DirectoryManager, PromptSpec


class PromptSpecManager:
    """Manages PromptSpec creation, validation, and file operations."""

    def __init__(self, dir_manager: DirectoryManager):
        """Initialize PromptSpec manager with directory manager."""
        self.dir_manager = dir_manager

    def create_prompt_spec(
        self,
        name: str | None = None,
        prompt_text: str = "",
        negative_prompt: str = "bad quality, blurry, low resolution, cartoonish",
        input_video_path: str | None = None,
        control_inputs: dict[str, str] | None = None,
        is_upsampled: bool = False,
        parent_prompt_text: str | None = None,
    ) -> PromptSpec:
        """Create a new PromptSpec using the new schema system.

        Args:
            name: Name for the prompt (auto-generated from prompt_text if not provided)
            prompt_text: The text prompt for generation
            negative_prompt: Negative prompt for improved quality
            input_video_path: Optional custom video path override
            control_inputs: Optional control input file paths
            is_upsampled: Whether this is an upsampled prompt
            parent_prompt_text: Original prompt text if upsampled

        Returns:
            PromptSpec object
        """
        # Auto-generate name from prompt text if not provided
        if name is None:
            name = generate_smart_name(prompt_text, max_length=30)

        # Build video path
        video_path = input_video_path or f"inputs/videos/{name}/color.mp4"

        # Default control inputs
        if control_inputs is None:
            control_inputs = {
                "depth": f"inputs/videos/{name}/depth.mp4",
                "seg": f"inputs/videos/{name}/segmentation.mp4",
            }

        # Generate unique ID
        from .schemas import SchemaUtils

        prompt_id = SchemaUtils.generate_prompt_id(prompt_text, video_path, control_inputs)

        # Create PromptSpec
        timestamp = datetime.now().isoformat() + "Z"
        prompt_spec = PromptSpec(
            id=prompt_id,
            name=name,
            prompt=prompt_text,
            negative_prompt=negative_prompt,
            input_video_path=video_path,
            control_inputs=control_inputs,
            timestamp=timestamp,
            is_upsampled=is_upsampled,
            parent_prompt_text=parent_prompt_text,
        )

        # Save to date-based directory
        file_path = self.dir_manager.get_prompt_file_path(
            prompt_spec.name, timestamp, prompt_spec.id
        )
        prompt_spec.save(file_path)

        print(f"[CREATED] PromptSpec: {prompt_id}")
        print(f"   Saved to: {file_path}")
        print(f"   Name: {name}")
        print(f"   Video: {video_path}")
        print(f"   Control Inputs: {list(control_inputs.keys())}")

        return prompt_spec

    def list_prompts(self, prompts_dir: Path, pattern: str | None = None) -> list[Path]:
        """List available PromptSpec files.

        Args:
            prompts_dir: Directory containing prompts
            pattern: Optional pattern to filter prompts

        Returns:
            List of PromptSpec file paths
        """
        prompt_files = []

        # Search in date-based directories
        for date_dir in self.dir_manager.list_date_directories(prompts_dir):
            date_path = prompts_dir / date_dir
            for prompt_file in date_path.glob("*.json"):
                if pattern is None or pattern.lower() in prompt_file.stem.lower():
                    prompt_files.append(prompt_file)

        return sorted(prompt_files, key=lambda x: x.stat().st_mtime, reverse=True)

    def get_prompt_info(self, prompt_path: str | Path) -> dict[str, Any]:
        """Get information about a PromptSpec file.

        Args:
            prompt_path: Path to PromptSpec JSON file

        Returns:
            Dictionary with prompt information
        """
        prompt_path = Path(prompt_path)

        if not prompt_path.exists():
            raise FileNotFoundError(f"PromptSpec file not found: {prompt_path}")

        with open(prompt_path) as f:
            prompt_data = json.load(f)

        return {
            "filename": prompt_path.name,
            "id": prompt_data.get("id", ""),
            "name": prompt_data.get("name", ""),
            "prompt_text": prompt_data.get("prompt", ""),
            "negative_prompt": prompt_data.get("negative_prompt", ""),
            "input_video_path": prompt_data.get("input_video_path", ""),
            "control_inputs": prompt_data.get("control_inputs", {}),
            "timestamp": prompt_data.get("timestamp", ""),
            "is_upsampled": prompt_data.get("is_upsampled", False),
            "parent_prompt_text": prompt_data.get("parent_prompt_text", ""),
            "file_path": str(prompt_path),
            "file_size": prompt_path.stat().st_size,
            "created_time": datetime.fromtimestamp(prompt_path.stat().st_ctime),
        }
