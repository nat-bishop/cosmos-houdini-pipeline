#!/usr/bin/env python3
"""
Prompt management system for Cosmos-Transfer1 workflow.
Orchestrates PromptSpec and RunSpec operations using specialized managers.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..config.config_manager import ConfigManager
from .prompt_spec_manager import PromptSpecManager
from .run_spec_manager import RunSpecManager
from .schema_validator import SchemaValidator
from .schemas import (
    BlurStrength,
    CannyThreshold,
    DirectoryManager,
    ExecutionStatus,
    PromptSpec,
    RunSpec,
)


class PromptManager:
    """Orchestrates prompt and run management using specialized managers."""

    def __init__(self, config_file: str = "cosmos_workflow/config/config.toml"):
        """Initialize prompt manager with configuration."""
        self.config_manager = ConfigManager(config_file)
        self.local_config = self.config_manager.get_local_config()

        # Ensure directories exist
        self.prompts_dir = self.local_config.prompts_dir
        self.runs_dir = self.local_config.runs_dir
        self.outputs_dir = self.local_config.outputs_dir
        self.videos_dir = self.local_config.videos_dir

        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.runs_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        # Initialize specialized managers
        self.dir_manager = DirectoryManager(self.prompts_dir, self.runs_dir)
        self.dir_manager.ensure_directories_exist()

        self.prompt_spec_manager = PromptSpecManager(self.dir_manager)
        self.run_spec_manager = RunSpecManager(self.dir_manager)
        self.validator = SchemaValidator()

    def create_prompt_spec(
        self,
        name: Optional[str] = None,
        prompt_text: str = "",
        negative_prompt: str = "bad quality, blurry, low resolution, cartoonish",
        input_video_path: Optional[str] = None,
        control_inputs: Optional[Dict[str, str]] = None,
        is_upsampled: bool = False,
        parent_prompt_text: Optional[str] = None,
    ) -> PromptSpec:
        """Create a new PromptSpec using the PromptSpecManager."""
        return self.prompt_spec_manager.create_prompt_spec(
            name=name,
            prompt_text=prompt_text,
            negative_prompt=negative_prompt,
            input_video_path=input_video_path,
            control_inputs=control_inputs,
            is_upsampled=is_upsampled,
            parent_prompt_text=parent_prompt_text,
        )

    def create_run_spec(
        self,
        prompt_spec: PromptSpec,
        control_weights: Optional[Dict[str, float]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        custom_output_path: Optional[str] = None,
    ) -> RunSpec:
        """Create a new RunSpec using the RunSpecManager."""
        return self.run_spec_manager.create_run_spec(
            prompt_id=prompt_spec.id,
            name=prompt_spec.name,
            control_weights=control_weights,
            parameters=parameters,
            output_path=custom_output_path,
        )

    def validate_prompt_spec(self, prompt_path: Union[str, Path]) -> bool:
        """Validate a PromptSpec using the SchemaValidator."""
        return self.validator.validate_prompt_spec(prompt_path)

    def validate_run_spec(self, run_path: Union[str, Path]) -> bool:
        """Validate a RunSpec using the SchemaValidator."""
        return self.validator.validate_run_spec(run_path)

    def list_prompts(self, pattern: Optional[str] = None) -> List[Path]:
        """List available PromptSpec files using the PromptSpecManager."""
        return self.prompt_spec_manager.list_prompts(self.prompts_dir, pattern)

    def list_runs(self, pattern: Optional[str] = None) -> List[Path]:
        """List available RunSpec files using the RunSpecManager."""
        return self.run_spec_manager.list_runs(self.runs_dir, pattern)

    def get_prompt_info(self, prompt_path: Union[str, Path]) -> Dict[str, Any]:
        """Get information about a PromptSpec using the PromptSpecManager."""
        return self.prompt_spec_manager.get_prompt_info(prompt_path)

    def get_run_info(self, run_path: Union[str, Path]) -> Dict[str, Any]:
        """Get information about a RunSpec using the RunSpecManager."""
        return self.run_spec_manager.get_run_info(run_path)


def main():
    """Command-line interface for prompt management."""
    parser = argparse.ArgumentParser(
        description="Manage Cosmos-Transfer1 prompts using new schema system"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create prompt-spec command
    create_spec_parser = subparsers.add_parser("create-spec", help="Create a new PromptSpec")
    create_spec_parser.add_argument("name", help="Name for the prompt")
    create_spec_parser.add_argument("prompt_text", help="The text prompt for generation")
    create_spec_parser.add_argument(
        "--negative-prompt",
        default="bad quality, blurry, low resolution, cartoonish",
        help="Negative prompt for improved quality",
    )
    create_spec_parser.add_argument("--video-path", help="Custom video path override")
    create_spec_parser.add_argument(
        "--control-inputs",
        nargs="*",
        metavar=("MODALITY", "PATH"),
        help="Control input file paths (e.g., depth inputs/videos/name/depth.mp4)",
    )
    create_spec_parser.add_argument(
        "--upsampled", action="store_true", help="Mark as upsampled prompt"
    )
    create_spec_parser.add_argument("--parent-prompt", help="Original prompt text if upsampled")

    # Create run-spec command
    create_run_parser = subparsers.add_parser("create-run", help="Create a new RunSpec")
    create_run_parser.add_argument("prompt_spec_path", help="Path to PromptSpec JSON file")
    create_run_parser.add_argument(
        "--weights",
        nargs=4,
        type=float,
        metavar=("VIS", "EDGE", "DEPTH", "SEG"),
        help="Control weights (default: 0.25 each)",
    )
    create_run_parser.add_argument(
        "--num-steps", type=int, default=35, help="Number of inference steps"
    )
    create_run_parser.add_argument("--guidance", type=float, default=7.0, help="Guidance scale")
    create_run_parser.add_argument("--sigma_max", type=float, default=70.0, help="Sigma max value")
    create_run_parser.add_argument(
        "--blur-strength",
        choices=["very_low", "low", "medium", "high", "very_high"],
        default="medium",
        help="Blur strength for vis controlnet",
    )
    create_run_parser.add_argument(
        "--canny-threshold",
        choices=["very_low", "low", "medium", "high", "very_high"],
        default="medium",
        help="Canny threshold for edge controlnet",
    )
    create_run_parser.add_argument("--fps", type=int, default=24, help="Output FPS")
    create_run_parser.add_argument("--seed", type=int, default=1, help="Random seed")
    create_run_parser.add_argument("--output-path", help="Custom output path")

    # Validate prompt command
    validate_parser = subparsers.add_parser("validate", help="Validate a PromptSpec JSON file")
    validate_parser.add_argument("prompt_file", help="Path to PromptSpec JSON file")

    # List prompts command
    list_parser = subparsers.add_parser("list", help="List available PromptSpec files")
    list_parser.add_argument("--pattern", help="Filter prompts by pattern")

    # Info command
    info_parser = subparsers.add_parser("info", help="Get information about a PromptSpec")
    info_parser.add_argument("prompt_file", help="Path to PromptSpec JSON file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        prompt_manager = PromptManager()

        if args.command == "create-spec":
            # Parse control inputs
            control_inputs = {}
            if args.control_inputs:
                for i in range(0, len(args.control_inputs), 2):
                    if i + 1 < len(args.control_inputs):
                        modality = args.control_inputs[i]
                        path = args.control_inputs[i + 1]
                        control_inputs[modality] = path

            prompt_spec = prompt_manager.create_prompt_spec(
                name=args.name,
                prompt_text=args.prompt_text,
                negative_prompt=args.negative_prompt,
                input_video_path=args.video_path,
                control_inputs=control_inputs if control_inputs else None,
                is_upsampled=args.upsampled,
                parent_prompt_text=args.parent_prompt,
            )

            print(f"\n💡 To create a RunSpec for this prompt:")
            print(
                f"   python -m cosmos_workflow.prompts.prompt_manager create-run {prompt_spec.id}.json"
            )

        elif args.command == "create-run":
            # Load the PromptSpec
            prompt_spec_path = Path(args.prompt_spec_path)
            if not prompt_spec_path.exists():
                print(f"[ERROR] PromptSpec file not found: {prompt_spec_path}")
                return

            prompt_spec = PromptSpec.load(prompt_spec_path)

            # Build control weights
            control_weights = None
            if args.weights:
                control_weights = {
                    "vis": args.weights[0],
                    "edge": args.weights[1],
                    "depth": args.weights[2],
                    "seg": args.weights[3],
                }

            # Build parameters
            parameters = {
                "num_steps": args.num_steps,
                "guidance": args.guidance,
                "sigma_max": args.sigma_max,
                "blur_strength": args.blur_strength,
                "canny_threshold": args.canny_threshold,
                "fps": args.fps,
                "seed": args.seed,
            }

            run_spec = prompt_manager.create_run_spec(
                prompt_spec=prompt_spec,
                control_weights=control_weights,
                parameters=parameters,
                custom_output_path=args.output_path,
            )

            print(f"\n🚀 To run this specification:")
            print(f"   python -m cosmos_workflow.main run {run_spec.id}.json")

        elif args.command == "validate":
            prompt_manager.validate_prompt_spec(args.prompt_file)

        elif args.command == "list":
            prompts = prompt_manager.list_prompts(args.pattern)
            if prompts:
                print("Available PromptSpec files:")
                for prompt in prompts:
                    print(f"  {prompt}")
            else:
                print("No PromptSpec files found.")

        elif args.command == "info":
            info = prompt_manager.get_prompt_info(args.prompt_file)
            print(f"PromptSpec Information:")
            print(f"  Filename: {info['filename']}")
            print(f"  ID: {info['id']}")
            print(f"  Name: {info['name']}")
            print(
                f"  Prompt Text: {info['prompt_text'][:100]}{'...' if len(info['prompt_text']) > 100 else ''}"
            )
            print(
                f"  Negative Prompt: {info['negative_prompt'][:100]}{'...' if len(info['negative_prompt']) > 100 else ''}"
            )
            print(f"  Video Path: {info['input_video_path']}")
            print(f"  Control Inputs: {list(info['control_inputs'].keys())}")
            print(f"  Timestamp: {info['timestamp']}")
            print(f"  Is Upsampled: {info['is_upsampled']}")
            if info["parent_prompt_text"]:
                print(
                    f"  Parent Prompt: {info['parent_prompt_text'][:100]}{'...' if len(info['parent_prompt_text']) > 100 else ''}"
                )
            print(f"  File Size: {info['file_size']} bytes")
            print(f"  Created: {info['created_time']}")

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
