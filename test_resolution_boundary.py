#!/usr/bin/env python3
"""Systematic resolution boundary testing for Cosmos Transfer1 upsampling.

This script finds the exact resolution boundary by binary search between
known working and failing resolutions.
"""

import json
import time
from pathlib import Path

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def create_test_video(ssh, width, height):
    """Create a test video at the specified resolution."""
    cmd = f"""cd /home/ubuntu/NatsFS/cosmos-transfer1 && \
ffmpeg -f lavfi -i testsrc2=duration=1:size={width}x{height}:rate=2 \
-frames:v 2 -pix_fmt yuv420p -y inputs/videos/test_{width}x{height}.mp4 2>/dev/null"""

    try:
        ssh.execute_command_success(cmd, timeout=30, stream_output=False)
        return True
    except:
        return False


def test_resolution(ssh, width, height, use_offload=True):
    """Test upsampling at a specific resolution.

    Returns:
        tuple: (success: bool, status: str, error: str)
    """
    pixels = width * height
    estimated_tokens = int(pixels * 2 * 0.0173)

    print(f"  Testing {width}x{height} ({pixels:,} pixels, ~{estimated_tokens} est. tokens)")

    # Create test video
    if not create_test_video(ssh, width, height):
        return False, "SKIP", "Failed to create test video"

    # Create test prompt
    test_prompt = {
        "name": f"test_{width}x{height}",
        "prompt": "A serene landscape with rolling hills",
        "video_path": f"/workspace/inputs/videos/test_{width}x{height}.mp4",
    }

    test_file = f"test_single_{width}x{height}.json"
    remote_file = f"/home/ubuntu/NatsFS/cosmos-transfer1/{test_file}"

    with ssh.get_sftp() as sftp:
        with sftp.open(remote_file, "w") as f:
            f.write(json.dumps([test_prompt]))

    # Build command
    offload_flag = "" if use_offload else "--no-offload"
    cmd = f"""sudo docker run --rm --gpus all --ipc=host --shm-size=8g \
-e VLLM_WORKER_MULTIPROC_METHOD=spawn \
-v /home/ubuntu/NatsFS/cosmos-transfer1:/workspace \
-w /workspace \
nvcr.io/ubuntu/cosmos-transfer1:latest \
python /workspace/scripts/working_prompt_upsampler.py \
--batch /workspace/{test_file} \
--output-dir /workspace/outputs/resolution_test \
--checkpoint-dir /workspace/checkpoints {offload_flag} 2>&1"""

    # Capture output
    exit_code, stdout, stderr = ssh.execute_command(cmd, timeout=300, stream_output=False)

    # Parse results
    if "SUCCESS: Batch processing completed" in stdout:
        # Extract actual token count if available
        token_line = [
            l for l in stdout.split("\n") if "tokens" in l.lower() and "actual" in l.lower()
        ]
        actual_tokens = "N/A"
        if token_line:
            try:
                actual_tokens = token_line[0].split("actual")[1].split("tokens")[0].strip()
            except:
                pass
        return True, "PASS", f"Actual tokens: {actual_tokens}"

    elif "Prompt length" in stdout and "longer than" in stdout:
        # Token limit exceeded
        error_lines = [l for l in stdout.split("\n") if "Prompt length" in l]
        if error_lines:
            # Extract actual token count
            try:
                actual = error_lines[0].split("Prompt length of")[1].split("is")[0].strip()
                return False, "TOKEN_LIMIT", f"Actual tokens: {actual}"
            except:
                return False, "TOKEN_LIMIT", error_lines[0][:100]
        return False, "TOKEN_LIMIT", "Token limit exceeded"

    elif "CUDA out of memory" in stdout or "OOM" in stdout:
        return False, "OOM", "Out of memory"

    elif "ERROR" in stdout:
        error_lines = [l for l in stdout.split("\n") if "ERROR" in l]
        return False, "ERROR", error_lines[0][:100] if error_lines else "Unknown error"

    else:
        return False, "UNKNOWN", "No success or error message found"


def binary_search_boundary(ssh, low_res, high_res, use_offload=True):
    """Binary search to find exact resolution boundary.

    Args:
        low_res: tuple (width, height) that works
        high_res: tuple (width, height) that fails
    """
    low_w, low_h = low_res
    high_w, high_h = high_res

    results = []

    while (high_w * high_h) - (low_w * low_h) > 5000:  # Stop when within 5000 pixels
        # Calculate midpoint maintaining aspect ratio
        mid_pixels = (low_w * low_h + high_w * high_h) // 2
        aspect_ratio = 16 / 9
        mid_h = int((mid_pixels / aspect_ratio) ** 0.5)
        mid_w = int(mid_h * aspect_ratio)

        # Round to nearest even numbers for video encoding
        mid_w = (mid_w // 2) * 2
        mid_h = (mid_h // 2) * 2

        print(f"\nBinary search: Testing {mid_w}x{mid_h}")
        success, status, error = test_resolution(ssh, mid_w, mid_h, use_offload)

        result = {
            "resolution": f"{mid_w}x{mid_h}",
            "pixels": mid_w * mid_h,
            "estimated_tokens": int(mid_w * mid_h * 2 * 0.0173),
            "success": success,
            "status": status,
            "error": error,
        }
        results.append(result)

        if success:
            low_w, low_h = mid_w, mid_h
            print(f"    [WORKS] - new lower bound: {mid_w}x{mid_h}")
        else:
            high_w, high_h = mid_w, mid_h
            print(f"    [FAILS] - new upper bound: {mid_w}x{mid_h}")

        time.sleep(2)  # Prevent overwhelming the system

    return results, (low_w, low_h), (high_w, high_h)


def main():
    cm = ConfigManager()

    print("=" * 80)
    print("RESOLUTION BOUNDARY TESTING FOR COSMOS TRANSFER1 UPSAMPLING")
    print("=" * 80)

    all_results = []

    with SSHManager(cm.get_ssh_options()) as ssh:
        # Clean up any running containers first
        print("\nCleaning up any existing containers...")
        ssh.execute_command("sudo docker container prune -f", timeout=30, stream_output=False)

        # Test specific resolutions first to establish boundaries
        print("\n" + "=" * 60)
        print("PHASE 1: Testing specific resolutions")
        print("=" * 60)

        test_resolutions = [
            (940, 529),  # Known to work
            (950, 534),  # Between 940x529 and 960x540
            (960, 540),  # Previously unclear
            (970, 546),  # Slightly above 960x540
            (1024, 576),  # 576p
            (1280, 720),  # 720p HD - known to fail
        ]

        for width, height in test_resolutions:
            success, status, error = test_resolution(ssh, width, height, use_offload=True)

            result = {
                "resolution": f"{width}x{height}",
                "pixels": width * height,
                "estimated_tokens": int(width * height * 2 * 0.0173),
                "success": success,
                "status": status,
                "error": error,
            }
            all_results.append(result)

            if success:
                print(f"    [PASS] {status}")
            else:
                print(f"    [FAIL] {status}: {error[:50]}")

            time.sleep(3)

        # Find working and failing boundaries
        working = [r for r in all_results if r["success"]]
        failing = [r for r in all_results if not r["success"] and r["status"] != "SKIP"]

        if working and failing:
            max_working = max(working, key=lambda x: x["pixels"])
            min_failing = min(failing, key=lambda x: x["pixels"])

            print("\n" + "=" * 60)
            print("PHASE 2: Binary search for exact boundary")
            print("=" * 60)
            print(f"Searching between {max_working['resolution']} and {min_failing['resolution']}")

            # Extract resolution tuples
            max_w, max_h = map(int, max_working["resolution"].split("x"))
            min_w, min_h = map(int, min_failing["resolution"].split("x"))

            binary_results, final_low, final_high = binary_search_boundary(
                ssh, (max_w, max_h), (min_w, min_h), use_offload=True
            )
            all_results.extend(binary_results)

            print("\n" + "=" * 60)
            print(
                f"FINAL BOUNDARY: Between {final_low[0]}x{final_low[1]} and {final_high[0]}x{final_high[1]}"
            )
            print(f"Pixel difference: {final_high[0]*final_high[1] - final_low[0]*final_low[1]:,}")
            print("=" * 60)

        # Test without offloading for comparison
        print("\n" + "=" * 60)
        print("PHASE 3: Testing memory impact (--no-offload)")
        print("=" * 60)

        memory_test_resolutions = [
            (640, 360),  # Should work
            (854, 480),  # 480p
            (960, 540),  # Test if OOM was the issue
        ]

        for width, height in memory_test_resolutions:
            print(f"\nTesting {width}x{height} without offloading...")
            success, status, error = test_resolution(ssh, width, height, use_offload=False)

            if success:
                print("    [WORKS] without offloading")
            elif status == "OOM":
                print("    [OOM] without offloading (expected)")
            else:
                print(f"    [FAIL] {status}: {error[:50]}")

            time.sleep(3)

    # Save all results
    output_file = Path("resolution_boundary_results.json")
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n\nResults saved to {output_file}")

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY OF FINDINGS")
    print("=" * 80)

    working_resolutions = sorted(
        [r for r in all_results if r["success"]], key=lambda x: x["pixels"]
    )

    if working_resolutions:
        print("\n### Maximum Working Resolution:")
        max_res = working_resolutions[-1]
        print(f"  {max_res['resolution']} ({max_res['pixels']:,} pixels)")
        print(f"  Estimated tokens: {max_res['estimated_tokens']}")
        if "Actual" in max_res.get("error", ""):
            print(f"  {max_res['error']}")

    print("\n### All Working Resolutions:")
    for r in working_resolutions:
        print(f"  [PASS] {r['resolution']} ({r['pixels']:,} pixels)")

    failing_resolutions = sorted(
        [r for r in all_results if not r["success"] and r["status"] != "SKIP"],
        key=lambda x: x["pixels"],
    )

    if failing_resolutions:
        print("\n### Failed Resolutions:")
        for r in failing_resolutions:
            print(f"  [FAIL] {r['resolution']} ({r['pixels']:,} pixels) - {r['status']}")
            if "Actual tokens" in r.get("error", ""):
                print(f"     {r['error']}")


if __name__ == "__main__":
    main()
