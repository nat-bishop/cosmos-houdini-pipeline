#!/usr/bin/env python3
"""
Video metadata extraction and processing module.

Handles video file analysis, frame extraction, and metadata generation
for use in Cosmos Transfer workflows.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import json
from dataclasses import dataclass
import hashlib


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


class VideoMetadataExtractor:
    """
    Extracts metadata from video files.
    
    This class provides functionality to analyze video files and extract
    relevant metadata for Cosmos Transfer workflows.
    """
    
    def __init__(self):
        """Initialize the video metadata extractor."""
        self.supported_formats = {'.mp4', '.avi', '.mov', '.mkv', '.webm'}
    
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
            
            # Extract middle frame statistics
            middle_frame_stats = self._analyze_middle_frame(cap, frame_count)
            
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
                middle_frame_stats=middle_frame_stats
            )
        
        finally:
            cap.release()
    
    def _calculate_file_hash(self, file_path: Path, chunk_size: int = 1024 * 1024) -> str:
        """
        Calculate hash of video file (first chunk only for speed).
        
        Args:
            file_path: Path to file
            chunk_size: Size of chunk to hash
            
        Returns:
            Hex string hash
        """
        hash_obj = hashlib.sha256()
        
        with open(file_path, 'rb') as f:
            chunk = f.read(chunk_size)
            hash_obj.update(chunk)
        
        return hash_obj.hexdigest()[:16]  # Use first 16 chars
    
    def _analyze_middle_frame(self, cap: cv2.VideoCapture, frame_count: int) -> Dict[str, Any]:
        """
        Analyze the middle frame of the video.
        
        Args:
            cap: OpenCV video capture object
            frame_count: Total number of frames
            
        Returns:
            Dictionary of frame statistics
        """
        if frame_count == 0:
            return {}
        
        # Seek to middle frame
        middle_frame_idx = frame_count // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, middle_frame_idx)
        
        ret, frame = cap.read()
        if not ret:
            return {}
        
        # Calculate statistics
        stats = {
            'mean_brightness': float(np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))),
            'std_brightness': float(np.std(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))),
            'dominant_colors': self._get_dominant_colors(frame),
            'histogram_peaks': self._get_histogram_peaks(frame)
        }
        
        return stats
    
    def _get_dominant_colors(self, frame: np.ndarray, n_colors: int = 3) -> List[List[int]]:
        """
        Get dominant colors from a frame.
        
        Args:
            frame: Video frame
            n_colors: Number of dominant colors to extract
            
        Returns:
            List of RGB color values
        """
        # Reshape frame to list of pixels
        pixels = frame.reshape(-1, 3)
        
        # Sample pixels for speed
        sample_size = min(1000, len(pixels))
        indices = np.random.choice(len(pixels), sample_size, replace=False)
        sampled_pixels = pixels[indices]
        
        # Simple k-means clustering
        from sklearn.cluster import KMeans
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(sampled_pixels)
        
        # Get cluster centers (dominant colors)
        colors = kmeans.cluster_centers_.astype(int)
        
        # Convert BGR to RGB
        colors = colors[:, [2, 1, 0]]
        
        return colors.tolist()
    
    def _get_histogram_peaks(self, frame: np.ndarray) -> Dict[str, List[int]]:
        """
        Get histogram peaks for each color channel.
        
        Args:
            frame: Video frame
            
        Returns:
            Dictionary with peaks for each channel
        """
        peaks = {}
        
        for i, color in enumerate(['blue', 'green', 'red']):
            hist = cv2.calcHist([frame], [i], None, [256], [0, 256])
            hist = hist.flatten()
            
            # Find peaks (local maxima)
            peak_indices = []
            for j in range(1, 255):
                if hist[j] > hist[j-1] and hist[j] > hist[j+1]:
                    peak_indices.append(int(j))
            
            # Keep top 3 peaks
            peak_indices.sort(key=lambda x: hist[x], reverse=True)
            peaks[color] = peak_indices[:3]
        
        return peaks
    
    def validate_video_compatibility(self, video_paths: List[Path]) -> Dict[str, Any]:
        """
        Validate that multiple videos are compatible.
        
        Args:
            video_paths: List of video file paths
            
        Returns:
            Dictionary with validation results
        """
        if not video_paths:
            return {'valid': False, 'errors': ['No video paths provided']}
        
        metadata_list = []
        errors = []
        
        # Extract metadata for all videos
        for path in video_paths:
            try:
                metadata = self.extract_metadata(path)
                metadata_list.append(metadata)
            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")
        
        if errors:
            return {'valid': False, 'errors': errors}
        
        # Check compatibility
        first = metadata_list[0]
        
        for i, metadata in enumerate(metadata_list[1:], 1):
            # Check resolution
            if metadata.width != first.width or metadata.height != first.height:
                errors.append(
                    f"{video_paths[i].name}: Resolution mismatch "
                    f"({metadata.width}x{metadata.height} vs {first.width}x{first.height})"
                )
            
            # Check frame count
            if metadata.frame_count != first.frame_count:
                errors.append(
                    f"{video_paths[i].name}: Frame count mismatch "
                    f"({metadata.frame_count} vs {first.frame_count})"
                )
            
            # Check FPS (with tolerance)
            if abs(metadata.fps - first.fps) > 0.1:
                errors.append(
                    f"{video_paths[i].name}: FPS mismatch "
                    f"({metadata.fps:.2f} vs {first.fps:.2f})"
                )
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'metadata': {
                'resolution': f"{first.width}x{first.height}",
                'fps': first.fps,
                'frame_count': first.frame_count,
                'duration': first.duration
            }
        }


class VideoProcessor:
    """
    Processes video files for Cosmos Transfer workflows.
    
    This class handles video conversion, resizing, and preparation
    for use as input to Cosmos Transfer.
    """
    
    def __init__(self):
        """Initialize the video processor."""
        self.standard_fps = 24
        self.standard_resolutions = {
            '720p': (1280, 720),
            '1080p': (1920, 1080),
            '4k': (3840, 2160)
        }
    
    def standardize_video(
        self,
        input_path: Path,
        output_path: Path,
        target_fps: int = 24,
        target_resolution: Optional[Tuple[int, int]] = None
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
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(
                str(output_path),
                fourcc,
                target_fps,
                (out_width, out_height)
            )
            
            # Process frames
            frame_interval = input_fps / target_fps
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Skip frames to match target FPS
                if frame_count % int(frame_interval) == 0:
                    # Resize if needed
                    if (out_width, out_height) != (input_width, input_height):
                        frame = cv2.resize(frame, (out_width, out_height))
                    
                    out.write(frame)
                
                frame_count += 1
            
            return True
        
        finally:
            cap.release()
            if 'out' in locals():
                out.release()
    
    def extract_frame(
        self,
        video_path: Path,
        frame_index: int,
        output_path: Optional[Path] = None
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
            return None
        
        try:
            # Seek to frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            
            ret, frame = cap.read()
            if not ret:
                return None
            
            # Save if output path provided
            if output_path:
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(output_path), frame)
            
            return frame
        
        finally:
            cap.release()
    
    def create_video_from_frames(
        self,
        frame_paths: List[Path],
        output_path: Path,
        fps: int = 24
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
            return False
        
        # Read first frame to get dimensions
        first_frame = cv2.imread(str(frame_paths[0]))
        if first_frame is None:
            return False
        
        height, width = first_frame.shape[:2]
        
        # Set up video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(
            str(output_path),
            fourcc,
            fps,
            (width, height)
        )
        
        try:
            # Write all frames
            for frame_path in frame_paths:
                frame = cv2.imread(str(frame_path))
                if frame is not None:
                    out.write(frame)
            
            return True
        
        finally:
            out.release()


def main():
    """Example usage of video metadata extraction."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python video_metadata.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    # Extract metadata
    extractor = VideoMetadataExtractor()
    
    try:
        metadata = extractor.extract_metadata(video_path)
        
        print("Video Metadata:")
        print("-" * 50)
        print(f"File: {metadata.file_path}")
        print(f"Duration: {metadata.duration:.2f} seconds")
        print(f"FPS: {metadata.fps:.2f}")
        print(f"Resolution: {metadata.width}x{metadata.height}")
        print(f"Frame Count: {metadata.frame_count}")
        print(f"Codec: {metadata.codec}")
        print(f"File Size: {metadata.file_size / 1024 / 1024:.2f} MB")
        print(f"Hash: {metadata.hash}")
        
        if metadata.middle_frame_stats:
            print("\nMiddle Frame Analysis:")
            print(f"  Mean Brightness: {metadata.middle_frame_stats['mean_brightness']:.2f}")
            print(f"  Std Brightness: {metadata.middle_frame_stats['std_brightness']:.2f}")
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()