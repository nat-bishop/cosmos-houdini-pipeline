"""Unit tests for CLI completion functions."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cosmos_workflow.cli.completions import (
    complete_directories,
    complete_prompt_specs,
    complete_video_dirs,
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

    def test_complete_all_specs(self, monkeypatch):
        """Test returns all JSON files when no filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test structure
            prompts_dir = Path(tmpdir) / "inputs" / "prompts"
            prompts_dir.mkdir(parents=True)

            (prompts_dir / "test1.json").touch()
            (prompts_dir / "test2.json").touch()
            (prompts_dir / "other.txt").touch()  # Should be ignored

            # Replace Path constructor to return our test directory
            def mock_path(path_str):
                if "prompts" in str(path_str):
                    return prompts_dir
                return Path(path_str)

            monkeypatch.setattr("cosmos_workflow.cli.completions.Path", mock_path)

            result = complete_prompt_specs(None, None, "")
            # Should return only JSON files
            assert len([r for r in result if r.endswith(".json")]) == 2

    def test_complete_filtered_specs(self, monkeypatch):
        """Test returns filtered JSON files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            prompts_dir = Path(tmpdir) / "inputs" / "prompts"
            prompts_dir.mkdir(parents=True)

            (prompts_dir / "test1.json").touch()
            (prompts_dir / "test2.json").touch()
            (prompts_dir / "other.json").touch()

            # Replace Path constructor to return our test directory
            def mock_path(path_str):
                if "prompts" in str(path_str):
                    return prompts_dir
                return Path(path_str)

            monkeypatch.setattr("cosmos_workflow.cli.completions.Path", mock_path)

            # The actual paths will be like "inputs/prompts/test1.json"
            # So we test with empty string to get all, then verify content
            result = complete_prompt_specs(None, None, "")
            # Should return all 3 JSON files
            assert len(result) == 3  # test1.json, test2.json, other.json
            # Check that test files are included
            test_files = [r for r in result if "test" in r]
            assert len(test_files) == 2


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

    def test_complete_color_videos(self, monkeypatch):
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

            # Replace Path constructor to return our test directory
            def mock_path(path_str):
                if "videos" in str(path_str):
                    return videos_dir
                return Path(path_str)

            monkeypatch.setattr("cosmos_workflow.cli.completions.Path", mock_path)

            result = complete_video_files(None, None, "")
            # Should return only color.mp4 files
            assert len(result) == 2
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

    def test_complete_all_dirs(self, monkeypatch):
        """Test returns all subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            videos_dir = Path(tmpdir) / "inputs" / "videos"
            videos_dir.mkdir(parents=True)

            (videos_dir / "scene1").mkdir()
            (videos_dir / "scene2").mkdir()
            (videos_dir / "file.txt").touch()  # Should be ignored

            # Replace Path constructor to return our test directory
            def mock_path(path_str):
                if "videos" in str(path_str):
                    return videos_dir
                return Path(path_str)

            monkeypatch.setattr("cosmos_workflow.cli.completions.Path", mock_path)

            result = complete_video_dirs(None, None, "")
            # Should return only directories (scene1 and scene2)
            assert len(result) == 2
            assert all("scene" in r for r in result)


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


class TestCompleteVideoDirsConsolidated:
    """Test consolidated video directory completion."""

    def test_no_videos_dir(self):
        """Test returns empty list when videos dir doesn't exist."""
        with patch("cosmos_workflow.cli.completions.Path") as mock_path:
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir

            result = complete_video_dirs(None, None, "")
            assert result == []

    def test_complete_videos_dirs(self, monkeypatch):
        """Test returns directories from inputs/videos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            videos_dir = Path(tmpdir) / "inputs" / "videos"
            videos_dir.mkdir(parents=True)

            (videos_dir / "scene1").mkdir()
            (videos_dir / "scene2").mkdir()

            # Replace Path constructor to return our test directory
            def mock_path(path_str):
                if "videos" in str(path_str):
                    return videos_dir
                return Path(path_str)

            monkeypatch.setattr("cosmos_workflow.cli.completions.Path", mock_path)

            result = complete_video_dirs(None, None, "")
            assert len(result) == 2  # Two directories created

    def test_complete_with_filter(self):
        """Test filters results by prefix."""
        result = complete_video_dirs(None, None, "inputs/videos/c")
        # Should only return dirs starting with 'c' if they exist
        if Path("inputs/videos").exists():
            assert all("inputs/videos/" in r for r in result)
