#!/usr/bin/env python3
"""
Video metadata extraction and processing module with AI-powered frame tagging.

Handles video file analysis, frame extraction, and metadata generation
using transformer models for automatic tagging of video content.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import json
from dataclasses import dataclass, field
import hashlib
import logging
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
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
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
            from transformers import (
                BlipProcessor, BlipForConditionalGeneration,
                pipeline
            )
            
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
                device=0 if self.device == "cuda" else -1
            )
            
            # Initialize object detection
            logger.info("Loading object detection model...")
            self.object_detector = pipeline(
                "object-detection",
                model="facebook/detr-resnet-50",
                device=0 if self.device == "cuda" else -1
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
                detected_objects=detected_objects
            )
            
        finally:
            cap.release()
    
    def _analyze_frame_with_ai(self, frame: np.ndarray) -> Tuple[List[str], str, List[Dict[str, Any]]]:
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
                tags = [item['label'] for item in classifications if item['score'] > 0.1]
                logger.info(f"Generated tags: {tags}")
            
            # Detect objects
            if self.object_detector:
                detections = self.object_detector(pil_image)
                detected_objects = [
                    {
                        'label': det['label'],
                        'score': float(det['score']),
                        'box': det['box']
                    }
                    for det in detections if det['score'] > 0.5
                ]
                logger.info(f"Detected {len(detected_objects)} objects")
                
        except Exception as e:
            logger.error(f"Error during AI analysis: {e}")
        
        return tags, caption, detected_objects
    
    def _analyze_middle_frame(self, cap: cv2.VideoCapture, frame_count: int) -> Tuple[Dict[str, Any], Optional[np.ndarray]]:
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
            'brightness': np.mean(frame),
            'contrast': np.std(frame),
            'histogram': {
                'blue': np.histogram(frame[:, :, 0], bins=256, range=(0, 256))[0].tolist(),
                'green': np.histogram(frame[:, :, 1], bins=256, range=(0, 256))[0].tolist(),
                'red': np.histogram(frame[:, :, 2], bins=256, range=(0, 256))[0].tolist()
            }
        }
        
        # Calculate dominant colors
        pixels = frame.reshape(-1, 3)
        from sklearn.cluster import KMeans
        try:
            kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
            kmeans.fit(pixels)
            dominant_colors = kmeans.cluster_centers_.astype(int).tolist()
            stats['dominant_colors'] = dominant_colors
        except:
            # Fallback if sklearn is not available
            stats['dominant_colors'] = []
        
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
        with open(file_path, 'rb') as f:
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
            'file_path': metadata.file_path,
            'duration': metadata.duration,
            'fps': metadata.fps,
            'frame_count': metadata.frame_count,
            'width': metadata.width,
            'height': metadata.height,
            'codec': metadata.codec,
            'file_size': metadata.file_size,
            'hash': metadata.hash,
            'middle_frame_stats': metadata.middle_frame_stats,
            'ai_tags': metadata.ai_tags,
            'ai_caption': metadata.ai_caption,
            'detected_objects': metadata.detected_objects
        }
        
        with open(output_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2)
    
    def load_metadata(self, metadata_path: Path) -> VideoMetadata:
        """
        Load metadata from JSON file.
        
        Args:
            metadata_path: Path to JSON file
            
        Returns:
            VideoMetadata object
        """
        with open(metadata_path, 'r') as f:
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


def main():
    """CLI interface for video metadata extraction."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract metadata from video files")
    parser.add_argument("video_path", type=Path, help="Path to video file")
    parser.add_argument("--output", type=Path, help="Output JSON file path")
    parser.add_argument("--no-ai", action="store_true", help="Disable AI analysis")
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu",
                       help="Device for AI models")
    
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