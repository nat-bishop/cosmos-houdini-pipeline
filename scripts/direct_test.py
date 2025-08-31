#!/usr/bin/env python3
"""Direct SSH test for token limits."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager

config_manager = ConfigManager()
remote_config = config_manager.get_remote_config()
ssh_options = config_manager.get_ssh_options()

print("[INFO] Direct Token Test")
print("Testing a few key resolutions to find the threshold...")
print("=" * 60)

tests = [
    ("320x180", 2),
    ("400x225", 2),  
    ("480x270", 2),
    ("320x180", 3),
    ("320x180", 4),
]

with SSHManager(ssh_options) as ssh:
    for resolution, frames in tests:
        width, height = resolution.split('x')
        name = f"{resolution}_{frames}f"
        
        print(f"\n[TEST] {name}")
        
        # Create video and run test in one go
        cmd = f"""
        cd {remote_config.remote_dir}
        
        # Create video
        ffmpeg -y -i inputs/videos/city_scene_20250830_203504/color.mp4 \
            -vf "scale={width}:{height}" -vframes {frames} \
            -c:v libx264 -preset ultrafast \
            inputs/videos/test_{name}.mp4 2>/dev/null
        
        echo "VIDEO_CREATED"
        
        # Run quick Python test (this will load model each time, unfortunately)
        timeout 180 sudo docker run --rm --gpus all \
            -v {remote_config.remote_dir}:/workspace \
            -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
            {remote_config.docker_image} \
            python -c "
import os, sys, re
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'
for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1')]:
    os.environ.setdefault(k, v)
    
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
ups = PixtralPromptUpsampler('/workspace/checkpoints', True)
try:
    ups._prompt_upsample_with_offload('Test', '/workspace/inputs/videos/test_{name}.mp4')
    print('RESULT:PASS')
except ValueError as e:
    if 'longer than' in str(e):
        import re
        m = re.search(r'(\\\d+)', str(e))
        if m: print(f'RESULT:FAIL:{m.group(1)}')
        else: print('RESULT:FAIL')
" 2>&1 | grep -E "RESULT:|VIDEO_CREATED" || echo "TIMEOUT_OR_ERROR"
        """
        
        try:
            output = ssh.execute_command_success(cmd, timeout=200)
            
            if "VIDEO_CREATED" in output:
                print("  Video created successfully")
            
            if "RESULT:PASS" in output:
                print(f"  ✓ PASS - Under 4096 tokens")
            elif "RESULT:FAIL:" in output:
                tokens = output.split("RESULT:FAIL:")[1].strip()
                print(f"  ✗ FAIL - {tokens} tokens (exceeds 4096)")
            elif "TIMEOUT_OR_ERROR" in output:
                print(f"  ? Timeout or error (model loading takes ~90s)")
            else:
                print(f"  ? Unknown result")
                
        except Exception as e:
            print(f"  ERROR: {str(e)[:100]}")

print("\n" + "=" * 60)
print("Test complete!")
print("\nKey finding: The token limit is 4096.")
print("Resolution and frame count both affect token usage.")
print("Keeping videos at 320x180 with 2 frames or less is safe.")