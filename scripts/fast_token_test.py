#!/usr/bin/env python3
"""Fast token limit test - creates all videos first then tests in one go."""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager


def main():
    config_manager = ConfigManager()
    remote_config = config_manager.get_remote_config()
    ssh_options = config_manager.get_ssh_options()
    
    print("[INFO] Fast Token Limit Test")
    print("=" * 60)
    
    # Test configurations
    tests = [
        # Resolution tests (2 frames, maintaining ~16:9 aspect)
        {"name": "160x90_2f", "width": 160, "height": 90, "frames": 2},
        {"name": "240x135_2f", "width": 240, "height": 135, "frames": 2},
        {"name": "320x180_2f", "width": 320, "height": 180, "frames": 2},
        {"name": "400x225_2f", "width": 400, "height": 225, "frames": 2},
        {"name": "480x270_2f", "width": 480, "height": 270, "frames": 2},
        {"name": "560x315_2f", "width": 560, "height": 315, "frames": 2},
        {"name": "640x360_2f", "width": 640, "height": 360, "frames": 2},
        {"name": "720x405_2f", "width": 720, "height": 405, "frames": 2},
        
        # Frame tests (320x180)
        {"name": "320x180_1f", "width": 320, "height": 180, "frames": 1},
        {"name": "320x180_3f", "width": 320, "height": 180, "frames": 3},
        {"name": "320x180_4f", "width": 320, "height": 180, "frames": 4},
        
        # Edge cases
        {"name": "360x203_2f", "width": 360, "height": 203, "frames": 2},
        {"name": "380x214_2f", "width": 380, "height": 214, "frames": 2},
        {"name": "420x236_2f", "width": 420, "height": 236, "frames": 2},
        {"name": "440x248_2f", "width": 440, "height": 248, "frames": 2},
    ]
    
    with SSHManager(ssh_options) as ssh:
        # Step 1: Create all test videos
        print("\n[1/3] Creating test videos...")
        for test in tests:
            cmd = f"""
            cd {remote_config.remote_dir}
            ffmpeg -y -i inputs/videos/city_scene_20250830_203504/color.mp4 \\
                -vf "scale={test['width']}:{test['height']}:flags=lanczos" \\
                -vframes {test['frames']} \\
                -c:v libx264 -preset ultrafast -pix_fmt yuv420p \\
                inputs/videos/token_test_{test['name']}.mp4 2>/dev/null
            """
            ssh.execute_command_success(cmd, timeout=10)
            print(f"  Created: {test['name']}")
        
        # Step 2: Create Python test script
        print("\n[2/3] Creating test script...")
        test_script = """
import os, sys, re
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'

# Set environment
for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1'),
             ('LOCAL_WORLD_SIZE', '1'), ('GROUP_RANK', '0'), ('ROLE_RANK', '0'),
             ('ROLE_NAME', 'default'), ('OMP_NUM_THREADS', '4'),
             ('MASTER_ADDR', '127.0.0.1'), ('MASTER_PORT', '29500')]:
    os.environ.setdefault(k, v)

print('[INIT] Loading model...')
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
upsampler = PixtralPromptUpsampler(
    checkpoint_dir='/workspace/checkpoints',
    offload_prompt_upsampler=False  # Keep loaded for speed
)
print('[READY] Model loaded')

# Test each video
test_configs = """ + json.dumps(tests) + """

results = []
for config in test_configs:
    name = config['name']
    video_path = f'/workspace/inputs/videos/token_test_{name}.mp4'
    
    try:
        # Short prompt to isolate video token impact
        result = upsampler._prompt_upsample('Sunset scene', video_path)
        print(f'PASS:{name}')
        results.append({'test': name, 'result': 'pass'})
    except ValueError as e:
        error_str = str(e)
        if 'longer than the maximum model length' in error_str:
            match = re.search(r'Prompt length of (\\d+)', error_str)
            if match:
                tokens = match.group(1)
                print(f'FAIL:{name}:TOKENS:{tokens}')
                results.append({'test': name, 'result': 'fail', 'tokens': int(tokens)})
            else:
                print(f'FAIL:{name}:TOKENS:unknown')
                results.append({'test': name, 'result': 'fail'})
        else:
            print(f'ERROR:{name}')
            results.append({'test': name, 'result': 'error'})
    except Exception as e:
        print(f'ERROR:{name}:{str(e)[:50]}')
        results.append({'test': name, 'result': 'error'})

# Save results
import json
with open('/workspace/outputs/token_test_results.json', 'w') as f:
    json.dump(results, f, indent=2)

print('\\nSUMMARY:')
for r in results:
    if r['result'] == 'pass':
        print(f"  ✓ {r['test']}: < 4096 tokens")
    elif r['result'] == 'fail':
        tokens = r.get('tokens', '?')
        print(f"  ✗ {r['test']}: {tokens} tokens")
    else:
        print(f"  ? {r['test']}: error")
"""
        
        # Save script
        with ssh.get_sftp() as sftp:
            script_path = f"{remote_config.remote_dir}/test_tokens.py"
            sftp.putfo(script_script.encode(), script_path)
        
        # Step 3: Run all tests in one Docker session
        print("\n[3/3] Running tests (model load ~90s, then fast)...")
        docker_cmd = f"""
        cd {remote_config.remote_dir}
        sudo docker run --rm --gpus all \\
            -v {remote_config.remote_dir}:/workspace \\
            -w /workspace \\
            -e VLLM_WORKER_MULTIPROC_METHOD=spawn \\
            -e CUDA_VISIBLE_DEVICES=0 \\
            {remote_config.docker_image} \\
            python /workspace/test_tokens.py
        """
        
        try:
            output = ssh.execute_command(docker_cmd, timeout=300, stream_output=False)
            exit_code, stdout, stderr = output
            
            # Parse results
            print("\n" + "=" * 60)
            print("RESULTS")
            print("=" * 60)
            
            # Extract summary from output
            if "SUMMARY:" in stdout:
                summary_start = stdout.find("SUMMARY:")
                summary = stdout[summary_start:]
                print(summary)
            
            # Load and analyze results
            try:
                results_json = ssh.execute_command_success(
                    f"cat {remote_config.remote_dir}/outputs/token_test_results.json"
                )
                results = json.loads(results_json)
                
                # Find threshold
                print("\n" + "=" * 60)
                print("ANALYSIS")
                print("=" * 60)
                
                # Resolution threshold
                print("\nRESOLUTION THRESHOLD (2 frames):")
                last_pass = None
                first_fail = None
                for r in results[:8]:
                    if r['result'] == 'pass':
                        last_pass = r['test']
                    elif r['result'] == 'fail' and first_fail is None:
                        first_fail = r['test']
                
                if last_pass and first_fail:
                    print(f"  ✓ Last passing: {last_pass}")
                    print(f"  ✗ First failing: {first_fail}")
                    # Extract resolution
                    last_w = int(last_pass.split('x')[0])
                    first_w = int(first_fail.split('x')[0])
                    print(f"  → Threshold between {last_w}px and {first_w}px width")
                
                # Frame threshold
                print("\nFRAME THRESHOLD (320x180):")
                frame_results = [(r['test'], r['result']) for r in results if '320x180' in r['test']]
                for name, result in frame_results:
                    frames = name.split('_')[1].replace('f', '')
                    status = "✓" if result == "pass" else "✗"
                    print(f"  {status} {frames} frame(s)")
                
                # Token calculation
                print("\nTOKEN USAGE PATTERNS:")
                for r in results:
                    if r['result'] == 'fail' and 'tokens' in r:
                        test = r['test']
                        tokens = r['tokens']
                        # Parse dimensions
                        parts = test.split('_')
                        dims = parts[0].split('x')
                        width = int(dims[0])
                        height = int(dims[1])
                        frames = int(parts[1].replace('f', ''))
                        
                        # Estimate tokens per pixel per frame
                        pixels = width * height
                        total_pixels = pixels * frames
                        tokens_per_1k_pixels = tokens / (total_pixels / 1000)
                        
                        print(f"  {test}: {tokens} tokens")
                        print(f"    → {width}x{height} = {pixels:,} pixels/frame")
                        print(f"    → {frames} frames = {total_pixels:,} total pixels")
                        print(f"    → ~{tokens_per_1k_pixels:.1f} tokens per 1K pixels")
                
            except Exception as e:
                print(f"Could not load results: {e}")
                
        except Exception as e:
            print(f"Test execution failed: {e}")
    
    print("\n[DONE] Test complete")


if __name__ == "__main__":
    main()