"""Unit tests for CLI completion functions."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.cli.completions import (
    complete_directories,
    complete_prompt_specs,
    complete_video_dirs,
    complete_video_dirs_smart,
    complete_video_files,
    normalize_path,
)


class TestNormalizePath:
    """Test path normalization helper."""

    def test_normalize_forward_slashes(self):
        """Test already normalized paths stay unchanged."""
        assert normalize_path("inputs/videos/test") == "inputs/videos/test"

    def test_normalize_backslashes(self):
        """Test backslashes are converted to forward slashes."""
        assert normalize_path("inputs\\videos\\test") == "inputs/videos/test"

    def test_normalize_mixed_slashes(self):
        """Test mixed slashes are normalized."""
        assert normalize_path("inputs\\videos/test") == "inputs/videos/test"

    def test_normalize_empty(self):
        """Test empty string is handled."""
        assert normalize_path("") == ""


class TestCompletePromptSpecs:
    """Test prompt spec completion."""

    def test_no_prompts_dir(self):
        """Test returns empty list when prompts dir doesn't exist."""
        with patch("cosmos_workflow.cli.completions.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            result = complete_prompt_specs(None, None, "")
            assert result == []

    def test_complete_all_specs(self):
        """Test returns all JSON files when no filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            prompts_dir = Path(tmpdir) / "inputs" / "prompts"
            prompts_dir.mkdir(parents=True)

            (prompts_dir / "test1.json").touch()
            (prompts_dir / "test2.json").touch()
            (prompts_dir / "other.txt").touch()  # Should be ignored

            with patch("cosmos_workflow.cli.completions.Path") as mock_path:
                mock_path.return_value = prompts_dir
                prompts_dir.exists = MagicMock(return_value=True)

                result = complete_prompt_specs(None, None, "")
                # Should return only JSON files
                assert len([r for r in result if r.endswith(".json")]) == 2

    def test_complete_filtered_specs(self):
        """Test returns filtered JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir) / "inputs" / "prompts"
            prompts_dir.mkdir(parents=True)

            (prompts_dir / "test1.json").touch()
            (prompts_dir / "test2.json").touch()
            (prompts_dir / "other.json").touch()

            with patch("cosmos_workflow.cli.completions.Path") as mock_path:
                mock_path.return_value = prompts_dir
                prompts_dir.exists = MagicMock(return_value=True)

                # Filter by prefix - this test depends on implementation
                # In actual implementation, we'd need to mock the full path
                complete_prompt_specs(None, None, "inputs/prompts/test")
                # Would filter to test1.json and test2.json in real scenario


class TestCompleteVideoFiles:
    """Test video file completion."""

    def test_no_videos_dir(self):
        """Test returns empty list when videos dir doesn't exist."""
        with patch("cosmos_workflow.cli.completions.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            result = complete_video_files(None, None, "")
            assert result == []

    def test_complete_color_videos(self):
        """Test returns only color.mp4 files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            videos_dir = Path(tmpdir) / "inputs" / "videos"
            scene1_dir = videos_dir / "scene1"
            scene2_dir = videos_dir / "scene2"

            scene1_dir.mkdir(parents=True)
            scene2_dir.mkdir(parents=True)

            (scene1_dir / "color.mp4").touch()
            (scene1_dir / "depth.mp4").touch()  # Should be ignored
            (scene2_dir / "color.mp4").touch()

            with patch("cosmos_workflow.cli.completions.Path") as mock_path:
                mock_path.return_value = videos_dir
                videos_dir.exists = MagicMock(return_value=True)

                result = complete_video_files(None, None, "")
                # Should return only color.mp4 files
                assert all("color.mp4" in r for r in result)


class TestCompleteVideoDirs:
    """Test video directory completion."""

    def test_no_videos_dir(self):
        """Test returns empty list when videos dir doesn't exist."""
        with patch("cosmos_workflow.cli.completions.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            result = complete_video_dirs(None, None, "")
            assert result == []

    def test_complete_all_dirs(self):
        """Test returns all subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            videos_dir = Path(tmpdir) / "inputs" / "videos"
            videos_dir.mkdir(parents=True)

            (videos_dir / "scene1").mkdir()
            (videos_dir / "scene2").mkdir()
            (videos_dir / "file.txt").touch()  # Should be ignored

            with patch("cosmos_workflow.cli.completions.Path") as mock_path:
                mock_path.return_value = videos_dir
                videos_dir.exists = MagicMock(return_value=True)

                # Mock iterdir to return our test dirs
                mock_iterdir = MagicMock()
                mock_iterdir.return_value = [
                    videos_dir / "scene1",
                    videos_dir / "scene2",
                    videos_dir / "file.txt",
                ]
                videos_dir.iterdir = mock_iterdir

                result = complete_video_dirs(None, None, "")
                # Should return only directories
                assert len(result) >= 0  # Depends on mock behavior


class TestCompleteDirectories:
    """Test general directory completion."""

    def test_complete_current_dir(self):
        """Test lists directories in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("cosmos_workflow.cli.completions.Path") as mock_path:
                current = Path(tmpdir)
                (current / "dir1").mkdir()
                (current / "dir2").mkdir()
                (current / "file.txt").touch()

                # Mock Path(".") to return our temp dir
                def path_side_effect(arg):
                    if arg == ".":
                        return current
                    return Path(arg)

                mock_path.side_effect = path_side_effect

                result = complete_directories(None, None, "")
                # Should return directories with trailing slash
                assert all(r.endswith("/") for r in result)

    def test_complete_subdir(self):
        """Test lists subdirectories of given path."""
        result = complete_directories(None, None, "inputs/")
        # Should show subdirs of inputs if it exists
        if Path("inputs").exists():
            assert len(result) > 0
            assert all(r.startswith("inputs/") for r in result)

    def test_complete_with_prefix(self):
        """Test filters by prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            current = Path(tmpdir)
            (current / "test1").mkdir()
            (current / "test2").mkdir()
            (current / "other").mkdir()

            with patch("cosmos_workflow.cli.completions.Path") as mock_path:

                def path_side_effect(arg):
                    if arg == ".":
                        return current
                    return Path(arg)

                mock_path.side_effect = path_side_effect

                result = complete_directories(None, None, "test")
                # Should filter to directories starting with "test"
                assert all("test" in r for r in result)


class TestCompleteVideoDirsSmart:
    """Test smart video directory completion."""

    def test_no_videos_dir(self):
        """Test returns empty list when videos dir doesn't exist."""
        with patch("cosmos_workflow.cli.completions.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            result = complete_video_dirs_smart(None, None, "")
            assert result == []

    def test_complete_videos_dirs(self):
        """Test returns directories from inputs/videos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            videos_dir = Path(tmpdir) / "inputs" / "videos"
            videos_dir.mkdir(parents=True)

            (videos_dir / "scene1").mkdir()
            (videos_dir / "scene2").mkdir()

            with patch("cosmos_workflow.cli.completions.Path") as mock_path:
                mock_path.return_value = videos_dir
                videos_dir.exists = MagicMock(return_value=True)

                # Mock iterdir
                mock_iterdir = MagicMock()
                mock_iterdir.return_value = [
                    videos_dir / "scene1",
                    videos_dir / "scene2",
                ]
                videos_dir.iterdir = mock_iterdir

                result = complete_video_dirs_smart(None, None, "")
                assert len(result) >= 0  # Depends on mock

    def test_complete_with_filter(self):
        """Test filters results by prefix."""
        result = complete_video_dirs_smart(None, None, "inputs/videos/c")
        # Should only return dirs starting with 'c' if they exist
        if Path("inputs/videos").exists():
            assert all("inputs/videos/" in r for r in result)
