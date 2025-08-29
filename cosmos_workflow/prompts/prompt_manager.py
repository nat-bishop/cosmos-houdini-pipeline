#!/usr/bin/env python3
"""
Prompt management system for Cosmos-Transfer1 workflow.
Handles prompt creation, validation, and batch operations.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
import argparse

from ..config.config_manager import ConfigManager


@dataclass
class PromptSchema:
    """Base prompt schema with common fields."""
    prompt: str
    input_video_path: str
    vis: Dict[str, Any]
    edge: Dict[str, Any]
    depth: Dict[str, Any]
    seg: Dict[str, Any]


class PromptManager:
    """Manages prompt creation, validation, and batch operations."""
    
    def __init__(self, config_file: str = "cosmos_workflow/config/config.toml"):
        """Initialize prompt manager with configuration."""
        self.config_manager = ConfigManager(config_file)
        self.local_config = self.config_manager.get_local_config()
        
        # Ensure directories exist
        self.prompts_dir = self.local_config.prompts_dir
        self.outputs_dir = self.local_config.outputs_dir
        self.videos_dir = self.local_config.videos_dir
        
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
    
    def create_prompt(self, base_name: str, prompt_text: str, 
                     control_weights: Optional[Dict[str, float]] = None,
                     custom_video_path: Optional[str] = None) -> Path:
        """
        Create a new prompt JSON file.
        
        Args:
            base_name: Base name for the prompt (e.g., 'building_flythrough_v1')
            prompt_text: The text prompt for generation
            control_weights: Optional custom control weights for modalities
            custom_video_path: Optional custom video path override
            
        Returns:
            Path to the created prompt JSON file
        """
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prompt_name = f"{base_name}_{timestamp}"
        
        # Create output directory
        output_dir = self.outputs_dir / prompt_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Default control weights
        default_weights = {
            "vis": 0.25,
            "edge": 0.25,
            "depth": 0.25,
            "seg": 0.25
        }
        
        # Use custom weights if provided
        if control_weights:
            default_weights.update(control_weights)
        
        # Build video path
        if custom_video_path:
            video_path = custom_video_path
        else:
            video_path = f"inputs/videos/{base_name}/color.mp4"
        
        # Create prompt schema
        prompt_data = {
            "prompt": prompt_text,
            "input_video_path": video_path,
            "vis": {"control_weight": default_weights["vis"]},
            "edge": {"control_weight": default_weights["edge"]},
            "depth": {
                "control_weight": default_weights["depth"],
                "input_control": f"inputs/videos/{base_name}/depth.mp4"
            },
            "seg": {
                "control_weight": default_weights["seg"],
                "input_control": f"inputs/videos/{base_name}/segmentation.mp4"
            }
        }
        
        # Write prompt file
        prompt_file = self.prompts_dir / f"{prompt_name}.json"
        with open(prompt_file, 'w') as f:
            json.dump(prompt_data, f, indent=2)
        
        print(f"✅ Created prompt: {prompt_file}")
        print(f"   Outputs will be saved under: {output_dir}")
        print()
        print("Next:")
        print("  1) If you don't have a modality (edge/depth/seg), delete its 'input_control' line or the whole block.")
        print("  2) Adjust control_weight values as needed.")
        print("  3) Run full cycle:")
        print(f"       python -m cosmos_workflow.main run {prompt_file}")
        
        return prompt_file
    
    def duplicate_prompt(self, existing_prompt_path: Union[str, Path]) -> Path:
        """
        Duplicate an existing prompt with a new timestamp.
        
        Args:
            existing_prompt_path: Path to existing prompt JSON file
            
        Returns:
            Path to the duplicated prompt JSON file
        """
        existing_prompt_path = Path(existing_prompt_path)
        
        if not existing_prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {existing_prompt_path}")
        
        # Extract the base name from the existing prompt filename
        # Handle timestamps with format: base_name_YYYYMMDD_HHMMSS
        filename = existing_prompt_path.stem
        if '_' in filename:
            # Split by underscore and check if the last two parts form a valid timestamp
            parts = filename.split('_')
            if len(parts) >= 3:
                # Check if last two parts look like a timestamp (YYYYMMDD_HHMMSS)
                potential_date = parts[-2]
                potential_time = parts[-1]
                if (len(potential_date) == 8 and potential_date.isdigit() and 
                    len(potential_time) == 6 and potential_time.isdigit()):
                    # Last two parts are timestamp, everything before is base name
                    base_name = '_'.join(parts[:-2])
                else:
                    # Just use the last underscore split
                    base_name = filename.rsplit('_', 1)[0]
            else:
                # Simple case: just one underscore
                base_name = parts[0]
        else:
            base_name = filename
        
        # Generate new timestamp with microsecond precision to ensure uniqueness
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        prompt_name = f"{base_name}_{timestamp}"
        
        # Create output directory
        output_dir = self.outputs_dir / prompt_name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy existing prompt content
        prompt_file = self.prompts_dir / f"{prompt_name}.json"
        with open(existing_prompt_path, 'r') as src, open(prompt_file, 'w') as dst:
            dst.write(src.read())
        
        print(f"✅ Duplicated prompt: {prompt_file}")
        print(f"   Outputs will be saved under: {output_dir}")
        print()
        print("Next:")
        print("  1) Edit the prompt text if needed: {prompt_file}")
        print("  2) Run full cycle:")
        print(f"       python -m cosmos_workflow.main run {prompt_file}")
        
        return prompt_file
    
    def validate_prompt(self, prompt_path: Union[str, Path]) -> bool:
        """
        Validate a prompt JSON file.
        
        Args:
            prompt_path: Path to prompt JSON file
            
        Returns:
            True if valid, False otherwise
        """
        prompt_path = Path(prompt_path)
        
        try:
            with open(prompt_path, 'r') as f:
                prompt_data = json.load(f)
            
            # Check required fields
            required_fields = ["prompt", "input_video_path", "vis", "edge", "depth", "seg"]
            for field in required_fields:
                if field not in prompt_data:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            # Check control weights
            for modality in ["vis", "edge", "depth", "seg"]:
                if "control_weight" not in prompt_data[modality]:
                    print(f"❌ Missing control_weight in {modality}")
                    return False
                
                weight = prompt_data[modality]["control_weight"]
                if not isinstance(weight, (int, float)) or weight < 0 or weight > 1:
                    print(f"❌ Invalid control_weight in {modality}: {weight}")
                    return False
            
            print(f"✅ Prompt validation passed: {prompt_path}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            return False
        except Exception as e:
            print(f"❌ Validation error: {e}")
            return False
    
    def list_prompts(self, pattern: Optional[str] = None) -> List[Path]:
        """
        List available prompt files.
        
        Args:
            pattern: Optional pattern to filter prompts
            
        Returns:
            List of prompt file paths
        """
        prompt_files = list(self.prompts_dir.glob("*.json"))
        
        if pattern:
            prompt_files = [p for p in prompt_files if pattern.lower() in p.stem.lower()]
        
        return sorted(prompt_files)
    
    def get_prompt_info(self, prompt_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Get information about a prompt file.
        
        Args:
            prompt_path: Path to prompt JSON file
            
        Returns:
            Dictionary with prompt information
        """
        prompt_path = Path(prompt_path)
        
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
        with open(prompt_path, 'r') as f:
            prompt_data = json.load(f)
        
        # Extract base name and timestamp
        filename = prompt_path.stem
        if '_' in filename:
            # Handle timestamps with format: base_name_YYYYMMDD_HHMMSS
            # Split by underscore and check if the last two parts form a valid timestamp
            parts = filename.split('_')
            if len(parts) >= 3:
                # Check if last two parts look like a timestamp (YYYYMMDD_HHMMSS)
                potential_date = parts[-2]
                potential_time = parts[-1]
                if (len(potential_date) == 8 and potential_date.isdigit() and 
                    len(potential_time) == 6 and potential_time.isdigit()):
                    # Last two parts are timestamp, everything before is base name
                    base_name = '_'.join(parts[:-2])
                    timestamp = f"{potential_date}_{potential_time}"
                else:
                    # Just use the last underscore split
                    base_name = filename.rsplit('_', 1)[0]
                    timestamp = filename.rsplit('_', 1)[1]
            else:
                # Simple case: just one underscore
                base_name = parts[0]
                timestamp = parts[1]
        else:
            base_name = filename
            timestamp = "unknown"
        
        return {
            "filename": filename,
            "base_name": base_name,
            "timestamp": timestamp,
            "prompt_text": prompt_data.get("prompt", ""),
            "input_video_path": prompt_data.get("input_video_path", ""),
            "control_weights": {
                modality: data.get("control_weight", 0)
                for modality, data in prompt_data.items()
                if isinstance(data, dict) and "control_weight" in data
            },
            "file_path": str(prompt_path),
            "file_size": prompt_path.stat().st_size,
            "created_time": datetime.fromtimestamp(prompt_path.stat().st_ctime)
        }


def main():
    """Command-line interface for prompt management."""
    parser = argparse.ArgumentParser(description="Manage Cosmos-Transfer1 prompts")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create prompt command
    create_parser = subparsers.add_parser("create", help="Create a new prompt")
    create_parser.add_argument("base_name", help="Base name for the prompt")
    create_parser.add_argument("prompt_text", help="The text prompt for generation")
    create_parser.add_argument("--weights", nargs=4, type=float, metavar=("VIS", "EDGE", "DEPTH", "SEG"),
                              help="Control weights for vis, edge, depth, seg (default: 0.25 each)")
    create_parser.add_argument("--video-path", help="Custom video path override")
    
    # Duplicate prompt command
    duplicate_parser = subparsers.add_parser("duplicate", help="Duplicate an existing prompt")
    duplicate_parser.add_argument("prompt_file", help="Path to existing prompt JSON file")
    
    # Validate prompt command
    validate_parser = subparsers.add_parser("validate", help="Validate a prompt JSON file")
    validate_parser.add_argument("prompt_file", help="Path to prompt JSON file")
    
    # List prompts command
    list_parser = subparsers.add_parser("list", help="List available prompts")
    list_parser.add_argument("--pattern", help="Filter prompts by pattern")
    
    # Info command
    info_parser = subparsers.add_parser("info", help="Get information about a prompt")
    info_parser.add_argument("prompt_file", help="Path to prompt JSON file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        prompt_manager = PromptManager()
        
        if args.command == "create":
            control_weights = None
            if args.weights:
                control_weights = {
                    "vis": args.weights[0],
                    "edge": args.weights[1],
                    "depth": args.weights[2],
                    "seg": args.weights[3]
                }
            
            prompt_manager.create_prompt(
                args.base_name,
                args.prompt_text,
                control_weights,
                args.video_path
            )
            
        elif args.command == "duplicate":
            prompt_manager.duplicate_prompt(args.prompt_file)
            
        elif args.command == "validate":
            prompt_manager.validate_prompt(args.prompt_file)
            
        elif args.command == "list":
            prompts = prompt_manager.list_prompts(args.pattern)
            if prompts:
                print("Available prompts:")
                for prompt in prompts:
                    print(f"  {prompt.name}")
            else:
                print("No prompts found.")
                
        elif args.command == "info":
            info = prompt_manager.get_prompt_info(args.prompt_file)
            print(f"Prompt Information:")
            print(f"  Filename: {info['filename']}")
            print(f"  Base Name: {info['base_name']}")
            print(f"  Timestamp: {info['timestamp']}")
            print(f"  Prompt Text: {info['prompt_text'][:100]}{'...' if len(info['prompt_text']) > 100 else ''}")
            print(f"  Video Path: {info['input_video_path']}")
            print(f"  Control Weights: {info['control_weights']}")
            print(f"  File Size: {info['file_size']} bytes")
            print(f"  Created: {info['created_time']}")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
