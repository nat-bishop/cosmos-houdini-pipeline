#!/usr/bin/env python3
"""Test if the 4096 token limit can be increased for prompt upsampling.

This script tests different max_model_len configurations to see if we can
process larger resolution videos.
"""

import json
import os
import subprocess
import sys
import time
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


def create_test_video(width: int, height: int, output_path: Path) -> bool:
    """Create a test video at specified resolution."""
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=size={width}x{height}:duration=1:rate=2",
        "-vframes",
        "2",
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
    except subprocess.CalledProcessError:
        return False


class TokenLimitTester:
    """Test different token limit configurations."""

    def __init__(self, checkpoint_dir: str = None):
        self.checkpoint_dir = checkpoint_dir or "mistralai/Pixtral-12B-2409"
        self.results = []

    def test_configuration(self, max_model_len: int, test_resolution: tuple[int, int]) -> dict:
        """Test a specific max_model_len configuration."""
        width, height = test_resolution
        estimated_tokens = int(width * height * 2 * 0.0173)

        print(f"\n{'='*60}")
        print(f"Testing max_model_len={max_model_len}")
        print(f"Resolution: {width}x{height} (~{estimated_tokens:,} tokens)")
        print(f"{'='*60}")

        result = {
            "max_model_len": max_model_len,
            "resolution": f"{width}x{height}",
            "estimated_tokens": estimated_tokens,
            "width": width,
            "height": height,
        }

        try:
            # Try to import and create upsampler with custom max_model_len
            from vllm import LLM, SamplingParams

            # Create a modified upsampler
            print(f"Loading model with max_model_len={max_model_len}...")

            model = LLM(
                model=self.checkpoint_dir,
                tensor_parallel_size=1,
                tokenizer_mode="mistral",
                gpu_memory_utilization=0.98,
                max_model_len=max_model_len,  # <-- Test different values
                max_num_seqs=2,
                limit_mm_per_prompt={"image": 2},
                enable_prefix_caching=True,
            )

            print("✅ Model loaded successfully!")

            # Create test video
            video_path = Path(f"test_{width}x{height}.mp4")
            if not create_test_video(width, height, video_path):
                result["success"] = False
                result["error"] = "Failed to create test video"
                return result

            # Test upsampling
            from cosmos_transfer1.utils.misc import extract_video_frames, image_to_base64

            image_paths = extract_video_frames(str(video_path))

            # Create prompt
            message = [{"role": "user", "content": [{"type": "text", "text": "A test video"}]}]

            # Add images to message
            for img_path in image_paths:
                base64_image = image_to_base64(img_path)
                message[0]["content"].append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    }
                )

            # Add instruction
            message[0]["content"].append({"type": "text", "text": "Describe this in detail."})

            # Run inference
            sampling_params = SamplingParams(temperature=0.6, max_tokens=300)
            outputs = model.chat(message, sampling_params)

            result["success"] = True
            result["output_length"] = len(outputs[0].outputs[0].text)
            print(f"✅ Upsampling successful! Output: {result['output_length']} chars")

            # Clean up
            del model
            import gc

            gc.collect()

            if video_path.exists():
                video_path.unlink()

        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

            if "max_model_len" in str(e).lower():
                print(f"❌ Model limit error: {str(e)[:200]}")
                result["error_type"] = "model_limit"
            elif "out of memory" in str(e).lower():
                print(f"❌ Out of memory: {str(e)[:200]}")
                result["error_type"] = "oom"
            else:
                print(f"❌ Error: {str(e)[:200]}")
                result["error_type"] = "other"

        self.results.append(result)
        return result

    def run_tests(self):
        """Run tests with different configurations."""
        # Test configurations: (max_model_len, resolution)
        test_configs = [
            # Test default limit
            (4096, (320, 180)),  # ~2000 tokens - should work
            (4096, (480, 270)),  # ~4500 tokens - should fail
            # Test increased limits
            (8192, (480, 270)),  # ~4500 tokens - might work
            (8192, (640, 360)),  # ~8000 tokens - borderline
            (16384, (640, 480)),  # ~10600 tokens - test
            (16384, (960, 540)),  # ~18000 tokens - should fail
            (32768, (1280, 720)),  # ~32000 tokens - test if possible
            # Test with very small to find actual working limit
            (4096, (256, 256)),  # ~2267 tokens
            (4096, (384, 216)),  # ~2869 tokens
            (4096, (400, 225)),  # ~3114 tokens
            (4096, (426, 240)),  # ~3537 tokens
        ]

        for max_len, resolution in test_configs:
            self.test_configuration(max_len, resolution)
            time.sleep(2)  # Give GPU time to clear

    def save_results(self, output_dir: Path):
        """Save test results."""
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save JSON
        json_path = output_dir / f"token_limit_tests_{int(time.time())}.json"
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")

        # Group by max_model_len
        by_limit = {}
        for r in self.results:
            limit = r["max_model_len"]
            if limit not in by_limit:
                by_limit[limit] = []
            by_limit[limit].append(r)

        for limit in sorted(by_limit.keys()):
            tests = by_limit[limit]
            successful = [t for t in tests if t.get("success")]
            failed = [t for t in tests if not t.get("success")]

            print(f"\nmax_model_len = {limit}:")
            if successful:
                max_working = max(successful, key=lambda x: x["estimated_tokens"])
                print(
                    f"  ✅ Max working: {max_working['resolution']} ({max_working['estimated_tokens']:,} tokens)"
                )
            if failed:
                min_failing = min(failed, key=lambda x: x["estimated_tokens"])
                print(
                    f"  ❌ Min failing: {min_failing['resolution']} ({min_failing['estimated_tokens']:,} tokens)"
                )

        print(f"\nResults saved to: {json_path}")


def main():
    """Main function."""
    import argparse

    parser = argparse.ArgumentParser(description="Test token limit configurations")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("token_limit_tests"), help="Output directory"
    )
    parser.add_argument("--checkpoint", type=str, default=None, help="Model checkpoint path")
    parser.add_argument("--quick", action="store_true", help="Quick test with fewer configurations")

    args = parser.parse_args()

    print("=" * 60)
    print("TOKEN LIMIT CONFIGURATION TEST")
    print("=" * 60)
    print("Testing if max_model_len can be increased beyond 4096")
    print(f"Output directory: {args.output_dir}")

    tester = TokenLimitTester(checkpoint_dir=args.checkpoint)

    if args.quick:
        # Quick test - just try a few key configurations
        print("\nQuick mode - testing key configurations only")
        tester.test_configuration(4096, (320, 180))  # Should work
        tester.test_configuration(8192, (480, 270))  # Test double limit
        tester.test_configuration(16384, (640, 480))  # Test 4x limit
    else:
        # Full test suite
        tester.run_tests()

    tester.save_results(args.output_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())
