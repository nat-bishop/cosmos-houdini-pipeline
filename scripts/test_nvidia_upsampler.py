#!/usr/bin/env python3
"""Test the NVIDIA-style upsampler on the remote GPU."""

import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def main():
    cm = ConfigManager()
    ssh = SSHManager(cm.get_ssh_options())

    # Upload the script using SCP or direct write
    print("Uploading NVIDIA-style upsampler script...")
    local_script = Path("scripts/nvidia_style_upsampler.py")
    script_content = local_script.read_text()

    # Write script content to a temp file first
    temp_upload = f"""
cat > /tmp/nvidia_style_upsampler.py << 'SCRIPT_EOF'
{script_content}
SCRIPT_EOF
"""

    ssh.execute_command_success(temp_upload, timeout=10)
    ssh.execute_command_success(
        "sudo mv /tmp/nvidia_style_upsampler.py /home/ubuntu/NatsFS/cosmos-transfer1/scripts/ && "
        "sudo chmod +x /home/ubuntu/NatsFS/cosmos-transfer1/scripts/nvidia_style_upsampler.py",
        timeout=5,
    )
    print("[SUCCESS] Script uploaded")

    # Test with a simple prompt first
    prompt = "Warm low-angle sunlight grazing facades"
    escaped_prompt = shlex.quote(prompt)

    # Run the upsampler
    docker_cmd = f"""
sudo docker run --rm --gpus all \
    -v /home/ubuntu/NatsFS/cosmos-transfer1:/workspace \
    -w /workspace \
    -e RANK=0 \
    nvcr.io/ubuntu/cosmos-transfer1:latest \
    python scripts/nvidia_style_upsampler.py \
        --prompt {escaped_prompt} \
        --input_video /workspace/inputs/videos/color.mp4 \
        --checkpoint_dir /workspace/checkpoints \
        --offload_prompt_upsampler \
        --output_file /workspace/outputs/upsampled_test.json
"""

    print("\nRunning upsampler (this may take a few minutes on first run)...")
    print("Docker command:", docker_cmd[:200] + "...")

    try:
        output = ssh.execute_command_success(docker_cmd, timeout=600)
        print("\n=== Output ===")
        print(output)

        # Try to get the result
        print("\n=== Getting result ===")
        result = ssh.execute_command_success(
            "cat /home/ubuntu/NatsFS/cosmos-transfer1/outputs/upsampled_test.json", timeout=10
        )
        print(result)

    except Exception as e:
        print(f"[ERROR] Execution failed: {e}")

        # Check for stuck containers
        print("\nChecking for any running containers...")
        containers = ssh.execute_command_success("sudo docker ps -a | head -5", timeout=10)
        print(containers)


if __name__ == "__main__":
    main()
