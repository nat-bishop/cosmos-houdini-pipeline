#!/usr/bin/env python3
"""Deploy and test the working upsampler on remote GPU."""

import json
import sys
from pathlib import Path

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager


def main():
    # Initialize configuration
    config_manager = ConfigManager()
    remote_config = config_manager.get_remote_config()
    ssh_options = config_manager.get_ssh_options()

    print("[INFO] Connecting to remote GPU server...")

    with SSHManager(ssh_options) as ssh:
        # Create scripts directory on remote
        scripts_dir = f"{remote_config.remote_dir}/scripts"
        ssh.execute_command_success(f"mkdir -p {scripts_dir}")

        # Upload the working upsampler script
        local_script = Path("scripts/working_prompt_upsampler.py")
        print(f"[INFO] Uploading {local_script} to remote...")
        with ssh.get_sftp() as sftp:
            remote_script_path = f"{scripts_dir}/working_prompt_upsampler.py"
            sftp.put(str(local_script), remote_script_path)

        # Upload test batch file
        local_batch = Path("inputs/test_upsample_batch.json")
        inputs_dir = f"{remote_config.remote_dir}/inputs"
        ssh.execute_command_success(f"mkdir -p {inputs_dir}")
        print(f"[INFO] Uploading {local_batch} to remote...")
        with ssh.get_sftp() as sftp:
            remote_batch_path = f"{inputs_dir}/test_upsample_batch.json"
            sftp.put(str(local_batch), remote_batch_path)

        # Check if video exists on remote
        video_check = ssh.execute_command_success(
            f"ls -la {remote_config.remote_dir}/inputs/videos/city_scene_20250830_203504/color.mp4 2>/dev/null || echo 'NOT_FOUND'"
        )

        if "NOT_FOUND" in video_check:
            print("[WARNING] Video file not found on remote. Uploading...")
            # Upload video if it exists locally
            local_video = Path("inputs/videos/city_scene_20250830_203504/color.mp4")
            if local_video.exists():
                videos_dir = f"{remote_config.remote_dir}/inputs/videos/city_scene_20250830_203504"
                ssh.execute_command_success(f"mkdir -p {videos_dir}")
                with ssh.get_sftp() as sftp:
                    remote_video_path = f"{videos_dir}/color.mp4"
                    sftp.put(str(local_video), remote_video_path)
            else:
                print("[ERROR] Video not found locally either. Creating a simple test video...")
                # Create a simple test video on remote
                create_test_video = f"""
                cd {remote_config.remote_dir}
                mkdir -p inputs/videos/city_scene_20250830_203504
                # Create a 2-second test video with ffmpeg
                ffmpeg -y -f lavfi -i testsrc=duration=2:size=640x480:rate=30 \
                    -c:v libx264 -pix_fmt yuv420p \
                    inputs/videos/city_scene_20250830_203504/color.mp4
                """
                ssh.execute_command_success(create_test_video)

        # Create output directory
        ssh.execute_command_success(f"mkdir -p {remote_config.remote_dir}/outputs/upsampled")

        # Build Docker command
        docker_cmd = f"""
        cd {remote_config.remote_dir}
        sudo docker run --rm --gpus all \\
            -v {remote_config.remote_dir}:/workspace \\
            -w /workspace \\
            -e VLLM_WORKER_MULTIPROC_METHOD=spawn \\
            -e CUDA_VISIBLE_DEVICES=0 \\
            -e RANK=0 \\
            -e LOCAL_RANK=0 \\
            -e WORLD_SIZE=1 \\
            -e LOCAL_WORLD_SIZE=1 \\
            -e GROUP_RANK=0 \\
            -e ROLE_RANK=0 \\
            -e ROLE_NAME=default \\
            -e OMP_NUM_THREADS=4 \\
            -e MASTER_ADDR=127.0.0.1 \\
            -e MASTER_PORT=29500 \\
            -e TORCHELASTIC_USE_AGENT_STORE=False \\
            -e TORCHELASTIC_MAX_RESTARTS=0 \\
            -e TORCHELASTIC_RUN_ID=local \\
            -e TORCH_NCCL_ASYNC_ERROR_HANDLING=1 \\
            -e TORCHELASTIC_ERROR_FILE=/tmp/torch_error.log \\
            {remote_config.docker_image} \\
            python /workspace/scripts/working_prompt_upsampler.py \\
                --batch /workspace/inputs/test_upsample_batch.json \\
                --output-dir /workspace/outputs/upsampled \\
                --checkpoint-dir /workspace/checkpoints
        """

        print("\n[INFO] Running upsampler in Docker container...")
        print("[INFO] This may take a few minutes on first run while loading the model...")

        try:
            output = ssh.execute_command_success(docker_cmd, timeout=600)
            print("\n[SUCCESS] Upsampler completed successfully!")
            print("\nOutput:")
            print(output)

            # Check for results
            results_check = ssh.execute_command_success(
                f"ls -la {remote_config.remote_dir}/outputs/upsampled/"
            )
            print("\nResults files:")
            print(results_check)

            # Try to read the batch results
            try:
                batch_results = ssh.execute_command_success(
                    f"cat {remote_config.remote_dir}/outputs/upsampled/batch_results.json"
                )
                results_data = json.loads(batch_results)
                print("\n[RESULTS]:")
                for result in results_data:
                    if result.get("success"):
                        print(f"\nPrompt: {result['name']}")
                        print(f"Original: {result['original_prompt']}")
                        print(f"Upsampled: {result.get('upsampled_prompt', 'N/A')}")
                    else:
                        print(f"\nFailed: {result['name']}")
                        print(f"Error: {result.get('error', 'Unknown error')}")
            except Exception as e:
                print(f"[INFO] Could not parse results: {e}")

        except Exception as e:
            print(f"\n[ERROR] Upsampler failed: {e}")
            print("\nTrying a simpler test with a single prompt...")

            # Try single prompt mode
            simple_cmd = f"""
            cd {remote_config.remote_dir}
            sudo docker run --rm --gpus all \\
                -v {remote_config.remote_dir}:/workspace \\
                -w /workspace \\
                -e VLLM_WORKER_MULTIPROC_METHOD=spawn \\
                -e CUDA_VISIBLE_DEVICES=0 \\
                {remote_config.docker_image} \\
                python -c "
import os
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'
print('[TEST] Environment set: VLLM_WORKER_MULTIPROC_METHOD =', os.environ.get('VLLM_WORKER_MULTIPROC_METHOD'))

# Set torch elastic defaults
for k, v in [('RANK', '0'), ('LOCAL_RANK', '0'), ('WORLD_SIZE', '1')]:
    os.environ.setdefault(k, v)

print('[TEST] Attempting import...')
try:
    from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
    print('[SUCCESS] Import worked!')
except Exception as e:
    print(f'[ERROR] Import failed: {{e}}')
"
            """

            try:
                test_output = ssh.execute_command_success(simple_cmd, timeout=60)
                print("\nSimple import test output:")
                print(test_output)
            except Exception as e2:
                print(f"Simple test also failed: {e2}")


if __name__ == "__main__":
    main()
