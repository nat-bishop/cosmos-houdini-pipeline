"""Autocomplete functions for CLI commands."""

from pathlib import Path


def complete_prompt_specs(_ctx, _param, incomplete):
    """Autocomplete for PromptSpec JSON files."""
    prompts_dir = Path("inputs/prompts")
    if not prompts_dir.exists():
        return []

    # Match files starting with incomplete text
    results = []
    for json_file in prompts_dir.rglob("*.json"):
        if json_file.is_file():
            relative_path = str(json_file)
            if not incomplete or relative_path.startswith(incomplete):
                results.append(relative_path)
    return sorted(results)


def complete_video_files(_ctx, _param, incomplete):
    """Autocomplete for video files in inputs/videos."""
    videos_dir = Path("inputs/videos")
    if not videos_dir.exists():
        return []

    results = []
    for video in videos_dir.rglob("color.mp4"):
        relative_path = str(video)
        if not incomplete or relative_path.startswith(incomplete):
            results.append(relative_path)
    return sorted(results)


def complete_video_dirs(_ctx, _param, incomplete):
    """Autocomplete for video directories."""
    videos_dir = Path("inputs/videos")
    if not videos_dir.exists():
        return []

    results = []
    for subdir in videos_dir.iterdir():
        if subdir.is_dir():
            dir_path = str(subdir)
            if not incomplete or dir_path.startswith(incomplete):
                results.append(dir_path)
    return sorted(results)


def complete_directories(_ctx, _param, incomplete):
    """Autocomplete for any directory."""
    if incomplete:
        base_path = Path(incomplete)
        parent = base_path.parent if base_path.parent != base_path else Path(".")
        prefix = base_path.name
    else:
        parent = Path(".")
        prefix = ""

    if not parent.exists():
        return []

    results = []
    for item in parent.iterdir():
        if item.is_dir():
            dir_path = str(item)
            if not prefix or item.name.startswith(prefix):
                results.append(dir_path + "/")
    return sorted(results)
