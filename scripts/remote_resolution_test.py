#!/usr/bin/env python3
"""Remote resolution testing script for running on GPU instance.

Deploy this to the remote instance to test actual resolution limits.
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
    """Create a test video using ffmpeg."""
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
        print(f"Failed to create video: {e.stderr[:200]}")
        return False


def test_with_modified_limit(
    resolution: ResolutionTest, video_path: Path, max_model_len: int = 4096
) -> dict:
    """Test upsampling with a specific max_model_len setting."""
    result = {
        "resolution": resolution.name,
        "width": resolution.width,
        "height": resolution.height,
        "pixels": resolution.pixels,
        "estimated_tokens": resolution.estimated_tokens,
        "max_model_len": max_model_len,
        "video_path": str(video_path),
    }

    try:
        # Import modules
        from cosmos_transfer1.utils.misc import extract_video_frames, image_to_base64
        from vllm import LLM, SamplingParams

        print(f"  Loading model with max_model_len={max_model_len}...")

        # Create model with custom max_model_len
        model = LLM(
            model="mistralai/Pixtral-12B-2409",
            tensor_parallel_size=1,
            tokenizer_mode="mistral",
            gpu_memory_utilization=0.98,
            max_model_len=max_model_len,  # Test different values
            max_num_seqs=2,
            limit_mm_per_prompt={"image": 2},
            enable_prefix_caching=True,
        )

        # Extract frames
        image_paths = extract_video_frames(str(video_path))

        # Create message
        message = [{"role": "user", "content": [{"type": "text", "text": "A test video showing"}]}]

        # Add images
        for img_path in image_paths:
            base64_image = image_to_base64(img_path)
            message[0]["content"].append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                }
            )

        # Add final instruction
        message[0]["content"].append(
            {
                "type": "text",
                "text": "Describe this video in detail, including colors, movement, and any patterns you observe.",
            }
        )

        # Run inference
        sampling_params = SamplingParams(temperature=0.6, max_tokens=300)

        start_time = time.time()
        outputs = model.chat(message, sampling_params)
        elapsed = time.time() - start_time

        result["success"] = True
        result["elapsed_time"] = elapsed
        result["output_length"] = len(outputs[0].outputs[0].text)
        result["output_preview"] = outputs[0].outputs[0].text[:200]

        print(f"  ✅ SUCCESS in {elapsed:.2f}s (output: {result['output_length']} chars)")

        # Clean up
        del model
        import gc

        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

    except Exception as e:
        result["success"] = False
        result["error"] = str(e)[:500]

        error_str = str(e).lower()
        if "token" in error_str or "4096" in error_str or "context length" in error_str:
            result["error_type"] = "token_limit"
            print("  ❌ TOKEN LIMIT ERROR")
        elif "out of memory" in error_str or "oom" in error_str:
            result["error_type"] = "out_of_memory"
            print("  ❌ OUT OF MEMORY")
        elif "vocab" in error_str:
            result["error_type"] = "vocab_error"
            print("  ❌ VOCAB ERROR")
        else:
            result["error_type"] = "other"
            print(f"  ❌ ERROR: {str(e)[:100]}")

    return result


def get_test_matrix() -> list[tuple[ResolutionTest, int]]:
    """Get test matrix of resolutions and max_model_len values."""
    tests = []

    # Test with default 4096 limit
    tests.extend(
        [
            (ResolutionTest(256, 144), 4096),  # ~1,275 tokens - should work
            (ResolutionTest(320, 180), 4096),  # ~1,991 tokens - should work
            (ResolutionTest(384, 216), 4096),  # ~2,869 tokens - should work
            (ResolutionTest(400, 225), 4096),  # ~3,114 tokens - should work
            (ResolutionTest(426, 240), 4096),  # ~3,537 tokens - borderline
            (ResolutionTest(450, 253), 4096),  # ~3,938 tokens - borderline
            (ResolutionTest(480, 270), 4096),  # ~4,485 tokens - should fail
            # NVIDIA 256p resolutions
            (ResolutionTest(256, 256), 4096),  # ~2,267 tokens
            (ResolutionTest(320, 256), 4096),  # ~2,834 tokens
            (ResolutionTest(320, 192), 4096),  # ~2,126 tokens
        ]
    )

    # Test with increased limits
    tests.extend(
        [
            (ResolutionTest(480, 270), 8192),  # ~4,485 tokens with 8K limit
            (ResolutionTest(640, 360), 8192),  # ~7,977 tokens with 8K limit
            (ResolutionTest(640, 480), 16384),  # ~10,636 tokens with 16K limit
            (ResolutionTest(960, 540), 16384),  # ~17,954 tokens with 16K limit - should fail
            # Test NVIDIA 720p with high limits
            (ResolutionTest(960, 704), 32768),  # ~23,388 tokens with 32K limit
            (ResolutionTest(1280, 704), 32768),  # ~31,179 tokens with 32K limit
        ]
    )

    # Test with 1 frame to see if it helps
    tests.extend(
        [
            (ResolutionTest(480, 270, frames=1), 4096),  # ~2,243 tokens
            (ResolutionTest(640, 480, frames=1), 4096),  # ~5,318 tokens - should fail
            (ResolutionTest(960, 704, frames=1), 16384),  # ~11,694 tokens
        ]
    )

    return tests


def main():
    """Main function."""
    output_dir = Path("/home/ubuntu/resolution_tests")
    output_dir.mkdir(parents=True, exist_ok=True)

    videos_dir = output_dir / "test_videos"
    videos_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("REMOTE RESOLUTION & TOKEN LIMIT TESTING")
    print("=" * 80)
    print(f"Output directory: {output_dir}")
    print(f"Testing on GPU: {os.environ.get('CUDA_VISIBLE_DEVICES', 'All available')}")

    # Check CUDA availability
    try:
        import torch

        if torch.cuda.is_available():
            print(f"CUDA available: {torch.cuda.device_count()} GPU(s)")
            print(f"GPU 0: {torch.cuda.get_device_name(0)}")
        else:
            print("WARNING: CUDA not available!")
    except ImportError:
        print("WARNING: PyTorch not found")

    # Get test matrix
    test_matrix = get_test_matrix()
    results = []

    print(f"\nTesting {len(test_matrix)} configurations...")
    print("-" * 80)

    for i, (resolution, max_len) in enumerate(test_matrix, 1):
        print(f"\n[{i}/{len(test_matrix)}] Testing {resolution.name} with max_model_len={max_len}")
        print(f"  Pixels: {resolution.pixels:,}")
        print(f"  Frames: {resolution.frames}")
        print(f"  Est. tokens: {resolution.estimated_tokens:,}")
        print(f"  Token limit: {max_len:,}")
        print(
            f"  Prediction: {'Should work' if resolution.estimated_tokens < max_len * 0.9 else 'Might fail'}"
        )

        # Create test video
        video_name = f"test_{resolution.name}_{resolution.frames}f.mp4"
        video_path = videos_dir / video_name

        if not video_path.exists():
            if not create_test_video(
                resolution.width, resolution.height, video_path, resolution.frames
            ):
                print("  ⏭️ Skipping - video creation failed")
                continue
        else:
            print(f"  Using existing video: {video_path}")

        # Test with modified limit
        result = test_with_modified_limit(resolution, video_path, max_len)
        results.append(result)

        # Save intermediate results
        intermediate_path = output_dir / f"results_partial_{int(time.time())}.json"
        with open(intermediate_path, "w") as f:
            json.dump(results, f, indent=2)

        # Delay between tests
        time.sleep(2)

    # Save final results
    final_path = output_dir / f"resolution_test_results_{int(time.time())}.json"
    with open(final_path, "w") as f:
        json.dump(results, f, indent=2)

    # Generate summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Group by max_model_len
    by_limit = {}
    for r in results:
        limit = r.get("max_model_len", 4096)
        if limit not in by_limit:
            by_limit[limit] = {"success": [], "failed": []}

        if r.get("success"):
            by_limit[limit]["success"].append(r)
        else:
            by_limit[limit]["failed"].append(r)

    for limit in sorted(by_limit.keys()):
        data = by_limit[limit]
        print(f"\nmax_model_len = {limit:,}:")

        if data["success"]:
            max_working = max(data["success"], key=lambda x: x["estimated_tokens"])
            print(
                f"  ✅ Max working: {max_working['resolution']} ({max_working['estimated_tokens']:,} tokens)"
            )

        if data["failed"]:
            min_failing = min(data["failed"], key=lambda x: x["estimated_tokens"])
            print(
                f"  ❌ Min failing: {min_failing['resolution']} ({min_failing['estimated_tokens']:,} tokens)"
            )

            # Show error types
            error_types = {}
            for f in data["failed"]:
                et = f.get("error_type", "unknown")
                error_types[et] = error_types.get(et, 0) + 1
            print(f"     Error types: {error_types}")

    print(f"\nResults saved to: {final_path}")

    # Write summary file
    summary_path = output_dir / "summary.txt"
    with open(summary_path, "w") as f:
        f.write("RESOLUTION TEST SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Test date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        for limit in sorted(by_limit.keys()):
            f.write(f"\nmax_model_len = {limit:,}:\n")
            data = by_limit[limit]
            f.write(f"  Successful: {len(data['success'])}\n")
            f.write(f"  Failed: {len(data['failed'])}\n")

            if data["success"]:
                max_working = max(data["success"], key=lambda x: x["estimated_tokens"])
                f.write(
                    f"  Max working: {max_working['resolution']} ({max_working['estimated_tokens']:,} tokens)\n"
                )

    print(f"Summary saved to: {summary_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
