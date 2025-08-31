#!/usr/bin/env python3
"""
Docker execution service for Cosmos-Transfer1 workflows.
Handles running Docker commands on remote instances with proper logging and error handling.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

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
        """
        Run Cosmos-Transfer1 inference on remote instance.

        Args:
            prompt_file: Name of prompt file (without path)
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use
        """
        prompt_name = prompt_file.stem

        logger.info(f"Running inference for {prompt_name} with {num_gpu} GPU(s)")

        # Create output directory
        remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
        self.remote_executor.create_directory(remote_output_dir)

        # Execute inference using bash script
        logger.info("Starting inference...")
        self._run_inference_script(prompt_name, num_gpu, cuda_devices)

        logger.info(f"Inference completed successfully for {prompt_name}")

    def run_upscaling(
        self,
        prompt_file: Path,
        control_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> None:
        """
        Run 4K upscaling on remote instance.

        Args:
            prompt_file: Name of prompt file (without path)
            control_weight: Control weight for upscaling
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use
        """
        prompt_name = prompt_file.stem

        logger.info(f"Running upscaling for {prompt_name} with weight {control_weight}")

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

        logger.info(f"Upscaling completed successfully for {prompt_name}")

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
        logger.info(f"Created upscaler spec: {spec_path}")

    def _check_remote_file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on the remote system."""
        return self.remote_executor.file_exists(remote_path)

    def get_docker_status(self) -> Dict[str, Any]:
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
            logger.warning(f"Failed to cleanup containers: {e}")

    def get_container_logs(self, container_id: str) -> str:
        """Get logs from a specific container."""
        try:
            return self.ssh_manager.execute_command_success(
                f"sudo docker logs {container_id}", stream_output=False
            )
        except Exception as e:
            logger.error(f"Failed to get container logs: {e}")
            return f"Error retrieving logs: {e}"
