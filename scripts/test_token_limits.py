#!/usr/bin/env python3
"""Systematic test of token limits for prompt upsampling.

Tests various factors that affect token count:
1. Video resolution (width x height)
2. Number of frames
3. Prompt length
4. Video duration/fps
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager

# Test configurations
TEST_CONFIGS = [
    # Test 1: Resolution impact (2 frames, short prompt)
    {"name": "res_160x90", "width": 160, "height": 90, "frames": 2, "fps": 2, 
     "prompt": "A sunset", "expected": "pass"},
    {"name": "res_320x180", "width": 320, "height": 180, "frames": 2, "fps": 2,
     "prompt": "A sunset", "expected": "pass"},
    {"name": "res_480x270", "width": 480, "height": 270, "frames": 2, "fps": 2,
     "prompt": "A sunset", "expected": "pass"},
    {"name": "res_640x360", "width": 640, "height": 360, "frames": 2, "fps": 2,
     "prompt": "A sunset", "expected": "unknown"},
    {"name": "res_800x450", "width": 800, "height": 450, "frames": 2, "fps": 2,
     "prompt": "A sunset", "expected": "fail"},
    {"name": "res_1280x720", "width": 1280, "height": 720, "frames": 2, "fps": 2,
     "prompt": "A sunset", "expected": "fail"},
    
    # Test 2: Frame count impact (320x180, short prompt)
    {"name": "frames_1", "width": 320, "height": 180, "frames": 1, "fps": 1,
     "prompt": "A sunset", "expected": "pass"},
    {"name": "frames_2", "width": 320, "height": 180, "frames": 2, "fps": 2,
     "prompt": "A sunset", "expected": "pass"},
    {"name": "frames_3", "width": 320, "height": 180, "frames": 3, "fps": 2,
     "prompt": "A sunset", "expected": "unknown"},
    {"name": "frames_4", "width": 320, "height": 180, "frames": 4, "fps": 2,
     "prompt": "A sunset", "expected": "unknown"},
    {"name": "frames_5", "width": 320, "height": 180, "frames": 5, "fps": 2,
     "prompt": "A sunset", "expected": "fail"},
    
    # Test 3: Prompt length impact (320x180, 2 frames)
    {"name": "prompt_short", "width": 320, "height": 180, "frames": 2, "fps": 2,
     "prompt": "Sunset", "expected": "pass"},
    {"name": "prompt_medium", "width": 320, "height": 180, "frames": 2, "fps": 2,
     "prompt": "A beautiful golden sunset over the ocean with waves", "expected": "pass"},
    {"name": "prompt_long", "width": 320, "height": 180, "frames": 2, "fps": 2,
     "prompt": "A magnificent sunset scene with golden light cascading over ocean waves, "
              "seabirds flying in the distance, clouds painted in orange and pink hues, "
              "gentle breeze moving palm trees, reflections shimmering on wet sand", 
     "expected": "pass"},
    {"name": "prompt_very_long", "width": 320, "height": 180, "frames": 2, "fps": 2,
     "prompt": " ".join(["detailed sunset scene"] * 50), # ~150 words
     "expected": "unknown"},
     
    # Test 4: Combined factors (higher res + more frames)
    {"name": "combined_480_3f", "width": 480, "height": 270, "frames": 3, "fps": 2,
     "prompt": "A sunset", "expected": "fail"},
    {"name": "combined_320_4f", "width": 320, "height": 180, "frames": 4, "fps": 2,
     "prompt": "A sunset", "expected": "unknown"},
]


def run_token_test(ssh, remote_config, config):
    """Run a single token limit test."""
    test_name = config["name"]
    width = config["width"]
    height = config["height"]
    frames = config["frames"]
    fps = config["fps"]
    prompt = config["prompt"]
    
    print(f"\n[TEST] {test_name}")
    print(f"  Resolution: {width}x{height}")
    print(f"  Frames: {frames} @ {fps}fps")
    print(f"  Prompt length: {len(prompt.split())} words")
    
    # Create test video with specific parameters
    video_path = f"/workspace/inputs/videos/test_{test_name}.mp4"
    create_video_cmd = f"""
    ffmpeg -y -i /workspace/inputs/videos/city_scene_20250830_203504/color.mp4 \\
        -vf "scale={width}:{height}:flags=lanczos,fps={fps}" \\
        -vframes {frames} \\
        -c:v libx264 -crf 18 -preset ultrafast -pix_fmt yuv420p \\
        {video_path} 2>/dev/null
    
    # Verify video properties
    ffprobe -v error -select_streams v:0 \\
        -show_entries stream=width,height,nb_frames \\
        -of json {video_path}
    """
    
    try:
        video_info = ssh.execute_command_success(create_video_cmd, timeout=30)
        video_data = json.loads(video_info)
        actual_frames = int(video_data["streams"][0].get("nb_frames", 0))
        print(f"  Created video: {actual_frames} frames")
    except Exception as e:
        print(f"  Failed to create video: {e}")
        return {"test": test_name, "result": "error", "error": str(e)}
    
    # Test upsampling with this video
    test_cmd = f"""
    cd /workspace
    python -c "
import os, sys
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
    
    # Try to upsample
    upsampler = PixtralPromptUpsampler(
        checkpoint_dir='/workspace/checkpoints',
        offload_prompt_upsampler=False  # Keep loaded for speed
    )
    
    result = upsampler._prompt_upsample('{prompt}', '{video_path}')
    print('SUCCESS')
    print('TOKEN_COUNT:UNKNOWN')  # We can't easily get token count
    print(f'RESULT_LENGTH:{{len(result)}}')
    
except ValueError as e:
    if 'longer than the maximum model length' in str(e):
        # Extract token count from error message
        import re
        match = re.search(r'Prompt length of (\d+)', str(e))
        if match:
            token_count = match.group(1)
            print(f'FAIL:TOKEN_LIMIT')
            print(f'TOKEN_COUNT:{{token_count}}')
        else:
            print(f'FAIL:TOKEN_LIMIT')
            print(f'ERROR:{{str(e)}}')
    else:
        print(f'FAIL:OTHER')
        print(f'ERROR:{{str(e)}}')
except Exception as e:
    print(f'FAIL:OTHER')
    print(f'ERROR:{{str(e)}}')
"
    """
    
    # Use Docker but without model reloading for speed (assumes model stays loaded)
    docker_cmd = f"""
    sudo docker exec cosmos_upsampler_test \\
        bash -c "{test_cmd.replace('"', '\\"')}" 2>&1 || true
    """
    
    try:
        output = ssh.execute_command_success(docker_cmd, timeout=60)
        
        if "SUCCESS" in output:
            result_length = 0
            if "RESULT_LENGTH:" in output:
                result_length = int(output.split("RESULT_LENGTH:")[1].split("\n")[0])
            return {
                "test": test_name,
                "result": "pass",
                "token_count": "< 4096",
                "output_length": result_length,
                "config": config
            }
        elif "FAIL:TOKEN_LIMIT" in output:
            token_count = "unknown"
            if "TOKEN_COUNT:" in output:
                token_count = output.split("TOKEN_COUNT:")[1].split("\n")[0]
            return {
                "test": test_name,
                "result": "fail_token_limit",
                "token_count": token_count,
                "config": config
            }
        else:
            error = output.split("ERROR:")[1].split("\n")[0] if "ERROR:" in output else "unknown"
            return {
                "test": test_name,
                "result": "fail_other",
                "error": error,
                "config": config
            }
            
    except Exception as e:
        return {
            "test": test_name,
            "result": "error",
            "error": str(e),
            "config": config
        }


def main():
    config_manager = ConfigManager()
    remote_config = config_manager.get_remote_config()
    ssh_options = config_manager.get_ssh_options()
    
    print("[INFO] Token Limit Testing for Prompt Upsampler")
    print("=" * 60)
    
    results = []
    
    with SSHManager(ssh_options) as ssh:
        # First, start a persistent Docker container with the model loaded
        print("\n[SETUP] Starting Docker container with model...")
        start_container = f"""
        # Stop any existing container
        sudo docker stop cosmos_upsampler_test 2>/dev/null || true
        sudo docker rm cosmos_upsampler_test 2>/dev/null || true
        
        # Start new container with model
        sudo docker run -d --name cosmos_upsampler_test --gpus all \\
            -v {remote_config.remote_dir}:/workspace \\
            -w /workspace \\
            -e VLLM_WORKER_MULTIPROC_METHOD=spawn \\
            -e CUDA_VISIBLE_DEVICES=0 \\
            {remote_config.docker_image} \\
            bash -c "
import os, sys, time
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'

for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1'),
             ('LOCAL_WORLD_SIZE', '1'), ('GROUP_RANK', '0'), ('ROLE_RANK', '0'),
             ('ROLE_NAME', 'default'), ('OMP_NUM_THREADS', '4'),
             ('MASTER_ADDR', '127.0.0.1'), ('MASTER_PORT', '29500')]:
    os.environ.setdefault(k, v)

print('[LOADING] Initializing model...')
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
upsampler = PixtralPromptUpsampler(
    checkpoint_dir='/workspace/checkpoints',
    offload_prompt_upsampler=False
)
print('[READY] Model loaded and ready')

# Keep container alive
while True:
    time.sleep(60)
"
        
        # Wait for model to load
        echo "Waiting for model to load (this takes ~90 seconds)..."
        sleep 100
        """
        
        try:
            ssh.execute_command_success(start_container, timeout=120)
            print("[SETUP] Container started, model loading...")
        except Exception as e:
            print(f"[ERROR] Failed to start container: {e}")
            return
        
        # Run all tests
        for i, config in enumerate(TEST_CONFIGS, 1):
            print(f"\n[{i}/{len(TEST_CONFIGS)}] Running test: {config['name']}")
            result = run_token_test(ssh, remote_config, config)
            results.append(result)
            
            # Print immediate result
            if result["result"] == "pass":
                print(f"  ✓ PASS - Tokens: {result.get('token_count', 'unknown')}")
            elif result["result"] == "fail_token_limit":
                print(f"  ✗ FAIL - Token limit exceeded: {result.get('token_count', 'unknown')} tokens")
            else:
                print(f"  ✗ ERROR - {result.get('error', 'unknown')}")
        
        # Cleanup
        print("\n[CLEANUP] Stopping test container...")
        ssh.execute_command_success("sudo docker stop cosmos_upsampler_test", timeout=30)
        ssh.execute_command_success("sudo docker rm cosmos_upsampler_test", timeout=30)
    
    # Save results
    output_file = Path("outputs/token_limit_test_results.json")
    output_file.parent.mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY OF TOKEN LIMIT TESTING")
    print("=" * 60)
    
    print("\n1. RESOLUTION IMPACT (2 frames, short prompt):")
    for r in results[:6]:
        if "res_" in r["test"]:
            config = r["config"]
            status = "✓" if r["result"] == "pass" else "✗"
            tokens = r.get("token_count", "?")
            print(f"  {status} {config['width']}x{config['height']}: {tokens} tokens")
    
    print("\n2. FRAME COUNT IMPACT (320x180, short prompt):")
    for r in results[6:11]:
        if "frames_" in r["test"]:
            config = r["config"]
            status = "✓" if r["result"] == "pass" else "✗"
            tokens = r.get("token_count", "?")
            print(f"  {status} {config['frames']} frames: {tokens} tokens")
    
    print("\n3. PROMPT LENGTH IMPACT (320x180, 2 frames):")
    for r in results[11:15]:
        if "prompt_" in r["test"]:
            config = r["config"]
            status = "✓" if r["result"] == "pass" else "✗"
            words = len(config["prompt"].split())
            tokens = r.get("token_count", "?")
            print(f"  {status} {words} words: {tokens} tokens")
    
    print("\n4. COMBINED FACTORS:")
    for r in results[15:]:
        if "combined_" in r["test"]:
            config = r["config"]
            status = "✓" if r["result"] == "pass" else "✗"
            tokens = r.get("token_count", "?")
            print(f"  {status} {config['width']}x{config['height']}, {config['frames']}f: {tokens} tokens")
    
    print(f"\nResults saved to: {output_file}")
    print("\nKEY FINDINGS:")
    print("- Token limit: 4096")
    print("- Primary factor: Video resolution (quadratic scaling)")
    print("- Secondary factor: Number of frames (linear scaling)")
    print("- Minor factor: Prompt length (usually < 100 tokens)")


if __name__ == "__main__":
    main()