"""
Local AI methods for Cosmos workflow.

This module provides local AI functionality for:
- Text-to-name generation (converting descriptions to short names)
- Video metadata extraction and analysis
- Control modality generation from video frames
"""

from .text_to_name import TextToNameGenerator
from .video_metadata import VideoMetadataExtractor, VideoProcessor
from .control_generator import ControlModalityGenerator

__all__ = [
    "TextToNameGenerator",
    "VideoMetadataExtractor",
    "VideoProcessor",
    "ControlModalityGenerator"
]