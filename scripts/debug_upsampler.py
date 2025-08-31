#!/usr/bin/env python3
"""Debug upsampler to see what's happening."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager

config_manager = ConfigManager()
remote_config = config_manager.get_remote_config()
ssh_options = config_manager.get_ssh_options()

with SSHManager(ssh_options) as ssh:
    # First, check if the model checkpoint exists
    print("[INFO] Checking model checkpoint...")
    check_cmd = f"ls -la {remote_config.remote_dir}/checkpoints/nvidia/ | head -10"
    result = ssh.execute_command_success(check_cmd)
    print(result)
    
    # Try a minimal test that just loads the model
    print("\n[INFO] Testing model loading...")
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

# Try to initialize (this will load the model)
print('[3] Initializing upsampler...')
upsampler = PixtralPromptUpsampler(
    checkpoint_dir='/workspace/checkpoints',
    offload_prompt_upsampler=True
)
print('[4] Upsampler initialized!')

# Try a simple upsample
print('[5] Testing upsampling...')
result = upsampler._prompt_upsample_with_offload(
    'A sunset', 
    '/workspace/inputs/videos/city_scene_20250830_203504/color.mp4'
)
print('[6] Upsampling complete!')
print('Result:', result[:100] if result else 'No result')
"
    """
    
    try:
        print("\n[INFO] Running test (this may take 2-3 minutes to load the model)...")
        output = ssh.execute_command(test_cmd, timeout=300, stream_output=True)
        exit_code, stdout, stderr = output
        
        if exit_code == 0:
            print("\n[SUCCESS] Test completed!")
            print("STDOUT:", stdout)
        else:
            print(f"\n[ERROR] Test failed with exit code {exit_code}")
            print("STDOUT:", stdout)
            print("STDERR:", stderr)
            
    except Exception as e:
        print(f"\n[ERROR]: {e}")