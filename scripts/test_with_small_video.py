#!/usr/bin/env python3
"""Test upsampler with properly sized video to avoid token limit."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager

config_manager = ConfigManager()
remote_config = config_manager.get_remote_config()
ssh_options = config_manager.get_ssh_options()

print("[INFO] Connecting to remote...")

with SSHManager(ssh_options) as ssh:
    # First, create a smaller test video (2 frames, 320px width)
    print("[INFO] Creating small test video...")
    create_small_video = f"""
    cd {remote_config.remote_dir}
    ffmpeg -y -i inputs/videos/city_scene_20250830_203504/color.mp4 \\
        -vf "scale=320:-2:flags=lanczos,fps=2" \\
        -vframes 2 \\
        -c:v libx264 -crf 18 -preset medium -pix_fmt yuv420p \\
        inputs/videos/test_small.mp4
    
    # Check the result
    ffprobe -v error -show_entries stream=width,height,nb_frames \\
        -of default=noprint_wrappers=1 \\
        inputs/videos/test_small.mp4
    """
    
    result = ssh.execute_command_success(create_small_video)
    print("Small video created:")
    print(result)
    
    # Now test the upsampler with the small video
    print("\n[INFO] Testing upsampler with small video...")
    test_cmd = f"""
    cd {remote_config.remote_dir}
    sudo docker run --rm --gpus all \\
        -v {remote_config.remote_dir}:/workspace \\
        -w /workspace \\
        -e VLLM_WORKER_MULTIPROC_METHOD=spawn \\
        -e CUDA_VISIBLE_DEVICES=0 \\
        {remote_config.docker_image} \\
        python -c "
import os
import sys
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'

# Set defaults
for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1'),
             ('LOCAL_WORLD_SIZE', '1'), ('GROUP_RANK', '0'), ('ROLE_RANK', '0'),
             ('ROLE_NAME', 'default'), ('OMP_NUM_THREADS', '4'),
             ('MASTER_ADDR', '127.0.0.1'), ('MASTER_PORT', '29500')]:
    os.environ.setdefault(k, v)

print('[1] Environment ready')

from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
print('[2] Import successful')

print('[3] Initializing upsampler...')
upsampler = PixtralPromptUpsampler(
    checkpoint_dir='/workspace/checkpoints',
    offload_prompt_upsampler=True
)
print('[4] Upsampler initialized!')

print('[5] Testing upsampling with small video...')
result = upsampler._prompt_upsample_with_offload(
    'A beautiful sunset over the ocean with warm golden light', 
    '/workspace/inputs/videos/test_small.mp4'
)
print('[6] Upsampling complete!')
print('\\n=== UPSAMPLED PROMPT ===')
print(result)
print('========================')
"
    """
    
    print("\n[INFO] Running test (model takes ~90 seconds to load)...")
    output = ssh.execute_command(test_cmd, timeout=300, stream_output=True)
    exit_code, stdout, stderr = output
    
    if exit_code == 0:
        print("\n[SUCCESS] Test completed!")
        # Extract just the upsampled prompt from output
        if "=== UPSAMPLED PROMPT ===" in stdout:
            prompt_start = stdout.find("=== UPSAMPLED PROMPT ===")
            prompt_end = stdout.find("========================", prompt_start)
            if prompt_start != -1 and prompt_end != -1:
                upsampled = stdout[prompt_start+24:prompt_end].strip()
                print("\nUpsampled prompt:")
                print(upsampled)
    else:
        print(f"\n[ERROR] Test failed with exit code {exit_code}")
        if "ValueError" in stderr:
            print("Still getting token limit error. Need smaller video.")
        print("STDERR:", stderr[-2000:] if len(stderr) > 2000 else stderr)