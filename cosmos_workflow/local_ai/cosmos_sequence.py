#!/usr/bin/env python3
"""
Cosmos-specific sequence validation and video conversion.

This module handles the strict validation and conversion of Cosmos Transfer
control modality sequences (color, depth, segmentation, vis, edge).
"""

import re
import cv2
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field
import json
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class CosmosSequenceInfo:
    """Information about a validated Cosmos sequence."""
    valid: bool
    modalities: Dict[str, List[Path]]  # e.g., {"color": [paths], "depth": [paths]}
    frame_count: int
    frame_numbers: List[int]
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class CosmosMetadata:
    """Simplified metadata for Cosmos inference."""
    id: str  # Quick hash
    name: str  # Short name from AI or user
    description: str  # AI-generated description
    frame_count: int
    fps: float
    modalities: List[str]
    video_path: str  # Path to color.mp4
    control_inputs: Dict[str, str]  # Paths to control videos (depth, seg, etc.)
    timestamp: str
    resolution: Tuple[int, int]  # width, height


class CosmosSequenceValidator:
    """
    Validates PNG sequences for Cosmos Transfer workflows.
    
    Enforces strict naming conventions and ensures consistency
    across control modalities.
    """
    
    REQUIRED_MODALITY = "color"
    OPTIONAL_MODALITIES = ["depth", "segmentation", "vis", "edge"]
    ALL_MODALITIES = [REQUIRED_MODALITY] + OPTIONAL_MODALITIES
    
    def __init__(self):
        """Initialize the validator."""
        # Pattern for Cosmos files: modality.XXXX.png
        self.pattern = re.compile(r'^(\w+)\.(\d{4})\.png$')
    
    def validate(self, input_dir: Path) -> CosmosSequenceInfo:
        """
        Validate a directory containing Cosmos control sequences.
        
        Args:
            input_dir: Directory to validate
            
        Returns:
            CosmosSequenceInfo with validation results
        """
        input_dir = Path(input_dir)
        
        if not input_dir.exists() or not input_dir.is_dir():
            return CosmosSequenceInfo(
                valid=False,
                modalities={},
                frame_count=0,
                frame_numbers=[],
                issues=[f"Directory does not exist: {input_dir}"]
            )
        
        # Find all PNG files
        png_files = list(input_dir.glob("*.png"))
        
        if not png_files:
            return CosmosSequenceInfo(
                valid=False,
                modalities={},
                frame_count=0,
                frame_numbers=[],
                issues=["No PNG files found in directory"]
            )
        
        # Categorize files by modality
        modalities = {}
        unexpected_files = []
        
        for png_file in png_files:
            match = self.pattern.match(png_file.name)
            if not match:
                unexpected_files.append(png_file.name)
                continue
            
            modality = match.group(1)
            frame_num = int(match.group(2))
            
            if modality not in self.ALL_MODALITIES:
                unexpected_files.append(png_file.name)
                continue
            
            if modality not in modalities:
                modalities[modality] = {}
            
            modalities[modality][frame_num] = png_file
        
        issues = []
        warnings = []
        
        # Check for unexpected files
        if unexpected_files:
            issues.append(f"Unexpected files found: {unexpected_files[:5]}{'...' if len(unexpected_files) > 5 else ''}")
        
        # Check for required modality
        if self.REQUIRED_MODALITY not in modalities:
            issues.append(f"Required modality '{self.REQUIRED_MODALITY}' not found")
            return CosmosSequenceInfo(
                valid=False,
                modalities={},
                frame_count=0,
                frame_numbers=[],
                issues=issues
            )
        
        # Get frame numbers from color (required)
        color_frames = modalities[self.REQUIRED_MODALITY]
        frame_numbers = sorted(color_frames.keys())
        frame_count = len(frame_numbers)
        
        # Check for gaps in color sequence
        expected_range = range(frame_numbers[0], frame_numbers[-1] + 1)
        missing_frames = set(expected_range) - set(frame_numbers)
        if missing_frames:
            issues.append(f"Missing frames in color sequence: {sorted(missing_frames)[:10]}{'...' if len(missing_frames) > 10 else ''}")
        
        # Validate other modalities have matching frame numbers
        for modality, frames in modalities.items():
            if modality == self.REQUIRED_MODALITY:
                continue
            
            modality_frame_numbers = set(frames.keys())
            color_frame_numbers = set(frame_numbers)
            
            # Check for mismatched frames
            extra_frames = modality_frame_numbers - color_frame_numbers
            missing_frames = color_frame_numbers - modality_frame_numbers
            
            if extra_frames:
                warnings.append(f"{modality} has extra frames not in color: {sorted(extra_frames)[:5]}...")
            if missing_frames:
                warnings.append(f"{modality} missing frames that exist in color: {sorted(missing_frames)[:5]}...")
        
        # Convert modalities dict to list format
        modality_paths = {}
        for modality, frames in modalities.items():
            # Only include frames that exist in color sequence
            paths = []
            for frame_num in frame_numbers:
                if frame_num in frames:
                    paths.append(frames[frame_num])
            if paths:
                modality_paths[modality] = paths
        
        valid = len(issues) == 0
        
        return CosmosSequenceInfo(
            valid=valid,
            modalities=modality_paths,
            frame_count=frame_count,
            frame_numbers=frame_numbers,
            issues=issues,
            warnings=warnings
        )


class CosmosVideoConverter:
    """
    Converts validated Cosmos sequences to videos.
    
    Creates separate video files for each control modality
    with proper naming for Cosmos Transfer workflows.
    """
    
    def __init__(self, fps: int = 24):
        """
        Initialize the converter.
        
        Args:
            fps: Frame rate for output videos
        """
        self.fps = fps
    
    def convert_sequence(
        self,
        sequence_info: CosmosSequenceInfo,
        output_dir: Path,
        name: str = "sequence"
    ) -> Dict[str, Any]:
        """
        Convert validated sequences to videos.
        
        Args:
            sequence_info: Validated sequence information
            output_dir: Base output directory
            name: Name for the output directory
            
        Returns:
            Dict with conversion results
        """
        if not sequence_info.valid:
            return {
                "success": False,
                "error": "Invalid sequence",
                "issues": sequence_info.issues
            }
        
        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"{name}_{timestamp}"
        output_path.mkdir(parents=True, exist_ok=True)
        
        results = {
            "success": True,
            "output_dir": str(output_path),
            "videos": {},
            "errors": []
        }
        
        # Convert each modality in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}
            
            for modality, paths in sequence_info.modalities.items():
                video_path = output_path / f"{modality}.mp4"
                future = executor.submit(
                    self._create_video,
                    paths,
                    video_path,
                    modality
                )
                futures[future] = modality
            
            for future in as_completed(futures):
                modality = futures[future]
                try:
                    success, video_path = future.result()
                    if success:
                        results["videos"][modality] = str(video_path)
                        logger.info(f"Created {modality}.mp4")
                    else:
                        results["errors"].append(f"Failed to create {modality}.mp4")
                        results["success"] = False
                except Exception as e:
                    results["errors"].append(f"Error creating {modality}.mp4: {str(e)}")
                    results["success"] = False
        
        return results
    
    def _create_video(
        self,
        frame_paths: List[Path],
        output_path: Path,
        modality: str
    ) -> Tuple[bool, Optional[Path]]:
        """
        Create a video from frame paths.
        
        Args:
            frame_paths: List of paths to frames
            output_path: Output video path
            modality: Name of modality (for logging)
            
        Returns:
            Tuple of (success, output_path)
        """
        if not frame_paths:
            logger.error(f"No frames for {modality}")
            return False, None
        
        # Read first frame to get dimensions
        first_frame = cv2.imread(str(frame_paths[0]))
        if first_frame is None:
            logger.error(f"Cannot read first frame for {modality}")
            return False, None
        
        height, width = first_frame.shape[:2]
        
        # Set up video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            str(output_path),
            fourcc,
            self.fps,
            (width, height)
        )
        
        if not out.isOpened():
            logger.error(f"Failed to open video writer for {modality}")
            return False, None
        
        try:
            # Write first frame
            out.write(first_frame)
            frames_written = 1
            
            # Write remaining frames
            for frame_path in frame_paths[1:]:
                frame = cv2.imread(str(frame_path))
                if frame is not None:
                    # Ensure consistent dimensions
                    if frame.shape[:2] != (height, width):
                        frame = cv2.resize(frame, (width, height))
                    out.write(frame)
                    frames_written += 1
                else:
                    logger.warning(f"Cannot read frame: {frame_path}")
            
            logger.info(f"Created {modality} video with {frames_written} frames")
            return True, output_path
            
        except Exception as e:
            logger.error(f"Error creating {modality} video: {e}")
            return False, None
            
        finally:
            out.release()
    
    def generate_metadata(
        self,
        sequence_info: CosmosSequenceInfo,
        output_dir: Path,
        name: str,
        description: Optional[str] = None,
        use_ai: bool = True
    ) -> CosmosMetadata:
        """
        Generate simplified metadata for the sequence.
        
        Args:
            sequence_info: Validated sequence information
            output_dir: Directory containing videos
            name: Short name for the sequence
            description: Description (will be AI-generated if not provided)
            use_ai: Whether to use AI for description generation
            
        Returns:
            CosmosMetadata object
        """
        # Generate quick hash ID
        hash_input = f"{name}_{datetime.now().isoformat()}_{sequence_info.frame_count}"
        id_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]
        
        # Get resolution from first color frame
        resolution = (1920, 1080)  # Default
        if "color" in sequence_info.modalities and sequence_info.modalities["color"]:
            first_frame = cv2.imread(str(sequence_info.modalities["color"][0]))
            if first_frame is not None:
                height, width = first_frame.shape[:2]
                resolution = (width, height)
        
        # Generate AI description if needed and possible
        if description is None:
            if use_ai and "color" in sequence_info.modalities:
                description = self._generate_ai_description(
                    sequence_info.modalities["color"]
                )
            else:
                description = f"Sequence with {sequence_info.frame_count} frames"
        
        # Build paths for video and control inputs
        video_path = str(output_dir / "color.mp4")
        control_inputs = {}
        for modality in sequence_info.modalities.keys():
            if modality != "color":
                control_inputs[modality] = str(output_dir / f"{modality}.mp4")
        
        # Create metadata
        metadata = CosmosMetadata(
            id=id_hash,
            name=name,
            description=description,
            frame_count=sequence_info.frame_count,
            fps=float(self.fps),
            modalities=list(sequence_info.modalities.keys()),
            video_path=video_path,
            control_inputs=control_inputs,
            timestamp=datetime.now().isoformat() + "Z",
            resolution=resolution
        )
        
        # Save metadata to JSON
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump({
                "id": metadata.id,
                "name": metadata.name,
                "description": metadata.description,
                "frame_count": metadata.frame_count,
                "fps": metadata.fps,
                "modalities": metadata.modalities,
                "video_path": metadata.video_path,
                "control_inputs": metadata.control_inputs,
                "timestamp": metadata.timestamp,
                "resolution": list(metadata.resolution)
            }, f, indent=2)
        
        return metadata
    
    def _generate_ai_description(self, color_frames: List[Path]) -> str:
        """
        Generate AI description from color frames.
        
        Args:
            color_frames: List of color frame paths
            
        Returns:
            Generated description or default
        """
        try:
            from transformers import BlipProcessor, BlipForConditionalGeneration
            from PIL import Image
            
            # Use middle frame for description
            middle_idx = len(color_frames) // 2
            frame_path = color_frames[middle_idx]
            
            # Load frame
            frame = cv2.imread(str(frame_path))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)
            
            # Generate caption with BLIP
            processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )
            model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )
            
            inputs = processor(pil_image, return_tensors="pt")
            out = model.generate(**inputs, max_length=50)
            description = processor.decode(out[0], skip_special_tokens=True)
            
            logger.info(f"Generated AI description: {description}")
            return description
            
        except ImportError:
            logger.warning("AI models not available (install transformers)")
            return f"Sequence with {len(color_frames)} frames"
        except Exception as e:
            logger.warning(f"Could not generate AI description: {e}")
            return f"Sequence with {len(color_frames)} frames"