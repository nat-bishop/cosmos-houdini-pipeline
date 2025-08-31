#!/usr/bin/env python3
"""
Test suite for the convert-sequence CLI command.

Tests PNG sequence validation, video conversion, metadata generation,
and error handling for the CLI interface.
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import cv2
import numpy as np
import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.cli import convert_png_sequence
from cosmos_workflow.local_ai.video_metadata import VideoMetadata


class TestConvertSequenceCommand:
    """Test the convert-sequence CLI command."""

    @pytest.fixture
    def mock_video_processor(self):
        """Create mock VideoProcessor."""
        with patch("cosmos_workflow.local_ai.video_metadata.VideoProcessor") as mock:
            processor = Mock()
            mock.return_value = processor
            processor.standard_resolutions = {
                "720p": (1280, 720),
                "1080p": (1920, 1080),
                "4k": (3840, 2160),
            }
            yield processor

    @pytest.fixture
    def mock_metadata_extractor(self):
        """Create mock VideoMetadataExtractor."""
        with patch("cosmos_workflow.local_ai.video_metadata.VideoMetadataExtractor") as mock:
            extractor = Mock()
            mock.return_value = extractor

            # Create sample metadata
            metadata = VideoMetadata(
                file_path="test_video.mp4",
                duration=10.0,
                fps=24.0,
                frame_count=240,
                width=1920,
                height=1080,
                codec="h264",
                file_size=1024000,
                hash="abc123",
                middle_frame_stats={"brightness": 128},
                ai_tags=["outdoor", "landscape"],
                ai_caption="A scenic outdoor landscape",
                detected_objects=[{"label": "tree", "confidence": 0.95}],
            )
            extractor.extract_metadata.return_value = metadata
            yield extractor

    @pytest.fixture
    def temp_png_dir(self):
        """Create temporary directory with PNG files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create dummy PNG files
            for i in range(10):
                png_path = tmpdir_path / f"frame_{i:03d}.png"
                # Create a small dummy image
                img = np.zeros((100, 100, 3), dtype=np.uint8)
                cv2.imwrite(str(png_path), img)

            yield tmpdir_path

    def test_convert_sequence_success(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir, capsys
    ):
        """Test successful PNG sequence conversion."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": "frame_{:03d}.png",
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = True

        # Run command
        with patch("sys.exit"):
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=24,
                resolution=None,
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

        # Verify calls
        mock_video_processor.validate_sequence.assert_called_once()
        mock_video_processor.create_video_from_frames.assert_called_once()

        # Check output
        captured = capsys.readouterr()
        assert "Valid sequence found: 10 frames" in captured.out
        assert "Video created successfully" in captured.out

    def test_convert_sequence_with_metadata(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir, capsys
    ):
        """Test conversion with metadata generation."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": "frame_{:03d}.png",
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = True

        # Run command with metadata
        with patch("sys.exit"):
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=24,
                resolution=None,
                generate_metadata=True,
                ai_analysis=True,
                verbose=True,
            )

        # Verify metadata extraction was called
        mock_metadata_extractor.extract_metadata.assert_called_once()
        mock_metadata_extractor.save_metadata.assert_called_once()

        # Check verbose output
        captured = capsys.readouterr()
        assert "Generating metadata" in captured.out
        assert "AI Caption: A scenic outdoor landscape" in captured.out
        assert "AI Tags: outdoor, landscape" in captured.out

    def test_convert_sequence_with_resolution(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir
    ):
        """Test conversion with resolution standardization."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": None,
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = True
        mock_video_processor.standardize_video.return_value = True

        # Test with preset resolution
        with patch("sys.exit"):
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=30,
                resolution="1080p",
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

        # Verify standardize was called with correct params
        mock_video_processor.standardize_video.assert_called_once()
        call_args = mock_video_processor.standardize_video.call_args
        assert call_args.kwargs["target_fps"] == 30
        # Check that target_resolution is passed as a tuple
        assert call_args.kwargs["target_resolution"] == (1920, 1080)

    def test_convert_sequence_custom_resolution(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir
    ):
        """Test conversion with custom WxH resolution."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": None,
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = True
        mock_video_processor.standardize_video.return_value = True

        # Test with custom resolution
        with patch("sys.exit"):
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=24,
                resolution="2560x1440",
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

        # Verify standardize was called with custom resolution as tuple
        call_args = mock_video_processor.standardize_video.call_args
        assert call_args.kwargs["target_resolution"] == (2560, 1440)

    def test_convert_sequence_invalid_directory(
        self, mock_video_processor, mock_metadata_extractor, capsys
    ):
        """Test error handling for invalid directory."""
        with patch("sys.exit") as mock_exit:
            convert_png_sequence(
                input_dir="/nonexistent/directory",
                output_path=None,
                fps=24,
                resolution=None,
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

            # Verify exit was called
            mock_exit.assert_called_with(1)

            # Check error message
            captured = capsys.readouterr()
            assert "[ERROR] Input directory does not exist" in captured.out

    def test_convert_sequence_validation_failure(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir, capsys
    ):
        """Test handling of validation failures."""
        # Setup mock to return validation failure
        mock_video_processor.validate_sequence.return_value = {
            "valid": False,
            "frame_count": 5,
            "missing_frames": [3, 4, 7],
            "pattern": None,
            "issues": ["Missing frames detected", "Invalid PNG file: frame_003.png"],
        }

        with patch("sys.exit") as mock_exit:
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=24,
                resolution=None,
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

            # Verify exit was called
            mock_exit.assert_called_with(1)

            # Check error messages
            captured = capsys.readouterr()
            assert "[ERROR] Invalid PNG sequence" in captured.out
            assert "Missing frames detected" in captured.out
            assert "Invalid PNG file: frame_003.png" in captured.out
            assert "Missing frames: [3, 4, 7]" in captured.out

    def test_convert_sequence_video_creation_failure(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir, capsys
    ):
        """Test handling of video creation failure."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": None,
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = False  # Simulate failure

        with patch("sys.exit") as mock_exit:
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=24,
                resolution=None,
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

            # Verify exit was called
            mock_exit.assert_called_with(1)

            # Check error message
            captured = capsys.readouterr()
            assert "[ERROR] Failed to create video" in captured.out

    def test_convert_sequence_custom_output_path(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir
    ):
        """Test conversion with custom output path."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": None,
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = True

        custom_output = "/custom/path/output.mp4"

        with patch("sys.exit"):
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=custom_output,
                fps=24,
                resolution=None,
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

        # Verify video was created with custom path (normalize for platform)
        call_args = mock_video_processor.create_video_from_frames.call_args
        from pathlib import Path

        assert Path(call_args.kwargs["output_path"]) == Path(custom_output)

    def test_convert_sequence_invalid_resolution_format(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir, capsys
    ):
        """Test error handling for invalid resolution format."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": None,
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = True

        with patch("sys.exit") as mock_exit:
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=24,
                resolution="invalid_format",
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

            # Verify exit was called
            mock_exit.assert_called_with(1)

            # Check error message
            captured = capsys.readouterr()
            assert "[ERROR] Invalid resolution format" in captured.out
            assert "Use 720p, 1080p, 4k, or WxH format" in captured.out

    def test_convert_sequence_standardization_failure(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir, capsys
    ):
        """Test handling of standardization failure."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": None,
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = True
        mock_video_processor.standardize_video.return_value = False  # Simulate failure

        with patch("sys.exit"):
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=24,
                resolution="1080p",
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

        # Check warning message
        captured = capsys.readouterr()
        assert "[WARNING] Standardization failed, using original video" in captured.out

    def test_convert_sequence_exception_handling(
        self, mock_video_processor, mock_metadata_extractor, capsys
    ):
        """Test exception handling with verbose output."""
        # Make validate_sequence raise an exception
        mock_video_processor.validate_sequence.side_effect = Exception("Test exception")

        with patch("sys.exit") as mock_exit, patch("traceback.print_exc") as mock_traceback:
            convert_png_sequence(
                input_dir="/some/dir",
                output_path=None,
                fps=24,
                resolution=None,
                generate_metadata=False,
                ai_analysis=False,
                verbose=True,  # Enable verbose for traceback
            )

            # Verify exit and traceback
            mock_exit.assert_called_with(1)
            mock_traceback.assert_called_once()

            # Check error message
            captured = capsys.readouterr()
            assert "[ERROR] PNG sequence conversion failed: Test exception" in captured.out

    def test_convert_sequence_no_unicode_emojis(
        self, mock_video_processor, mock_metadata_extractor, temp_png_dir, capsys
    ):
        """Test that output doesn't contain Unicode emojis (Windows compatibility)."""
        # Setup mocks
        mock_video_processor.validate_sequence.return_value = {
            "valid": True,
            "frame_count": 10,
            "missing_frames": [],
            "pattern": "frame_{:03d}.png",
            "issues": [],
        }
        mock_video_processor.create_video_from_frames.return_value = True

        # Run command
        with patch("sys.exit"):
            convert_png_sequence(
                input_dir=str(temp_png_dir),
                output_path=None,
                fps=24,
                resolution=None,
                generate_metadata=False,
                ai_analysis=False,
                verbose=False,
            )

        # Check output doesn't contain emojis
        captured = capsys.readouterr()
        # Common emojis that might cause issues
        emojis = ["🔍", "✅", "🎬", "📐", "📊", "📋", "✨", "💡", "⚠️", "❌"]
        for emoji in emojis:
            assert emoji not in captured.out, f"Found emoji {emoji} in output"

        # Check that status messages are present with text labels
        assert "[INFO]" in captured.out or "[SUCCESS]" in captured.out


class TestCLIIntegration:
    """Test CLI command line integration."""

    def test_cli_convert_sequence_help(self):
        """Test convert-sequence help message."""
        with patch("sys.argv", ["cli.py", "convert-sequence", "--help"]):
            with pytest.raises(SystemExit) as exc_info:
                from cosmos_workflow.cli import main

                main()

            # Help should exit with 0
            assert exc_info.value.code == 0

    def test_cli_convert_sequence_parsing(self):
        """Test argument parsing for convert-sequence."""
        test_args = [
            "cli.py",
            "convert-sequence",
            "./input_dir",
            "--output",
            "./output.mp4",
            "--fps",
            "30",
            "--resolution",
            "1080p",
            "--generate-metadata",
            "--ai-analysis",
            "--verbose",
        ]

        with patch("sys.argv", test_args):
            with patch("cosmos_workflow.cli.convert_png_sequence") as mock_convert:
                with patch("sys.exit"):
                    from cosmos_workflow.cli import main

                    main()

                    # Verify function was called with correct arguments
                    mock_convert.assert_called_once_with(
                        input_dir="./input_dir",
                        output_path="./output.mp4",
                        fps=30,
                        resolution="1080p",
                        generate_metadata=True,
                        ai_analysis=True,
                        verbose=True,
                    )

    def test_cli_convert_sequence_minimal_args(self):
        """Test convert-sequence with minimal arguments."""
        test_args = ["cli.py", "convert-sequence", "./input_dir"]

        with patch("sys.argv", test_args):
            with patch("cosmos_workflow.cli.convert_png_sequence") as mock_convert:
                with patch("sys.exit"):
                    from cosmos_workflow.cli import main

                    main()

                    # Verify defaults were used
                    mock_convert.assert_called_once_with(
                        input_dir="./input_dir",
                        output_path=None,
                        fps=24,  # Default
                        resolution=None,
                        generate_metadata=True,  # Default is True now
                        ai_analysis=False,
                        verbose=False,
                    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
