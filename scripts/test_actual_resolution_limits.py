#!/usr/bin/env python3
"""Test actual resolution limits by running upsampling on various resolutions.

This script creates test videos at different resolutions and attempts to
upsample them to find the exact working limits.
"""

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# Use the existing working upsampler
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class ResolutionTest:
    """Test case for a resolution."""

    width: int
    height: int
    frames: int = 2

    @property
    def name(self) -> str:
        return f"{self.width}x{self.height}"

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def estimated_tokens(self) -> int:
        return int(self.pixels * self.frames * 0.0173)


def create_test_video(width: int, height: int, output_path: Path, frames: int = 2) -> bool:
    """Create a test video."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={width}x{height}:duration=1:rate={frames}",
        "-vframes",
        str(frames),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-crf",
        "18",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to create video: {e.stderr}")
        return False


def test_resolution_with_script(resolution: ResolutionTest, video_path: Path) -> dict:
    """Test a resolution using the working upsampler script."""
    result = {
        "resolution": resolution.name,
        "width": resolution.width,
        "height": resolution.height,
        "pixels": resolution.pixels,
        "estimated_tokens": resolution.estimated_tokens,
        "video_path": str(video_path),
    }

    # Use the working_prompt_upsampler.py script
    cmd = [
        sys.executable,
        "scripts/working_prompt_upsampler.py",
        "--prompt",
        "A beautiful sunset over the ocean",
        "--video",
        str(video_path),
        "--output",
        f"test_output_{resolution.name}.json",
    ]

    try:
        start_time = time.time()
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent.parent,
            check=False,  # Run from project root
        )
        elapsed = time.time() - start_time

        result["elapsed_time"] = elapsed

        if process.returncode == 0:
            result["success"] = True
            result["stdout"] = process.stdout[-500:]  # Last 500 chars

            # Try to read output file
            output_file = Path(f"test_output_{resolution.name}.json")
            if output_file.exists():
                with open(output_file) as f:
                    output_data = json.load(f)
                    if output_data and len(output_data) > 0:
                        result["upsampled_length"] = len(output_data[0].get("upsampled", ""))
                output_file.unlink()  # Clean up

            print(f"  ✅ SUCCESS in {elapsed:.2f}s")
        else:
            result["success"] = False
            result["error"] = process.stderr[-500:] if process.stderr else "Unknown error"
            result["return_code"] = process.returncode

            # Check for specific errors
            error_text = (process.stderr or "") + (process.stdout or "")
            if "vocab" in error_text.lower():
                result["error_type"] = "vocab_error"
                print("  ❌ VOCAB ERROR")
            elif "token" in error_text.lower() or "4096" in error_text:
                result["error_type"] = "token_limit"
                print("  ❌ TOKEN LIMIT")
            elif "memory" in error_text.lower():
                result["error_type"] = "out_of_memory"
                print("  ❌ OUT OF MEMORY")
            else:
                result["error_type"] = "other"
                print(f"  ❌ ERROR: {process.returncode}")

    except subprocess.TimeoutExpired:
        result["success"] = False
        result["error"] = "Timeout after 60 seconds"
        result["error_type"] = "timeout"
        print("  ❌ TIMEOUT")
    except Exception as e:
        result["success"] = False
        result["error"] = str(e)
        result["error_type"] = "exception"
        print(f"  ❌ EXCEPTION: {e}")

    return result


def get_test_resolutions() -> list[ResolutionTest]:
    """Get resolutions to test, focusing on finding the exact limit."""
    return [
        # Very small (should work)
        ResolutionTest(256, 144),  # ~1,275 tokens
        ResolutionTest(320, 180),  # ~1,991 tokens
        # Near the suspected limit
        ResolutionTest(384, 216),  # ~2,869 tokens
        ResolutionTest(400, 225),  # ~3,114 tokens
        ResolutionTest(416, 234),  # ~3,366 tokens
        ResolutionTest(426, 240),  # ~3,537 tokens
        ResolutionTest(440, 248),  # ~3,774 tokens
        ResolutionTest(450, 253),  # ~3,938 tokens
        ResolutionTest(460, 259),  # ~4,121 tokens
        ResolutionTest(470, 264),  # ~4,292 tokens
        ResolutionTest(480, 270),  # ~4,485 tokens
        # NVIDIA 256p resolutions (should work?)
        ResolutionTest(256, 256),  # ~2,267 tokens
        ResolutionTest(320, 256),  # ~2,834 tokens
        ResolutionTest(320, 192),  # ~2,126 tokens
        # Test with different frame counts
        ResolutionTest(480, 270, frames=1),  # ~2,243 tokens (1 frame)
        ResolutionTest(320, 180, frames=4),  # ~3,982 tokens (4 frames)
    ]


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test actual resolution limits")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("resolution_tests"), help="Output directory"
    )
    parser.add_argument("--use-remote", action="store_true", help="Run tests on remote GPU")

    args = parser.parse_args()

    print("=" * 80)
    print("ACTUAL RESOLUTION LIMIT TESTING")
    print("=" * 80)
    print(f"Output directory: {args.output_dir}")
    print(f"Using: {'Remote GPU' if args.use_remote else 'Local testing'}")

    # Create directories
    videos_dir = args.output_dir / "test_videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    results_dir = args.output_dir / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Get test resolutions
    resolutions = get_test_resolutions()
    results = []

    print(f"\nTesting {len(resolutions)} resolutions...")
    print("-" * 80)

    for i, resolution in enumerate(resolutions, 1):
        print(f"\n[{i}/{len(resolutions)}] Testing {resolution.name}")
        print(f"  Pixels: {resolution.pixels:,}")
        print(f"  Frames: {resolution.frames}")
        print(f"  Est. tokens: {resolution.estimated_tokens:,}")
        print(
            f"  Prediction: {'Should work (<4096)' if resolution.estimated_tokens < 4096 else 'Might fail (>4096)'}"
        )

        # Create test video
        video_path = videos_dir / f"test_{resolution.name}_{resolution.frames}f.mp4"
        if not create_test_video(
            resolution.width, resolution.height, video_path, resolution.frames
        ):
            print("  ⏭️ Skipping - video creation failed")
            continue

        # Test upsampling
        if args.use_remote:
            # TODO: Implement remote testing
            print("  ⏭️ Remote testing not yet implemented")
            result = {"resolution": resolution.name, "success": False, "error": "Not implemented"}
        else:
            result = test_resolution_with_script(resolution, video_path)

        results.append(result)

        # Small delay between tests
        time.sleep(1)

    # Save results
    json_path = results_dir / f"resolution_test_results_{int(time.time())}.json"
    with open(json_path, "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    successful = [r for r in results if r.get("success")]
    failed = [r for r in results if not r.get("success")]

    print(f"\nTotal tested: {len(results)}")
    print(f"Successful: {len(successful)}")
    print(f"Failed: {len(failed)}")

    if successful:
        print("\n✅ Working resolutions:")
        for r in sorted(successful, key=lambda x: x["pixels"]):
            print(f"  {r['resolution']}: {r['estimated_tokens']:,} tokens")

    if failed:
        print("\n❌ Failed resolutions:")
        for r in sorted(failed, key=lambda x: x["pixels"]):
            error_type = r.get("error_type", "unknown")
            print(f"  {r['resolution']}: {r['estimated_tokens']:,} tokens ({error_type})")

    # Find the boundary
    if successful and failed:
        max_working = max(successful, key=lambda x: x["pixels"])
        min_failing = min(failed, key=lambda x: x["pixels"])

        print("\n🎯 BOUNDARY FOUND:")
        print(
            f"  Max working: {max_working['resolution']} ({max_working['estimated_tokens']:,} tokens)"
        )
        print(
            f"  Min failing: {min_failing['resolution']} ({min_failing['estimated_tokens']:,} tokens)"
        )
        print(
            f"  Actual limit: Between {max_working['estimated_tokens']:,} and {min_failing['estimated_tokens']:,} tokens"
        )

    print(f"\nResults saved to: {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
