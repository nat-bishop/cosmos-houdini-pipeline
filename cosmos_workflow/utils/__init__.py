#!/usr/bin/env python3
"""Utility modules for Cosmos workflow system."""

from .workflow_utils import (
    ensure_path_exists,
    format_duration,
)


def calculate_tokens(width: int, height: int, frames: int) -> float:
    """Calculate token cost for video generation.

    Args:
        width: Video width in pixels
        height: Video height in pixels
        frames: Number of frames

    Returns:
        Token cost as float

    Raises:
        ValueError: If any dimension is negative
    """
    if width < 0 or height < 0 or frames < 0:
        raise ValueError("dimensions must be positive")
    if width == 0 or height == 0 or frames == 0:
        return 0
    return width * height * frames * 0.0173


__all__ = [
    "calculate_tokens",
    "ensure_path_exists",
    "format_duration",
]
