#!/usr/bin/env python3
"""Upload and run the simple prompt upsampler on remote GPU."""

import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.config.config_manager import ConfigManager


def main():
    # Get SSH connection
    config_manager = ConfigManager()
    ssh_options = config_manager.get_ssh_options()
    ssh = SSHManager(ssh_options)
    remote_config = config_manager.get_remote_config()
    
    print("Uploading simple upsampler script...")
    
    # Upload the script
    upload_cmd = f"""
    cat > /home/ubuntu/NatsFS/cosmos-transfer1/scripts/simple_prompt_upsampler.py << 'EOF'
{open('scripts/simple_prompt_upsampler.py').read()}
EOF
    """
    
    try:
        ssh.execute_command_success(upload_cmd, timeout=10)
        print("[SUCCESS] Script uploaded")
    except Exception as e:
        print(f"[ERROR] Upload failed: {e}")
        return
    
    # Make it executable
    ssh.execute_command_success(
        "chmod +x /home/ubuntu/NatsFS/cosmos-transfer1/scripts/simple_prompt_upsampler.py",
        timeout=5
    )
    
    # Run the upsampler in Docker
    print("\nRunning prompt upsampler on GPU...")
    print("This will take a few minutes on first run to load the model...")
    
    docker_cmd = f"""
    sudo docker run --rm --gpus all \\
        -v {remote_config.remote_dir}:/workspace \\
        -w /workspace \\
        {remote_config.docker_image} \\
        python scripts/simple_prompt_upsampler.py \\
            --batch-file /workspace/inputs/upsample_batch_*.json \\
            --output-file /workspace/outputs/upsampled_results.json \\
            --checkpoint-dir /workspace/checkpoints \\
            --default-video /workspace/inputs/videos/color.mp4
    """
    
    # Note: Using the latest batch file with wildcard
    # In production, you'd specify the exact file
    
    # Find the actual batch file
    list_cmd = "ls -t /home/ubuntu/NatsFS/cosmos-transfer1/inputs/upsample_batch_*.json | head -1"
    batch_file = ssh.execute_command_success(list_cmd, timeout=5).strip()
    
    if batch_file:
        print(f"Found batch file: {batch_file}")
        
        # Update command with actual file
        docker_cmd = f"""
        sudo docker run --rm --gpus all \\
            -v {remote_config.remote_dir}:/workspace \\
            -w /workspace \\
            {remote_config.docker_image} \\
            python scripts/simple_prompt_upsampler.py \\
                --batch-file {batch_file.replace('/home/ubuntu/NatsFS/cosmos-transfer1', '/workspace')} \\
                --output-file /workspace/outputs/upsampled_results.json \\
                --checkpoint-dir /workspace/checkpoints \\
                --default-video /workspace/inputs/videos/color.mp4
        """
        
        print("\nExecuting Docker command...")
        try:
            output = ssh.execute_command_success(docker_cmd, timeout=600)  # 10 minute timeout
            print("\n=== Docker Output ===")
            print(output)
            print("===================")
            
            # Download results
            print("\nDownloading results...")
            download_cmd = f"cat {remote_config.remote_dir}/outputs/upsampled_results.json"
            results_json = ssh.execute_command_success(download_cmd, timeout=10)
            
            # Save locally
            local_output = Path("outputs/upsampled_results.json")
            local_output.parent.mkdir(exist_ok=True)
            local_output.write_text(results_json)
            
            # Parse and display
            results = json.loads(results_json)
            print(f"\n[SUCCESS] Downloaded {len(results)} upsampled prompts")
            
            for r in results:
                print(f"\n{r.get('name', 'unnamed')}:")
                print(f"  Original: {r.get('original_prompt', '')[:100]}...")
                print(f"  Upsampled: {r.get('upsampled_prompt', '')[:100]}...")
                
        except Exception as e:
            print(f"\n[ERROR] Execution failed: {e}")
            
            # Check for any running containers
            print("\nChecking for stuck containers...")
            containers = ssh.execute_command_success("sudo docker ps -a", timeout=5)
            print(containers)
            
    else:
        print("[ERROR] No batch file found. Run the upsampling command first to create one.")


if __name__ == "__main__":
    main()