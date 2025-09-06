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
        """Convert Windows path to Unix path.

        Handles Windows paths that may have escape sequences like \v (vertical tab).
        """
        if not path:
            return path

        # Fix escape sequences that may have been introduced
        # These occur when Python interprets backslash sequences in file paths
        # For example: \videos becomes \x0bideos (vertical tab + ideos)
        path = path.replace("\x0b", "/v")  # \v (vertical tab) in \videos
        path = path.replace("\x0c", "/f")  # \f (form feed) in \files
        path = path.replace("\x07", "/a")  # \a (bell) in \apps
        path = path.replace("\x08", "/b")  # \b (backspace) in \bin
        path = path.replace("\x0d", "/r")  # \r (carriage return) in \resources
        path = path.replace("\x09", "/t")  # \t (tab) in \temp
        path = path.replace("\x0a", "/n")  # \n (newline) in \new

        # Now convert remaining backslashes to forward slashes
        unix_path = path.replace("\\", "/")

        return unix_path

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
        inputs = prompt_dict.get("inputs", {})
        visual_input = inputs.get("video", "")

        # Convert Windows paths to Unix for GPU server
        if visual_input:
            visual_input = visual_input.replace("\\", "/")

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
                # Use provided segmentation video
                control_overrides["seg"] = {
                    "input_control": seg_input.replace("\\", "/"),
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
                # Use provided depth video
                control_overrides["depth"] = {
                    "input_control": depth_input.replace("\\", "/"),
                    "control_weight": depth_weight,
                }
            else:
                # Auto-generate depth (null means auto-generate)
                control_overrides["depth"] = {"input_control": None, "control_weight": depth_weight}

        # Handle visual (vis) control - always auto-generated
        vis_weight = weights.get("vis", 0.25)
        if vis_weight > 0:
            control_overrides["vis"] = {"control_weight": vis_weight}

        # Handle edge control - always auto-generated
        edge_weight = weights.get("edge", 0.25)
        if edge_weight > 0:
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
