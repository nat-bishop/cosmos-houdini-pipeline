#!/usr/bin/env python3
"""Simple token limit tests for prompt upsampler."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager

# Simplified test cases
TESTS = [
    # Resolution tests (2 frames each)
    {"name": "160px", "width": 160, "frames": 2},
    {"name": "240px", "width": 240, "frames": 2},
    {"name": "320px", "width": 320, "frames": 2},
    {"name": "400px", "width": 400, "frames": 2},
    {"name": "480px", "width": 480, "frames": 2},
    {"name": "560px", "width": 560, "frames": 2},
    {"name": "640px", "width": 640, "frames": 2},
    
    # Frame count tests (320px width)
    {"name": "1frame", "width": 320, "frames": 1},
    {"name": "2frames", "width": 320, "frames": 2},
    {"name": "3frames", "width": 320, "frames": 3},
    {"name": "4frames", "width": 320, "frames": 4},
]


def main():
    config_manager = ConfigManager()
    remote_config = config_manager.get_remote_config()
    ssh_options = config_manager.get_ssh_options()
    
    print("[INFO] Testing Token Limits for Prompt Upsampler")
    print("=" * 60)
    
    results = []
    
    with SSHManager(ssh_options) as ssh:
        for test in TESTS:
            name = test["name"]
            width = test["width"]
            frames = test["frames"]
            
            print(f"\n[TEST] {name}: {width}px width, {frames} frame(s)")
            
            # Create test video
            height = int(width * 9 / 16)  # 16:9 aspect ratio
            video_file = f"test_{name}.mp4"
            
            create_and_test = f"""
            cd {remote_config.remote_dir}
            
            # Create video with specific size
            ffmpeg -y -i inputs/videos/city_scene_20250830_203504/color.mp4 \\
                -vf "scale={width}:{height}:flags=lanczos" \\
                -vframes {frames} \\
                -c:v libx264 -preset ultrafast -pix_fmt yuv420p \\
                inputs/videos/{video_file} 2>/dev/null
            
            # Test with upsampler
            sudo docker run --rm --gpus all \\
                -v {remote_config.remote_dir}:/workspace \\
                -w /workspace \\
                -e VLLM_WORKER_MULTIPROC_METHOD=spawn \\
                -e CUDA_VISIBLE_DEVICES=0 \\
                {remote_config.docker_image} \\
                python -c "
import os, sys, re
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'

# Set environment
for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1'),
             ('LOCAL_WORLD_SIZE', '1'), ('GROUP_RANK', '0'), ('ROLE_RANK', '0'),
             ('ROLE_NAME', 'default'), ('OMP_NUM_THREADS', '4'),
             ('MASTER_ADDR', '127.0.0.1'), ('MASTER_PORT', '29500')]:
    os.environ.setdefault(k, v)

try:
    from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
    upsampler = PixtralPromptUpsampler(
        checkpoint_dir='/workspace/checkpoints',
        offload_prompt_upsampler=True
    )
    
    result = upsampler._prompt_upsample_with_offload(
        'A sunset', 
        '/workspace/inputs/videos/{video_file}'
    )
    print('PASS')
    
except ValueError as e:
    error_str = str(e)
    if 'longer than the maximum model length' in error_str:
        # Extract token count
        match = re.search(r'Prompt length of (\\\d+)', error_str)
        if match:
            print(f'FAIL_TOKENS:{{match.group(1)}}')
        else:
            print('FAIL_TOKENS:unknown')
    else:
        print(f'FAIL_OTHER')
except Exception as e:
    print(f'FAIL_ERROR')
" 2>&1 | grep -E "PASS|FAIL" | head -1
            """
            
            try:
                output = ssh.execute_command_success(create_and_test, timeout=180)
                output = output.strip()
                
                if "PASS" in output:
                    print(f"  ✓ PASS - Under 4096 tokens")
                    results.append({"test": name, "width": width, "frames": frames, 
                                  "result": "pass", "tokens": "< 4096"})
                elif "FAIL_TOKENS:" in output:
                    tokens = output.split(":")[1]
                    print(f"  ✗ FAIL - {tokens} tokens (exceeds 4096)")
                    results.append({"test": name, "width": width, "frames": frames,
                                  "result": "fail", "tokens": tokens})
                else:
                    print(f"  ? ERROR - {output}")
                    results.append({"test": name, "width": width, "frames": frames,
                                  "result": "error", "output": output})
                    
            except Exception as e:
                print(f"  ? ERROR - {str(e)[:100]}")
                results.append({"test": name, "width": width, "frames": frames,
                              "result": "error", "error": str(e)[:200]})
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print("\nRESOLUTION IMPACT (2 frames):")
    for r in results[:7]:
        if "px" in r["test"]:
            status = "✓" if r["result"] == "pass" else "✗"
            print(f"  {status} {r['width']}px: {r.get('tokens', '?')}")
    
    print("\nFRAME COUNT IMPACT (320px):")
    for r in results[7:]:
        if "frame" in r["test"]:
            status = "✓" if r["result"] == "pass" else "✗"
            print(f"  {status} {r['frames']} frames: {r.get('tokens', '?')}")
    
    # Save results
    output_file = Path("outputs/token_test_results.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")


if __name__ == "__main__":
    main()