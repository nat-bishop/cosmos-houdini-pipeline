"""Simple utilities for converting database format to NVIDIA Cosmos format.

This module handles the conversion from our database structure to the specific
JSON format required by NVIDIA Cosmos Transfer scripts.
"""

import json
from pathlib import Path
from typing import Any


def to_cosmos_inference_json(
    prompt_dict: dict[str, Any], run_dict: dict[str, Any]
) -> dict[str, Any]:
    """Convert database prompt and run dicts to NVIDIA Cosmos inference format.

    Args:
        prompt_dict: Prompt data from database
        run_dict: Run data from database

    Returns:
        Dictionary in NVIDIA Cosmos format for inference.sh
    """
    # Extract execution config
    execution_config = run_dict.get("execution_config", {})
    weights = execution_config.get("weights", {})

    # Get run_id for path construction
    run_id = run_dict.get("id", "")

    # Extract inputs
    inputs = prompt_dict.get("inputs", {})

    # Convert video paths to match actual upload location with run_id
    def convert_video_path(path: str) -> str:
        """Convert video path to match how files are uploaded in run-specific directories.

        Files are uploaded to runs/{run_id}/inputs/videos/, so we need to
        strip any local path structure and use the run-specific path.

        Example:
            inputs/videos/city_scene_20250830_203504/color.mp4 -> runs/{run_id}/inputs/videos/color.mp4
        """
        if not path:
            return path

        # Convert Windows backslashes to forward slashes
        path = path.replace("\\", "/")

        # Convert to Path to extract filename
        path_obj = Path(path)
        filename = path_obj.name

        # Return run-specific path
        return f"runs/{run_id}/inputs/videos/{filename}"

    # Extract negative prompt from parameters if not at top level
    negative_prompt = prompt_dict.get("negative_prompt", "")
    if not negative_prompt and "parameters" in prompt_dict:
        negative_prompt = prompt_dict.get("parameters", {}).get("negative_prompt", "")

    # Use a default negative prompt if still empty
    if not negative_prompt:
        negative_prompt = "low quality, blurry, distorted"

    # Build Cosmos format with correct NVIDIA structure
    cosmos_json = {
        "prompt": prompt_dict.get("prompt_text", ""),
        "negative_prompt": negative_prompt,
        "input_video_path": convert_video_path(inputs.get("video", "")),
        # Additional parameters
        "num_steps": execution_config.get("num_steps", 35),
        "guidance": execution_config.get("guidance", 7.0),
        "sigma_max": execution_config.get("sigma_max", 70.0),
        "seed": execution_config.get("seed", 42),
        "fps": execution_config.get("fps", 8),
    }

    # TODO: Upscaling should NOT be included in inference JSON
    # It needs to be a separate GPU run with its own controlnet spec
    # containing only input_video_path and upscale control weight.
    # See ROADMAP.md for implementation details.

    # Add control configurations only if weight > 0
    # This matches NVIDIA's approach where controls are optional
    vis_weight = weights.get("vis", 0.25)
    if vis_weight > 0:
        cosmos_json["vis"] = {"control_weight": vis_weight}

    edge_weight = weights.get("edge", 0.25)
    if edge_weight > 0:
        cosmos_json["edge"] = {"control_weight": edge_weight}

    depth_weight = weights.get("depth", 0.25)
    if depth_weight > 0:
        cosmos_json["depth"] = {"control_weight": depth_weight}
        # Only add input_control if video path exists
        depth_path = inputs.get("depth", "")
        if depth_path:
            cosmos_json["depth"]["input_control"] = convert_video_path(depth_path)

    seg_weight = weights.get("seg", 0.25)
    if seg_weight > 0:
        cosmos_json["seg"] = {"control_weight": seg_weight}
        # Only add input_control if video path exists
        seg_path = inputs.get("seg", "")
        if seg_path:
            cosmos_json["seg"]["input_control"] = convert_video_path(seg_path)

    return cosmos_json


def to_cosmos_upscale_json(
    input_video_path: str,
    control_weight: float = 0.5,
    prompt: str | None = None,
) -> dict[str, Any]:
    """Convert upscaling parameters to Cosmos format JSON specification.

    Phase 1 Upscaling Refactor: Enhanced to support video-agnostic upscaling
    with conditional prompt inclusion.

    Creates a spec for 4K upscaling that includes:
    - input_video_path: Path to the video to upscale (from run or arbitrary file)
    - upscale.control_weight: Weight for upscaling control strength
    - prompt: Optional text prompt to guide upscaling (ONLY included when provided)

    This follows the design principle of including fields only when explicitly
    provided, keeping the JSON clean and focused.

    Args:
        input_video_path: Path to input video (from inference run output or any video file)
        control_weight: Control weight for upscaling strength (0.0-1.0, default: 0.5)
        prompt: Optional prompt to guide the upscaling process.
               When None or empty string, field is omitted from JSON.

    Returns:
        Dictionary in Cosmos format for upscaling operations.
        Prompt field only present when explicitly provided.
    """
    spec = {"input_video_path": input_video_path, "upscale": {"control_weight": control_weight}}

    # Only include prompt if provided (following design principle)
    if prompt:
        spec["prompt"] = prompt

    return spec


def write_cosmos_json(cosmos_data: dict[str, Any], output_path: str | Path) -> Path:
    """Write Cosmos format data to a JSON file.

    Args:
        cosmos_data: Dictionary in Cosmos format
        output_path: Path where to write the JSON

    Returns:
        Path to the written file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(cosmos_data, f, indent=2)

    return output_path


def to_cosmos_batch_json(prompts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert a list of prompt dicts to NVIDIA Cosmos batch format for upsampling.

    Args:
        prompts: List of prompt dictionaries from database

    Returns:
        List of dicts in format expected by prompt_upsampler.py
    """
    batch_data = []
    for prompt in prompts:
        inputs = prompt.get("inputs", {})
        video_path = inputs.get("video", "")
        # Flatten video path if present
        if video_path:
            video_path = f"inputs/videos/{Path(video_path).name}"
        batch_data.append(
            {
                "name": f"prompt_{prompt.get('id', 'unknown')}",
                "prompt": prompt.get("prompt_text", ""),
                "video_path": video_path,
                "spec_id": prompt.get("id", ""),
            }
        )

    return batch_data


def to_cosmos_batch_inference_jsonl(
    runs_and_prompts: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Convert multiple run/prompt pairs to NVIDIA Cosmos batch inference JSONL format.

    Args:
        runs_and_prompts: List of (run_dict, prompt_dict) tuples

    Returns:
        List of dictionaries, each representing one line in the JSONL file.
        Each dict contains:
        - visual_input: path to input video
        - prompt: text prompt
        - control_overrides: optional per-video control settings
    """
    batch_lines = []

    for run_dict, prompt_dict in runs_and_prompts:
        # Get basic fields
        run_id = run_dict["id"]
        inputs = prompt_dict.get("inputs", {})
        visual_input = inputs.get("video", "")

        # Use run-specific paths to match actual upload location
        if visual_input:
            # Use run-specific path instead of generic inputs/videos/
            visual_input = f"runs/{run_id}/inputs/videos/{Path(visual_input).name}"

        # Build the JSONL line
        line = {
            "visual_input": visual_input,
            "prompt": prompt_dict.get("prompt_text", ""),
        }

        # Add control overrides based on execution config
        execution_config = run_dict.get("execution_config", {})
        weights = execution_config.get("weights", {})

        control_overrides = {}

        # Handle segmentation control
        seg_weight = weights.get("seg", 0.25)
        if seg_weight > 0:
            seg_input = inputs.get("seg", "")
            if seg_input:
                # Use provided segmentation video (run-specific path)
                control_overrides["seg"] = {
                    "input_control": f"runs/{run_id}/inputs/videos/{Path(seg_input).name}",
                    "control_weight": seg_weight,
                }
            else:
                # Auto-generate segmentation (null means auto-generate)
                control_overrides["seg"] = {"input_control": None, "control_weight": seg_weight}

        # Handle depth control
        depth_weight = weights.get("depth", 0.25)
        if depth_weight > 0:
            depth_input = inputs.get("depth", "")
            if depth_input:
                # Use provided depth video (run-specific path)
                control_overrides["depth"] = {
                    "input_control": f"runs/{run_id}/inputs/videos/{Path(depth_input).name}",
                    "control_weight": depth_weight,
                }
            else:
                # Auto-generate depth (null means auto-generate)
                control_overrides["depth"] = {"input_control": None, "control_weight": depth_weight}

        # Handle visual (vis) control - always auto-generated
        vis_weight = weights.get("vis", 0.25)
        if vis_weight > 0:
            control_overrides["vis"] = {"control_weight": vis_weight}

        # Handle edge control
        edge_weight = weights.get("edge", 0.25)
        if edge_weight > 0:
            edge_input = inputs.get("edge", "")
            if edge_input:
                # Use provided edge video (run-specific path)
                control_overrides["edge"] = {
                    "input_control": f"runs/{run_id}/inputs/videos/{Path(edge_input).name}",
                    "control_weight": edge_weight,
                }
            else:
                # Auto-generate edge
                control_overrides["edge"] = {"control_weight": edge_weight}

        # Only add control_overrides if there are any
        if control_overrides:
            line["control_overrides"] = control_overrides

        # Add metadata for tracking (will be ignored by inference script)
        line["_run_id"] = run_dict.get("id", "")
        line["_prompt_id"] = prompt_dict.get("id", "")

        batch_lines.append(line)

    return batch_lines


def write_batch_jsonl(batch_data: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Write batch data to a JSONL file.

    Args:
        batch_data: List of dictionaries to write as JSONL
        output_path: Path where to write the JSONL file

    Returns:
        Path to the written file
    """
    import json

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        for line_data in batch_data:
            # Remove internal metadata fields before writing
            clean_data = {k: v for k, v in line_data.items() if not k.startswith("_")}
            f.write(json.dumps(clean_data) + "\n")

    return output_path
