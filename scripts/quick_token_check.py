#!/usr/bin/env python3
"""Quick token limit check with specific resolutions."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager

config_manager = ConfigManager()
remote_config = config_manager.get_remote_config()
ssh_options = config_manager.get_ssh_options()

# Test these specific sizes
tests = [
    ("320x180_2f", 320, 180, 2),  # Known to work
    ("400x225_2f", 400, 225, 2),  # Test
    ("480x270_2f", 480, 270, 2),  # Test  
    ("640x360_2f", 640, 360, 2),  # Failed before at 640x480
]

print("[INFO] Quick Token Limit Check")
print("=" * 60)

with SSHManager(ssh_options) as ssh:
    for name, width, height, frames in tests:
        print(f"\n[TEST] {name}: {width}x{height}, {frames} frames")
        
        # Create video and test in one command
        cmd = f"""
        cd {remote_config.remote_dir}
        
        # Create test video
        ffmpeg -y -i inputs/videos/city_scene_20250830_203504/color.mp4 \\
            -vf "scale={width}:{height}:flags=lanczos" \\
            -vframes {frames} \\
            -c:v libx264 -preset ultrafast -pix_fmt yuv420p \\
            inputs/videos/test_{name}.mp4 2>/dev/null
        
        echo "Video created: test_{name}.mp4"
        
        # Test with minimal Docker command
        sudo docker run --rm --gpus all \\
            -v {remote_config.remote_dir}:/workspace \\
            -e VLLM_WORKER_MULTIPROC_METHOD=spawn \\
            {remote_config.docker_image} \\
            python -c "
import os, sys, re
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'
for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1')]:
    os.environ.setdefault(k, v)

from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
upsampler = PixtralPromptUpsampler('/workspace/checkpoints', True)

try:
    upsampler._prompt_upsample_with_offload('Test', '/workspace/inputs/videos/test_{name}.mp4')
    print('RESULT:PASS')
except ValueError as e:
    if 'longer than' in str(e):
        match = re.search(r'(\\\d+)', str(e))
        if match:
            print(f'RESULT:FAIL_TOKENS:{{match.group(1)}}')
        else:
            print('RESULT:FAIL_TOKENS')
    else:
        print('RESULT:FAIL_OTHER')
" 2>&1 | grep "RESULT:" | head -1
        """
        
        try:
            output = ssh.execute_command_success(cmd, timeout=180)
            if "PASS" in output:
                print(f"  ✓ PASS - Under 4096 tokens")
            elif "FAIL_TOKENS:" in output:
                tokens = output.split(":")[2] if output.count(":") >= 2 else "?"
                print(f"  ✗ FAIL - {tokens} tokens (exceeds 4096)")
            else:
                print(f"  ? Result: {output}")
        except Exception as e:
            print(f"  ERROR: {str(e)[:100]}")

print("\n" + "=" * 60)
print("Quick test complete!")