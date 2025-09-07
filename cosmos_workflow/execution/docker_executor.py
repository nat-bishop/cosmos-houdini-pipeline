#!/usr/bin/env python3
"""Docker execution service for Cosmos-Transfer1 workflows.
Handles running Docker commands on remote instances with proper logging and error handling.
"""

import json
from pathlib import Path
from typing import Any

from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.command_builder import DockerCommandBuilder, RemoteCommandExecutor
from cosmos_workflow.utils.logging import get_run_logger, logger
from cosmos_workflow.utils.workflow_utils import get_log_path


class DockerExecutor:
    """Executes Docker commands on remote instances using bash scripts."""

    def __init__(self, ssh_manager: SSHManager, remote_dir: str, docker_image: str):
        self.ssh_manager = ssh_manager
        self.remote_dir = remote_dir
        self.docker_image = docker_image
        self.remote_executor = RemoteCommandExecutor(ssh_manager)

    def run_inference(
        self,
        prompt_file: Path,
        run_id: str,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> dict:
        """Run Cosmos-Transfer1 inference on remote instance.

        Starts inference as a background process on the GPU. Returns immediately
        with 'started' status. Use 'cosmos status --stream' or Docker container
        logs to monitor progress.

        Args:
            prompt_file: Name of prompt file (without path).
            run_id: Run ID for tracking (REQUIRED).
            num_gpu: Number of GPUs to use.
            cuda_devices: CUDA device IDs to use.

        Returns:
            Dict containing status ('started'), log_path to local log file,
            and prompt_name for the executed inference.

        Raises:
            Exception: If inference launch fails.
        """
        prompt_name = prompt_file.stem

        # Setup run-specific logger
        run_logger = get_run_logger(run_id, prompt_name)

        run_logger.info("Starting inference for prompt: %s", prompt_name)
        run_logger.debug("GPU config: num_gpu=%d, devices=%s", num_gpu, cuda_devices)

        # Create output directory on remote
        remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}"
        self.remote_executor.create_directory(remote_output_dir)

        # Setup local log path
        local_log_path = get_log_path("inference", prompt_name, run_id)

        try:
            # Log path for reference
            remote_log_path = f"{self.remote_dir}/outputs/{prompt_name}/run.log"
            run_logger.info("Remote log path: %s", remote_log_path)

            # Execute inference using bash script
            run_logger.info("Starting inference on GPU. This may take several minutes...")
            run_logger.info("Use 'cosmos status --stream' to monitor progress")
            run_logger.info("Launching inference in background...")

            self._run_inference_script(prompt_name, num_gpu, cuda_devices)

            run_logger.info("Inference started successfully for %s", prompt_name)
            run_logger.info("The process is now running in the background on the GPU")

            return {
                "status": "started",  # Changed from "success" to "started"
                "log_path": str(local_log_path),
                "prompt_name": prompt_name,
            }

        except Exception as e:
            run_logger.error("Inference failed for %s: %s", prompt_name, e)
            return {"status": "failed", "error": str(e), "log_path": str(local_log_path)}

    def run_upscaling(
        self,
        prompt_file: Path,
        run_id: str,
        control_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> dict:
        """Run 4K upscaling on remote instance.

        Starts upscaling as a background process on the GPU. Returns immediately
        with 'started' status. Use 'cosmos status --stream' or Docker container
        logs to monitor progress.

        Args:
            prompt_file: Name of prompt file (without path).
            run_id: Run ID for tracking (REQUIRED).
            control_weight: Control weight for upscaling (0.0-1.0).
            num_gpu: Number of GPUs to use.
            cuda_devices: CUDA device IDs to use.

        Returns:
            Dict containing status ('started') and log_path to local log file.

        Raises:
            FileNotFoundError: If input video for upscaling is not found.
            Exception: If upscaling launch fails.
        """
        prompt_name = prompt_file.stem

        # Setup run-specific logger
        run_logger = get_run_logger(run_id, f"{prompt_name}_upscaled")
        run_logger.info("Running upscaling for %s with weight %s", prompt_name, control_weight)

        # Setup local log path
        local_log_path = get_log_path("upscaling", f"{prompt_name}_upscaled", run_id)

        try:
            # Check if input video exists
            input_video_path = f"{self.remote_dir}/outputs/{prompt_name}/output.mp4"
            if not self.remote_executor.file_exists(input_video_path):
                raise FileNotFoundError(f"Input video not found: {input_video_path}")

            # Create upscaled output directory
            remote_output_dir = f"{self.remote_dir}/outputs/{prompt_name}_upscaled"
            self.remote_executor.create_directory(remote_output_dir)

            # Create upscaler spec
            self._create_upscaler_spec(prompt_name, control_weight)

            # Log path for reference
            remote_log_path = f"{self.remote_dir}/outputs/{prompt_name}_upscaled/run.log"
            run_logger.info("Remote log path: %s", remote_log_path)

            # Execute upscaling using bash script
            run_logger.info("Starting upscaling on GPU. This may take several minutes...")
            run_logger.info("Use 'cosmos status --stream' to monitor progress")
            run_logger.info("Launching upscaling in background...")

            self._run_upscaling_script(prompt_name, control_weight, num_gpu, cuda_devices)

            run_logger.info("Upscaling started successfully for %s", prompt_name)
            run_logger.info("The process is now running in the background on the GPU")

            return {
                "status": "started",  # Changed from "success" to "started"
                "log_path": str(local_log_path),
                "prompt_name": prompt_name,
            }

        except Exception as e:
            run_logger.error("Upscaling failed for %s: %s", prompt_name, e)
            return {"status": "failed", "error": str(e), "log_path": str(local_log_path)}

    def run_prompt_enhancement(
        self,
        batch_filename: str,
        run_id: str | None = None,  # Changed from operation_id to run_id for consistency
        offload: bool = True,
        checkpoint_dir: str = "/workspace/checkpoints",
        timeout: int = 600,
    ) -> dict:
        """Run prompt enhancement using Pixtral model on GPU.

        Starts enhancement as a background process on the GPU. Returns immediately
        with 'started' status. Use 'cosmos status --stream' or Docker container
        logs to monitor progress.

        Args:
            batch_filename: Name of batch JSON file in inputs directory
            run_id: Run ID for tracking (REQUIRED for consistency with inference)
            offload: Whether to offload model between prompts (True for memory efficiency)
            checkpoint_dir: Directory containing model checkpoints
            timeout: Not used for background execution (kept for compatibility)

        Returns:
            Dict containing status ('started') and log_path to local log file.

        Raises:
            FileNotFoundError: If script or batch file not found.
            Exception: If enhancement launch fails.
        """
        # Setup run-specific logger (consistent with inference)
        if run_id:
            run_logger = get_run_logger(
                run_id, f"prompt_enhancement_{batch_filename.split('.')[0]}"
            )
            local_log_path = get_log_path("enhancement", f"prompt_enhancement_{run_id}", run_id)
        else:
            run_logger = logger
            local_log_path = None

        run_logger.info("Running prompt enhancement for batch %s", batch_filename)

        # Setup container log path (inside container, like inference.sh does)
        container_log_path = None
        if run_id:
            # Use /workspace path inside container (gets mounted from remote_dir)
            container_log_path = f"/workspace/logs/enhancement_{run_id}/run.log"
            # Ensure log directory exists on remote
            self.remote_executor.create_directory(f"{self.remote_dir}/logs/enhancement_{run_id}")

        try:
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

            # Add logging redirection if we have a log path (use container path)
            if container_log_path:
                # Wrap in bash -c for proper shell operator interpretation
                cmd = f"({cmd}) 2>&1 | tee {container_log_path}; echo '[COSMOS_COMPLETE]' >> {container_log_path}"
                cmd = f'bash -c "{cmd}"'

            builder.set_command(cmd)

            # Build the docker command
            command = builder.build()

            # Run in background like inference does
            background_command = f"nohup {command} > /dev/null 2>&1 &"

            # Execute in background - returns immediately
            run_logger.info("Starting prompt enhancement on GPU...")
            run_logger.info("Use 'cosmos status --stream' to monitor progress")
            run_logger.info("Launching enhancement in background...")

            # This returns immediately since we're running in background
            self.ssh_manager.execute_command(background_command, timeout=5)

            run_logger.info("Prompt enhancement started successfully for batch %s", batch_filename)
            run_logger.info("The process is now running in the background on the GPU")

            return {
                "status": "started",  # Changed from "success" to "started" for consistency
                "log_path": str(local_log_path) if local_log_path else None,
                "batch_filename": batch_filename,
            }

        except Exception as e:
            run_logger.error("Prompt enhancement launch failed: %s", e)
            return {
                "status": "failed",
                "error": str(e),
                "log_path": str(local_log_path) if local_log_path else None,
            }

    def _run_inference_script(self, prompt_name: str, num_gpu: int, cuda_devices: str) -> None:
        """Run inference using the bash script in background."""
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")
        builder.set_command(
            f'bash -lc "/workspace/bashscripts/inference.sh {prompt_name} {num_gpu} {cuda_devices}"'
        )

        # Run the command in background by appending & and using nohup
        command = builder.build()
        background_command = f"nohup {command} > /dev/null 2>&1 &"

        # This returns immediately since we're running in background
        self.ssh_manager.execute_command(background_command, timeout=5)
        logger.info("Inference started in background")

    def _run_upscaling_script(
        self, prompt_name: str, control_weight: float, num_gpu: int, cuda_devices: str
    ) -> None:
        """Run upscaling using the bash script in background."""
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")
        builder.set_command(
            f'bash -lc "/workspace/bashscripts/upscale.sh {prompt_name} {control_weight} {num_gpu} {cuda_devices}"'
        )

        # Run the command in background
        command = builder.build()
        background_command = f"nohup {command} > /dev/null 2>&1 &"

        # This returns immediately since we're running in background
        self.ssh_manager.execute_command(background_command, timeout=5)
        logger.info("Upscaling started in background")

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
                DockerCommandBuilder.build_info_command(), stream_output=False
            )

            # Check available images
            images_output = self.ssh_manager.execute_command_success(
                DockerCommandBuilder.build_images_command(), stream_output=False
            )

            # Use get_active_container for container info
            container = self.get_active_container()

            return {
                "docker_running": True,
                "docker_info": docker_info,
                "available_images": images_output,
                "active_container": container,  # More structured than raw text
            }

        except Exception as e:
            return {"docker_running": False, "error": str(e)}

    def get_active_container(self) -> dict[str, str] | None:
        """Get the active cosmos container (expects exactly one).

        Returns:
            Dict with container info if found:
                - id: Full container ID
                - id_short: First 12 chars of ID
                - name: Container name
                - status: Container status
                - image: Image name
                - created: Creation timestamp
                - warning: Optional warning if multiple containers
            None if no containers found
        """
        try:
            # Get containers matching our image
            cmd = (
                f'sudo docker ps --filter "ancestor={self.docker_image}" '
                f'--format "{{{{.ID}}}}|{{{{.Names}}}}|{{{{.Status}}}}|'
                f'{{{{.Image}}}}|{{{{.CreatedAt}}}}"'
            )
            output = self.ssh_manager.execute_command_success(cmd, stream_output=False)

            if not output or not output.strip():
                return None

            lines = output.strip().split("\n")
            containers = []

            for line in lines:
                if "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 5:
                        containers.append(
                            {
                                "id": parts[0],
                                "id_short": parts[0][:12],
                                "name": parts[1],
                                "status": parts[2],
                                "image": parts[3],
                                "created": parts[4],
                            }
                        )

            if not containers:
                return None

            # Return first container, with warning if multiple
            container = containers[0]
            if len(containers) > 1:
                container["warning"] = (
                    f"Multiple containers detected ({len(containers)}), "
                    f"using most recent: {container['name']}"
                )
                logger.warning(
                    "Multiple cosmos containers found: %d. Using %s",
                    len(containers),
                    container["name"],
                )

            return container

        except Exception as e:
            logger.error("Failed to get active container: %s", e)
            return None

    def get_gpu_info(self) -> dict[str, str] | None:
        """Get GPU information from the remote instance.

        Returns:
            Dict with GPU info if available:
                - name: GPU model name
                - memory_total: Total GPU memory
                - cuda_version: CUDA version
            None if GPU not available or nvidia-smi fails
        """
        try:
            # Query GPU info using nvidia-smi
            cmd = (
                "nvidia-smi --query-gpu=name,memory.total,driver_version "
                "--format=csv,noheader,nounits"
            )
            output = self.ssh_manager.execute_command_success(cmd, stream_output=False)

            if not output or not output.strip():
                return None

            # Parse CSV output (e.g., "Tesla T4, 15360, 525.60.13")
            parts = [p.strip() for p in output.strip().split(",")]
            if len(parts) >= 3:
                gpu_info = {
                    "name": parts[0],
                    "memory_total": f"{parts[1]} MB",
                    "driver_version": parts[2],
                }

                # Try to get CUDA version
                try:
                    cuda_output = self.ssh_manager.execute_command_success(
                        "nvidia-smi | grep 'CUDA Version' | sed 's/.*CUDA Version: \\([0-9.]*\\).*/\\1/'",
                        stream_output=False,
                    )
                    if cuda_output and cuda_output.strip():
                        gpu_info["cuda_version"] = cuda_output.strip()
                except Exception:
                    # CUDA version is optional, skip if retrieval fails
                    logger.debug("Could not retrieve CUDA version")

                return gpu_info

        except Exception as e:
            logger.debug("GPU not available or nvidia-smi failed: %s", e)
            return None

    def kill_containers(self) -> dict[str, Any]:
        """Kill all running containers for the cosmos docker image.

        Returns:
            Dict with status, killed_count, and list of killed container IDs.
        """
        try:
            # Get all running containers for our image
            cmd = f'sudo docker ps --filter "ancestor={self.docker_image}" --format "{{{{.ID}}}}"'
            output = self.ssh_manager.execute_command_success(cmd, stream_output=False)

            if not output or not output.strip():
                logger.info("No running containers found for image %s", self.docker_image)
                return {
                    "status": "success",
                    "killed_count": 0,
                    "killed_containers": [],
                    "message": "No running containers found",
                }

            # Parse container IDs
            container_ids = [cid.strip() for cid in output.strip().split("\n") if cid.strip()]

            if not container_ids:
                return {
                    "status": "success",
                    "killed_count": 0,
                    "killed_containers": [],
                    "message": "No running containers found",
                }

            # Kill all containers
            kill_cmd = DockerCommandBuilder.build_kill_command(container_ids)
            self.ssh_manager.execute_command_success(kill_cmd, stream_output=False)

            logger.info("Killed %d containers: %s", len(container_ids), container_ids)

            return {
                "status": "success",
                "killed_count": len(container_ids),
                "killed_containers": container_ids,
                "message": f"Successfully killed {len(container_ids)} container(s)",
            }

        except Exception as e:
            logger.error("Failed to kill containers: %s", e)
            return {"status": "failed", "error": str(e), "killed_count": 0, "killed_containers": []}

    def get_container_logs(self, container_id: str) -> str:
        """Get logs from a specific container."""
        try:
            return self.ssh_manager.execute_command_success(
                DockerCommandBuilder.build_logs_command(container_id), stream_output=False
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

        # Setup logging paths
        remote_log_path = f"{self.remote_dir}/logs/batch/{batch_name}.log"
        # Ensure remote log directory exists
        self.remote_executor.create_directory(f"{self.remote_dir}/logs/batch")

        # Check if batch file exists
        batch_path = f"{self.remote_dir}/inputs/batches/{batch_jsonl_file}"
        if not self.remote_executor.file_exists(batch_path):
            raise FileNotFoundError(f"Batch file not found: {batch_path}")

        # Create output directory
        remote_output_dir = f"{self.remote_dir}/outputs/{batch_name}"
        self.remote_executor.create_directory(remote_output_dir)

        # Execute batch inference using bash script
        logger.info("Starting batch inference on GPU. This may take a while...")
        logger.info("Use 'cosmos status --stream' to monitor progress")
        logger.info("Launching batch inference in background...")
        self._run_batch_inference_script(
            batch_name, batch_jsonl_file, num_gpu, cuda_devices, remote_log_path
        )

        logger.info("Batch inference started successfully for %s", batch_name)
        logger.info("The process is now running in the background on the GPU")

        return {
            "batch_name": batch_name,
            "output_dir": remote_output_dir,
            "status": "started",
        }

    def _run_batch_inference_script(
        self,
        batch_name: str,
        batch_jsonl_file: str,
        num_gpu: int,
        cuda_devices: str,
        remote_log_path: str | None = None,
    ) -> None:
        """Run batch inference using the bash script in background."""
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")

        # Build command with optional logging
        cmd = f"/workspace/scripts/batch_inference.sh {batch_name} {batch_jsonl_file} {num_gpu} {cuda_devices}"
        if remote_log_path:
            cmd = f'({cmd}) 2>&1 | tee {remote_log_path}; echo "[COSMOS_COMPLETE]" >> {remote_log_path}'

        builder.set_command(f'bash -lc "{cmd}"')

        # Run the command in background
        command = builder.build()
        background_command = f"nohup {command} > /dev/null 2>&1 &"

        # This returns immediately since we're running in background
        self.ssh_manager.execute_command(background_command, timeout=5)
        logger.info("Batch inference started in background")

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
            # Use get_active_container for auto-detection
            logger.info("Auto-detecting active container for image %s", self.docker_image)
            container = self.get_active_container()

            if not container:
                raise RuntimeError("No running containers found")

            container_id = container["id"]

            # Show warning if multiple containers detected
            if "warning" in container:
                print(f"[WARNING] {container['warning']}")

        logger.info("Streaming logs from container %s", container_id)
        print(f"[INFO] Streaming logs from container {container_id[:12]}...")
        print("[INFO] Press Ctrl+C to stop streaming\n")

        try:
            # Stream logs using existing SSH streaming infrastructure
            self.ssh_manager.execute_command(
                DockerCommandBuilder.build_logs_command(container_id, follow=True),
                timeout=86400,  # 24 hour timeout for long-running streams
                stream_output=True,
            )
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            print("\n[INFO] Stopped streaming logs")
            logger.info("Log streaming interrupted by user")
