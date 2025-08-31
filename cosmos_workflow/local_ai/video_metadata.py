#!/usr/bin/env python3
"""
Video metadata extraction and processing module with AI-powered frame tagging.

Handles video file analysis, frame extraction, and metadata generation
using transformer models for automatic tagging of video content.
"""

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class VideoMetadata:
    """Container for video metadata."""

    file_path: str
    duration: float  # seconds
    fps: float
    frame_count: int
    width: int
    height: int
    codec: str
    file_size: int  # bytes
    hash: str  # file hash for verification
    middle_frame_stats: Dict[str, Any]  # Statistics from middle frame
    ai_tags: List[str] = field(default_factory=list)  # AI-generated tags
    ai_caption: str = ""  # AI-generated caption
    detected_objects: List[Dict[str, Any]] = field(default_factory=list)  # Detected objects


class VideoMetadataExtractor:
    """
    Extracts metadata from video files with AI-powered analysis.

    This class provides functionality to analyze video files and extract
    relevant metadata for Cosmos Transfer workflows, including AI-generated
    tags and descriptions.
    """

    def __init__(self, use_ai: bool = True, device: str = "cpu"):
        """
        Initialize the video metadata extractor.

        Args:
            use_ai: Whether to use AI models for tagging
            device: Device to run AI models on ("cpu" or "cuda")
        """
        self.supported_formats = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
        self.use_ai = use_ai
        self.device = device

        # Initialize AI models if requested
        self.image_tagger = None
        self.captioner = None

        if self.use_ai:
            self._initialize_ai_models()

    def _initialize_ai_models(self):
        """Initialize AI models for image analysis."""
        try:
            from transformers import BlipForConditionalGeneration, BlipProcessor, pipeline

            # Initialize BLIP model for image captioning
            logger.info("Loading BLIP model for image captioning...")
            self.caption_processor = BlipProcessor.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            )
            self.caption_model = BlipForConditionalGeneration.from_pretrained(
                "Salesforce/blip-image-captioning-base"
            ).to(self.device)

            # Initialize image classification pipeline for tagging
            logger.info("Loading image classification model for tagging...")
            self.image_classifier = pipeline(
                "image-classification",
                model="google/vit-base-patch16-224",
                device=0 if self.device == "cuda" else -1,
            )

            # Initialize object detection
            logger.info("Loading object detection model...")
            self.object_detector = pipeline(
                "object-detection",
                model="facebook/detr-resnet-50",
                device=0 if self.device == "cuda" else -1,
            )

            logger.info("AI models loaded successfully")

        except ImportError as e:
            logger.warning(f"Could not load AI models: {e}")
            logger.warning("Install transformers and torch for AI features:")
            logger.warning("pip install transformers torch pillow")
            self.use_ai = False
        except Exception as e:
            logger.error(f"Error initializing AI models: {e}")
            self.use_ai = False

    def extract_metadata(self, video_path: Path) -> VideoMetadata:
        """
        Extract metadata from a video file.

        Args:
            video_path: Path to the video file

        Returns:
            VideoMetadata object containing extracted information

        Raises:
            ValueError: If video file cannot be read or is invalid
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise ValueError(f"Video file not found: {video_path}")

        if video_path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Unsupported video format: {video_path.suffix}")

        # Open video
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")

        try:
            # Extract basic metadata
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Get codec
            fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
            codec = "".join([chr((fourcc >> 8 * i) & 0xFF) for i in range(4)])

            # Calculate duration
            duration = frame_count / fps if fps > 0 else 0

            # Get file size
            file_size = video_path.stat().st_size

            # Calculate file hash (first 1MB for speed)
            file_hash = self._calculate_file_hash(video_path)

            # Extract middle frame for analysis
            middle_frame_stats, middle_frame = self._analyze_middle_frame(cap, frame_count)

            # Initialize AI-related fields
            ai_tags = []
            ai_caption = ""
            detected_objects = []

            # Perform AI analysis if enabled and frame was extracted
            if self.use_ai and middle_frame is not None:
                ai_tags, ai_caption, detected_objects = self._analyze_frame_with_ai(middle_frame)

            return VideoMetadata(
                file_path=str(video_path),
                duration=duration,
                fps=fps,
                frame_count=frame_count,
                width=width,
                height=height,
                codec=codec,
                file_size=file_size,
                hash=file_hash,
                middle_frame_stats=middle_frame_stats,
                ai_tags=ai_tags,
                ai_caption=ai_caption,
                detected_objects=detected_objects,
            )

        finally:
            cap.release()

    def _analyze_frame_with_ai(
        self, frame: np.ndarray
    ) -> Tuple[List[str], str, List[Dict[str, Any]]]:
        """
        Analyze a frame using AI models.

        Args:
            frame: Frame as numpy array (BGR format from OpenCV)

        Returns:
            Tuple of (tags, caption, detected_objects)
        """
        # Convert BGR to RGB and create PIL Image
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)

        tags = []
        caption = ""
        detected_objects = []

        try:
            # Generate caption
            if self.caption_processor and self.caption_model:
                inputs = self.caption_processor(pil_image, return_tensors="pt").to(self.device)
                out = self.caption_model.generate(**inputs, max_length=50)
                caption = self.caption_processor.decode(out[0], skip_special_tokens=True)
                logger.info(f"Generated caption: {caption}")

            # Generate tags from classification
            if self.image_classifier:
                classifications = self.image_classifier(pil_image, top_k=5)
                tags = [item["label"] for item in classifications if item["score"] > 0.1]
                logger.info(f"Generated tags: {tags}")

            # Detect objects
            if self.object_detector:
                detections = self.object_detector(pil_image)
                detected_objects = [
                    {"label": det["label"], "score": float(det["score"]), "box": det["box"]}
                    for det in detections
                    if det["score"] > 0.5
                ]
                logger.info(f"Detected {len(detected_objects)} objects")

        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")

        return tags, caption, detected_objects

    def _analyze_middle_frame(
        self, cap: cv2.VideoCapture, frame_count: int
    ) -> Tuple[Dict[str, Any], Optional[np.ndarray]]:
        """
        Analyze the middle frame of the video.

        Args:
            cap: OpenCV VideoCapture object
            frame_count: Total number of frames

        Returns:
            Tuple of (statistics dictionary, frame array)
        """
        if frame_count == 0:
            return {}, None

        # Seek to middle frame
        middle_frame_idx = frame_count // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_idx)

        ret, frame = cap.read()
        if not ret:
            return {}, None

        # Calculate statistics
        stats = {
            "brightness": np.mean(frame),
            "contrast": np.std(frame),
            "histogram": {
                "blue": np.histogram(frame[:, :, 0], bins=256, range=(0, 256))[0].tolist(),
                "green": np.histogram(frame[:, :, 1], bins=256, range=(0, 256))[0].tolist(),
                "red": np.histogram(frame[:, :, 2], bins=256, range=(0, 256))[0].tolist(),
            },
        }

        # Calculate dominant colors
        pixels = frame.reshape(-1, 3)
        from sklearn.cluster import KMeans

        try:
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans.fit(pixels)
            dominant_colors = kmeans.cluster_centers_.astype(int).tolist()
            stats["dominant_colors"] = dominant_colors
        except:
            # Fallback if sklearn is not available
            stats["dominant_colors"] = []

        return stats, frame

    def _calculate_file_hash(self, file_path: Path, chunk_size: int = 1024 * 1024) -> str:
        """
        Calculate SHA256 hash of file (first chunk only for speed).

        Args:
            file_path: Path to file
            chunk_size: Size of chunk to hash (default 1MB)

        Returns:
            Hex string of hash
        """
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            chunk = f.read(chunk_size)
            sha256.update(chunk)
        return sha256.hexdigest()

    def extract_frame(self, video_path: Path, frame_number: int) -> Optional[np.ndarray]:
        """
        Extract a specific frame from video.

        Args:
            video_path: Path to video file
            frame_number: Frame index to extract

        Returns:
            Frame as numpy array or None if extraction fails
        """
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            return None

        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            return frame if ret else None
        finally:
            cap.release()

    def save_metadata(self, metadata: VideoMetadata, output_path: Path) -> None:
        """
        Save metadata to JSON file.

        Args:
            metadata: VideoMetadata object
            output_path: Path to save JSON file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dictionary
        metadata_dict = {
            "file_path": metadata.file_path,
            "duration": metadata.duration,
            "fps": metadata.fps,
            "frame_count": metadata.frame_count,
            "width": metadata.width,
            "height": metadata.height,
            "codec": metadata.codec,
            "file_size": metadata.file_size,
            "hash": metadata.hash,
            "middle_frame_stats": metadata.middle_frame_stats,
            "ai_tags": metadata.ai_tags,
            "ai_caption": metadata.ai_caption,
            "detected_objects": metadata.detected_objects,
        }

        with open(output_path, "w") as f:
            json.dump(metadata_dict, f, indent=2)

    def load_metadata(self, metadata_path: Path) -> VideoMetadata:
        """
        Load metadata from JSON file.

        Args:
            metadata_path: Path to JSON file

        Returns:
            VideoMetadata object
        """
        with open(metadata_path, "r") as f:
            data = json.load(f)

        return VideoMetadata(**data)


def analyze_video(video_path: Path, use_ai: bool = True) -> VideoMetadata:
    """
    Convenience function to analyze a video file.

    Args:
        video_path: Path to video file
        use_ai: Whether to use AI models for analysis

    Returns:
        VideoMetadata object
    """
    extractor = VideoMetadataExtractor(use_ai=use_ai)
    return extractor.extract_metadata(video_path)


class VideoProcessor:
    """
    Processes video files and PNG sequences for Cosmos Transfer workflows.

    This class handles video conversion, PNG sequence validation and conversion,
    resizing, and preparation for use as input to Cosmos Transfer.
    """

    def __init__(self):
        """Initialize the video processor."""
        self.standard_fps = 24
        self.standard_resolutions = {"720p": (1280, 720), "1080p": (1920, 1080), "4k": (3840, 2160)}

    def validate_sequence(self, input_dir: Path) -> Dict[str, Any]:
        """
        Validate a PNG sequence before conversion.

        Args:
            input_dir: Directory containing PNG files

        Returns:
            Dictionary with validation results:
                - valid: bool indicating if sequence is valid
                - frame_count: number of frames found
                - missing_frames: list of missing frame indices
                - pattern: detected naming pattern
                - issues: list of issue descriptions
        """
        input_dir = Path(input_dir)

        if not input_dir.exists() or not input_dir.is_dir():
            return {
                "valid": False,
                "frame_count": 0,
                "missing_frames": [],
                "pattern": None,
                "issues": [f"Directory does not exist: {input_dir}"],
            }

        # Find all PNG files
        png_files = sorted(input_dir.glob("*.png"))

        if not png_files:
            return {
                "valid": False,
                "frame_count": 0,
                "missing_frames": [],
                "pattern": None,
                "issues": ["No PNG files found in directory"],
            }

        # Try to detect naming pattern
        import re

        issues = []
        missing_frames = []
        pattern = None

        # Common patterns
        patterns = [
            (r"frame_(\d{3,4})\.png", "frame_{:03d}.png"),
            (r"frame(\d{3,4})\.png", "frame{:03d}.png"),
            (r"image_(\d+)\.png", "image_{}.png"),
            (r"(\d{3,4})\.png", "{:03d}.png"),
        ]

        frame_numbers = []
        for png_file in png_files:
            name = png_file.name
            for regex, fmt in patterns:
                match = re.match(regex, name)
                if match:
                    frame_numbers.append(int(match.group(1)))
                    if pattern is None:
                        pattern = fmt
                    break

        # Check for gaps in sequence
        if frame_numbers:
            frame_numbers = sorted(frame_numbers)
            expected_range = range(frame_numbers[0], frame_numbers[-1] + 1)
            missing_frames = [i for i in expected_range if i not in frame_numbers]

            if missing_frames:
                issues.append(
                    f"Missing frames detected: {missing_frames[:10]}{'...' if len(missing_frames) > 10 else ''}"
                )

        # Verify files are valid PNGs
        sample_size = min(5, len(png_files))
        for i in range(sample_size):
            try:
                img = cv2.imread(str(png_files[i]))
                if img is None:
                    issues.append(f"Invalid PNG file: {png_files[i].name}")
            except Exception as e:
                issues.append(f"Error reading {png_files[i].name}: {str(e)}")

        valid = len(issues) == 0

        return {
            "valid": valid,
            "frame_count": len(png_files),
            "missing_frames": missing_frames,
            "pattern": pattern,
            "issues": issues,
        }

    def standardize_video(
        self,
        input_path: Path,
        output_path: Path,
        target_fps: int = 24,
        target_resolution: Optional[Tuple[int, int]] = None,
    ) -> bool:
        """
        Standardize a video file for Cosmos Transfer.

        Args:
            input_path: Path to input video
            output_path: Path for output video
            target_fps: Target frame rate
            target_resolution: Target resolution (width, height)

        Returns:
            True if successful, False otherwise
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Open input video
        cap = cv2.VideoCapture(str(input_path))

        if not cap.isOpened():
            logger.error(f"Cannot open video: {input_path}")
            return False

        try:
            # Get input properties
            input_fps = cap.get(cv2.CAP_PROP_FPS)
            input_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            input_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Determine output properties
            if target_resolution:
                out_width, out_height = target_resolution
            else:
                out_width, out_height = input_width, input_height

            # Set up video writer
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            out = cv2.VideoWriter(str(output_path), fourcc, target_fps, (out_width, out_height))

            if not out.isOpened():
                logger.error("Failed to open video writer")
                return False

            # Process frames
            frame_interval = input_fps / target_fps if input_fps > 0 else 1
            frame_count = 0
            written_frames = 0

            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Skip frames to match target FPS
                if frame_count % max(1, int(frame_interval)) == 0:
                    # Resize if needed
                    if (out_width, out_height) != (input_width, input_height):
                        frame = cv2.resize(frame, (out_width, out_height))

                    out.write(frame)
                    written_frames += 1

                frame_count += 1

            logger.info(f"Standardized video: {written_frames} frames at {target_fps} FPS")
            return written_frames > 0

        except Exception as e:
            logger.error(f"Error standardizing video: {e}")
            return False

        finally:
            cap.release()
            if "out" in locals():
                out.release()

    def extract_frame(
        self, video_path: Path, frame_index: int, output_path: Optional[Path] = None
    ) -> Optional[np.ndarray]:
        """
        Extract a specific frame from a video.

        Args:
            video_path: Path to video file
            frame_index: Index of frame to extract
            output_path: Optional path to save frame image

        Returns:
            Frame as numpy array, or None if failed
        """
        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            logger.error(f"Cannot open video: {video_path}")
            return None

        try:
            # Seek to frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

            ret, frame = cap.read()
            if not ret:
                logger.error(f"Cannot read frame {frame_index}")
                return None

            # Save if output path provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(output_path), frame)
                logger.info(f"Saved frame to {output_path}")

            return frame

        finally:
            cap.release()

    def create_video_from_frames(
        self, frame_paths: List[Path], output_path: Path, fps: int = 24
    ) -> bool:
        """
        Create a video from a sequence of frame images.

        Args:
            frame_paths: List of paths to frame images
            output_path: Path for output video
            fps: Frame rate for output video

        Returns:
            True if successful, False otherwise
        """
        if not frame_paths:
            logger.error("No frame paths provided")
            return False

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Read first frame to get dimensions
        first_frame = cv2.imread(str(frame_paths[0]))
        if first_frame is None:
            logger.error(f"Cannot read first frame: {frame_paths[0]}")
            return False

        height, width = first_frame.shape[:2]

        # Set up video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

        if not out.isOpened():
            logger.error("Failed to open video writer")
            return False

        try:
            # Write first frame
            out.write(first_frame)
            frames_written = 1

            # Write remaining frames
            for frame_path in frame_paths[1:]:
                frame = cv2.imread(str(frame_path))
                if frame is not None:
                    # Resize if dimensions don't match
                    if frame.shape[:2] != (height, width):
                        frame = cv2.resize(frame, (width, height))
                    out.write(frame)
                    frames_written += 1
                else:
                    logger.warning(f"Cannot read frame: {frame_path}")

            logger.info(f"Created video with {frames_written} frames at {fps} FPS")
            return frames_written > 0

        except Exception as e:
            logger.error(f"Error creating video: {e}")
            return False

        finally:
            out.release()


def main():
    """CLI interface for video metadata extraction."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract metadata from video files")
    parser.add_argument("video_path", type=Path, help="Path to video file")
    parser.add_argument("--output", type=Path, help="Output JSON file path")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI analysis")
    parser.add_argument(
        "--device", choices=["cpu", "cuda"], default="cpu", help="Device for AI models"
    )

    args = parser.parse_args()

    try:
        extractor = VideoMetadataExtractor(use_ai=not args.no_ai, device=args.device)
        metadata = extractor.extract_metadata(args.video_path)

        # Print metadata
        print(f"Video: {metadata.file_path}")
        print(f"Duration: {metadata.duration:.2f} seconds")
        print(f"Resolution: {metadata.width}x{metadata.height}")
        print(f"FPS: {metadata.fps}")
        print(f"Frame Count: {metadata.frame_count}")
        print(f"Codec: {metadata.codec}")
        print(f"File Size: {metadata.file_size / (1024*1024):.2f} MB")

        if metadata.ai_caption:
            print(f"\nAI Caption: {metadata.ai_caption}")

        if metadata.ai_tags:
            print(f"AI Tags: {', '.join(metadata.ai_tags)}")

        if metadata.detected_objects:
            print(f"\nDetected Objects:")
            for obj in metadata.detected_objects:
                print(f"  - {obj['label']}: {obj['score']:.2%}")

        # Save if output specified
        if args.output:
            extractor.save_metadata(metadata, args.output)
            print(f"\nMetadata saved to: {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
