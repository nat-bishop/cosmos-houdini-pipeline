"""Tests for video utility functions including thumbnail generation."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from cosmos_workflow.ui.utils.video import (
    extract_video_metadata,
    generate_thumbnail_fast,
    get_multimodal_inputs,
    get_video_duration_seconds,
    get_video_files,
    validate_video_directory,
)


class TestGenerateThumbnailFast:
    """Test the generate_thumbnail_fast function with production standards."""

    @patch("cosmos_workflow.ui.utils.video.subprocess.run")
    def test_generate_thumbnail(self, mock_run):
        """Test thumbnail generation storing in same directory as video."""
        # Setup
        mock_run.return_value = Mock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock video file
            video_path = Path(tmpdir) / "output.mp4"
            video_path.touch()

            # Expected thumbnail path (same directory as video)
            expected_thumb = video_path.parent / "output.thumb.jpg"

            # Call the function (thumbnail doesn't exist yet)
            result = generate_thumbnail_fast(str(video_path))

            # Verify ffmpeg was called with correct parameters
            mock_run.assert_called_once()
            ffmpeg_args = mock_run.call_args[0][0]
            assert ffmpeg_args[0] == "ffmpeg"
            assert "-i" in ffmpeg_args
            assert str(video_path) in ffmpeg_args
            assert str(expected_thumb) in ffmpeg_args
            assert "-vf" in ffmpeg_args
            assert "scale=384:216" in ffmpeg_args

            # Function returns None since we didn't create the thumbnail file
            assert result is None

    def test_generate_thumbnail_video_not_exists(self):
        """Test that None is returned when video doesn't exist."""
        result = generate_thumbnail_fast("/nonexistent/video.mp4")
        assert result is None

    @patch("cosmos_workflow.ui.utils.video.subprocess.run")
    def test_generate_thumbnail_already_exists(self, mock_run):
        """Test that existing thumbnail is returned without regeneration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "output.mp4"
            video_path.touch()

            # Create existing thumbnail
            thumb_path = Path(tmpdir) / "output.thumb.jpg"
            thumb_path.touch()

            # Call the function
            result = generate_thumbnail_fast(str(video_path))

            # Should return existing thumbnail without calling ffmpeg
            assert result == str(thumb_path)
            mock_run.assert_not_called()

    @patch("cosmos_workflow.ui.utils.video.subprocess.run")
    def test_generate_thumbnail_ffmpeg_failure(self, mock_run):
        """Test handling of ffmpeg failure."""
        mock_run.return_value = Mock(returncode=1)  # Non-zero return code

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "output.mp4"
            video_path.touch()

            result = generate_thumbnail_fast(str(video_path))

            # Should return None on ffmpeg failure
            assert result is None

    @patch("cosmos_workflow.ui.utils.video.subprocess.run")
    def test_generate_thumbnail_timeout(self, mock_run):
        """Test handling of ffmpeg timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 5)

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "output.mp4"
            video_path.touch()

            result = generate_thumbnail_fast(str(video_path))

            # Should return None on timeout
            assert result is None


class TestExtractVideoMetadata:
    """Test video metadata extraction."""

    @patch.dict("sys.modules", {"cv2": MagicMock()})
    def test_extract_metadata_with_cv2(self):
        """Test metadata extraction using OpenCV."""
        # Get the mocked cv2 module
        import sys

        mock_cv2 = sys.modules["cv2"]

        # Setup mock video capture
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True

        # Mock the cv2 constants
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5
        mock_cv2.CAP_PROP_FRAME_COUNT = 7
        mock_cv2.CAP_PROP_FOURCC = 6

        mock_cap.get.side_effect = lambda prop: {
            3: 1920,  # WIDTH
            4: 1080,  # HEIGHT
            5: 24,  # FPS
            7: 120,  # FRAME_COUNT
            6: 1234,  # FOURCC
        }.get(prop, 0)
        mock_cv2.VideoCapture.return_value = mock_cap

        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "test.mp4"
            video_path.touch()

            metadata = extract_video_metadata(video_path)

            assert metadata["resolution"] == "1920x1080"
            assert "120 frames" in metadata["duration"]
            assert metadata["fps"] == "24"
            assert metadata["frame_count"] == "120"

            mock_cap.release.assert_called_once()

    def test_extract_metadata_file_not_exists(self):
        """Test metadata extraction for non-existent file."""
        metadata = extract_video_metadata(Path("/nonexistent/video.mp4"))

        assert metadata["resolution"] == "Unknown"
        assert metadata["duration"] == "Unknown"
        assert metadata["fps"] == "Unknown"
        assert metadata["codec"] == "Unknown"
        assert metadata["frame_count"] == "0"


class TestVideoDirectoryValidation:
    """Test video directory validation functions."""

    def test_validate_video_directory_valid(self):
        """Test validation of a valid video directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)
            # Create required color.mp4 file
            (dir_path / "color.mp4").touch()

            is_valid, message = validate_video_directory(tmpdir)

            assert is_valid is True
            assert message == "Valid video directory"

    def test_validate_video_directory_missing_color(self):
        """Test validation when color.mp4 is missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, message = validate_video_directory(tmpdir)

            assert is_valid is False
            assert "Missing required file: color.mp4" in message

    def test_validate_video_directory_not_exists(self):
        """Test validation for non-existent directory."""
        is_valid, message = validate_video_directory("/nonexistent/dir")

        assert is_valid is False
        assert "Directory does not exist" in message

    def test_validate_video_directory_not_dir(self):
        """Test validation when path is not a directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            is_valid, message = validate_video_directory(tmpfile.name)

            assert is_valid is False
            assert "Path is not a directory" in message


class TestGetMultimodalInputs:
    """Test multimodal input file discovery."""

    def test_get_multimodal_inputs_all_present(self):
        """Test when all expected multimodal files are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create all expected files
            expected_files = ["color.mp4", "depth.mp4", "segmentation.mp4", "canny.mp4"]
            for filename in expected_files:
                (dir_path / filename).touch()

            inputs = get_multimodal_inputs(dir_path)

            assert set(inputs) == set(expected_files)
            assert len(inputs) == 4

    def test_get_multimodal_inputs_partial(self):
        """Test when only some multimodal files are present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create only some files
            (dir_path / "color.mp4").touch()
            (dir_path / "depth.mp4").touch()

            inputs = get_multimodal_inputs(dir_path)

            assert set(inputs) == {"color.mp4", "depth.mp4"}
            assert len(inputs) == 2

    def test_get_multimodal_inputs_empty_dir(self):
        """Test with empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            inputs = get_multimodal_inputs(Path(tmpdir))
            assert inputs == []

    def test_get_multimodal_inputs_nonexistent_dir(self):
        """Test with non-existent directory."""
        inputs = get_multimodal_inputs(Path("/nonexistent"))
        assert inputs == []


class TestGetVideoFiles:
    """Test video file discovery."""

    def test_get_video_files_various_formats(self):
        """Test finding video files of various formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            # Create video files with different extensions
            video_files = [
                "video1.mp4",
                "video2.avi",
                "video3.MOV",  # Test uppercase
                "video4.mkv",
                "not_video.txt",  # Should be ignored
            ]

            for filename in video_files:
                (dir_path / filename).touch()

            found_videos = get_video_files(dir_path)
            found_names = [f.name for f in found_videos]

            assert "video1.mp4" in found_names
            assert "video2.avi" in found_names
            assert "video3.MOV" in found_names
            assert "video4.mkv" in found_names
            assert "not_video.txt" not in found_names

    def test_get_video_files_custom_extensions(self):
        """Test with custom extension list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dir_path = Path(tmpdir)

            (dir_path / "video.mp4").touch()
            (dir_path / "video.avi").touch()
            (dir_path / "video.webm").touch()

            # Only look for .mp4 files
            found_videos = get_video_files(dir_path, extensions=[".mp4"])

            assert len(found_videos) == 1
            assert found_videos[0].name == "video.mp4"


class TestGetVideoDurationSeconds:
    """Test video duration extraction."""

    @patch("cosmos_workflow.ui.utils.video.extract_video_metadata")
    def test_get_duration_from_metadata_string(self, mock_extract):
        """Test parsing duration from metadata string."""
        mock_extract.return_value = {
            "duration": "120 frames (5.0s @ 24fps)",
            "frame_count": "120",
            "fps": "24",
        }

        duration = get_video_duration_seconds(Path("test.mp4"))
        assert duration == 5.0

    @patch("cosmos_workflow.ui.utils.video.extract_video_metadata")
    def test_get_duration_from_frame_count(self, mock_extract):
        """Test calculating duration from frame count and fps."""
        mock_extract.return_value = {"duration": "Unknown", "frame_count": "240", "fps": "30"}

        duration = get_video_duration_seconds(Path("test.mp4"))
        assert duration == 8.0  # 240 frames / 30 fps

    @patch("cosmos_workflow.ui.utils.video.extract_video_metadata")
    def test_get_duration_unknown(self, mock_extract):
        """Test when duration cannot be determined."""
        mock_extract.return_value = {"duration": "Unknown", "frame_count": "0", "fps": "0"}

        duration = get_video_duration_seconds(Path("test.mp4"))
        assert duration is None
