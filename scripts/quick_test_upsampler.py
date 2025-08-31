#!/usr/bin/env python3
"""Quick test of upsampler directly via SSH."""

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
    # Upload the updated script
    print("[INFO] Uploading updated script...")
    with ssh.get_sftp() as sftp:
        sftp.put("scripts/working_prompt_upsampler.py", 
                 f"{remote_config.remote_dir}/scripts/working_prompt_upsampler.py")
    
    # Test with a simple prompt
    print("[INFO] Running upsampler test...")
    cmd = f"""
    cd {remote_config.remote_dir}
    sudo docker run --rm --gpus all \\
        -v {remote_config.remote_dir}:/workspace \\
        -w /workspace \\
        -e VLLM_WORKER_MULTIPROC_METHOD=spawn \\
        -e CUDA_VISIBLE_DEVICES=0 \\
        {remote_config.docker_image} \\
        python /workspace/scripts/working_prompt_upsampler.py \\
            --prompt "A beautiful sunset over the ocean" \\
            --video /workspace/inputs/videos/city_scene_20250830_203504/color.mp4 \\
            --output-dir /workspace/outputs/upsampled_test \\
            --checkpoint-dir /workspace/checkpoints
    """
    
    try:
        output = ssh.execute_command_success(cmd, timeout=300)
        print("\n[SUCCESS] Output:")
        print(output)
    except Exception as e:
        print(f"\n[ERROR]: {e}")
        
    # Check if output was created
    check_cmd = f"ls -la {remote_config.remote_dir}/outputs/upsampled_test/ 2>/dev/null || echo 'No output'"
    result = ssh.execute_command_success(check_cmd)
    print("\n[INFO] Output files:")
    print(result)