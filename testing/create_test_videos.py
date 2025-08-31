#!/usr/bin/env python3
"""Create test videos at various resolutions for vocab error testing."""

import subprocess
import sys
from pathlib import Path


def create_test_video(output_path: Path, width: int, height: int, duration: int = 5, fps: int = 24):
    """Create a test video with specific resolution using ffmpeg.

    Args:
        output_path: Output video file path
        width: Video width in pixels
        height: Video height in pixels
        duration: Video duration in seconds
        fps: Frame rate
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Create a test pattern video with text overlay showing resolution
    filter_complex = (
        f"testsrc2=size={width}x{height}:rate={fps}:duration={duration},"
        f"drawtext=text='{width}x{height}':fontsize=48:fontcolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:box=1:boxborderw=5:boxcolor=black@0.5"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        filter_complex,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        str(output_path),
    ]

    print(f"Creating {width}x{height} test video: {output_path.name}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        print(f"ERROR creating {output_path.name}: {result.stderr}")
        return False

    return True


def main():
    """Create test videos at various resolutions."""
    # Define test resolutions
    resolutions = [
        ("360p", 640, 360),
        ("480p", 854, 480),
        ("540p", 960, 540),
        ("600p", 1067, 600),
        ("720p", 1280, 720),
        ("900p", 1600, 900),
        ("1080p", 1920, 1080),
        ("1440p", 2560, 1440),
        ("4k", 3840, 2160),
    ]

    # Additional resolutions for binary search
    binary_search_resolutions = [
        ("576p", 1024, 576),
        ("648p", 1152, 648),
        ("684p", 1216, 684),
        ("756p", 1344, 756),
        ("792p", 1408, 792),
        ("828p", 1472, 828),
        ("864p", 1536, 864),
    ]

    output_dir = Path("testing/test_videos")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Creating standard test videos...")
    for name, width, height in resolutions:
        output_path = output_dir / f"test_{name}.mp4"
        if not create_test_video(output_path, width, height):
            print(f"Failed to create {name} video")

    print("\nCreating binary search test videos...")
    for name, width, height in binary_search_resolutions:
        output_path = output_dir / f"test_{name}.mp4"
        if not create_test_video(output_path, width, height):
            print(f"Failed to create {name} video")

    print(f"\nAll test videos created in: {output_dir.absolute()}")

    # Create a reference video from actual content if available
    sample_videos = list(Path("inputs/videos").glob("*.mp4"))
    if sample_videos:
        print(f"\nFound {len(sample_videos)} existing videos in inputs/videos/")
        source = sample_videos[0]

        # Create resized versions of real content
        for name, width, height in [("480p", 854, 480), ("720p", 1280, 720), ("1080p", 1920, 1080)]:
            output_path = output_dir / f"real_content_{name}.mp4"
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-vf",
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "23",
                "-t",
                "5",  # Use only first 5 seconds
                str(output_path),
            ]

            print(f"Creating real content at {name}: {output_path.name}")
            subprocess.run(cmd, capture_output=True, check=False)

    print("\nTest video creation complete!")
    print("\nNext steps:")
    print("1. Run basic upsampling test:")
    print(
        '   python -m cosmos_workflow.cli create-spec "test" "A test scene" --video-path testing/test_videos/test_480p.mp4'
    )
    print("2. Follow the test plan in testing/upsample_test_plan.md")


if __name__ == "__main__":
    # Check if ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: ffmpeg not found. Please install ffmpeg to create test videos.")
        print("Install with: apt-get install ffmpeg (Linux) or download from https://ffmpeg.org")
        sys.exit(1)

    main()
