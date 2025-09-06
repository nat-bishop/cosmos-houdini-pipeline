#!/usr/bin/env python3
"""Docker execution service for Cosmos-Transfer1 workflows.
Handles running Docker commands on remote instances with proper logging and error handling.
"""

import json
import logging
from pathlib import Path
from typing import Any

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.command_builder import DockerCommandBuilder, RemoteCommandExecutor

logger = logging.getLogger(__name__)


class DockerExecutor:
    """Executes Docker commands on remote instances using bash scripts."""

    def __init__(self, ssh_manager: SSHManager, remote_dir: str, docker_image: str):
        self.ssh_manager = ssh_manager
        self.remote_dir = remote_dir
        self.docker_image = docker_image
        self.remote_executor = RemoteCommandExecutor(ssh_manager)

    def run_inference(self, prompt_file: Path, num_gpu: int = 1, cuda_devices: str = "0") -> None:
        """Run Cosmos-Transfer1 inference on remote instance.

        Args:
            prompt_file: Name of prompt file (without path)
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use
        """
        prompt_name = prompt_file.stem

        logger.info("Running inference for %s with {num_gpu} GPU(s)", prompt_name)

        # Create output directory
        remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
        self.remote_executor.create_directory(remote_output_dir)

        # Execute inference using bash script
        logger.info("Starting inference...")
        self._run_inference_script(prompt_name, num_gpu, cuda_devices)

        logger.info("Inference completed successfully for %s", prompt_name)

    def run_inference_with_logging(
        self,
        prompt_file: Path,
        num_gpu: int = 1,
        cuda_devices: str = "0",
        log_path: str | None = None,
    ) -> None:
        """Run inference with optional log file capture.

        Args:
            prompt_file: Name of prompt file (without path)
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use
            log_path: Optional path to write logs to
        """

        prompt_name = prompt_file.stem
        logger.info("Running inference for %s", prompt_name)

        # Create output directory
        remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
        self.remote_executor.create_directory(remote_output_dir)

        # Execute inference
        logger.info("Starting inference...")
        self._run_inference_script(prompt_name, num_gpu, cuda_devices)

        # If log_path provided, capture Docker logs
        if log_path:
            # Get container ID (most recent for our image)
            cmd = f'sudo docker ps -l -q --filter "ancestor={self.docker_image}"'
            container_id = self.ssh_manager.execute_command_success(
                cmd, stream_output=False
            ).strip()

            if container_id:
                logger.info("Capturing logs from container %s to %s", container_id, log_path)

                # Stream logs to file
                with open(log_path, "w") as log_file:
                    # Get logs (not following, just current state)
                    logs_cmd = f"sudo docker logs {container_id}"
                    exit_code, stdout, stderr = self.ssh_manager.execute_command(
                        logs_cmd, timeout=60, stream_output=False
                    )

                    # Write to file
                    log_file.write(stdout)
                    if stderr:
                        log_file.write(f"\n=== STDERR ===\n{stderr}")
                    log_file.flush()

                    # Now follow new logs
                    follow_cmd = f"sudo docker logs -f {container_id}"

                    # Custom streaming to file
                    stdin, stdout_stream, stderr_stream = self.ssh_manager.ssh_client.exec_command(
                        follow_cmd
                    )

                    # Stream to file in real-time
                    for line in stdout_stream:
                        line = line.strip()
                        if line:
                            print(f"  {line}")  # Console
                            log_file.write(f"{line}\n")
                            log_file.flush()  # Real-time

        logger.info("Inference completed for %s", prompt_name)

    def run_upscaling(
        self,
        prompt_file: Path,
        control_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> None:
        """Run 4K upscaling on remote instance.

        Args:
            prompt_file: Name of prompt file (without path)
            control_weight: Control weight for upscaling
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use
        """
        prompt_name = prompt_file.stem

        logger.info("Running upscaling for %s with weight {control_weight}", prompt_name)

        # Check if input video exists
        input_video_path = f"{self.remote_dir}/outputs/{prompt_name}/output.mp4"
        if not self.remote_executor.file_exists(input_video_path):
            raise FileNotFoundError(f"Input video not found: {input_video_path}")

        # Create upscaled output directory
        remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}_upscaled"
        self.remote_executor.create_directory(remote_output_dir)

        # Create upscaler spec
        self._create_upscaler_spec(prompt_name, control_weight)

        # Execute upscaling using bash script
        logger.info("Starting upscaling...")
        self._run_upscaling_script(prompt_name, control_weight, num_gpu, cuda_devices)

        logger.info("Upscaling completed successfully for %s", prompt_name)

    def run_prompt_enhancement(
        self,
        batch_filename: str,
        offload: bool = True,
        checkpoint_dir: str = "/workspace/checkpoints",
        timeout: int = 600,
    ) -> None:
        """Run prompt enhancement using Pixtral model on GPU.

        Processes a batch of prompts using the prompt_upsampler.py script.
        Follows the same pattern as run_inference and run_upscaling.

        Args:
            batch_filename: Name of batch JSON file in inputs directory
            offload: Whether to offload model between prompts (True for memory efficiency)
            checkpoint_dir: Directory containing model checkpoints
            timeout: Execution timeout in seconds
        """
        logger.info("Running prompt enhancement for batch %s", batch_filename)

        # Verify script exists on remote
        script_path = f"{self.remote_dir}/scripts/prompt_upsampler.py"
        if not self.remote_executor.file_exists(script_path):
            raise FileNotFoundError(f"Upsampler script not found at {script_path}")

        # Verify batch file exists
        batch_path = f"{self.remote_dir}/inputs/{batch_filename}"
        if not self.remote_executor.file_exists(batch_path):
            raise FileNotFoundError(f"Batch file not found at {batch_path}")

        # Ensure output directory exists
        output_dir = f"{self.remote_dir}/outputs"
        self.remote_executor.create_directory(output_dir)

        # Build Docker command
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu("0")
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")
        builder.add_environment("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
        builder.add_environment("CUDA_VISIBLE_DEVICES", "0")

        # Build the command - note it's Python script, not bash
        # Script defaults to offload=True, use --no-offload to disable
        offload_flag = "" if offload else "--no-offload"
        cmd = (
            f"python /workspace/scripts/prompt_upsampler.py "
            f"--batch /workspace/inputs/{batch_filename} "
            f"--output-dir /workspace/outputs "
            f"--checkpoint-dir {checkpoint_dir}"
        )
        if offload_flag:
            cmd += f" {offload_flag}"
        builder.set_command(cmd)

        # Execute via remote executor
        logger.info("Starting prompt enhancement (batch mode)...")
        self.remote_executor.execute_docker(builder, timeout=timeout)

        logger.info("Prompt enhancement completed for batch %s", batch_filename)

    def _run_inference_script(self, prompt_name: str, num_gpu: int, cuda_devices: str) -> None:
        """Run inference using the bash script."""
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")
        builder.set_command(
            f'bash -lc "/workspace/bashscripts/inference.sh {prompt_name} {num_gpu} {cuda_devices}"'
        )

        self.remote_executor.execute_docker(builder, timeout=3600)  # 1 hour timeout

    def _run_upscaling_script(
        self, prompt_name: str, control_weight: float, num_gpu: int, cuda_devices: str
    ) -> None:
        """Run upscaling using the bash script."""
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")
        builder.set_command(
            f'bash -lc "/workspace/bashscripts/upscale.sh {prompt_name} {control_weight} {num_gpu} {cuda_devices}"'
        )

        self.remote_executor.execute_docker(builder, timeout=1800)  # 30 minute timeout

    def _create_upscaler_spec(self, prompt_name: str, control_weight: float) -> None:
        """Create upscaler specification file on remote."""
        upscaler_spec = {
            "input_video_path": f"outputs/{prompt_name}/output.mp4",
            "upscale": {"control_weight": control_weight},
        }

        # Write spec to remote
        spec_content = json.dumps(upscaler_spec, indent=2)
        spec_path = f"{self.remote_dir}/outputs/{prompt_name}/upscaler_spec.json"

        self.remote_executor.write_file(spec_path, spec_content)
        logger.info("Created upscaler spec: %s", spec_path)

    def _check_remote_file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on the remote system."""
        return self.remote_executor.file_exists(remote_path)

    def get_docker_status(self) -> dict[str, Any]:
        """Get Docker status on remote instance."""
        try:
            # Check if Docker is running
            docker_info = self.ssh_manager.execute_command_success(
                "sudo docker info", stream_output=False
            )

            # Check available images
            images_output = self.ssh_manager.execute_command_success(
                "sudo docker images", stream_output=False
            )

            # Check running containers
            containers_output = self.ssh_manager.execute_command_success(
                "sudo docker ps", stream_output=False
            )

            return {
                "docker_running": True,
                "docker_info": docker_info,
                "available_images": images_output,
                "running_containers": containers_output,
            }

        except Exception as e:
            return {"docker_running": False, "error": str(e)}

    def cleanup_containers(self) -> None:
        """Clean up any stopped containers on remote."""
        try:
            self.ssh_manager.execute_command_success(
                "sudo docker container prune -f", stream_output=False
            )
            logger.info("Cleaned up stopped containers")
        except Exception as e:
            logger.warning("Failed to cleanup containers: %s", e)

    def get_container_logs(self, container_id: str) -> str:
        """Get logs from a specific container."""
        try:
            return self.ssh_manager.execute_command_success(
                f"sudo docker logs {container_id}", stream_output=False
            )
        except Exception as e:
            logger.error("Failed to get container logs: %s", e)
            return f"Error retrieving logs: {e}"

    def run_batch_inference(
        self,
        batch_name: str,
        batch_jsonl_file: str,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> dict[str, Any]:
        """Run batch inference for multiple prompts/videos.

        Args:
            batch_name: Name for the batch output directory
            batch_jsonl_file: Name of JSONL file with batch data (in inputs/batches/)
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use

        Returns:
            Dictionary with batch results including output paths
        """
        logger.info("Running batch inference %s with %d GPU(s)", batch_name, num_gpu)

        # Check if batch file exists
        batch_path = f"{self.remote_dir}/inputs/batches/{batch_jsonl_file}"
        if not self.remote_executor.file_exists(batch_path):
            raise FileNotFoundError(f"Batch file not found: {batch_path}")

        # Create output directory
        remote_output_dir = f"{self.remote_dir}/outputs/{batch_name}"
        self.remote_executor.create_directory(remote_output_dir)

        # Execute batch inference using bash script
        logger.info("Starting batch inference...")
        self._run_batch_inference_script(batch_name, batch_jsonl_file, num_gpu, cuda_devices)

        # Get list of output files
        output_files = self._get_batch_output_files(batch_name)

        logger.info("Batch inference completed successfully for %s", batch_name)
        return {
            "batch_name": batch_name,
            "output_dir": remote_output_dir,
            "output_files": output_files,
        }

    def _run_batch_inference_script(
        self, batch_name: str, batch_jsonl_file: str, num_gpu: int, cuda_devices: str
    ) -> None:
        """Run batch inference using the bash script."""
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")
        builder.set_command(
            f'bash -lc "/workspace/scripts/batch_inference.sh {batch_name} {batch_jsonl_file} {num_gpu} {cuda_devices}"'
        )

        self.remote_executor.execute_docker(builder, timeout=7200)  # 2 hour timeout for batch

    def _get_batch_output_files(self, batch_name: str) -> list[str]:
        """Get list of output files from batch inference."""
        output_dir = f"{self.remote_dir}/outputs/{batch_name}"
        try:
            # List all mp4 files in the output directory
            result = self.ssh_manager.execute_command_success(
                f"ls -1 {output_dir}/*.mp4 2>/dev/null || true", stream_output=False
            )
            if result:
                files = result.strip().split("\n")
                return [f for f in files if f]
            return []
        except Exception as e:
            logger.warning("Failed to list output files: %s", e)
            return []

    def stream_container_logs(self, container_id: str | None = None) -> None:
        """Stream container logs in real-time.

        Args:
            container_id: Optional container ID. If not provided, auto-detects
                         the most recent container for the configured Docker image.

        Raises:
            RuntimeError: If no running containers are found.
        """
        if not container_id:
            # Auto-detect the most recent container matching our image
            logger.info("Auto-detecting most recent container for image %s", self.docker_image)
            cmd = f'sudo docker ps -l -q --filter "ancestor={self.docker_image}"'
            container_id = self.ssh_manager.execute_command_success(
                cmd, stream_output=False
            ).strip()

            if not container_id:
                raise RuntimeError("No running containers found")

        logger.info("Streaming logs from container %s", container_id)
        print(f"[INFO] Streaming logs from container {container_id[:12]}...")
        print("[INFO] Press Ctrl+C to stop streaming\n")

        try:
            # Stream logs using existing SSH streaming infrastructure
            self.ssh_manager.execute_command(
                f"sudo docker logs -f {container_id}",
                timeout=86400,  # 24 hour timeout for long-running streams
                stream_output=True,
            )
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\n[INFO] Stopped streaming logs")
            logger.info("Log streaming interrupted by user")
