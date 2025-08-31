#!/usr/bin/env python3
"""Test the standalone upsampler with proper environment setup."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import shlex

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def main():
    cm = ConfigManager()
    ssh = SSHManager(cm.get_ssh_options())

    print("Uploading standalone upsampler script...")
    local_script = Path("scripts/standalone_upsampler.py")
    script_content = local_script.read_text()

    # Upload script
    temp_upload = f"""
cat > /tmp/standalone_upsampler.py << 'SCRIPT_EOF'
{script_content}
SCRIPT_EOF
"""

    ssh.execute_command_success(temp_upload, timeout=10)
    ssh.execute_command_success(
        "sudo cp /tmp/standalone_upsampler.py /home/ubuntu/NatsFS/cosmos-transfer1/scripts/ && "
        "sudo chmod +x /home/ubuntu/NatsFS/cosmos-transfer1/scripts/standalone_upsampler.py",
        timeout=5,
    )
    print("[SUCCESS] Script uploaded")

    # Test with a simple prompt
    prompt = "Warm low-angle sunlight grazing facades with gentle rim lighting"
    escaped_prompt = shlex.quote(prompt)

    # Run WITHOUT setting RANK externally - let the script set all defaults
    docker_cmd = f"""
sudo docker run --rm --gpus all \
    -v /home/ubuntu/NatsFS/cosmos-transfer1:/workspace \
    -w /workspace \
    nvcr.io/ubuntu/cosmos-transfer1:latest \
    python scripts/standalone_upsampler.py \
        --prompt {escaped_prompt} \
        --input-video /workspace/inputs/videos/color.mp4 \
        --checkpoint-dir /workspace/checkpoints \
        --output-file /workspace/outputs/standalone_test.json \
        --offload
"""

    print("\n[INFO] Running standalone upsampler with proper defaults...")
    print("[INFO] This may take several minutes on first run to load the model...\n")

    try:
        output = ssh.execute_command_success(docker_cmd, timeout=600)

        # Show output
        print("=== Docker Output ===")
        # Show last 100 lines to see the result
        lines = output.split("\n")
        for line in lines[-100:]:
            print(line)

        # Try to get the saved result
        print("\n=== Fetching Result ===")
        try:
            result = ssh.execute_command_success(
                "cat /home/ubuntu/NatsFS/cosmos-transfer1/outputs/standalone_test.json", timeout=10
            )
            print(result)
        except:
            print("[WARNING] Could not fetch result file")

    except Exception as e:
        print(f"\n[ERROR] Execution failed: {e}")

        # Check if container is stuck
        containers = ssh.execute_command_success(
            'sudo docker ps --format "table {{.ID}}\t{{.Status}}\t{{.Names}}"', timeout=5
        )
        print("\nDocker containers:", containers)


if __name__ == "__main__":
    main()
