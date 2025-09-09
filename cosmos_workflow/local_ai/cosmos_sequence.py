#!/usr/bin/env python3
"""Cosmos-specific sequence validation and video conversion.

This module handles the strict validation and conversion of Cosmos Transfer
control modality sequences (color, depth, segmentation, vis, edge).
"""

import hashlib
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2

from cosmos_workflow.utils.smart_naming import generate_smart_name

logger = logging.getLogger(__name__)


@dataclass
class CosmosSequenceInfo:
    """Information about a validated Cosmos sequence."""

    valid: bool
    modalities: dict[str, list[Path]]  # e.g., {"color": [paths], "depth": [paths]}
    frame_count: int
    frame_numbers: list[int]
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class CosmosMetadata:
    """Simplified metadata for Cosmos inference."""

    id: str  # Quick hash
    name: str  # Short name from AI or user
    description: str  # AI-generated description
    frame_count: int
    fps: float
    modalities: list[str]
    video_path: str  # Path to color.mp4
    control_inputs: dict[str, str]  # Paths to control videos (depth, seg, etc.)
    timestamp: str
    resolution: tuple[int, int]  # width, height


class CosmosSequenceValidator:
    """Validates PNG sequences for Cosmos Transfer workflows.

    Enforces strict naming conventions and ensures consistency
    across control modalities.
    """

    REQUIRED_MODALITY = "color"
    OPTIONAL_MODALITIES = ("depth", "segmentation", "vis", "edge")  # Tuple - immutable
    ALL_MODALITIES = (REQUIRED_MODALITY, *OPTIONAL_MODALITIES)

    def __init__(self):
        """Initialize the validator."""
        # Pattern for Cosmos files: modality.XXXX.png
        self.pattern = re.compile(r"^(\w+)\.(\d{4})\.png$")

    def validate(self, input_dir: Path) -> CosmosSequenceInfo:
        """Validate a directory containing Cosmos control sequences.

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
                issues=[f"Directory does not exist: {input_dir}"],
            )

        # Find all PNG files
        png_files = list(input_dir.glob("*.png"))

        if not png_files:
            return CosmosSequenceInfo(
                valid=False,
                modalities={},
                frame_count=0,
                frame_numbers=[],
                issues=["No PNG files found in directory"],
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
            issues.append(
                f"Unexpected files found: {unexpected_files[:5]}{'...' if len(unexpected_files) > 5 else ''}"
            )

        # Check for required modality
        if self.REQUIRED_MODALITY not in modalities:
            issues.append(f"Required modality '{self.REQUIRED_MODALITY}' not found")
            return CosmosSequenceInfo(
                valid=False, modalities={}, frame_count=0, frame_numbers=[], issues=issues
            )

        # Get frame numbers from color (required)
        color_frames = modalities[self.REQUIRED_MODALITY]
        frame_numbers = sorted(color_frames.keys())
        frame_count = len(frame_numbers)

        # Check for gaps in color sequence
        expected_range = range(frame_numbers[0], frame_numbers[-1] + 1)
        missing_frames = set(expected_range) - set(frame_numbers)
        if missing_frames:
            issues.append(
                f"Missing frames in color sequence: {sorted(missing_frames)[:10]}{'...' if len(missing_frames) > 10 else ''}"
            )

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
                warnings.append(
                    f"{modality} has extra frames not in color: {sorted(extra_frames)[:5]}..."
                )
            if missing_frames:
                warnings.append(
                    f"{modality} missing frames that exist in color: {sorted(missing_frames)[:5]}..."
                )

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
            warnings=warnings,
        )


class CosmosVideoConverter:
    """Converts validated Cosmos sequences to videos.

    Creates separate video files for each control modality
    with proper naming for Cosmos Transfer workflows.
    """

    def __init__(self, fps: int = 24):
        """Initialize the converter.

        Args:
            fps: Frame rate for output videos
        """
        self.fps = fps

    def convert_sequence(
        self,
        sequence_info: CosmosSequenceInfo,
        output_dir: Path,
        name: str | None = None,
        use_ai_naming: bool = True,
    ) -> dict[str, Any]:
        """Convert validated sequences to videos.

        Args:
            sequence_info: Validated sequence information
            output_dir: Base output directory
            name: Name for the output directory (will be AI-generated if not provided)
            use_ai_naming: Whether to use AI for automatic naming

        Returns:
            Dict with conversion results
        """
        if not sequence_info.valid:
            return {"success": False, "error": "Invalid sequence", "issues": sequence_info.issues}

        # Generate AI-based name if not provided
        if name is None and use_ai_naming:
            # Generate description first to derive name
            if "color" in sequence_info.modalities:
                description = self._generate_ai_description(sequence_info.modalities["color"])
                name = generate_smart_name(description)
                logger.info("Generated smart name: '%s' from description: '%s'", name, description)
            else:
                name = "sequence"
        elif name is None:
            name = "sequence"

        # Create timestamped output directory
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"{name}_{timestamp}"
        output_path.mkdir(parents=True, exist_ok=True)

        results = {"success": True, "output_dir": str(output_path), "videos": {}, "errors": []}

        # Convert each modality in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {}

            for modality, paths in sequence_info.modalities.items():
                video_path = output_path / f"{modality}.mp4"
                future = executor.submit(self._create_video, paths, video_path, modality)
                futures[future] = modality

            for future in as_completed(futures):
                modality = futures[future]
                try:
                    success, video_path = future.result()
                    if success:
                        results["videos"][modality] = str(video_path)
                        logger.info("Created %s.mp4", modality)
                    else:
                        results["errors"].append(f"Failed to create {modality}.mp4")
                        results["success"] = False
                except Exception as e:
                    results["errors"].append(f"Error creating {modality}.mp4: {e!s}")
                    results["success"] = False

        return results

    def _create_video(
        self, frame_paths: list[Path], output_path: Path, modality: str
    ) -> tuple[bool, Path | None]:
        """Create a video from frame paths.

        Args:
            frame_paths: List of paths to frames
            output_path: Output video path
            modality: Name of modality (for logging)

        Returns:
            Tuple of (success, output_path)
        """
        if not frame_paths:
            logger.error("No frames for %s", modality)
            return False, None

        # Read first frame to get dimensions
        first_frame = cv2.imread(str(frame_paths[0]))
        if first_frame is None:
            logger.error("Cannot read first frame for %s", modality)
            return False, None

        height, width = first_frame.shape[:2]

        # Set up video writer - use H.264 for browser compatibility
        # Try H.264 first (browser compatible), fallback to mp4v if needed
        try:
            fourcc = cv2.VideoWriter_fourcc(*"avc1")  # H.264 codec
            out = cv2.VideoWriter(str(output_path), fourcc, self.fps, (width, height))
            if not out.isOpened():
                # Fallback to mp4v if H.264 fails
                logger.warning("H.264 codec failed for %s, using mp4v fallback", modality)
                fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                out = cv2.VideoWriter(str(output_path), fourcc, self.fps, (width, height))
        except Exception:
            # If avc1 fails completely, use mp4v
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(output_path), fourcc, self.fps, (width, height))

        if not out.isOpened():
            logger.error("Failed to open video writer for %s", modality)
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
                    logger.warning("Cannot read frame: %s", frame_path)

            logger.info("Created %s video with %d frames", modality, frames_written)

            # Validate codec for browser compatibility
            self._validate_video_codec(output_path, modality)

            return True, output_path

        except Exception as e:
            logger.error("Error creating %s video: %s", modality, e)
            return False, None

        finally:
            out.release()

    @staticmethod
    def _validate_video_codec(video_path: Path, modality: str) -> None:
        """Validate that the video codec is browser-compatible.

        Args:
            video_path: Path to the video file
            modality: Name of the modality for logging
        """
        try:
            cap = cv2.VideoCapture(str(video_path))
            if cap.isOpened():
                fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
                codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])
                cap.release()

                # Check if codec is browser-compatible
                browser_compatible = codec.lower() in ["h264", "avc1"]

                if not browser_compatible:
                    logger.warning(
                        "Video %s.mp4 uses codec '%s' which may not play in browsers. "
                        "Consider converting to H.264 for browser compatibility.",
                        modality,
                        codec,
                    )
                else:
                    logger.info("Video %s.mp4 uses browser-compatible codec: %s", modality, codec)
        except Exception as e:
            logger.warning("Could not validate video codec for %s: %s", modality, e)

    def generate_metadata(
        self,
        sequence_info: CosmosSequenceInfo,
        output_dir: Path,
        name: str | None = None,
        description: str | None = None,
        use_ai: bool = True,
    ) -> CosmosMetadata:
        """Generate simplified metadata for the sequence.

        Args:
            sequence_info: Validated sequence information
            output_dir: Directory containing videos
            name: Short name for the sequence (will be AI-generated if not provided)
            description: Description (will be AI-generated if not provided)
            use_ai: Whether to use AI for description and name generation

        Returns:
            CosmosMetadata object
        """
        # Generate AI description if needed and possible
        if description is None:
            if use_ai and "color" in sequence_info.modalities:
                description = self._generate_ai_description(sequence_info.modalities["color"])
            else:
                description = f"Sequence with {sequence_info.frame_count} frames"

        # Generate smart name from description if not provided
        if name is None:
            if (
                use_ai
                and description
                and description != f"Sequence with {sequence_info.frame_count} frames"
            ):
                name = generate_smart_name(description)
                logger.info("Generated smart name: '%s' from description: '%s'", name, description)
            else:
                name = "sequence"

        # Generate quick hash ID (MD5 is fine for non-cryptographic ID generation)
        hash_input = f"{name}_{datetime.now(timezone.utc).isoformat()}_{sequence_info.frame_count}"
        id_hash = hashlib.md5(hash_input.encode()).hexdigest()[:12]  # noqa: S324

        # Get resolution from first color frame
        resolution = (1920, 1080)  # Default
        if sequence_info.modalities.get("color"):
            first_frame = cv2.imread(str(sequence_info.modalities["color"][0]))
            if first_frame is not None:
                height, width = first_frame.shape[:2]
                resolution = (width, height)

        # Build paths for video and control inputs
        video_path = str(output_dir / "color.mp4")
        control_inputs = {}
        for modality in sequence_info.modalities:
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
            timestamp=datetime.now(timezone.utc).isoformat() + "Z",
            resolution=resolution,
        )

        # Save metadata to JSON
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(
                {
                    "id": metadata.id,
                    "name": metadata.name,
                    "description": metadata.description,
                    "frame_count": metadata.frame_count,
                    "fps": metadata.fps,
                    "modalities": metadata.modalities,
                    "video_path": metadata.video_path,
                    "control_inputs": metadata.control_inputs,
                    "timestamp": metadata.timestamp,
                    "resolution": list(metadata.resolution),
                },
                f,
                indent=2,
            )

        return metadata

    @staticmethod
    def _generate_ai_description(color_frames: list[Path]) -> str:
        """Generate AI description from color frames.

        Args:
            color_frames: List of color frame paths

        Returns:
            Generated description or default
        """
        try:
            from PIL import Image
            from transformers import BlipForConditionalGeneration, BlipProcessor

            # Use middle frame for description
            middle_idx = len(color_frames) // 2
            frame_path = color_frames[middle_idx]

            # Load frame
            frame = cv2.imread(str(frame_path))
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(frame_rgb)

            # Generate caption with BLIP
            processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
            model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )

            inputs = processor(pil_image, return_tensors="pt")
            out = model.generate(**inputs, max_length=50)
            description = processor.decode(out[0], skip_special_tokens=True)

            logger.info("Generated AI description: %s", description)
            return description

        except ImportError:
            logger.warning("AI models not available (install transformers)")
            return f"Sequence with {len(color_frames)} frames"
        except Exception as e:
            logger.warning("Could not generate AI description: %s", e)
            return f"Sequence with {len(color_frames)} frames"
