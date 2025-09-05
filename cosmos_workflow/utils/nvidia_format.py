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

    # Extract inputs
    inputs = prompt_dict.get("inputs", {})

    # Convert Windows paths to Unix paths for GPU server
    def to_unix_path(path: str) -> str:
        """Convert Windows path to Unix path."""
        if path:
            return path.replace("\\", "/")
        return path

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
        "input_video_path": to_unix_path(inputs.get("video", "")),
        # Additional parameters
        "num_steps": execution_config.get("num_steps", 35),
        "guidance": execution_config.get("guidance", 7.0),
        "sigma_max": execution_config.get("sigma_max", 70.0),
        "seed": execution_config.get("seed", 42),
        "fps": execution_config.get("fps", 8),
    }

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
            cosmos_json["depth"]["input_control"] = to_unix_path(depth_path)

    seg_weight = weights.get("seg", 0.25)
    if seg_weight > 0:
        cosmos_json["seg"] = {"control_weight": seg_weight}
        # Only add input_control if video path exists
        seg_path = inputs.get("seg", "")
        if seg_path:
            cosmos_json["seg"]["input_control"] = to_unix_path(seg_path)

    return cosmos_json


def to_cosmos_upscale_json(
    prompt_dict: dict[str, Any], run_dict: dict[str, Any], upscale_weight: float = 0.5
) -> dict[str, Any]:
    """Convert database dicts to NVIDIA Cosmos upscale format.

    Args:
        prompt_dict: Prompt data from database
        run_dict: Run data from database
        upscale_weight: Weight for upscaling (0.0-1.0)

    Returns:
        Dictionary in NVIDIA Cosmos format for upscale.sh
    """
    # Upscaling uses similar format but with upscale-specific params
    cosmos_json = to_cosmos_inference_json(prompt_dict, run_dict)

    # Add upscale specific configuration
    cosmos_json["upscale"] = {"control_weight": upscale_weight}

    # For upscaling, we typically use fewer steps
    cosmos_json["num_steps"] = 10

    return cosmos_json


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
        batch_data.append(
            {
                "name": f"prompt_{prompt.get('id', 'unknown')}",
                "prompt": prompt.get("prompt_text", ""),
                "video_path": inputs.get("video", ""),
                "spec_id": prompt.get("id", ""),
            }
        )

    return batch_data
