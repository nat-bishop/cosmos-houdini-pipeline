#!/usr/bin/env python3
"""Persistent upsampler for testing multiple resolutions without model reloading.

This script keeps the model loaded in memory and tests various resolutions
to understand exactly when vocab errors occur.
"""

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

# CRITICAL: Set this BEFORE any imports that might use VLLM
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

# Set torch elastic environment variables
env_defaults = {
    "RANK": "0",
    "LOCAL_RANK": "0",
    "WORLD_SIZE": "1",
    "LOCAL_WORLD_SIZE": "1",
    "GROUP_RANK": "0",
    "ROLE_RANK": "0",
    "ROLE_NAME": "default",
    "OMP_NUM_THREADS": "4",
    "MASTER_ADDR": "127.0.0.1",
    "MASTER_PORT": "29500",
    "TORCHELASTIC_USE_AGENT_STORE": "False",
    "TORCHELASTIC_MAX_RESTARTS": "0",
    "TORCHELASTIC_RUN_ID": "local",
    "TORCH_NCCL_ASYNC_ERROR_HANDLING": "1",
}
for k, v in env_defaults.items():
    os.environ.setdefault(k, v)


@dataclass
class ResolutionTest:
    """Test case for a specific resolution."""

    category: str  # 1080p, 720p, 512p, 480p, 256p
    aspect_ratio: str  # 1:1, 4:3, 3:4, 16:9, 9:16
    width: int
    height: int
    frames: int = 2

    @property
    def name(self) -> str:
        return f"{self.category}_{self.aspect_ratio.replace(':', 'x')}_{self.width}x{self.height}"

    @property
    def pixels(self) -> int:
        return self.width * self.height

    @property
    def estimated_tokens(self) -> int:
        """Estimate tokens using formula: w × h × frames × 0.0173"""
        return int(self.pixels * self.frames * 0.0173)

    @property
    def exceeds_limit(self) -> bool:
        """Check if exceeds 4096 token limit."""
        return self.estimated_tokens > 4096


def get_nvidia_resolutions() -> list[ResolutionTest]:
    """Get all NVIDIA-supported resolutions for testing."""
    resolutions = []

    # Based on cosmos_transfer1/diffusion/datasets/augmentors/control_input.py
    configs = {
        "1080p": {
            "1:1": (1024, 1024),
            "4:3": (1440, 1056),
            "3:4": (1056, 1440),
            "16:9": (1920, 1056),
            "9:16": (1056, 1920),
        },
        "720p": {
            "1:1": (960, 960),
            "4:3": (960, 704),
            "3:4": (704, 960),
            "16:9": (1280, 704),
            "9:16": (704, 1280),
        },
        "512p": {
            "1:1": (512, 512),
            "4:3": (640, 512),
            "3:4": (512, 640),
            "16:9": (640, 384),
            "9:16": (384, 640),
        },
        "480p": {
            "1:1": (480, 480),
            "4:3": (640, 480),
            "3:4": (480, 640),
            "16:9": (768, 432),
            "9:16": (432, 768),
        },
        "256p": {
            "1:1": (256, 256),
            "4:3": (320, 256),
            "3:4": (256, 320),
            "16:9": (320, 192),
            "9:16": (192, 320),
        },
    }

    for category, aspect_configs in configs.items():
        for aspect_ratio, (width, height) in aspect_configs.items():
            resolutions.append(
                ResolutionTest(
                    category=category,
                    aspect_ratio=aspect_ratio.replace(",", ":"),
                    width=width,
                    height=height,
                )
            )

    return sorted(resolutions, key=lambda r: r.pixels)


def create_test_video(resolution: ResolutionTest, output_dir: Path) -> Path:
    """Create a test video at the specified resolution."""
    output_path = output_dir / f"test_{resolution.name}.mp4"

    # Skip if already exists
    if output_path.exists():
        print(f"  Using existing video: {output_path}")
        return output_path

    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={resolution.width}x{resolution.height}:duration=1:rate=2",
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
        print(f"  Created video: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"  Failed to create video: {e.stderr}")
        return None


class PersistentUpsampler:
    """Upsampler that keeps model loaded between tests."""

    def __init__(self, checkpoint_dir: str = None):
        """Initialize upsampler with model loaded once."""
        self.model = None
        self.checkpoint_dir = checkpoint_dir
        self.results = []

    def load_model(self):
        """Load the upsampling model."""
        print("\n" + "=" * 80)
        print("Loading Pixtral-12B model (this takes ~30 seconds)...")
        print("=" * 80)

        try:
            # Import after environment setup
            from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler

            # Use default checkpoint if not specified
            if not self.checkpoint_dir:
                self.checkpoint_dir = "mistralai/Pixtral-12B-2409"

            self.model = PixtralPromptUpsampler(checkpoint=self.checkpoint_dir, num_gpus=1)

            print("✅ Model loaded successfully!\n")
            return True

        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False

    def test_resolution(self, resolution: ResolutionTest, video_path: Path) -> dict:
        """Test upsampling at a specific resolution."""
        if not self.model:
            return {"error": "Model not loaded"}

        result = {
            "resolution": resolution.name,
            "category": resolution.category,
            "aspect_ratio": resolution.aspect_ratio,
            "width": resolution.width,
            "height": resolution.height,
            "pixels": resolution.pixels,
            "estimated_tokens": resolution.estimated_tokens,
            "exceeds_limit": resolution.exceeds_limit,
            "video_path": str(video_path),
        }

        # Test prompt
        test_prompt = "A beautiful sunset over the ocean with waves"

        try:
            start_time = time.time()

            # Run upsampling
            upsampled = self.model.run(
                prompts=[test_prompt], input_videos=[str(video_path)], num_frames=resolution.frames
            )

            elapsed = time.time() - start_time

            result["success"] = True
            result["upsampled_prompt"] = upsampled[0] if upsampled else None
            result["elapsed_time"] = elapsed
            result["error"] = None

            print(f"  ✅ SUCCESS in {elapsed:.2f}s")
            if upsampled and upsampled[0]:
                print(f"  Upsampled length: {len(upsampled[0])} chars")

        except Exception as e:
            elapsed = time.time() - start_time
            error_msg = str(e)

            result["success"] = False
            result["upsampled_prompt"] = None
            result["elapsed_time"] = elapsed
            result["error"] = error_msg

            # Check for specific error types
            if "vocab" in error_msg.lower():
                result["error_type"] = "vocab_error"
                print(f"  ❌ VOCAB ERROR after {elapsed:.2f}s")
            elif "token" in error_msg.lower() or "4096" in error_msg:
                result["error_type"] = "token_limit"
                print(f"  ❌ TOKEN LIMIT after {elapsed:.2f}s")
            else:
                result["error_type"] = "other"
                print(f"  ❌ ERROR after {elapsed:.2f}s: {error_msg[:100]}")

        self.results.append(result)
        return result

    def test_all_resolutions(self, output_dir: Path):
        """Test all NVIDIA resolutions."""
        resolutions = get_nvidia_resolutions()

        print(f"\nTesting {len(resolutions)} NVIDIA resolutions")
        print("=" * 80)

        # Create videos directory
        videos_dir = output_dir / "test_videos"
        videos_dir.mkdir(parents=True, exist_ok=True)

        for i, resolution in enumerate(resolutions, 1):
            print(f"\n[{i}/{len(resolutions)}] Testing {resolution.name}")
            print(f"  Category: {resolution.category}")
            print(f"  Resolution: {resolution.width}x{resolution.height}")
            print(f"  Pixels: {resolution.pixels:,}")
            print(f"  Est. tokens: {resolution.estimated_tokens:,}")
            print(f"  Exceeds 4096: {'YES ⚠️' if resolution.exceeds_limit else 'NO ✅'}")

            # Create test video
            video_path = create_test_video(resolution, videos_dir)
            if not video_path:
                print("  ⏭️ Skipping due to video creation failure")
                continue

            # Test upsampling
            self.test_resolution(resolution, video_path)

            # Add small delay between tests
            time.sleep(0.5)

    def save_results(self, output_dir: Path):
        """Save test results to files."""
        results_dir = output_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = results_dir / f"upsampling_results_{int(time.time())}.json"
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: {json_path}")

        # Generate summary
        self.print_summary()

        # Save summary to file
        summary_path = results_dir / f"summary_{int(time.time())}.txt"
        with open(summary_path, "w") as f:
            f.write(self.generate_summary_text())
        print(f"Summary saved to: {summary_path}")

    def print_summary(self):
        """Print summary of results."""
        print("\n" + "=" * 80)
        print("SUMMARY OF RESULTS")
        print("=" * 80)

        successful = [r for r in self.results if r.get("success")]
        failed = [r for r in self.results if not r.get("success")]

        print(f"\nTotal tested: {len(self.results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")

        if successful:
            print("\n✅ SUCCESSFUL RESOLUTIONS:")
            for r in successful:
                print(
                    f"  - {r['resolution']}: {r['pixels']:,} pixels, ~{r['estimated_tokens']:,} tokens"
                )

        if failed:
            print("\n❌ FAILED RESOLUTIONS:")
            for r in failed:
                error_type = r.get("error_type", "unknown")
                print(
                    f"  - {r['resolution']}: {r['pixels']:,} pixels, ~{r['estimated_tokens']:,} tokens ({error_type})"
                )

        # Find the boundary
        if successful and failed:
            max_working = max(successful, key=lambda r: r["pixels"])
            min_failing = min(failed, key=lambda r: r["pixels"])

            print("\n🎯 TOKEN LIMIT BOUNDARY:")
            print(
                f"  Max working: {max_working['resolution']} ({max_working['estimated_tokens']:,} tokens)"
            )
            print(
                f"  Min failing: {min_failing['resolution']} ({min_failing['estimated_tokens']:,} tokens)"
            )
            print(
                f"  Estimated limit: ~{(max_working['estimated_tokens'] + min_failing['estimated_tokens']) // 2:,} tokens"
            )

    def generate_summary_text(self) -> str:
        """Generate summary text for saving."""
        lines = []
        lines.append("=" * 80)
        lines.append("UPSAMPLING RESOLUTION TEST RESULTS")
        lines.append("=" * 80)
        lines.append(f"Test date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"Total resolutions tested: {len(self.results)}")

        for r in self.results:
            status = "✅" if r.get("success") else "❌"
            lines.append(f"\n{status} {r['resolution']}")
            lines.append(f"   Category: {r['category']}")
            lines.append(f"   Resolution: {r['width']}x{r['height']}")
            lines.append(f"   Pixels: {r['pixels']:,}")
            lines.append(f"   Est. tokens: {r['estimated_tokens']:,}")
            if not r.get("success"):
                lines.append(f"   Error: {r.get('error_type', 'unknown')}")

        return "\n".join(lines)


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test upsampling with persistent model")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("upsampling_tests"),
        help="Output directory for results",
    )
    parser.add_argument("--checkpoint", type=str, default=None, help="Model checkpoint path")
    parser.add_argument("--single", type=str, help="Test single resolution (e.g., '720p_16:9')")

    args = parser.parse_args()

    print("=" * 80)
    print("PERSISTENT UPSAMPLER TEST")
    print("=" * 80)
    print(f"Output directory: {args.output_dir}")

    # Create upsampler
    upsampler = PersistentUpsampler(checkpoint_dir=args.checkpoint)

    # Load model once
    if not upsampler.load_model():
        print("Failed to load model. Exiting.")
        return 1

    # Test resolutions
    if args.single:
        # Test single resolution
        print(f"\nTesting single resolution: {args.single}")
        # Parse and test single resolution
        # TODO: Implement single resolution testing
    else:
        # Test all resolutions
        upsampler.test_all_resolutions(args.output_dir)

    # Save results
    upsampler.save_results(args.output_dir)

    print("\n✅ Testing complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
