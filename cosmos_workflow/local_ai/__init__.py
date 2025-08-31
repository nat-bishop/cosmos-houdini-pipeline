"""
Local AI methods for Cosmos workflow.

This module provides local AI functionality for:
- Text-to-name generation (converting descriptions to short names)
- Video metadata extraction and analysis
- Video processing and standardization
- PNG sequence to video conversion
"""

from .text_to_name import TextToNameGenerator
from .video_metadata import VideoMetadata, VideoMetadataExtractor, VideoProcessor

__all__ = ["TextToNameGenerator", "VideoMetadataExtractor", "VideoMetadata", "VideoProcessor"]
