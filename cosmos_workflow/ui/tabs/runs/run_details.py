"""Run details helper functions for extracting and processing run information.

This module contains helper functions used to extract metadata, resolve paths,
and prepare data for run details display.
"""

import json
from datetime import datetime
from pathlib import Path

from cosmos_workflow.utils.logging import logger


def extract_run_metadata(run_details: dict) -> dict:
    """Extract basic metadata from run details.

    Args:
        run_details: Raw run details from API

    Returns:
        Dictionary with duration, dates, status, etc.
    """
    metadata = {
        "duration": "N/A",
        "created_at": run_details.get("created_at", ""),
        "completed_at": run_details.get("completed_at", ""),
        "status": run_details.get("status", "unknown"),
        "log_path": run_details.get("log_path", ""),
    }

    # Calculate duration
    if metadata["created_at"] and metadata["completed_at"]:
        try:
            start = datetime.fromisoformat(metadata["created_at"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(metadata["completed_at"].replace("Z", "+00:00"))
            duration_delta = end - start
            metadata["duration"] = str(duration_delta).split(".")[0]
        except Exception:  # noqa: S110
            pass

    return metadata


def resolve_video_paths(outputs: dict, run_id: str, ops) -> tuple:
    """Resolve output and upscaled video paths from run outputs.

    Args:
        outputs: Outputs dictionary from run details
        run_id: Run ID for checking upscaled version
        ops: CosmosAPI instance

    Returns:
        Tuple of (video_paths, output_gallery, output_video)
    """
    output_video = ""
    video_paths = []
    output_gallery = []

    # New structure: outputs.output_path
    if isinstance(outputs, dict) and "output_path" in outputs:
        output_path = outputs["output_path"]
        if output_path and output_path.endswith(".mp4"):
            output_video = str(Path(output_path))
            if Path(output_video).exists():
                video_paths = [output_video]

    # Old structure: outputs.files array
    elif isinstance(outputs, dict) and "files" in outputs:
        files = outputs.get("files", [])
        for file_path in files:
            if file_path.endswith("output.mp4"):
                output_video = str(Path(file_path))
                if Path(output_video).exists():
                    video_paths = [output_video]
                break

    # Set output gallery from video paths
    if video_paths:
        output_gallery = video_paths

    return video_paths, output_gallery, output_video


def load_spec_and_weights(run_id: str) -> dict:
    """Load spec.json and extract control weights.

    Args:
        run_id: Run ID to locate spec.json

    Returns:
        Dictionary with spec data or empty dict if not found
    """
    spec_data = {}
    if run_id:
        spec_path = Path(f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/inputs/spec.json")
        if spec_path.exists():
            try:
                with open(spec_path) as f:
                    spec_data = json.load(f)
                logger.info("Loaded spec.json for run {}", run_id)
            except Exception as e:
                logger.warning("Failed to load spec.json: {}", str(e))
    return spec_data


def build_input_gallery(spec_data: dict, prompt_inputs: dict, run_id: str) -> tuple:
    """Build input video gallery from spec data and prompt inputs.

    Args:
        spec_data: Loaded spec.json data
        prompt_inputs: Input paths from prompt
        run_id: Run ID for locating generated controls

    Returns:
        Tuple of (input_videos list, control_weights dict)
    """
    input_videos = []
    control_weights = {"vis": 0, "edge": 0, "depth": 0, "seg": 0}

    if spec_data:
        # Add main video from prompt if it exists
        if prompt_inputs.get("video"):
            path = Path(prompt_inputs["video"])
            if path.exists():
                input_videos.append((str(path), "Color/Visual"))
                control_weights["vis"] = 1.0

        # Process each control type
        control_types = {"edge": "Edge", "depth": "Depth", "seg": "Segmentation"}

        for control_key, control_label in control_types.items():
            control_config = spec_data.get(control_key, {})
            weight = control_config.get("control_weight", 0)

            # Only process if weight > 0
            if weight > 0:
                control_weights[control_key] = weight
                label_with_weight = f"{control_label} (Weight: {weight})"

                # First try prompt's input for this control
                if prompt_inputs.get(control_key):
                    control_path = Path(prompt_inputs[control_key])
                    if control_path.exists():
                        input_videos.append((str(control_path), label_with_weight))
                        continue

                # If no prompt input, check for AI-generated control
                indexed_path = Path(
                    f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{control_key}_input_control_0.mp4"
                )
                non_indexed_path = Path(
                    f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{control_key}_input_control.mp4"
                )

                if indexed_path.exists():
                    input_videos.append((str(indexed_path), label_with_weight))
                elif non_indexed_path.exists():
                    input_videos.append((str(non_indexed_path), label_with_weight))

    # Fallback if no spec.json - use prompt inputs with default weights
    elif prompt_inputs:
        video_keys = {
            "video": ("Color/Visual", 1.0),
            "edge": ("Edge", 0.5),
            "depth": ("Depth", 0.5),
            "seg": ("Segmentation", 0.5),
        }
        for key, (label, default_weight) in video_keys.items():
            if prompt_inputs.get(key):
                path = Path(prompt_inputs[key])
                if path.exists():
                    if key != "video":
                        label = f"{label} (Weight: {default_weight})"
                    input_videos.append((str(path), label))
                    if key == "video":
                        control_weights["vis"] = default_weight
                    else:
                        control_weights[key] = default_weight

    return input_videos, control_weights


def read_log_content(log_path: str, lines: int = 15) -> str:
    """Read last N lines from log file.

    Args:
        log_path: Path to log file
        lines: Number of lines to read from end

    Returns:
        Log content or error message
    """
    if not log_path or not Path(log_path).exists():
        return ""

    try:
        with open(log_path) as f:
            all_lines = f.readlines()
            return "".join(all_lines[-lines:])
    except Exception:
        return "Error reading log file"


# Maintain backward compatibility with underscore-prefixed names
_extract_run_metadata = extract_run_metadata
_resolve_video_paths = resolve_video_paths
_load_spec_and_weights = load_spec_and_weights
_build_input_gallery = build_input_gallery
_read_log_content = read_log_content

__all__ = [
    "build_input_gallery",
    "extract_run_metadata",
    "load_spec_and_weights",
    "read_log_content",
    "resolve_video_paths",
]
