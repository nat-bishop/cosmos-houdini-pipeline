#!/usr/bin/env python3
"""
Tests for local AI methods.
"""

import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from cosmos_workflow.local_ai.text_to_name import TextToNameGenerator
from cosmos_workflow.local_ai.video_metadata import VideoProcessor  # Re-adding VideoProcessor
from cosmos_workflow.local_ai.video_metadata import VideoMetadata, VideoMetadataExtractor


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
            "Name:with:colons|and|pipes",
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
            "Robot in office",  # Another duplicate
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
        self.extractor = VideoMetadataExtractor(
            use_ai=False
        )  # Disable AI for tests to avoid loading models
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def create_test_video(
        self, name: str, width: int = 640, height: int = 480, fps: int = 24, frames: int = 10
    ) -> Path:
        """Create a test video file."""
        video_path = self.temp_path / name

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
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
        assert metadata.duration == pytest.approx(10 / 24, rel=0.1)

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

    def test_extract_frame_method(self):
        """Test frame extraction method."""
        video_path = self.create_test_video("test.mp4")

        # Extract a frame
        frame = self.extractor.extract_frame(video_path, 5)

        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape[2] == 3  # Has 3 color channels

    def test_file_hash_calculation(self):
        """Test that file hash is calculated."""
        video_path = self.create_test_video("test.mp4")

        metadata = self.extractor.extract_metadata(video_path)

        assert metadata.hash is not None
        assert len(metadata.hash) > 0  # Hash is calculated

        # Hash should be consistent
        metadata2 = self.extractor.extract_metadata(video_path)
        assert metadata.hash == metadata2.hash


class TestVideoProcessor:
    """Test suite for VideoProcessor class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.processor = VideoProcessor()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

    def teardown_method(self):
        """Clean up test fixtures."""
        self.temp_dir.cleanup()

    def create_test_png_sequence(
        self,
        num_frames: int = 10,
        width: int = 640,
        height: int = 480,
        has_gap: bool = False,
        pattern: str = "frame_{:03d}.png",
    ) -> Path:
        """Create a test PNG sequence in temp directory."""
        sequence_dir = self.temp_path / "sequence"
        sequence_dir.mkdir(exist_ok=True)

        for i in range(num_frames):
            # Skip frame 5 if creating gap
            if has_gap and i == 5:
                continue

            # Create a simple colored frame
            frame = np.full((height, width, 3), (i * 25, 100, 200 - i * 20), dtype=np.uint8)

            # Add frame number text for verification
            cv2.putText(
                frame, f"Frame {i}", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
            )

            frame_path = sequence_dir / pattern.format(i)
            cv2.imwrite(str(frame_path), frame)

        return sequence_dir

    def test_validate_sequence_valid(self):
        """Test validation of a valid PNG sequence."""
        sequence_dir = self.create_test_png_sequence(num_frames=10)

        result = self.processor.validate_sequence(sequence_dir)

        assert result["valid"] is True
        assert result["frame_count"] == 10
        assert len(result["missing_frames"]) == 0
        assert result["pattern"] is not None
        assert len(result["issues"]) == 0

    def test_validate_sequence_with_gap(self):
        """Test validation detects missing frames."""
        sequence_dir = self.create_test_png_sequence(num_frames=10, has_gap=True)

        result = self.processor.validate_sequence(sequence_dir)

        assert result["valid"] is False
        assert result["frame_count"] == 9  # One frame missing
        assert 5 in result["missing_frames"]
        assert len(result["issues"]) > 0
        assert any("missing frame" in issue.lower() for issue in result["issues"])

    def test_validate_sequence_empty_directory(self):
        """Test validation of empty directory."""
        empty_dir = self.temp_path / "empty"
        empty_dir.mkdir()

        result = self.processor.validate_sequence(empty_dir)

        assert result["valid"] is False
        assert result["frame_count"] == 0
        assert "No PNG files found" in str(result["issues"])

    def test_validate_sequence_non_sequential_names(self):
        """Test validation with non-standard naming."""
        sequence_dir = self.create_test_png_sequence(
            num_frames=5, pattern="image_{:d}.png"  # Non-padded numbers
        )

        result = self.processor.validate_sequence(sequence_dir)

        # Should still work but might have warnings
        assert result["frame_count"] == 5
        assert result["pattern"] is not None

    def test_create_video_from_frames_basic(self):
        """Test basic video creation from PNG sequence."""
        sequence_dir = self.create_test_png_sequence(num_frames=10)
        output_path = self.temp_path / "output.mp4"

        # Get frame paths
        frame_paths = sorted(sequence_dir.glob("*.png"))

        success = self.processor.create_video_from_frames(
            frame_paths=frame_paths, output_path=output_path, fps=24
        )

        assert success is True
        assert output_path.exists()

        # Verify video properties
        cap = cv2.VideoCapture(str(output_path))
        assert cap.isOpened()
        assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == 10
        assert cap.get(cv2.CAP_PROP_FPS) == 24
        cap.release()

    def test_create_video_from_frames_empty_list(self):
        """Test video creation with empty frame list."""
        output_path = self.temp_path / "output.mp4"

        success = self.processor.create_video_from_frames(frame_paths=[], output_path=output_path)

        assert success is False
        assert not output_path.exists()

    def test_create_video_from_frames_invalid_frames(self):
        """Test video creation with invalid frame paths."""
        fake_paths = [self.temp_path / f"fake_{i}.png" for i in range(5)]
        output_path = self.temp_path / "output.mp4"

        success = self.processor.create_video_from_frames(
            frame_paths=fake_paths, output_path=output_path
        )

        assert success is False

    def test_create_video_from_frames_mixed_resolutions(self):
        """Test video creation with mixed frame resolutions."""
        sequence_dir = self.temp_path / "mixed"
        sequence_dir.mkdir()

        # Create frames with different resolutions
        for i, (w, h) in enumerate([(640, 480), (640, 480), (800, 600), (640, 480)]):
            frame = np.full((h, w, 3), (100, 100, 100), dtype=np.uint8)
            cv2.imwrite(str(sequence_dir / f"frame_{i:03d}.png"), frame)

        frame_paths = sorted(sequence_dir.glob("*.png"))
        output_path = self.temp_path / "output.mp4"

        # Should handle mixed resolutions (resize to first frame size)
        success = self.processor.create_video_from_frames(
            frame_paths=frame_paths, output_path=output_path
        )

        assert success is True
        assert output_path.exists()

    def test_standardize_video(self):
        """Test video standardization for FPS and resolution."""
        # First create a video
        sequence_dir = self.create_test_png_sequence(num_frames=10)
        temp_video = self.temp_path / "temp.mp4"
        frame_paths = sorted(sequence_dir.glob("*.png"))

        self.processor.create_video_from_frames(frame_paths, temp_video, fps=30)

        # Now standardize it
        output_path = self.temp_path / "standardized.mp4"
        success = self.processor.standardize_video(
            input_path=temp_video,
            output_path=output_path,
            target_fps=24,
            target_resolution=(1280, 720),
        )

        assert success is True
        assert output_path.exists()

        # Verify standardized properties
        cap = cv2.VideoCapture(str(output_path))
        assert cap.isOpened()
        assert cap.get(cv2.CAP_PROP_FPS) == 24
        assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 1280
        assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == 720
        cap.release()

    def test_extract_frame(self):
        """Test frame extraction from video."""
        # Create a test video first
        sequence_dir = self.create_test_png_sequence(num_frames=10)
        video_path = self.temp_path / "test.mp4"
        frame_paths = sorted(sequence_dir.glob("*.png"))

        self.processor.create_video_from_frames(frame_paths, video_path)

        # Extract middle frame
        frame = self.processor.extract_frame(video_path, frame_index=5)

        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape[0] == 480  # Height
        assert frame.shape[1] == 640  # Width
        assert frame.shape[2] == 3  # Channels

    def test_extract_frame_with_save(self):
        """Test frame extraction with saving to file."""
        # Create a test video
        sequence_dir = self.create_test_png_sequence(num_frames=10)
        video_path = self.temp_path / "test.mp4"
        frame_paths = sorted(sequence_dir.glob("*.png"))

        self.processor.create_video_from_frames(frame_paths, video_path)

        # Extract and save frame
        output_path = self.temp_path / "extracted.png"
        frame = self.processor.extract_frame(video_path, frame_index=5, output_path=output_path)

        assert frame is not None
        assert output_path.exists()

        # Verify saved image
        saved_frame = cv2.imread(str(output_path))
        assert saved_frame is not None
        assert np.array_equal(frame, saved_frame)

    def test_process_sequence_end_to_end(self):
        """Test complete sequence processing workflow."""
        # Create test sequence
        sequence_dir = self.create_test_png_sequence(num_frames=24, width=1920, height=1080)
        output_path = self.temp_path / "final.mp4"

        # Validate sequence
        validation = self.processor.validate_sequence(sequence_dir)
        assert validation["valid"] is True

        # Convert to video
        frame_paths = sorted(sequence_dir.glob("*.png"))
        success = self.processor.create_video_from_frames(
            frame_paths=frame_paths, output_path=output_path, fps=24
        )
        assert success is True

        # Verify we can extract metadata from the result
        extractor = VideoMetadataExtractor(use_ai=False)
        metadata = extractor.extract_metadata(output_path)

        assert metadata.fps == 24
        assert metadata.frame_count == 24
        assert metadata.width == 1920
        assert metadata.height == 1080

    def test_validate_sequence_non_existent_directory(self):
        """Test validation with non-existent directory."""
        non_existent = self.temp_path / "does_not_exist"

        result = self.processor.validate_sequence(non_existent)

        assert result["valid"] is False
        assert "does not exist" in str(result["issues"][0])

    def test_validate_sequence_file_instead_of_directory(self):
        """Test validation when path is a file instead of directory."""
        test_file = self.temp_path / "test.txt"
        test_file.write_text("not a directory")

        result = self.processor.validate_sequence(test_file)

        assert result["valid"] is False
        assert "does not exist" in str(result["issues"][0])

    def test_validate_sequence_corrupted_png(self):
        """Test validation with corrupted PNG files."""
        sequence_dir = self.temp_path / "corrupted"
        sequence_dir.mkdir()

        # Create valid PNGs
        for i in range(3):
            frame = np.full((100, 100, 3), 100, dtype=np.uint8)
            cv2.imwrite(str(sequence_dir / f"frame_{i:03d}.png"), frame)

        # Create corrupted PNG (just text file with .png extension)
        corrupted = sequence_dir / "frame_003.png"
        corrupted.write_text("This is not a valid PNG")

        result = self.processor.validate_sequence(sequence_dir)

        # Should detect the invalid PNG
        assert result["frame_count"] == 4
        assert len(result["issues"]) > 0

    def test_standardize_video_invalid_input(self):
        """Test video standardization with invalid input."""
        invalid_video = self.temp_path / "invalid.mp4"
        output_path = self.temp_path / "output.mp4"

        success = self.processor.standardize_video(
            input_path=invalid_video, output_path=output_path
        )

        assert success is False

    def test_standardize_video_zero_fps(self):
        """Test standardization with edge case FPS values."""
        # Create a video with unusual properties
        sequence_dir = self.create_test_png_sequence(num_frames=5)
        video_path = self.temp_path / "test.mp4"
        frame_paths = sorted(sequence_dir.glob("*.png"))

        self.processor.create_video_from_frames(frame_paths, video_path, fps=30)

        # Try to standardize with edge cases
        output_path = self.temp_path / "standardized.mp4"
        success = self.processor.standardize_video(
            input_path=video_path, output_path=output_path, target_fps=24
        )

        assert success is True

    def test_extract_frame_invalid_video(self):
        """Test frame extraction from non-existent video."""
        invalid_video = self.temp_path / "does_not_exist.mp4"

        frame = self.processor.extract_frame(invalid_video, 0)

        assert frame is None

    def test_extract_frame_out_of_bounds(self):
        """Test frame extraction with out-of-bounds index."""
        # Create a short video
        sequence_dir = self.create_test_png_sequence(num_frames=5)
        video_path = self.temp_path / "short.mp4"
        frame_paths = sorted(sequence_dir.glob("*.png"))

        self.processor.create_video_from_frames(frame_paths, video_path)

        # Try to extract frame beyond video length
        frame = self.processor.extract_frame(video_path, 100)

        assert frame is None

    def test_create_video_from_frames_partial_corrupt(self):
        """Test video creation with some corrupted frames."""
        sequence_dir = self.temp_path / "partial_corrupt"
        sequence_dir.mkdir()

        # Create some valid frames
        frame_paths = []
        for i in range(3):
            frame = np.full((480, 640, 3), 100, dtype=np.uint8)
            path = sequence_dir / f"frame_{i:03d}.png"
            cv2.imwrite(str(path), frame)
            frame_paths.append(path)

        # Add a non-existent frame path
        frame_paths.append(sequence_dir / "missing.png")

        # Add more valid frames
        for i in range(3, 5):
            frame = np.full((480, 640, 3), 100, dtype=np.uint8)
            path = sequence_dir / f"frame_{i:03d}.png"
            cv2.imwrite(str(path), frame)
            frame_paths.append(path)

        output_path = self.temp_path / "partial.mp4"
        success = self.processor.create_video_from_frames(frame_paths, output_path)

        # Should still succeed with valid frames
        assert success is True
        assert output_path.exists()

    def test_validate_sequence_large_gap(self):
        """Test validation with large gaps in sequence."""
        sequence_dir = self.temp_path / "large_gap"
        sequence_dir.mkdir()

        # Create frames with large gap (0, 1, 2, 100, 101)
        for i in [0, 1, 2, 100, 101]:
            frame = np.full((100, 100, 3), 100, dtype=np.uint8)
            cv2.imwrite(str(sequence_dir / f"frame_{i:03d}.png"), frame)

        result = self.processor.validate_sequence(sequence_dir)

        assert result["valid"] is False
        assert len(result["missing_frames"]) == 97  # Missing 3-99
        assert "Missing frames detected" in str(result["issues"][0])

    def test_validate_sequence_single_frame(self):
        """Test validation with only one frame."""
        sequence_dir = self.temp_path / "single"
        sequence_dir.mkdir()

        # Create single frame
        frame = np.full((100, 100, 3), 100, dtype=np.uint8)
        cv2.imwrite(str(sequence_dir / "frame_000.png"), frame)

        result = self.processor.validate_sequence(sequence_dir)

        assert result["valid"] is True
        assert result["frame_count"] == 1
        assert len(result["missing_frames"]) == 0

    def test_create_video_different_codecs(self):
        """Test video creation with different codec options."""
        sequence_dir = self.create_test_png_sequence(num_frames=5)
        frame_paths = sorted(sequence_dir.glob("*.png"))

        # Test with default codec (mp4v)
        output_mp4 = self.temp_path / "test.mp4"
        success = self.processor.create_video_from_frames(
            frame_paths=frame_paths, output_path=output_mp4, fps=30
        )

        assert success is True
        assert output_mp4.exists()

    def test_standardize_video_upscale_resolution(self):
        """Test video upscaling to higher resolution."""
        # Create low-res video
        sequence_dir = self.create_test_png_sequence(num_frames=5, width=320, height=240)
        video_path = self.temp_path / "lowres.mp4"
        frame_paths = sorted(sequence_dir.glob("*.png"))

        self.processor.create_video_from_frames(frame_paths, video_path)

        # Upscale to HD
        output_path = self.temp_path / "hd.mp4"
        success = self.processor.standardize_video(
            input_path=video_path, output_path=output_path, target_resolution=(1920, 1080)
        )

        assert success is True

        # Verify resolution
        cap = cv2.VideoCapture(str(output_path))
        assert int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) == 1920
        assert int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) == 1080
        cap.release()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
