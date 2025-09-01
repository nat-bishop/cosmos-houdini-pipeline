#!/usr/bin/env python3
"""Simple test to check resolution boundaries - fast version."""

import json

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def main():
    cm = ConfigManager()

    # Test just a few key resolutions
    test_cases = [
        (350, 197),  # Known to work
        (940, 529),  # Worked in previous tests
        (950, 534),  # Between boundaries
        (960, 540),  # Unclear
    ]

    results = []

    print("RESOLUTION BOUNDARY TEST - SIMPLE")
    print("=" * 60)

    with SSHManager(cm.get_ssh_options()) as ssh:
        for width, height in test_cases:
            pixels = width * height
            tokens = int(pixels * 2 * 0.0173)

            print(f"\n{width}x{height} ({pixels:,} px, ~{tokens} tokens)")

            # Just create the video
            cmd = f"cd /home/ubuntu/NatsFS/cosmos-transfer1 && ffmpeg -f lavfi -i testsrc2=size={width}x{height}:rate=2 -frames:v 2 -y inputs/videos/test_{width}x{height}.mp4 2>&1 | grep -E 'frame=|Video:' | tail -1"

            exit_code, stdout, stderr = ssh.execute_command(cmd, timeout=10, stream_output=False)

            if exit_code == 0:
                print("  Video created successfully")
                results.append(
                    {
                        "resolution": f"{width}x{height}",
                        "pixels": pixels,
                        "estimated_tokens": tokens,
                        "status": "VIDEO_OK",
                    }
                )
            else:
                print("  Failed to create video")
                results.append(
                    {
                        "resolution": f"{width}x{height}",
                        "pixels": pixels,
                        "estimated_tokens": tokens,
                        "status": "VIDEO_FAIL",
                    }
                )

    # Save results
    with open("resolution_boundary_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 60)
    print("Results saved to resolution_boundary_results.json")


if __name__ == "__main__":
    main()
