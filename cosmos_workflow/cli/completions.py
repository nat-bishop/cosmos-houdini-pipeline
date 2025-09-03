"""Autocomplete functions for CLI commands."""

from pathlib import Path


def normalize_path(path_str):
    """Normalize path to use forward slashes consistently."""
    return str(path_str).replace("\\", "/")


def complete_prompt_specs(_ctx, _param, incomplete):
    """Autocomplete for PromptSpec JSON files."""
    prompts_dir = Path("inputs/prompts")
    if not prompts_dir.exists():
        return []

    # Normalize incomplete path for comparison
    incomplete_norm = normalize_path(incomplete) if incomplete else ""

    # Match files starting with incomplete text
    results = []
    for json_file in prompts_dir.rglob("*.json"):
        if json_file.is_file():
            relative_path = normalize_path(json_file)
            if not incomplete_norm or relative_path.startswith(incomplete_norm):
                results.append(relative_path)
    return sorted(results)


def complete_video_files(_ctx, _param, incomplete):
    """Autocomplete for video files in inputs/videos."""
    videos_dir = Path("inputs/videos")
    if not videos_dir.exists():
        return []

    # Normalize incomplete path for comparison
    incomplete_norm = normalize_path(incomplete) if incomplete else ""

    results = []
    for video in videos_dir.rglob("color.mp4"):
        relative_path = normalize_path(video)
        if not incomplete_norm or relative_path.startswith(incomplete_norm):
            results.append(relative_path)
    return sorted(results)


def complete_video_dirs(_ctx, _param, incomplete):
    """Autocomplete for video directories."""
    videos_dir = Path("inputs/videos")
    if not videos_dir.exists():
        return []

    # Normalize incomplete path for comparison
    incomplete_norm = normalize_path(incomplete) if incomplete else ""

    results = []
    for subdir in videos_dir.iterdir():
        if subdir.is_dir():
            dir_path = normalize_path(subdir)
            if not incomplete_norm or dir_path.startswith(incomplete_norm):
                results.append(dir_path)
    return sorted(results)


def complete_directories(_ctx, _param, incomplete):
    """Autocomplete for any directory."""
    incomplete_norm = normalize_path(incomplete) if incomplete else ""

    if incomplete_norm and incomplete_norm.endswith("/"):
        # If ends with slash, list subdirs of that directory
        parent = Path(incomplete_norm[:-1])
        prefix = ""
    elif incomplete_norm and "/" in incomplete_norm:
        # Has a path separator, split into parent and prefix
        parent = Path(incomplete_norm).parent
        prefix = Path(incomplete_norm).name
    else:
        # No path separator, list current directory
        parent = Path(".")
        prefix = incomplete_norm

    if not parent.exists():
        return []

    results = []
    for item in parent.iterdir():
        if item.is_dir():
            dir_name = item.name
            if not prefix or dir_name.startswith(prefix):
                # Build the full path
                if parent == Path("."):
                    dir_path = normalize_path(item)
                else:
                    dir_path = normalize_path(parent / dir_name)
                results.append(dir_path + "/")
    return sorted(results)


def complete_video_dirs_smart(_ctx, _param, incomplete):
    """Autocomplete for video directories in inputs/videos/."""
    videos_dir = Path("inputs/videos")
    if not videos_dir.exists():
        return []

    # Normalize incomplete path for comparison
    incomplete_norm = normalize_path(incomplete) if incomplete else ""

    results = []
    for subdir in videos_dir.iterdir():
        if subdir.is_dir():
            dir_path = normalize_path(subdir)
            if not incomplete_norm or dir_path.startswith(incomplete_norm):
                results.append(dir_path)

    return sorted(results)
