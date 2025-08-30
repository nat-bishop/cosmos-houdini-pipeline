#!/usr/bin/env python3
"""
Tests for local AI methods.
"""

import pytest
import numpy as np
from pathlib import Path
import tempfile
import cv2

from cosmos_workflow.local_ai import (
    TextToNameGenerator,
    VideoMetadataExtractor,
    VideoProcessor
)
from cosmos_workflow.local_ai.video_metadata import VideoMetadata


class TestTextToNameGenerator:
    """Test suite for TextToNameGenerator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = TextToNameGenerator()
    
    def test_basic_name_generation(self):
        """Test basic name generation from text."""
        text = "A futuristic cyberpunk city at night with neon lights"
        name = self.generator.generate_name(text)
        
        # Check that name is generated
        assert name is not None
        assert len(name) > 0
        
        # Check filesystem safety
        assert "/" not in name
        assert "\\" not in name
        assert ":" not in name
        
        # Check that key words are included
        assert any(word in name for word in ["futuristic", "cyberpunk", "city", "night", "neon"])
    
    def test_stop_word_filtering(self):
        """Test that stop words are filtered out."""
        text = "The very beautiful and amazing city with the lights"
        name = self.generator.generate_name(text)
        
        # Stop words should not be in the name
        assert "the" not in name.lower()
        assert "and" not in name.lower()
        assert "with" not in name.lower()
    
    def test_priority_words(self):
        """Test that priority words are preferred."""
        text = "Some random words with robot and cyberpunk elements"
        name = self.generator.generate_name(text)
        
        # Priority words should be included
        assert "robot" in name or "cyberpunk" in name
    
    def test_word_limit(self):
        """Test that name respects word limits."""
        text = "This is a very long description with many words that should be shortened"
        name = self.generator.generate_name(text)
        
        # Check word count
        word_count = len(name.split("_"))
        assert word_count <= 4
        assert word_count >= 2
    
    def test_filesystem_safety(self):
        """Test that generated names are filesystem-safe."""
        texts = [
            "Name with special characters: @#$%^&*()",
            "Name with spaces and tabs\t\n",
            "Name/with/slashes\\and\\backslashes",
            "Name:with:colons|and|pipes"
        ]
        
        for text in texts:
            name = self.generator.generate_name(text)
            
            # Check that problematic characters are removed/replaced
            assert all(c.isalnum() or c in "_-" for c in name)
    
    def test_empty_input(self):
        """Test handling of empty input."""
        name = self.generator.generate_name("")
        assert name == "untitled"
    
    def test_batch_generation(self):
        """Test batch name generation with duplicate handling."""
        texts = [
            "Robot in office",
            "Robot in office",  # Duplicate
            "Robot in office"   # Another duplicate
        ]
        
        names = self.generator.batch_generate(texts)
        
        # Check that all names are unique
        assert len(names) == len(texts)
        assert len(set(names)) == len(names)
        
        # Check that duplicates are numbered
        assert names[0] != names[1]
        assert names[0] != names[2]
        assert names[1] != names[2]
    
    def test_context_influence(self):
        """Test that context influences name generation."""
        text = "Beautiful scene with water"
        
        # Without context
        name1 = self.generator.generate_name(text)
        
        # With ocean context
        name2 = self.generator.generate_name(text, context="ocean waves beach")
        
        # Names might be different due to context
        # (This is probabilistic, so we just check they're generated)
        assert name1 is not None
        assert name2 is not None
    
    def test_max_length(self):
        """Test that names don't exceed maximum length."""
        text = "a" * 200  # Very long input
        name = self.generator.generate_name(text)
        
        assert len(name) <= 50


class TestVideoMetadataExtractor:
    """Test suite for VideoMetadataExtractor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = VideoMetadataExtractor()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def create_test_video(self, name: str, width: int = 640, height: int = 480, 
                         fps: int = 24, frames: int = 10) -> Path:
        """Create a test video file."""
        video_path = self.temp_path / name
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))
        
        # Write frames
        for i in range(frames):
            # Create a frame with changing color
            frame = np.full((height, width, 3), i * 25, dtype=np.uint8)
            out.write(frame)
        
        out.release()
        return video_path
    
    def test_extract_metadata_basic(self):
        """Test basic metadata extraction."""
        video_path = self.create_test_video("test.mp4")
        
        metadata = self.extractor.extract_metadata(video_path)
        
        assert isinstance(metadata, VideoMetadata)
        assert metadata.width == 640
        assert metadata.height == 480
        assert metadata.fps == 24
        assert metadata.frame_count == 10
        assert metadata.duration == pytest.approx(10/24, rel=0.1)
    
    def test_extract_metadata_missing_file(self):
        """Test handling of missing file."""
        with pytest.raises(ValueError, match="Video file not found"):
            self.extractor.extract_metadata(Path("nonexistent.mp4"))
    
    def test_extract_metadata_unsupported_format(self):
        """Test handling of unsupported format."""
        txt_file = self.temp_path / "test.txt"
        txt_file.write_text("Not a video")
        
        with pytest.raises(ValueError, match="Unsupported video format"):
            self.extractor.extract_metadata(txt_file)
    
    def test_validate_compatibility_matching(self):
        """Test validation of compatible videos."""
        video1 = self.create_test_video("video1.mp4", 640, 480, 24, 10)
        video2 = self.create_test_video("video2.mp4", 640, 480, 24, 10)
        
        result = self.extractor.validate_video_compatibility([video1, video2])
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['metadata']['resolution'] == "640x480"
        assert result['metadata']['fps'] == 24
    
    def test_validate_compatibility_resolution_mismatch(self):
        """Test validation with resolution mismatch."""
        video1 = self.create_test_video("video1.mp4", 640, 480, 24, 10)
        video2 = self.create_test_video("video2.mp4", 1280, 720, 24, 10)
        
        result = self.extractor.validate_video_compatibility([video1, video2])
        
        assert result['valid'] is False
        assert any("Resolution mismatch" in error for error in result['errors'])
    
    def test_validate_compatibility_frame_count_mismatch(self):
        """Test validation with frame count mismatch."""
        video1 = self.create_test_video("video1.mp4", 640, 480, 24, 10)
        video2 = self.create_test_video("video2.mp4", 640, 480, 24, 20)
        
        result = self.extractor.validate_video_compatibility([video1, video2])
        
        assert result['valid'] is False
        assert any("Frame count mismatch" in error for error in result['errors'])
    
    def test_file_hash_calculation(self):
        """Test that file hash is calculated."""
        video_path = self.create_test_video("test.mp4")
        
        metadata = self.extractor.extract_metadata(video_path)
        
        assert metadata.hash is not None
        assert len(metadata.hash) == 16  # We use first 16 chars
        
        # Hash should be consistent
        metadata2 = self.extractor.extract_metadata(video_path)
        assert metadata.hash == metadata2.hash


class TestVideoProcessor:
    """Test suite for VideoProcessor."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = VideoProcessor()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()
    
    def create_test_video(self, name: str, width: int = 640, height: int = 480,
                         fps: int = 30, frames: int = 30) -> Path:
        """Create a test video file."""
        video_path = self.temp_path / name
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(str(video_path), fourcc, fps, (width, height))
        
        for i in range(frames):
            frame = np.full((height, width, 3), i * 8, dtype=np.uint8)
            out.write(frame)
        
        out.release()
        return video_path
    
    def test_standardize_video_fps_conversion(self):
        """Test FPS conversion."""
        input_video = self.create_test_video("input.mp4", fps=30)
        output_video = self.temp_path / "output.mp4"
        
        success = self.processor.standardize_video(
            input_video,
            output_video,
            target_fps=24
        )
        
        assert success is True
        assert output_video.exists()
        
        # Check output video properties
        cap = cv2.VideoCapture(str(output_video))
        assert cap.get(cv2.CAP_PROP_FPS) == 24
        cap.release()
    
    def test_standardize_video_resolution_change(self):
        """Test resolution change."""
        input_video = self.create_test_video("input.mp4", width=1280, height=720)
        output_video = self.temp_path / "output.mp4"
        
        success = self.processor.standardize_video(
            input_video,
            output_video,
            target_resolution=(640, 480)
        )
        
        assert success is True
        assert output_video.exists()
        
        # Check output video properties
        cap = cv2.VideoCapture(str(output_video))
        assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 640
        assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == 480
        cap.release()
    
    def test_extract_frame(self):
        """Test frame extraction."""
        video = self.create_test_video("test.mp4", frames=10)
        
        # Extract middle frame
        frame = self.processor.extract_frame(video, 5)
        
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape == (480, 640, 3)
    
    def test_extract_frame_with_save(self):
        """Test frame extraction with saving."""
        video = self.create_test_video("test.mp4", frames=10)
        output_path = self.temp_path / "frame.jpg"
        
        frame = self.processor.extract_frame(video, 5, output_path)
        
        assert frame is not None
        assert output_path.exists()
    
    def test_create_video_from_frames(self):
        """Test video creation from frames."""
        # Create test frames
        frame_paths = []
        for i in range(10):
            frame = np.full((480, 640, 3), i * 25, dtype=np.uint8)
            frame_path = self.temp_path / f"frame_{i:03d}.jpg"
            cv2.imwrite(str(frame_path), frame)
            frame_paths.append(frame_path)
        
        output_video = self.temp_path / "output.mp4"
        
        success = self.processor.create_video_from_frames(
            frame_paths,
            output_video,
            fps=24
        )
        
        assert success is True
        assert output_video.exists()
        
        # Check output video
        cap = cv2.VideoCapture(str(output_video))
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 10
        assert cap.get(cv2.CAP_PROP_FPS) == 24
        cap.release()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
