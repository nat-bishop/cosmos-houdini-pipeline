"""Resolution testing utilities for upsampling.

This module provides tools to test various video resolutions
to find the maximum working resolution for prompt upsampling.
"""

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class ResolutionTest:
    """Test case for a specific resolution."""

    width: int
    height: int
    frames: int = 2
    name: str | None = None

    def __post_init__(self):
        if not self.name:
            self.name = f"{self.width}x{self.height}"

    @property
    def pixels(self) -> int:
        """Total pixels per frame."""
        return self.width * self.height

    @property
    def estimated_tokens(self) -> int:
        """Estimated token count based on empirical formula."""
        # Formula from testing: tokens = width * height * frames * 0.0173
        return int(self.pixels * self.frames * 0.0173)

    def is_safe(self, max_tokens: int = 4096) -> bool:
        """Check if resolution is within safe token limit."""
        return self.estimated_tokens <= max_tokens


class ResolutionTester:
    """Test various resolutions for upsampling compatibility."""

    # Common resolutions to test
    STANDARD_RESOLUTIONS = [
        # Very safe (under 2K tokens)
        ResolutionTest(320, 180, name="320x180 (Safe)"),
        ResolutionTest(320, 192, name="256p"),
        ResolutionTest(320, 256, name="256p Wide"),
        # Borderline (3-4K tokens)
        ResolutionTest(400, 225, name="400x225"),
        ResolutionTest(426, 240, name="240p"),
        ResolutionTest(480, 270, name="270p"),
        # Likely to fail (over 4K tokens)
        ResolutionTest(640, 360, name="360p"),
        ResolutionTest(640, 480, name="480p"),
        ResolutionTest(854, 480, name="480p Wide"),
        ResolutionTest(1280, 720, name="720p"),
        ResolutionTest(1280, 704, name="720p (NVIDIA)"),
    ]

    def __init__(self, test_dir: Path = Path("test_videos")):
        self.test_dir = test_dir
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def create_test_video(self, resolution: ResolutionTest) -> Path:
        """Create a test video at specified resolution.

        Args:
            resolution: Resolution test case

        Returns:
            Path to created video file
        """
        output_path = self.test_dir / f"test_{resolution.width}x{resolution.height}.mp4"

        # Use ffmpeg to create a test video
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={resolution.width}x{resolution.height}:duration=1:rate={resolution.frames}",
            "-vframes",
            str(resolution.frames),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "18",
            str(output_path),
        ]

        try:
            subprocess.run(cmd, check=True, capture_output=True)
            log.info(f"Created test video: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to create test video: {e}")
            raise

    def estimate_all_resolutions(self, max_tokens: int = 4096) -> dict:
        """Estimate token counts for all standard resolutions.

        Args:
            max_tokens: Maximum token limit

        Returns:
            Dictionary of resolution analysis
        """
        results = {
            "max_tokens": max_tokens,
            "safe_resolutions": [],
            "unsafe_resolutions": [],
            "all_resolutions": [],
        }

        for res in self.STANDARD_RESOLUTIONS:
            info = {
                "name": res.name,
                "width": res.width,
                "height": res.height,
                "pixels": res.pixels,
                "estimated_tokens": res.estimated_tokens,
                "is_safe": res.is_safe(max_tokens),
                "percentage_of_limit": round(res.estimated_tokens / max_tokens * 100, 1),
            }

            results["all_resolutions"].append(info)

            if res.is_safe(max_tokens):
                results["safe_resolutions"].append(info)
            else:
                results["unsafe_resolutions"].append(info)

        # Find the maximum safe resolution
        if results["safe_resolutions"]:
            max_safe = max(results["safe_resolutions"], key=lambda x: x["pixels"])
            results["max_safe_resolution"] = max_safe

        return results

    def find_max_resolution(
        self, max_tokens: int = 4096, aspect_ratio: float = 16 / 9
    ) -> ResolutionTest:
        """Find the maximum resolution that fits within token limit.

        Args:
            max_tokens: Maximum token limit
            aspect_ratio: Desired aspect ratio

        Returns:
            Maximum safe resolution
        """
        # Calculate maximum pixels
        max_pixels = int(max_tokens / (2 * 0.0173))  # 2 frames

        # Calculate dimensions maintaining aspect ratio
        height = int((max_pixels / aspect_ratio) ** 0.5)
        width = int(height * aspect_ratio)

        # Round down to nearest multiple of 8 (for video encoding)
        width = (width // 8) * 8
        height = (height // 8) * 8

        return ResolutionTest(width, height)

    def create_batch_test(
        self, output_file: Path, test_prompt: str = "A beautiful landscape"
    ) -> None:
        """Create a batch test file for all resolutions.

        Args:
            output_file: Path to output JSON file
            test_prompt: Prompt to use for testing
        """
        batch_data = []

        for res in self.STANDARD_RESOLUTIONS:
            video_path = self.create_test_video(res)
            batch_data.append(
                {
                    "name": res.name,
                    "prompt": test_prompt,
                    "video_path": str(video_path),
                    "metadata": {
                        "width": res.width,
                        "height": res.height,
                        "estimated_tokens": res.estimated_tokens,
                        "expected_to_work": res.is_safe(),
                    },
                }
            )

        with open(output_file, "w") as f:
            json.dump(batch_data, f, indent=2)

        log.info(f"Created batch test file: {output_file}")

    def analyze_results(self, results_file: Path) -> dict:
        """Analyze results from batch testing.

        Args:
            results_file: Path to results JSON file

        Returns:
            Analysis of what resolutions worked
        """
        with open(results_file) as f:
            results = json.load(f)

        analysis = {
            "total_tested": len(results),
            "successful": [],
            "failed": [],
            "max_working_resolution": None,
            "max_working_tokens": 0,
        }

        for result in results:
            metadata = result.get("metadata", {})
            resolution_info = {
                "name": result["name"],
                "width": metadata.get("width"),
                "height": metadata.get("height"),
                "tokens": metadata.get("estimated_tokens"),
                "success": result.get("success", False),
            }

            if result.get("success"):
                analysis["successful"].append(resolution_info)
                if metadata.get("estimated_tokens", 0) > analysis["max_working_tokens"]:
                    analysis["max_working_tokens"] = metadata["estimated_tokens"]
                    analysis["max_working_resolution"] = resolution_info
            else:
                analysis["failed"].append(resolution_info)

        return analysis


def print_resolution_table(max_tokens: int = 4096) -> None:
    """Print a table of resolutions and their token estimates."""
    tester = ResolutionTester()
    results = tester.estimate_all_resolutions(max_tokens)

    print(f"\n{'='*60}")
    print(f"Resolution Analysis (Max Tokens: {max_tokens})")
    print(f"{'='*60}")
    print(f"{'Resolution':<20} {'Pixels':<10} {'Tokens':<10} {'Status':<10}")
    print(f"{'-'*60}")

    for res in results["all_resolutions"]:
        status = "✅ SAFE" if res["is_safe"] else "❌ UNSAFE"
        print(f"{res['name']:<20} {res['pixels']:<10} {res['estimated_tokens']:<10} {status}")

    print(f"\n{'='*60}")
    if results.get("max_safe_resolution"):
        max_safe = results["max_safe_resolution"]
        print(
            f"Maximum Safe Resolution: {max_safe['name']} ({max_safe['pixels']} pixels, {max_safe['estimated_tokens']} tokens)"
        )
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Run analysis when module is executed directly
    print_resolution_table()

    # Test different token limits
    for token_limit in [4096, 8192, 16384, 32768]:
        tester = ResolutionTester()
        max_res = tester.find_max_resolution(token_limit)
        print(
            f"Max resolution for {token_limit} tokens: {max_res.width}x{max_res.height} (~{max_res.estimated_tokens} tokens)"
        )
