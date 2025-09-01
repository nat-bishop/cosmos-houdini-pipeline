#!/usr/bin/env python3
"""Quick resolution test to find the boundary."""

import json
import time

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def quick_test(ssh, width, height):
    """Quick test at a resolution - just check if video creation and prompt work."""
    pixels = width * height
    estimated_tokens = int(pixels * 2 * 0.0173)

    print(f"\nTesting {width}x{height} ({pixels:,} pixels)")
    print(f"  Estimated tokens: {estimated_tokens}")

    # Create test video
    cmd = f"""cd /home/ubuntu/NatsFS/cosmos-transfer1 && \
ffmpeg -f lavfi -i testsrc2=duration=1:size={width}x{height}:rate=2 \
-frames:v 2 -pix_fmt yuv420p -y inputs/videos/test_{width}x{height}.mp4 2>/dev/null && echo "VIDEO_CREATED" """

    result = ssh.execute_command(cmd, timeout=30, stream_output=False)
    if "VIDEO_CREATED" not in result[1]:
        return "SKIP", "Failed to create video"

    # Create simple prompt
    test_prompt = [
        {
            "name": f"test_{width}x{height}",
            "prompt": "Test",
            "video_path": f"/workspace/inputs/videos/test_{width}x{height}.mp4",
        }
    ]

    test_file = f"quick_test_{width}x{height}.json"
    remote_file = f"/home/ubuntu/NatsFS/cosmos-transfer1/{test_file}"

    with ssh.get_sftp() as sftp:
        with sftp.open(remote_file, "w") as f:
            f.write(json.dumps(test_prompt))

    # Run upsampling with offloading (safer for memory)
    cmd = f"""sudo docker run --rm --gpus all --ipc=host --shm-size=8g \
-e VLLM_WORKER_MULTIPROC_METHOD=spawn \
-v /home/ubuntu/NatsFS/cosmos-transfer1:/workspace \
-w /workspace \
nvcr.io/ubuntu/cosmos-transfer1:latest \
python /workspace/scripts/working_prompt_upsampler.py \
--batch /workspace/{test_file} \
--output-dir /workspace/outputs/quick_test \
--checkpoint-dir /workspace/checkpoints 2>&1 | tail -100"""

    exit_code, stdout, stderr = ssh.execute_command(cmd, timeout=180, stream_output=False)

    # Check results
    if "SUCCESS: Batch processing completed" in stdout:
        # Try to extract actual token count
        for line in stdout.split("\n"):
            if "actual" in line.lower() and "token" in line.lower():
                print(f"  Found: {line.strip()}")
        return "PASS", "Success"
    elif "Prompt length" in stdout and "longer than" in stdout:
        # Extract actual tokens
        for line in stdout.split("\n"):
            if "Prompt length" in line:
                try:
                    actual = line.split("Prompt length of")[1].split("is")[0].strip()
                    return "FAIL", f"Token limit - actual: {actual}"
                except:
                    pass
        return "FAIL", "Token limit exceeded"
    elif "CUDA out of memory" in stdout:
        return "OOM", "Out of memory"
    else:
        return "ERROR", "Unknown error"


def main():
    cm = ConfigManager()

    # Key resolutions to test
    test_resolutions = [
        (350, 197),  # Small - should work
        (940, 529),  # Previously worked
        (950, 534),  # Between 940 and 960
        (960, 540),  # Unclear status
        (970, 546),  # Slightly above 960
        (980, 551),  # Further up
        (1024, 576),  # 576p
    ]

    results = []

    print("=" * 70)
    print("QUICK RESOLUTION BOUNDARY TEST")
    print("=" * 70)

    with SSHManager(cm.get_ssh_options()) as ssh:
        # Clean up
        print("\nCleaning up containers...")
        ssh.execute_command("sudo docker container prune -f", timeout=30, stream_output=False)

        for width, height in test_resolutions:
            status, message = quick_test(ssh, width, height)

            result = {
                "resolution": f"{width}x{height}",
                "pixels": width * height,
                "estimated_tokens": int(width * height * 2 * 0.0173),
                "success": status == "PASS",
                "status": status,
                "error": message,
            }
            results.append(result)

            if status == "PASS":
                print("  Result: [PASS]")
            else:
                print(f"  Result: [{status}] {message}")

            time.sleep(2)

    # Save and summarize
    with open("resolution_boundary_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    working = [r for r in results if r["success"]]
    failing = [r for r in results if not r["success"] and r["status"] != "SKIP"]

    if working:
        max_working = max(working, key=lambda x: x["pixels"])
        print(f"\nMaximum working: {max_working['resolution']} ({max_working['pixels']:,} pixels)")

    if failing:
        min_failing = min(failing, key=lambda x: x["pixels"])
        print(f"Minimum failing: {min_failing['resolution']} ({min_failing['pixels']:,} pixels)")

    print("\nAll results:")
    for r in results:
        status = "[PASS]" if r["success"] else f"[{r['status']}]"
        print(f"  {r['resolution']}: {status} - {r['error']}")


if __name__ == "__main__":
    main()
