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
        stream_logs: bool = False,
    ) -> dict:
        """Run Cosmos-Transfer1 inference on remote instance.

        Executes inference with real-time log streaming. Logs are streamed
        from the remote instance using efficient seek-based position tracking
        in a background thread during execution.

        Args:
            prompt_file: Name of prompt file (without path).
            run_id: Run ID for tracking (REQUIRED).
            num_gpu: Number of GPUs to use.
            cuda_devices: CUDA device IDs to use.

        Returns:
            Dict containing status (success/failed), log_path to local log file,
            and prompt_name for the executed inference.

        Raises:
            Exception: If inference execution fails or streaming encounters errors.
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
        log_dir = Path(f"outputs/{prompt_name}/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        local_log_path = log_dir / f"run_{run_id}.log"

        try:
            # Log path for reference
            remote_log_path = f"{self.remote_dir}/outputs/{prompt_name}/run.log"
            run_logger.info("Remote log path: %s", remote_log_path)

            # Conditionally stream logs
            if stream_logs:
                import threading

                from cosmos_workflow.monitoring.log_streamer import RemoteLogStreamer

                streamer = RemoteLogStreamer(self.ssh_manager)
                stream_thread = threading.Thread(
                    target=streamer.stream_remote_log,
                    args=(remote_log_path, local_log_path),
                    kwargs={
                        "poll_interval": 2.0,
                        "timeout": 3600,
                        "wait_for_file": True,
                        "completion_marker": "[COSMOS_COMPLETE]",
                    },
                    daemon=True,
                )
                stream_thread.start()
                run_logger.info("Started log streaming from remote...")
            else:
                run_logger.info("Use 'cosmos stream' to view logs in real-time")

            # Execute inference using bash script
            run_logger.info("Executing inference script on remote...")
            self._run_inference_script(prompt_name, num_gpu, cuda_devices)

            # Wait for streaming thread if enabled
            if stream_logs:
                stream_thread.join(timeout=5)

            run_logger.info("Inference completed successfully for %s", prompt_name)

            return {
                "status": "success",
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
        stream_logs: bool = False,
    ) -> dict:
        """Run 4K upscaling on remote instance.

        Executes upscaling with real-time log streaming. Logs are streamed
        from the remote instance using efficient seek-based position tracking
        in a background thread during execution.

        Args:
            prompt_file: Name of prompt file (without path).
            run_id: Run ID for tracking (REQUIRED).
            control_weight: Control weight for upscaling (0.0-1.0).
            num_gpu: Number of GPUs to use.
            cuda_devices: CUDA device IDs to use.

        Returns:
            Dict containing status (success/failed) and log_path to local log file.

        Raises:
            FileNotFoundError: If input video for upscaling is not found.
            Exception: If upscaling execution fails or streaming encounters errors.
        """
        prompt_name = prompt_file.stem

        # Setup run-specific logger
        run_logger = get_run_logger(run_id, f"{prompt_name}_upscaled")
        run_logger.info("Running upscaling for %s with weight %f", prompt_name, control_weight)

        # Setup local log path
        log_dir = Path(f"outputs/{prompt_name}_upscaled/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        local_log_path = log_dir / f"run_{run_id}.log"

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

            # Conditionally stream logs
            if stream_logs:
                import threading

                from cosmos_workflow.monitoring.log_streamer import RemoteLogStreamer

                streamer = RemoteLogStreamer(self.ssh_manager)
                stream_thread = threading.Thread(
                    target=streamer.stream_remote_log,
                    args=(remote_log_path, local_log_path),
                    kwargs={
                        "poll_interval": 2.0,
                        "timeout": 1800,  # 30 minutes for upscaling
                        "wait_for_file": True,
                        "completion_marker": "[COSMOS_COMPLETE]",
                    },
                    daemon=True,
                )
                stream_thread.start()
                run_logger.info("Started log streaming for upscaling...")
            else:
                run_logger.info("Use 'cosmos stream' to view logs in real-time")

            # Execute upscaling using bash script
            run_logger.info("Starting upscaling...")
            self._run_upscaling_script(prompt_name, control_weight, num_gpu, cuda_devices)

            # Wait for streaming thread if enabled
            if stream_logs:
                stream_thread.join(timeout=5)

            run_logger.info("Upscaling completed successfully for %s", prompt_name)

            return {
                "status": "success",
                "log_path": str(local_log_path),
                "prompt_name": prompt_name,
            }

        except Exception as e:
            run_logger.error("Upscaling failed for %s: %s", prompt_name, e)
            return {"status": "failed", "error": str(e), "log_path": str(local_log_path)}

    def run_prompt_enhancement(
        self,
        batch_filename: str,
        operation_id: str | None = None,
        offload: bool = True,
        checkpoint_dir: str = "/workspace/checkpoints",
        timeout: int = 600,
        stream_logs: bool = False,
    ) -> dict:
        """Run prompt enhancement using Pixtral model on GPU.

        Processes a batch of prompts using the prompt_upsampler.py script.
        Note: This doesn't create a Run in the database, but we still
        track operations for debugging.

        Args:
            batch_filename: Name of batch JSON file in inputs directory
            operation_id: Optional operation ID for tracking
            offload: Whether to offload model between prompts (True for memory efficiency)
            checkpoint_dir: Directory containing model checkpoints
            timeout: Execution timeout in seconds

        Returns:
            Dict with status and optional log_path if operation_id provided
        """
        # Setup logger
        if operation_id:
            log_dir = Path("outputs/prompt_enhancement/logs")
            log_dir.mkdir(parents=True, exist_ok=True)
            local_log_path = log_dir / f"op_{operation_id}.log"
            # Use bound logger for this operation
            op_logger = logger.bind(operation_id=operation_id)
        else:
            local_log_path = None
            op_logger = logger

        op_logger.info("Running prompt enhancement for batch %s", batch_filename)

        # Setup remote log path if we're streaming
        remote_log_path = None
        if stream_logs and operation_id:
            remote_log_path = f"{self.remote_dir}/logs/prompt_enhancement/op_{operation_id}.log"
            # Ensure log directory exists
            self.remote_executor.create_directory(f"{self.remote_dir}/logs/prompt_enhancement")

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

            # Add logging redirection if streaming
            if remote_log_path:
                cmd = f"({cmd}) 2>&1 | tee {remote_log_path}; echo '[COSMOS_COMPLETE]' >> {remote_log_path}"

            builder.set_command(cmd)

            # Start streaming thread if requested
            if stream_logs and remote_log_path and local_log_path:
                import threading

                from cosmos_workflow.monitoring.log_streamer import RemoteLogStreamer

                streamer = RemoteLogStreamer(self.ssh_manager)
                stream_thread = threading.Thread(
                    target=streamer.stream_remote_log,
                    args=(remote_log_path, local_log_path),
                    kwargs={
                        "poll_interval": 2.0,
                        "timeout": timeout + 60,  # Give extra time for cleanup
                        "wait_for_file": True,
                        "completion_marker": "[COSMOS_COMPLETE]",
                    },
                    daemon=True,
                )
                stream_thread.start()
                op_logger.info("Started log streaming for prompt enhancement")

            # Execute via remote executor
            op_logger.info("Starting prompt enhancement (batch mode)...")
            self.remote_executor.execute_docker(builder, timeout=timeout)

            op_logger.info("Prompt enhancement completed for batch %s", batch_filename)

            result = {"status": "success"}
            if local_log_path:
                result["log_path"] = str(local_log_path)
            return result

        except Exception as e:
            op_logger.error("Prompt enhancement failed: %s", e)
            result = {"status": "failed", "error": str(e)}
            if local_log_path:
                result["log_path"] = str(local_log_path)
            return result

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
        stream_logs: bool = False,
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

        # Setup logging paths if streaming
        remote_log_path = None
        local_log_path = None
        if stream_logs:
            remote_log_path = f"{self.remote_dir}/logs/batch/{batch_name}.log"
            local_log_path = Path(f"outputs/batch/{batch_name}/batch.log")
            local_log_path.parent.mkdir(parents=True, exist_ok=True)
            # Ensure remote log directory exists
            self.remote_executor.create_directory(f"{self.remote_dir}/logs/batch")

        # Check if batch file exists
        batch_path = f"{self.remote_dir}/inputs/batches/{batch_jsonl_file}"
        if not self.remote_executor.file_exists(batch_path):
            raise FileNotFoundError(f"Batch file not found: {batch_path}")

        # Create output directory
        remote_output_dir = f"{self.remote_dir}/outputs/{batch_name}"
        self.remote_executor.create_directory(remote_output_dir)

        # Start streaming thread if requested
        if stream_logs and remote_log_path and local_log_path:
            import threading

            from cosmos_workflow.monitoring.log_streamer import RemoteLogStreamer

            streamer = RemoteLogStreamer(self.ssh_manager)
            stream_thread = threading.Thread(
                target=streamer.stream_remote_log,
                args=(remote_log_path, local_log_path),
                kwargs={
                    "poll_interval": 2.0,
                    "timeout": 7200 + 60,  # 2 hour timeout + extra time
                    "wait_for_file": True,
                    "completion_marker": "[COSMOS_COMPLETE]",
                },
                daemon=True,
            )
            stream_thread.start()
            logger.info("Started log streaming for batch inference")

        # Execute batch inference using bash script
        logger.info("Starting batch inference...")
        self._run_batch_inference_script(
            batch_name, batch_jsonl_file, num_gpu, cuda_devices, remote_log_path
        )

        # Get list of output files
        output_files = self._get_batch_output_files(batch_name)

        logger.info("Batch inference completed successfully for %s", batch_name)
        return {
            "batch_name": batch_name,
            "output_dir": remote_output_dir,
            "output_files": output_files,
        }

    def _run_batch_inference_script(
        self,
        batch_name: str,
        batch_jsonl_file: str,
        num_gpu: int,
        cuda_devices: str,
        remote_log_path: str | None = None,
    ) -> None:
        """Run batch inference using the bash script."""
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
            logger.info(f"Auto-detecting most recent container for image {self.docker_image}")
            cmd = f'sudo docker ps -l -q --filter "ancestor={self.docker_image}"'
            container_id = self.ssh_manager.execute_command_success(
                cmd, stream_output=False
            ).strip()

            if not container_id:
                raise RuntimeError("No running containers found")

        logger.info(f"Streaming logs from container {container_id}")
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
