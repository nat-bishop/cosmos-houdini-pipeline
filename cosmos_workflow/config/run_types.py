"""Central definition of run types and their behaviors.

This module defines all valid run types and their properties to ensure
consistency across the codebase.
"""

from enum import Enum
from typing import TypedDict


class RunType(str, Enum):
    """All valid run types in the system."""

    TRANSFER = "transfer"  # Main inference/generation
    ENHANCE = "enhance"  # Prompt enhancement
    UPSCALE = "upscale"  # Video upscaling
    REASON = "reason"  # Reasoning/analysis
    PREDICT = "predict"  # Prediction/forecast


class RunTypeConfig(TypedDict):
    """Configuration for a run type."""

    uses_gpu: bool  # Does this run type use GPU resources?
    blocks_overwrite: bool  # Should this prevent prompt overwriting?
    container_prefix: str  # Docker container name prefix
    description: str  # Human-readable description


# Central configuration for all run types
RUN_TYPE_CONFIGS: dict[RunType, RunTypeConfig] = {
    RunType.TRANSFER: {
        "uses_gpu": True,
        "blocks_overwrite": True,  # Main GPU work - always blocks
        "container_prefix": "cosmos_transfer",
        "description": "Main inference/generation runs",
    },
    RunType.ENHANCE: {
        "uses_gpu": True,
        "blocks_overwrite": True,  # Uses GPU - should block
        "container_prefix": "cosmos_enhance",
        "description": "Prompt enhancement using AI models",
    },
    RunType.UPSCALE: {
        "uses_gpu": True,
        "blocks_overwrite": True,  # Uses GPU - should block
        "container_prefix": "cosmos_upscale",
        "description": "Video upscaling to higher resolution",
    },
    RunType.REASON: {
        "uses_gpu": True,
        "blocks_overwrite": True,  # Uses GPU - should block
        "container_prefix": "cosmos_reason",
        "description": "Reasoning and analysis tasks",
    },
    RunType.PREDICT: {
        "uses_gpu": True,
        "blocks_overwrite": True,  # Uses GPU - should block
        "container_prefix": "cosmos_predict",
        "description": "Prediction and forecasting tasks",
    },
}


def is_blocking_run(model_type: str) -> bool:
    """Check if a run type should block prompt overwriting.

    Args:
        model_type: The model type string

    Returns:
        True if this run type blocks overwriting
    """
    try:
        run_type = RunType(model_type)
        return RUN_TYPE_CONFIGS[run_type]["blocks_overwrite"]
    except (ValueError, KeyError):
        # Unknown run types block by default for safety
        return True


def uses_gpu_resources(model_type: str) -> bool:
    """Check if a run type uses GPU resources.

    Args:
        model_type: The model type string

    Returns:
        True if this run type uses GPU
    """
    try:
        run_type = RunType(model_type)
        return RUN_TYPE_CONFIGS[run_type]["uses_gpu"]
    except (ValueError, KeyError):
        # Assume unknown types use GPU for safety
        return True


def get_container_prefix(model_type: str) -> str:
    """Get the Docker container prefix for a run type.

    Args:
        model_type: The model type string

    Returns:
        Container name prefix
    """
    try:
        run_type = RunType(model_type)
        return RUN_TYPE_CONFIGS[run_type]["container_prefix"]
    except (ValueError, KeyError):
        # Fallback for unknown types
        return f"cosmos_{model_type}"
