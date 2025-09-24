"""Run details helper functions for extracting and processing run information.

This module contains helper functions used to extract metadata, resolve paths,
and prepare data for run details display.
"""

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
    output_video = None  # Initialize as None instead of empty string
    video_paths = []
    output_gallery = []

    # New structure: outputs.output_path
    if isinstance(outputs, dict) and "output_path" in outputs:
        output_path = outputs["output_path"]
        if output_path and output_path.endswith(".mp4"):
            video_path = str(Path(output_path))
            if Path(video_path).exists():
                output_video = video_path
                video_paths = [output_video]

    # Old structure: outputs.files array
    elif isinstance(outputs, dict) and "files" in outputs:
        files = outputs.get("files", [])
        for file_path in files:
            if file_path.endswith("output.mp4"):
                video_path = str(Path(file_path))
                if Path(video_path).exists():
                    output_video = video_path
                    video_paths = [output_video]
                    break

    # Set output gallery from video paths
    if video_paths:
        output_gallery = video_paths

    return video_paths, output_gallery, output_video


def extract_control_weights(exec_config: dict) -> dict:
    """Extract control weights from execution config.

    Args:
        exec_config: Execution configuration dictionary

    Returns:
        Dictionary with standardized control weights for vis, edge, depth, seg
    """
    weights = {"vis": 0, "edge": 0, "depth": 0, "seg": 0}

    if not exec_config:
        return weights

    # Extract weights from nested structure (e.g., {"vis": {"control_weight": 1.0}})
    for control_type in ["vis", "edge", "depth", "seg"]:
        if control_type in exec_config:
            config_value = exec_config[control_type]
            if isinstance(config_value, dict):
                weights[control_type] = config_value.get("control_weight", 0)
            elif isinstance(config_value, int | float):
                # Handle direct numeric values
                weights[control_type] = float(config_value)

    # Also check for a top-level "weights" key (alternative structure)
    if "weights" in exec_config:
        weights_section = exec_config["weights"]
        if isinstance(weights_section, dict):
            for control_type in ["vis", "edge", "depth", "seg"]:
                if control_type in weights_section:
                    weights[control_type] = float(weights_section.get(control_type, 0))

    return weights


def build_input_gallery(prompt_inputs: dict, run_id: str, exec_config: dict) -> tuple:
    """Build input video gallery from execution config and prompt inputs.

    Args:
        prompt_inputs: Input paths from prompt
        run_id: Run ID for locating generated controls
        exec_config: Execution config with control weights

    Returns:
        Tuple of (input_videos list, control_weights dict, video_labels list)
    """
    input_videos = []
    video_labels = []

    # Extract control weights using helper function
    control_weights = extract_control_weights(exec_config)

    if not exec_config:
        logger.error(
            "ERROR: No execution_config found for run {}. This indicates corrupted or incomplete run data.",
            run_id,
        )

    if prompt_inputs:
        # Add main video if weight > 0
        if prompt_inputs.get("video") and control_weights["vis"] > 0:
            path = Path(prompt_inputs["video"])
            if path.exists():
                input_videos.append(str(path))
                video_labels.append(f"Color ({control_weights['vis']:.2f})")

        # Add control videos
        control_map = {
            "edge": "Edge",
            "depth": "Depth",
            "seg": "Segmentation",
        }

        for key, label in control_map.items():
            weight = control_weights[key]
            if weight > 0:
                # First try prompt's input for this control
                if prompt_inputs.get(key):
                    path = Path(prompt_inputs[key])
                    if path.exists():
                        input_videos.append(str(path))
                        video_labels.append(f"{label} ({weight:.2f})")
                        continue

                # If no prompt input, check for AI-generated control
                indexed_path = Path(
                    f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{key}_input_control_0.mp4"
                )
                non_indexed_path = Path(
                    f"F:/Art/cosmos-houdini-experiments/outputs/run_{run_id}/outputs/{key}_input_control.mp4"
                )

                if indexed_path.exists():
                    input_videos.append(str(indexed_path))
                    video_labels.append(f"{label} ({weight:.2f})")
                elif non_indexed_path.exists():
                    input_videos.append(str(non_indexed_path))
                    video_labels.append(f"{label} ({weight:.2f})")

    return input_videos, control_weights, video_labels


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
_build_input_gallery = build_input_gallery
_read_log_content = read_log_content
_extract_control_weights = extract_control_weights

__all__ = [
    "build_input_gallery",
    "extract_control_weights",
    "extract_run_metadata",
    "read_log_content",
    "resolve_video_paths",
]
