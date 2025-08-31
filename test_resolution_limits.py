#!/usr/bin/env python3
"""Test script to find exact resolution limits for upsampling."""

import json
import time

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def test_resolution(ssh, width, height):
    """Test upsampling at a specific resolution."""
    # Create test prompt file
    test_prompt = {
        "name": f"test_{width}x{height}",
        "prompt": "Test prompt for resolution limits",
        "video_path": f"/workspace/inputs/videos/test_{width}x{height}.mp4",
    }

    # Upload test file
    test_file = f"test_single_{width}x{height}.json"
    remote_file = f"/home/ubuntu/NatsFS/cosmos-transfer1/{test_file}"
    with ssh.get_sftp() as sftp:
        with sftp.open(remote_file, "w") as f:
            f.write(json.dumps([test_prompt]))

    # Run upsampling
    cmd = f'''sudo docker run --rm --gpus all --ipc=host --shm-size=8g \
        -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
        -v /home/ubuntu/NatsFS/cosmos-transfer1:/workspace \
        -w /workspace \
        nvcr.io/ubuntu/cosmos-transfer1:latest \
        python /workspace/scripts/working_prompt_upsampler.py \
        --batch /workspace/{test_file} \
        --output-dir /workspace/outputs/resolution_test \
        --checkpoint-dir /workspace/checkpoints 2>&1 | grep -E "ERROR|SUCCESS|Prompt length"'''

    exit_code, stdout, stderr = ssh.execute_command(cmd, timeout=180)

    # Check for errors
    if "Prompt length" in stdout or "ERROR" in stdout:
        # Extract error message
        if "Prompt length" in stdout:
            error_line = [l for l in stdout.split("\n") if "Prompt length" in l][0]
            return False, error_line
        else:
            error_line = [l for l in stdout.split("\n") if "ERROR" in l][0]
            return False, error_line
    elif "SUCCESS" in stdout:
        return True, "Success"
    else:
        return False, "Unknown error"


def main():
    cm = ConfigManager()

    # Resolutions to test (from our created videos)
    test_resolutions = [
        (320, 180),  # Known safe
        (384, 216),
        (416, 234),
        (426, 240),  # Expected boundary
        (448, 252),  # Should fail
    ]

    results = []

    with SSHManager(cm.get_ssh_options()) as ssh:
        print("Testing resolution limits for upsampling...")
        print("=" * 60)

        for width, height in test_resolutions:
            pixels = width * height
            estimated_tokens = int(pixels * 2 * 0.0173)  # 2 frames

            print(f"\nTesting {width}x{height} ({pixels:,} pixels, ~{estimated_tokens} tokens)")
            print("-" * 40)

            # Check if video exists
            check_cmd = f"ls -la /home/ubuntu/NatsFS/cosmos-transfer1/inputs/videos/test_{width}x{height}.mp4 2>/dev/null | wc -l"
            result = ssh.execute_command_success(check_cmd)

            if result.strip() == "0":
                print("  Video not found, skipping")
                continue

            success, message = test_resolution(ssh, width, height)

            result_entry = {
                "resolution": f"{width}x{height}",
                "pixels": pixels,
                "estimated_tokens": estimated_tokens,
                "success": success,
                "message": message,
            }
            results.append(result_entry)

            if success:
                print("  [SUCCESS] - Upsampling completed")
            else:
                print(f"  [FAILED] - {message}")

            # Small delay between tests
            time.sleep(2)

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    print("\n### Working Resolutions:")
    for r in results:
        if r["success"]:
            print(f"  {r['resolution']} - {r['estimated_tokens']} tokens")

    print("\n### Failed Resolutions:")
    for r in results:
        if not r["success"]:
            print(f"  {r['resolution']} - {r['estimated_tokens']} tokens")
            print(f"    Error: {r['message'][:80]}...")

    # Find the boundary
    working_resolutions = [r for r in results if r["success"]]
    if working_resolutions:
        max_working = max(working_resolutions, key=lambda x: x["pixels"])
        print(f"\n### Maximum Working Resolution: {max_working['resolution']}")
        print(f"    Pixels: {max_working['pixels']:,}")
        print(f"    Tokens: {max_working['estimated_tokens']}")
        print(f"    % of 4096 limit: {max_working['estimated_tokens']/4096*100:.1f}%")

    # Save results
    with open("resolution_test_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to resolution_test_results.json")


if __name__ == "__main__":
    main()
