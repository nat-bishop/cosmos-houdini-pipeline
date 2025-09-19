#!/usr/bin/env python3
"""Docker execution service for Cosmos-Transfer1 workflows.
Handles running Docker commands on remote instances with proper logging and error handling.
"""

import json
from pathlib import Path
from typing import Any

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.command_builder import DockerCommandBuilder, RemoteCommandExecutor
from cosmos_workflow.utils.logging import get_run_logger, logger
from cosmos_workflow.utils.workflow_utils import get_log_path


class DockerExecutor:
    """Executes Docker commands on remote instances using bash scripts."""

    def __init__(
        self,
        ssh_manager: SSHManager,
        remote_dir: str,
        docker_image: str,
        config_manager: ConfigManager | None = None,
    ):
        self.ssh_manager = ssh_manager
        self.remote_dir = remote_dir
        self.docker_image = docker_image
        self.remote_executor = RemoteCommandExecutor(ssh_manager)
        self.config_manager = config_manager

        # Get timeout from config or use default
        self.docker_timeout = 3600  # Default 1 hour
        if config_manager:
            try:
                config_data = config_manager.get_config()
                self.docker_timeout = config_data.get("timeouts", {}).get("docker_execution", 3600)
                logger.info("Using docker timeout from config: {} seconds", self.docker_timeout)
            except Exception:
                logger.debug("Using default docker timeout: {} seconds", self.docker_timeout)

    def _create_fallback_log(
        self,
        run_id: str,
        error_message: str,
        stderr: str = "",
        exit_code: int | None = None,
        is_batch: bool = False,
    ) -> None:
        """Create a fallback log file when Docker fails to start.

        This ensures that even when Docker fails with exit code 125 or other startup
        issues, there's still a log file with error information for debugging.

        Args:
            run_id: The run ID for this operation (or batch name for batch runs)
            error_message: Error message to include in the log
            stderr: Standard error output from Docker command
            exit_code: Exit code from Docker command
            is_batch: Whether this is for a batch run (changes directory structure)
        """
        try:
            # Create remote log directory and file using correct format
            if is_batch:
                # For batch, use batch directory structure
                remote_log_dir = f"{self.remote_dir}/outputs/{run_id}"
                remote_log_path = f"{remote_log_dir}/batch_run.log"
            else:
                # For single runs, use run directory structure
                remote_log_dir = f"{self.remote_dir}/outputs/run_{run_id}/logs"
                remote_log_path = f"{remote_log_dir}/{run_id}.log"

            # Ensure log directory exists
            self.remote_executor.create_directory(remote_log_dir)

            # Build error log content
            from datetime import datetime, timezone

            error_log = "[ERROR] Docker failed to start\n"
            error_log += f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
            if exit_code is not None:
                error_log += f"Exit Code: {exit_code}\n"
            error_log += f"Error: {error_message}\n"
            if stderr:
                error_log += f"\n=== Docker stderr ===\n{stderr}\n"

            # Write the error log to remote
            self.remote_executor.write_file(remote_log_path, error_log)
            logger.info("Created fallback log at: {}", remote_log_path)
        except Exception as e:
            logger.error("Failed to create fallback log: {}", e)

    def run_inference(
        self,
        prompt_file: Path,
        run_id: str,
        num_gpu: int = 1,
        cuda_devices: str = "0",
        stream_output: bool = False,
    ) -> dict:
        """Run Cosmos-Transfer1 inference on remote instance synchronously.

        Executes inference and waits for completion. Returns when the Docker
        container finishes with either success or failure status.

        Args:
            prompt_file: Name of prompt file (without path).
            run_id: Run ID for tracking (REQUIRED).
            num_gpu: Number of GPUs to use.
            cuda_devices: CUDA device IDs to use.
            stream_output: Whether to stream output to console in real-time.

        Returns:
            Dict containing status ('completed' or 'failed'), exit_code,
            log_path to local log file, and prompt_name.

        Raises:
            Exception: If inference launch fails.
        """
        prompt_name = prompt_file.stem

        # Setup run-specific logger
        run_logger = get_run_logger(run_id, prompt_name)

        run_logger.info("Starting inference for prompt: {}", prompt_name)
        run_logger.debug("GPU config: num_gpu={}, devices={}", num_gpu, cuda_devices)

        # Create output directory on remote using run_id
        remote_output_dir = f"{self.remote_dir}/outputs/run_{run_id}"
        self.remote_executor.create_directory(remote_output_dir)

        # Setup local log path
        local_log_path = get_log_path("inference", f"run_{run_id}", run_id)

        try:
            # Log path for reference
            remote_log_path = f"{self.remote_dir}/outputs/run_{run_id}/run.log"
            logger.info("Remote log path: {}", remote_log_path)

            # Execute inference using bash script
            logger.info("Starting inference on GPU. This may take several minutes...")
            logger.info("Use 'cosmos status --stream' to monitor progress")
            logger.info("Launching inference in background...")

            # Run inference synchronously and get exit code
            exit_code = self._run_inference_script(
                prompt_name,
                run_id,
                num_gpu,
                cuda_devices,
                stream_output=stream_output,
                run_logger=run_logger,
            )

            if exit_code == 0:
                logger.info("Inference completed successfully for {}", prompt_name)
                return {
                    "status": "completed",
                    "exit_code": exit_code,
                    "log_path": str(local_log_path),
                    "prompt_name": prompt_name,
                }
            else:
                logger.error("Inference failed with exit code {}", exit_code)
                return {
                    "status": "failed",
                    "exit_code": exit_code,
                    "error": f"Inference failed with exit code {exit_code}",
                    "log_path": str(local_log_path),
                    "prompt_name": prompt_name,
                }

        except Exception as e:
            logger.error("Inference failed for {}: {}", prompt_name, e)
            return {"status": "failed", "error": str(e), "log_path": str(local_log_path)}

    def run_upscaling(
        self,
        video_path: str,
        run_id: str,
        control_weight: float = 0.5,
        prompt: str | None = None,
        num_gpu: int = 1,
        cuda_devices: str = "0",
        stream_output: bool = False,
    ) -> dict:
        """Run 4K upscaling on remote instance synchronously.

        Executes upscaling and waits for completion. Returns when the Docker
        container finishes with either success or failure status.

        Args:
            video_path: Remote path to the video file to upscale.
            run_id: Run ID for tracking (REQUIRED).
            control_weight: Control weight for upscaling (0.0-1.0).
            prompt: Optional prompt to guide the upscaling process.
            num_gpu: Number of GPUs to use.
            cuda_devices: CUDA device IDs to use.
            stream_output: Whether to stream output to console in real-time.

        Returns:
            Dict containing status ('completed' or 'failed'), exit_code,
            and log_path to local log file.

        Raises:
            FileNotFoundError: If input video for upscaling is not found.
            Exception: If upscaling launch fails.
        """
        # Setup run-specific logger
        from pathlib import Path

        video_name = Path(video_path).name
        run_logger = get_run_logger(run_id, f"upscale_{video_name}")
        run_logger.info("Running upscaling for video {} with weight {}", video_path, control_weight)
        if prompt:
            logger.info("Using prompt: {}", prompt[:100])

        # Setup local log path
        local_log_path = get_log_path("upscaling", f"run_{run_id}", run_id)

        try:
            # Check if input video exists on remote
            if not self.remote_executor.file_exists(video_path):
                raise FileNotFoundError(f"Input video not found: {video_path}")

            # Create output directory using run_id (same pattern as inference)
            remote_output_dir = f"{self.remote_dir}/outputs/run_{run_id}"
            self.remote_executor.create_directory(remote_output_dir)

            # Create upscaler spec using the new format
            from cosmos_workflow.utils.nvidia_format import to_cosmos_upscale_json

            # Convert absolute path to relative path for spec
            relative_video_path = video_path.replace(f"{self.remote_dir}/", "")

            upscale_spec = to_cosmos_upscale_json(
                input_video_path=relative_video_path,
                control_weight=control_weight,
                prompt=prompt,
            )

            # Write spec to remote run directory
            import json

            # Write spec directly to remote run directory
            spec_remote_path = f"{remote_output_dir}/spec.json"
            spec_content = json.dumps(upscale_spec, indent=2)
            self.remote_executor.write_file(spec_remote_path, spec_content)

            # Log path for reference
            remote_log_path = f"{self.remote_dir}/outputs/run_{run_id}/run.log"
            logger.info("Remote log path: {}", remote_log_path)

            # Execute upscaling using bash script
            logger.info("Starting upscaling on GPU. This may take several minutes...")
            logger.info("Use 'cosmos status --stream' to monitor progress")
            logger.info("Launching upscaling in background...")

            # Run upscaling synchronously and get exit code
            exit_code = self._run_upscaling_script(
                video_path,
                run_id,
                control_weight,
                num_gpu,
                cuda_devices,
                stream_output=stream_output,
                run_logger=run_logger,
            )

            if exit_code == 0:
                logger.info("Upscaling completed successfully for video {}", video_name)
                return {
                    "status": "completed",
                    "exit_code": exit_code,
                    "log_path": str(local_log_path),
                    "video_path": video_path,
                }
            else:
                logger.error("Upscaling failed with exit code {}", exit_code)
                return {
                    "status": "failed",
                    "exit_code": exit_code,
                    "error": f"Upscaling failed with exit code {exit_code}",
                    "log_path": str(local_log_path),
                    "video_path": video_path,
                }

        except Exception as e:
            logger.error("Upscaling failed for video {}: {}", video_path, e)
            return {"status": "failed", "error": str(e), "log_path": str(local_log_path)}

    def run_prompt_enhancement(
        self,
        batch_filename: str,
        run_id: str | None = None,  # Changed from operation_id to run_id for consistency
        offload: bool = True,
        checkpoint_dir: str = "/workspace/checkpoints",
    ) -> dict:
        """Run prompt enhancement using Pixtral model on GPU synchronously.

        Executes enhancement and waits for completion. Streams output to console
        for real-time progress monitoring.

        Args:
            batch_filename: Name of batch JSON file in inputs directory
            run_id: Run ID for tracking (REQUIRED for consistency with inference)
            offload: Whether to offload model between prompts (True for memory efficiency)
            checkpoint_dir: Directory containing model checkpoints

        Returns:
            Dict containing status ('completed' or 'failed'), exit_code, and log_path.

        Raises:
            FileNotFoundError: If script or batch file not found.
            Exception: If enhancement launch fails.
        """
        # Setup run-specific logger (consistent with inference)
        if run_id:
            run_logger = get_run_logger(
                run_id, f"prompt_enhancement_{batch_filename.split('.')[0]}"
            )
            local_log_path = get_log_path("enhancement", f"run_{run_id}", run_id)
        else:
            run_logger = logger
            local_log_path = None

        run_logger.info("Running prompt enhancement for batch {}", batch_filename)

        # Setup container log path (inside container, like inference.sh does)
        container_log_path = None
        if run_id:
            # Use consistent path structure: outputs/run_{run_id}/run.log
            container_log_path = f"/workspace/outputs/run_{run_id}/run.log"
            # Ensure output directory exists on remote
            self.remote_executor.create_directory(f"{self.remote_dir}/outputs/run_{run_id}")

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
                f"--output-dir /workspace/outputs/run_{run_id} "
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

            # Add container name for tracking (consistent with other operations)
            if run_id:
                container_name = f"cosmos_enhance_{run_id[:8]}"
                builder.with_name(container_name)

            # Build the docker command
            command = builder.build()
            logger.debug("Executing Docker command for enhancement: %s", command)

            # Run synchronously (blocking)
            logger.info("Starting prompt enhancement on GPU...")

            # Execute and wait for completion
            exit_code, stdout, stderr = self.ssh_manager.execute_command(
                command,
                timeout=min(1800, self.docker_timeout // 2),  # Half of docker timeout or 30 min
                stream_output=True,  # Stream output for CLI
            )

            logger.info("Prompt enhancement completed with exit code %d", exit_code)

            if exit_code == 0:
                return {
                    "status": "completed",
                    "exit_code": exit_code,
                    "log_path": str(local_log_path) if local_log_path else None,
                    "batch_filename": batch_filename,
                }
            else:
                # Create fallback log for Docker failures, especially exit code 125
                if exit_code == 125 and run_id:
                    self._create_fallback_log(
                        run_id=run_id,
                        error_message=f"Docker failed to start container for enhancement {batch_filename}",
                        stderr=stderr if stderr else "",
                        exit_code=exit_code,
                    )
                return {
                    "status": "failed",
                    "exit_code": exit_code,
                    "error": f"Enhancement failed with exit code {exit_code}",
                    "log_path": str(local_log_path) if local_log_path else None,
                }

        except Exception as e:
            logger.error("Prompt enhancement launch failed: {}", e)
            return {
                "status": "failed",
                "error": str(e),
                "log_path": str(local_log_path) if local_log_path else None,
            }

    def _run_inference_script(
        self,
        prompt_name: str,
        run_id: str,
        num_gpu: int,
        cuda_devices: str,
        stream_output: bool = False,
        run_logger=None,
    ) -> int:
        """Run inference using the bash script synchronously.

        Args:
            prompt_name: Name of the prompt
            run_id: Run ID for tracking
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs
            stream_output: Whether to stream output
            run_logger: Optional logger instance for run-specific logging

        Returns:
            Exit code from the docker container (0 for success, non-zero for failure)
        """
        # Use provided logger or fall back to global logger
        if run_logger is None:
            run_logger = logger
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")

        # Add container name for tracking
        container_name = f"cosmos_transfer_{run_id[:8]}"
        builder.with_name(container_name)

        builder.set_command(
            f'bash -lc "bash /workspace/bashscripts/inference.sh {run_id} {num_gpu} {cuda_devices}"'
        )

        # Run synchronously (blocking)
        command = builder.build()
        logger.debug("Executing Docker command for inference: %s", command)

        # Execute and wait for completion
        exit_code, stdout, stderr = self.ssh_manager.execute_command(
            command,
            timeout=self.docker_timeout,  # Use configured timeout
            stream_output=stream_output,
        )

        # Log Docker startup failures to unified log
        if exit_code != 0:
            logger.error("Docker container failed with exit code {}", exit_code)
            logger.error("Command: {}", command)
            if stderr:
                logger.error("STDERR: {}", stderr)
            if stdout and not stream_output:  # Don't duplicate if already streamed
                logger.info("STDOUT: {}", stdout)

            # Create fallback log for Docker failures, especially exit code 125
            if exit_code == 125:
                self._create_fallback_log(
                    run_id=run_id,
                    error_message=f"Docker failed to start container for inference {prompt_name}",
                    stderr=stderr,
                    exit_code=exit_code,
                )

        logger.info("Inference completed with exit code %d", exit_code)
        return exit_code

    def _run_upscaling_script(
        self,
        video_path: str,
        run_id: str,
        control_weight: float,
        num_gpu: int,
        cuda_devices: str,
        stream_output: bool = False,
        run_logger=None,
    ) -> int:
        """Run upscaling using the bash script synchronously.

        Args:
            video_path: Path to video file
            run_id: Run ID for tracking
            control_weight: Control weight for upscaling
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs
            stream_output: Whether to stream output
            run_logger: Optional logger instance for run-specific logging

        Returns:
            Exit code from the docker container (0 for success, non-zero for failure)
        """
        # Use provided logger or fall back to global logger
        if run_logger is None:
            run_logger = logger
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")

        # Add container name for tracking
        container_name = f"cosmos_upscale_{run_id[:8]}"
        builder.with_name(container_name)

        # For backward compatibility with upscale.sh, extract parent_run_id if video is from a run
        # Otherwise, use the run_id itself as parent_run_id
        import re

        run_match = re.search(r"run_(rs_\w+)", video_path)
        parent_run_id = run_match.group(1) if run_match else run_id

        builder.set_command(
            f'bash -lc "/workspace/bashscripts/upscale.sh {run_id} {control_weight} {num_gpu} {cuda_devices} {parent_run_id}"'
        )

        # Run synchronously (blocking)
        command = builder.build()
        logger.debug("Executing Docker command for upscaling: %s", command)

        # Execute and wait for completion
        exit_code, stdout, stderr = self.ssh_manager.execute_command(
            command,
            timeout=self.docker_timeout,  # Use configured timeout
            stream_output=stream_output,
        )

        # Log Docker startup failures to unified log
        if exit_code != 0:
            logger.error("Docker container failed with exit code {}", exit_code)
            logger.error("Command: {}", command)
            if stderr:
                logger.error("STDERR: {}", stderr)
            if stdout and not stream_output:  # Don't duplicate if already streamed
                logger.info("STDOUT: {}", stdout)

            # Create fallback log for Docker failures, especially exit code 125
            if exit_code == 125:
                self._create_fallback_log(
                    run_id=run_id,
                    error_message=f"Docker failed to start container for upscaling {video_path}",
                    stderr=stderr,
                    exit_code=exit_code,
                )

        logger.info("Upscaling completed with exit code %d", exit_code)
        return exit_code

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
        logger.info("Created upscaler spec: {}", spec_path)

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
            logger.error("Failed to get active container: {}", e)
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
                "nvidia-smi --query-gpu=name,memory.total,memory.used,memory.free,"
                "utilization.gpu,utilization.memory,driver_version "
                "--format=csv,noheader,nounits"
            )
            output = self.ssh_manager.execute_command_success(cmd, stream_output=False)

            if not output or not output.strip():
                return None

            # Parse CSV output (e.g., "Tesla T4, 15360, 469, 14891, 0, 3, 525.60.13")
            parts = [p.strip() for p in output.strip().split(",")]
            if len(parts) >= 7:
                gpu_info = {
                    "name": parts[0],
                    "memory_total": f"{parts[1]} MB",
                    "memory_used": f"{parts[2]} MB",
                    "memory_free": f"{parts[3]} MB",
                    "gpu_utilization": f"{parts[4]}%",
                    "memory_utilization": f"{parts[5]}%",
                    "driver_version": parts[6],
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
            logger.debug("GPU not available or nvidia-smi failed: {}", e)
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
                logger.info("No running containers found for image {}", self.docker_image)
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

            # Use execute_command instead of execute_command_success because docker kill
            # returns exit code 137 (SIGKILL) which is expected behavior, not an error
            exit_code, stdout, stderr = self.ssh_manager.execute_command(
                kill_cmd, stream_output=False
            )

            # Exit code 137 means the container was killed with SIGKILL (expected)
            # Exit code 0 means the kill command succeeded normally
            if exit_code not in [0, 137]:
                raise RuntimeError(f"Failed to kill containers: {stderr}")

            logger.info("Killed {} containers: {}", len(container_ids), container_ids)

            return {
                "status": "success",
                "killed_count": len(container_ids),
                "killed_containers": container_ids,
                "message": f"Successfully killed {len(container_ids)} container(s)",
            }

        except Exception as e:
            logger.error("Failed to kill containers: {}", e)
            return {"status": "failed", "error": str(e), "killed_count": 0, "killed_containers": []}

    def get_container_logs(self, container_id: str) -> str:
        """Get logs from a specific container."""
        try:
            return self.ssh_manager.execute_command_success(
                DockerCommandBuilder.build_logs_command(container_id), stream_output=False
            )
        except Exception as e:
            logger.error("Failed to get container logs: {}", e)
            return f"Error retrieving logs: {e}"

    def run_batch_inference(
        self,
        batch_name: str,
        batch_jsonl_file: str,
        base_controlnet_spec: str,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> dict[str, Any]:
        """Run batch inference for multiple prompts/videos.

        Args:
            batch_name: Name for the batch output directory
            batch_jsonl_file: Name of JSONL file with batch data (in inputs/batches/)
            base_controlnet_spec: Name of base controlnet spec file (in inputs/batches/)
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use

        Returns:
            Dictionary with batch results including output paths
        """
        logger.info("Running batch inference {} with {} GPU(s)", batch_name, num_gpu)

        # Check if batch file exists
        batch_path = f"{self.remote_dir}/inputs/batches/{batch_jsonl_file}"
        if not self.remote_executor.file_exists(batch_path):
            raise FileNotFoundError(f"Batch file not found: {batch_path}")

        # Check if base controlnet spec exists
        spec_path = f"{self.remote_dir}/inputs/batches/{base_controlnet_spec}"
        if not self.remote_executor.file_exists(spec_path):
            raise FileNotFoundError(f"Base controlnet spec not found: {spec_path}")

        # Don't create output directory here - let the batch_inference.sh script handle it
        # to avoid permission conflicts between SSH user and Docker container user

        # Execute batch inference using bash script (blocking)
        logger.info("Starting batch inference on GPU. This may take a while...")
        logger.info("Running batch inference synchronously...")

        # Run without the remote_log_path - the script itself handles logging
        exit_code = self._run_batch_inference_script(
            batch_name, batch_jsonl_file, base_controlnet_spec, num_gpu, cuda_devices
        )

        # Handle exit codes like single inference
        if exit_code != 0:
            logger.error("Batch inference failed with exit code {}", exit_code)
            # Create fallback log for failures
            self._create_fallback_log(
                run_id=batch_name,
                error_message=f"Batch inference {batch_name} failed with exit code {exit_code}",
                stderr="Check batch_run.log for details",
                exit_code=exit_code,
                is_batch=True,
            )

        # Get output files after completion
        remote_output_dir = f"{self.remote_dir}/outputs/{batch_name}"
        output_files = self._get_batch_output_files(batch_name)

        if output_files:
            logger.info("Batch inference completed successfully for {}", batch_name)
            logger.info("Generated {} output files", len(output_files))
            return {
                "batch_name": batch_name,
                "output_dir": remote_output_dir,
                "status": "completed",
                "output_files": output_files,
            }
        else:
            logger.error("Batch inference completed but no output files found")
            return {
                "batch_name": batch_name,
                "output_dir": remote_output_dir,
                "status": "failed",
                "error": "No output files generated",
            }

    def _run_batch_inference_script(
        self,
        batch_name: str,
        batch_jsonl_file: str,
        base_controlnet_spec: str,
        num_gpu: int,
        cuda_devices: str,
    ) -> int:
        """Run batch inference using the bash script synchronously.

        Returns:
            Exit code from the docker container (0 for success, non-zero for failure)
        """
        builder = DockerCommandBuilder(self.docker_image)
        builder.with_gpu()
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(self.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")

        # Build command - the script itself handles logging to outputs/{batch_name}/batch_run.log
        cmd = f"/workspace/bashscripts/batch_inference.sh {batch_name} {batch_jsonl_file} {base_controlnet_spec} {num_gpu} {cuda_devices}"
        builder.set_command(f'bash -lc "{cmd}"')

        # Add container name for tracking
        container_name = f"cosmos_batch_{batch_name[:8]}"
        builder.with_name(container_name)

        # Run the command synchronously (blocking, same as single inference)
        command = builder.build()
        logger.debug("Executing Docker command for batch inference: %s", command)

        # Execute and wait for completion (blocking)
        exit_code, stdout, stderr = self.ssh_manager.execute_command(
            command,
            timeout=3600,  # 1 hour timeout for batch inference
            stream_output=False,  # Could be made configurable
        )

        if exit_code != 0:
            logger.error("Batch inference failed with exit code {}", exit_code)
            if stderr:
                logger.error("STDERR: {}", stderr)
        else:
            logger.info("Batch inference completed successfully")

        return exit_code

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
            logger.warning("Failed to list output files: {}", e)
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
            logger.info("Auto-detecting active container for image {}", self.docker_image)
            container = self.get_active_container()

            if not container:
                raise RuntimeError("No running containers found")

            container_id = container["id"]

            # Show warning if multiple containers detected
            if "warning" in container:
                print(f"[WARNING] {container['warning']}")

        logger.info("Streaming logs from container {}", container_id)
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
