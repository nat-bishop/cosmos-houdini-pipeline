"""GPU execution module for running NVIDIA Cosmos models on remote GPU servers.

This module handles all GPU-related operations including inference,
batch processing, and prompt upsampling using remote Docker containers.
"""

import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.config import ConfigManager
from cosmos_workflow.connection import SSHManager
from cosmos_workflow.execution.command_builder import RemoteCommandExecutor
from cosmos_workflow.execution.docker_executor import DockerExecutor
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.utils import nvidia_format
from cosmos_workflow.utils.json_handler import JSONHandler
from cosmos_workflow.utils.logging import logger


class GPUExecutor:
    """Execute GPU operations on remote servers.

    This class manages GPU execution for the NVIDIA Cosmos workflow,
    including model inference, batch processing, and prompt upsampling.
    It coordinates SSH connections, file transfers, and Docker containers
    on remote GPU nodes.
    """

    def __init__(self, config_manager: ConfigManager | None = None, service=None):
        """Initialize GPU executor.

        Args:
            config_manager: Configuration manager instance. If None, creates default.
            service: Optional DataRepository service for database updates.
        """
        self.config_manager = config_manager or ConfigManager()
        self.service = service  # For database updates in completion handlers
        self.ssh_manager = None
        self.file_transfer = None
        self.remote_executor = None
        self.docker_executor = None
        self._services_initialized = False
        self.json_handler = JSONHandler()

    def _initialize_services(self):
        """Initialize all required services for GPU execution.

        This method lazily initializes services on first use to avoid
        creating connections when not needed.
        """
        if self._services_initialized:
            return

        # Initialize SSH and related services
        self.ssh_manager = SSHManager(self.config_manager.get_ssh_options())
        remote_config = self.config_manager.get_remote_config()
        self.file_transfer = FileTransferService(self.ssh_manager, remote_config.remote_dir)
        self.remote_executor = RemoteCommandExecutor(self.ssh_manager)
        self.docker_executor = DockerExecutor(
            self.ssh_manager,
            remote_config.remote_dir,
            remote_config.docker_image,
            config_manager=self.config_manager,
        )

        self._services_initialized = True

    # ========== Format Conversion Helpers ==========

    # ========== Container Monitoring (REMOVED) ==========
    # Background monitoring has been replaced by synchronous execution
    # All operations now block until completion and return results immediately
    # No polling or status checking is needed

    # ========== Single Run Execution ==========

    # ========== Thread-Safe Download Helper ==========

    def _thread_safe_download(self, remote_path: str, local_path: str) -> bool:
        """Download a file using thread-safe paramiko SFTP.

        IMPORTANT: This is a workaround for threading limitations in our architecture.

        WHY THIS EXISTS:
        - Completion handlers run in background threads (for async monitoring)
        - Our FileTransferService and SSHManager weren't designed for multi-threading
        - They use context managers and shared connections that don't work across threads

        WHAT IT DOES:
        - Creates its own SSH connection inside the thread
        - Uses raw paramiko instead of our wrappers
        - Downloads the file and closes the connection

        FUTURE IMPROVEMENT:
        - Redesign FileTransferService to be thread-safe with connection pooling
        - Or move to an async/await architecture throughout the codebase
        - Or use a message queue system to handle downloads in the main thread

        Args:
            remote_path: Remote file path
            local_path: Local file path

        Returns:
            True if download succeeded, False otherwise
        """
        import paramiko

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # noqa: S507
            ssh.connect(**self.config_manager.get_ssh_options())

            try:
                sftp = ssh.open_sftp()
                try:
                    sftp.get(remote_path, str(local_path))
                    return True
                except FileNotFoundError:
                    logger.error("File not found: {}", remote_path)
                    return False
                finally:
                    sftp.close()
            finally:
                ssh.close()
        except Exception as e:
            logger.error("Thread-safe download failed: {}", e)
            return False

    # ========== Completion Handlers ==========

    def _handle_inference_completion(self, run_id: str, exit_code: int, container_name: str):
        """Handle inference container completion.

        This runs in a background thread, so it needs to be self-contained.
        We'll do the download directly here using paramiko SFTP.

        Args:
            run_id: Database run ID
            exit_code: Container exit code (0=success, -1=timeout/error, other=failed)
            container_name: Container name for logging
        """
        logger.info("Handling inference completion for run {} (exit code: {})", run_id, exit_code)

        # Debug logging for service availability
        if self.service is None:
            logger.error(
                "ERROR: self.service is None in completion handler! Cannot update database."
            )
        else:
            logger.info("self.service is available: {}", type(self.service))

        try:
            if exit_code == 0:
                # Success - try to download outputs
                run_dir = Path("outputs") / f"run_{run_id}"
                run_dir.mkdir(parents=True, exist_ok=True)

                # Output paths
                outputs_dir = run_dir / "outputs"
                outputs_dir.mkdir(exist_ok=True)
                local_output = outputs_dir / "output.mp4"

                # Get remote config - add explicit error handling
                try:
                    logger.debug("Getting remote config for run {}", run_id)
                    remote_config = self.config_manager.get_remote_config()
                    remote_output = f"{remote_config.remote_dir}/outputs/run_{run_id}/output.mp4"
                except Exception as e:
                    logger.error("Failed to get remote config: {} (type: {})", e, type(e).__name__)
                    logger.error("config_manager type: {}", type(self.config_manager))
                    if self.service:
                        self.service.update_run_status(run_id, "failed")
                        self.service.update_run(run_id, error_message=f"Configuration error: {e}")
                    return

                # Download using thread-safe helper
                if self._thread_safe_download(remote_output, local_output):
                    logger.info("Downloaded output file for run {}", run_id)

                    # Update database with success
                    if self.service:
                        self.service.update_run(
                            run_id,
                            outputs={
                                "output_path": str(local_output),
                                "completed_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        self.service.update_run_status(run_id, "completed")
                    logger.info("Inference run {} completed successfully", run_id)
                else:
                    # Output not found or download failed
                    if self.service:
                        self.service.update_run_status(run_id, "failed")
                        self.service.update_run(
                            run_id, error_message="Output file not found after completion"
                        )
                    logger.error("Output file not found for run {}", run_id)
            else:
                # Container failed or timed out
                if self.service:
                    self.service.update_run_status(run_id, "failed")
                    if exit_code == -1:
                        error_msg = "Container timed out or monitoring error"
                    else:
                        error_msg = f"Container failed with exit code {exit_code}"
                    self.service.update_run(run_id, error_message=error_msg)
                logger.error("Inference run {} failed with exit code {}", run_id, exit_code)
        except Exception as e:
            logger.error("Error in completion handler for run {}: {}", run_id, e)
            if self.service:
                self.service.update_run_status(run_id, "failed")
                self.service.update_run(run_id, error_message=f"Completion handler error: {e}")

    def _handle_enhancement_completion(self, run_id: str, exit_code: int, container_name: str):
        """Handle enhancement container completion.

        Args:
            run_id: Database run ID
            exit_code: Container exit code
            container_name: Container name for logging
        """
        logger.info("Handling enhancement completion for run {} (exit code: {})", run_id, exit_code)

        if exit_code == 0:
            # Download and parse results
            remote_config = self.config_manager.get_remote_config()
            remote_results = f"{remote_config.remote_dir}/outputs/run_{run_id}/batch_results.json"

            try:
                with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
                    tmp_path = Path(tmp.name)

                # Download using thread-safe helper
                if self._thread_safe_download(remote_results, str(tmp_path)):
                    try:
                        results = self.json_handler.read_json(tmp_path)
                    finally:
                        tmp_path.unlink(missing_ok=True)
                else:
                    results = None

                if results and len(results) > 0:
                    enhanced_text = results[0].get("upsampled_prompt", "")
                    if self.service:
                        self.service.update_run(
                            run_id,
                            outputs={
                                "enhanced_text": enhanced_text,
                                "completed_at": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        self.service.update_run_status(run_id, "completed")
                    logger.info("Enhancement run {} completed successfully", run_id)
                else:
                    if self.service:
                        self.service.update_run_status(run_id, "failed")
                        self.service.update_run(
                            run_id, error_message="No enhancement results found"
                        )
                    logger.error("No enhancement results for run {}", run_id)

            except Exception as e:
                logger.error("Failed to process enhancement results for run {}: {}", run_id, e)
                if self.service:
                    self.service.update_run_status(run_id, "failed")
                    self.service.update_run(run_id, error_message=f"Results processing failed: {e}")
        else:
            # Enhancement failed
            if self.service:
                self.service.update_run_status(run_id, "failed")
                if exit_code == -1:
                    error_msg = "Enhancement timed out or monitoring error"
                else:
                    error_msg = f"Enhancement failed with exit code {exit_code}"
                self.service.update_run(run_id, error_message=error_msg)
            logger.error("Enhancement run {} failed with exit code {}", run_id, exit_code)

    def _handle_upscaling_completion(self, run_id: str, exit_code: int, container_name: str):
        """Handle upscaling container completion.

        Args:
            run_id: Database run ID
            exit_code: Container exit code
            container_name: Container name for logging
        """
        logger.info("Handling upscaling completion for run {} (exit code: {})", run_id, exit_code)

        if exit_code == 0:
            # Success - download 4K output
            run_dir = Path("outputs") / f"run_{run_id}"
            run_dir.mkdir(parents=True, exist_ok=True)

            # Output paths
            outputs_dir = run_dir / "outputs"
            outputs_dir.mkdir(exist_ok=True)
            local_output = outputs_dir / "output_4k.mp4"

            # Get remote config
            remote_config = self.config_manager.get_remote_config()
            remote_output = f"{remote_config.remote_dir}/outputs/run_{run_id}/output_4k.mp4"

            # Download using thread-safe helper
            if self._thread_safe_download(remote_output, local_output):
                logger.info("Downloaded 4K output file for run {}", run_id)

                # Update database with success
                if self.service:
                    self.service.update_run(
                        run_id,
                        outputs={
                            "output_path": str(local_output),
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )
                    self.service.update_run_status(run_id, "completed")
                logger.info("Upscaling run {} completed successfully", run_id)
            else:
                # Output not found or download failed
                if self.service:
                    self.service.update_run_status(run_id, "failed")
                    self.service.update_run(run_id, error_message="4K output file not found")
                logger.error("4K output not found for run {}", run_id)
        else:
            # Upscaling failed
            if self.service:
                self.service.update_run_status(run_id, "failed")
                if exit_code == -1:
                    error_msg = "Upscaling timed out or monitoring error"
                else:
                    error_msg = f"Upscaling failed with exit code {exit_code}"
                self.service.update_run(run_id, error_message=error_msg)
            logger.error("Upscaling run {} failed with exit code {}", run_id, exit_code)

    def execute_run(
        self,
        run: dict[str, Any],
        prompt: dict[str, Any],
        stream_output: bool = False,
    ) -> dict[str, Any]:
        """Execute a single run on the GPU synchronously.

        Args:
            run: Run dictionary containing id, execution_config, etc.
            prompt: Prompt dictionary containing prompt_text, inputs, etc.

        Returns:
            Dictionary containing execution results with status='completed',
            output_path, and other metadata. The run blocks until completion.

        Raises:
            RuntimeError: If GPU execution fails
        """
        # Initialize services if not already done
        self._initialize_services()

        run_id = run["id"]

        logger.info("Executing run {} on GPU", run_id)

        # Create local run directory
        run_dir = Path("outputs") / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Prepare inputs for GPU execution
        inputs_dir = run_dir / "inputs"
        inputs_dir.mkdir(exist_ok=True)

        # Create spec file for this single run using nvidia_format
        spec_data = nvidia_format.to_cosmos_inference_json(prompt, run)

        spec_file = inputs_dir / "spec.json"
        self.json_handler.write_json(spec_data, spec_file)

        # Execute on GPU using DockerExecutor
        try:
            with self.ssh_manager:
                # Upload batch and any video files
                remote_config = self.config_manager.get_remote_config()

                # Clean all old run directories before starting
                logger.info("Cleaning up old run directories...")
                cleanup_cmd = f"rm -rf {remote_config.remote_dir}/outputs/run_* 2>/dev/null || true"
                self.remote_executor.execute_command(cleanup_cmd)

                remote_run_dir = f"{remote_config.remote_dir}/runs/{run_id}"

                # Upload spec file
                self.file_transfer.upload_file(spec_file, f"{remote_run_dir}/inputs")

                # Upload all video files from inputs (video, depth, seg, etc.)
                inputs = prompt.get("inputs", {})
                for input_type, input_path in inputs.items():
                    if input_path and Path(input_path).exists():
                        logger.info("Uploading {}: {}", input_type, input_path)
                        self.file_transfer.upload_file(
                            Path(input_path), f"{remote_run_dir}/inputs/videos"
                        )

                # Upload bash scripts if not already present
                scripts_dir = Path(__file__).parent.parent.parent / "scripts"
                remote_scripts_dir = f"{remote_config.remote_dir}/bashscripts"

                # Upload inference.sh script
                inference_script = scripts_dir / "inference.sh"
                if inference_script.exists():
                    logger.info("Uploading inference script to remote")
                    self.file_transfer.upload_file(inference_script, remote_scripts_dir)
                else:
                    logger.warning("Inference script not found at {}", inference_script)

                # Upload upscale.sh script (might be needed later)
                upscale_script = scripts_dir / "upscale.sh"
                if upscale_script.exists():
                    self.file_transfer.upload_file(upscale_script, remote_scripts_dir)

                # Run inference synchronously with streaming output
                # Create a prompt file path for DockerExecutor (it expects Path)
                prompt_file = Path(f"{run_id}.json")  # Just a name, not used inside
                inference_result = self.docker_executor.run_inference(
                    prompt_file=prompt_file,
                    run_id=run_id,
                    stream_output=stream_output,  # Use parameter to control streaming
                )

                # Check the result status
                if inference_result["status"] == "failed":
                    error_msg = inference_result.get(
                        "error",
                        f"Inference failed with exit code {inference_result.get('exit_code', 'unknown')}",
                    )
                    raise RuntimeError(error_msg)

                elif inference_result["status"] == "completed":
                    # Inference completed successfully, download outputs immediately
                    logger.info("Inference completed for run {}, downloading outputs...", run_id)

                    try:
                        output_path = self._download_outputs(run_id, run_dir, upscaled=False)

                        # Return completed status with output path
                        return {
                            "status": "completed",
                            "output_path": str(output_path),
                            "message": "Inference completed successfully",
                            "run_id": run_id,
                            "log_path": str(run_dir / "logs" / "inference.log"),
                        }
                    except Exception as download_error:
                        logger.error(
                            "Failed to download outputs for run {}: {}", run_id, download_error
                        )
                        raise RuntimeError(
                            f"Inference completed but output download failed: {download_error}"
                        ) from download_error

                else:
                    # Unexpected status
                    raise RuntimeError(
                        f"Unexpected inference status: {inference_result.get('status')}"
                    )

        except Exception as e:
            logger.error("GPU execution failed for run {}: {}", run_id, e)
            raise RuntimeError(f"GPU execution failed: {e}") from e

    def _download_outputs(
        self,
        run_id: str,
        local_run_dir: Path,
        upscaled: bool = False,
    ) -> Path:
        """Download output files from remote GPU server.

        Args:
            run_id: The run ID
            local_run_dir: Local directory for this run
            upscaled: Whether this is an upscale operation (affects output filename)

        Returns:
            Path to the downloaded output file
        """
        remote_config = self.config_manager.get_remote_config()
        outputs_dir = local_run_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)
        logs_dir = local_run_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # All runs use the same directory structure now
        remote_output_dir = f"{remote_config.remote_dir}/outputs/run_{run_id}"

        # Determine output filename based on operation type
        if upscaled:
            remote_file = f"{remote_output_dir}/output_4k.mp4"
            local_file = outputs_dir / "output_4k.mp4"
        else:
            remote_file = f"{remote_output_dir}/output.mp4"
            local_file = outputs_dir / "output.mp4"

        # Download the output file
        try:
            self.file_transfer.download_file(remote_file, str(local_file))
            logger.info("Downloaded output to {}", local_file)
        except Exception as e:
            logger.error("Failed to download output: {}", e)
            # Re-raise the exception so the failure is properly reported
            raise RuntimeError(f"Failed to download output file: {e}") from e

        # Download any auto-generated control files (if they exist)
        # These are created by the NVIDIA model when not provided in the spec
        control_types = ["edge", "depth", "seg", "vis"]
        for control_type in control_types:
            # The NVIDIA model generates files as {control_type}_input_control.mp4
            remote_control_file = f"{remote_output_dir}/{control_type}_input_control.mp4"
            local_control_file = outputs_dir / f"{control_type}_input_control.mp4"

            try:
                self.file_transfer.download_file(remote_control_file, str(local_control_file))
                logger.info(
                    "Downloaded auto-generated {} control to {}", control_type, local_control_file
                )
            except FileNotFoundError:
                # This is expected - not all runs generate all control types
                logger.debug(
                    "No auto-generated {} control found (expected if provided in spec)",
                    control_type,
                )
            except Exception as e:
                # Log but don't fail - control files are supplementary
                logger.warning("Failed to download {} control file: {}", control_type, e)

        # Also download the log file
        remote_log = f"{remote_output_dir}/run.log"
        docker_log_path = outputs_dir / "run.log"  # Keep in outputs as backup
        try:
            self.file_transfer.download_file(remote_log, str(docker_log_path))
            logger.info("Downloaded Docker log to {}", docker_log_path)

            # Append to unified log
            unified_log = logs_dir / f"{run_id}.log"
            if docker_log_path.exists() and unified_log.exists():
                with open(unified_log, "a") as unified:
                    unified.write("\n" + "=" * 60 + "\n")
                    unified.write("=== DOCKER EXECUTION LOGS ===\n")
                    unified.write("=" * 60 + "\n\n")
                    with open(docker_log_path) as docker:
                        unified.write(docker.read())
                logger.info("Appended Docker logs to unified log")
        except FileNotFoundError:
            logger.warning("Remote log not found: {}", remote_log)
        except Exception as e:
            logger.error("Failed to download/append log: {}", e)

        return local_file

    # ========== Batch Execution ==========

    def execute_batch_runs(
        self,
        runs_and_prompts: list[tuple[dict[str, Any], dict[str, Any]]],
    ) -> dict[str, Any]:
        """Execute multiple runs as a batch on the GPU.

        This method optimizes GPU utilization by processing multiple prompts
        together in a single Docker container execution.

        Args:
            runs_and_prompts: List of (run_dict, prompt_dict) tuples

        Returns:
            Dictionary containing batch results with status and output_mapping

        Raises:
            RuntimeError: If batch execution fails
        """
        if not runs_and_prompts:
            logger.warning("Empty batch provided to execute_batch_runs")
            return {
                "status": "success",
                "batch_name": "empty_batch",
                "output_mapping": {},
            }

        # Initialize services if not already done
        self._initialize_services()

        logger.info("Executing batch of {} runs on GPU", len(runs_and_prompts))

        # Generate batch name from first run ID
        batch_name = f"batch_{runs_and_prompts[0][0]['id'][:8]}_{len(runs_and_prompts)}"
        batch_dir = Path("outputs") / batch_name
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Prepare batch data using the JSONL format for batch inference
        # Use the batch-specific format with control_overrides structure
        batch_lines = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

        # Create batch JSONL file (not JSON array)
        batch_file = batch_dir / "batch.jsonl"
        nvidia_format.write_batch_jsonl(batch_lines, batch_file)

        # Execute batch on GPU
        try:
            with self.ssh_manager:
                # Upload batch file and videos
                remote_config = self.config_manager.get_remote_config()

                # Upload batch file to inputs/batches/ as expected by batch_inference.sh
                remote_batch_location = f"{remote_config.remote_dir}/inputs/batches"
                self.file_transfer.upload_file(batch_file, remote_batch_location)

                # Upload any videos to run-specific paths as expected by JSONL format
                for run_dict, prompt_dict in runs_and_prompts:
                    run_id = run_dict["id"]
                    inputs = prompt_dict.get("inputs", {})

                    # Upload ALL input files (video, seg, depth, edge, etc.)
                    for input_type, input_path in inputs.items():
                        if input_path and Path(input_path).exists():
                            # Upload to runs/{run_id}/inputs/videos/ as referenced in JSONL
                            remote_video_dir = (
                                f"{remote_config.remote_dir}/runs/{run_id}/inputs/videos"
                            )
                            logger.info(
                                "Uploading {} for run {}: {}", input_type, run_id, input_path
                            )
                            self.file_transfer.upload_file(Path(input_path), remote_video_dir)

                # Run batch inference
                batch_result = self.docker_executor.run_batch_inference(
                    batch_name=batch_name,
                    batch_jsonl_file=batch_file.name,
                )

                if batch_result["status"] == "failed":
                    raise RuntimeError(f"Batch execution failed: {batch_result.get('error')}")

                # Batch now runs synchronously, so should have completed status
                if batch_result.get("status") != "completed":
                    raise RuntimeError(f"Unexpected batch status: {batch_result.get('status')}")

                # Download all batch outputs to batch directory (simpler approach)
                logger.info("Downloading batch outputs to local batch directory")

                # Ensure batch output directory exists locally
                outputs_dir = batch_dir / "outputs"
                outputs_dir.mkdir(exist_ok=True)

                # Download all output files to batch directory
                remote_output_dir = batch_result.get(
                    "output_dir", f"{remote_config.remote_dir}/outputs/{batch_name}"
                )
                output_files = batch_result.get("output_files", [])

                for remote_file in output_files:
                    # Extract just the filename
                    filename = Path(remote_file).name
                    local_file = outputs_dir / filename

                    try:
                        self.file_transfer.download_file(remote_file, str(local_file))
                        logger.info("Downloaded {} to {}", filename, local_file)
                    except Exception as e:
                        logger.error("Failed to download {}: {}", filename, e)

                # Download the batch log file
                remote_log = f"{remote_output_dir}/batch_run.log"
                local_log = batch_dir / "batch_run.log"
                try:
                    self.file_transfer.download_file(remote_log, str(local_log))
                    logger.info("Downloaded batch log to {}", local_log)
                except Exception as e:
                    logger.warning("Could not download batch log: {}", e)

                # Update database for each run to point to files in batch directory
                logger.info("Updating database with batch output paths")
                for i, (run_dict, _) in enumerate(runs_and_prompts):
                    run_id = run_dict["id"]

                    # Build outputs dictionary with paths in batch directory
                    outputs = {
                        "output_path": str(outputs_dir / f"video_{i:03d}.mp4"),
                        "log_path": str(local_log),
                        "batch_id": batch_name,
                        "batch_index": i,
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }

                    # Check if control files exist and add them
                    control_types = ["edge", "depth", "seg", "vis"]
                    for control_type in control_types:
                        control_file = outputs_dir / f"{control_type}_input_control_{i:03d}.mp4"
                        if control_file.exists():
                            outputs[f"{control_type}_control"] = str(control_file)

                    # Update run in database
                    self.service.update_run(run_id, outputs=outputs)
                    self.service.update_run_status(run_id, "completed")
                    logger.info("Updated run {} with batch output paths", run_id)

                return {
                    "status": "success",
                    "batch_name": batch_name,
                    "run_count": len(runs_and_prompts),
                    "output_dir": str(batch_dir),
                    "duration_seconds": batch_result.get("duration_seconds", 0),
                }

        except Exception as e:
            logger.error("Batch execution failed: {}", e)
            return {
                "status": "failed",
                "batch_name": batch_name,
                "error": str(e),
                "started_at": datetime.now(timezone.utc).isoformat(),
            }

    # ========== Upsampling Methods ==========

    def execute_enhancement_run(
        self,
        run: dict[str, Any],
        prompt: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute prompt enhancement as a database run.

        This method runs prompt enhancement with proper run tracking,
        creating run directories and storing results in the database format.

        Args:
            run: Run dictionary with id and execution_config
            prompt: Prompt dictionary with prompt_text and inputs

        Returns:
            Dictionary containing status and run information

        Raises:
            RuntimeError: If enhancement fails
        """
        # Initialize services if not already done
        self._initialize_services()

        run_id = run["id"]
        prompt_text = prompt["prompt_text"]
        execution_config = run["execution_config"]
        model = execution_config.get("model", "pixtral")
        video_path = execution_config.get("video_context")

        logger.info("Executing enhancement run {} with model {}", run_id, model)

        # Create run directory structure
        run_dir = Path("outputs") / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = run_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Prepare batch data for the upsampler script
        batch_data = [
            {
                "name": "prompt",
                "prompt": prompt_text,
                "video_path": video_path or "",
            }
        ]

        # Create batch file
        batch_filename = f"enhance_{run_id}.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            local_batch_path = Path(temp_dir) / batch_filename
            self.json_handler.write_json(batch_data, local_batch_path)

            try:
                with self.ssh_manager:
                    remote_config = self.config_manager.get_remote_config()

                    # Clean old run directories
                    logger.info("Cleaning up old run directories...")
                    cleanup_cmd = (
                        f"rm -rf {remote_config.remote_dir}/outputs/run_* 2>/dev/null || true"
                    )
                    self.remote_executor.execute_command(cleanup_cmd)

                    # Upload batch file
                    remote_inputs_dir = f"{remote_config.remote_dir}/inputs"
                    self.file_transfer.upload_file(local_batch_path, remote_inputs_dir)

                    # Upload video if provided
                    if video_path and Path(video_path).exists():
                        remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                        logger.info("Uploading video for context: {}", video_path)
                        self.file_transfer.upload_file(Path(video_path), remote_videos_dir)

                    # Upload upsampler script
                    scripts_dir = f"{remote_config.remote_dir}/scripts"
                    local_script = (
                        Path(__file__).parent.parent.parent / "scripts" / "prompt_upsampler.py"
                    )
                    if not local_script.exists():
                        raise FileNotFoundError(f"Upsampler script not found at {local_script}")
                    self.file_transfer.upload_file(local_script, scripts_dir)

                    # Execute prompt enhancement via DockerExecutor (already synchronous)
                    logger.info("Starting prompt enhancement on GPU...")
                    enhancement_result = self.docker_executor.run_prompt_enhancement(
                        batch_filename=batch_filename,
                        run_id=run_id,
                        offload=True,  # Memory efficient
                        checkpoint_dir="/workspace/checkpoints",
                    )

                    if enhancement_result["status"] == "failed":
                        raise RuntimeError(
                            f"Prompt enhancement failed: {enhancement_result.get('error', 'Unknown error')}"
                        )

                    elif enhancement_result["status"] == "completed":
                        # Enhancement completed successfully, download outputs
                        logger.info(
                            "Enhancement completed for run {}, downloading outputs...", run_id
                        )

                        # Download the enhanced prompts output files
                        remote_output_dir = f"{remote_config.remote_dir}/outputs/run_{run_id}"
                        local_output_dir = run_dir / "outputs"
                        local_output_dir.mkdir(exist_ok=True)

                        # The script may save either batch_results.json (for batch mode) or prompt_upsampled.json (single mode)
                        # Try both to be robust
                        remote_batch_results = f"{remote_output_dir}/batch_results.json"
                        remote_prompt_upsampled = f"{remote_output_dir}/prompt_upsampled.json"
                        local_batch_results = local_output_dir / "batch_results.json"
                        local_prompt_upsampled = local_output_dir / "prompt_upsampled.json"

                        results = None
                        enhanced_text = None

                        # First try batch_results.json (expected for batch mode)
                        try:
                            logger.info(
                                "Checking for batch_results.json at: {}", remote_batch_results
                            )
                            self.file_transfer.download_file(
                                remote_batch_results, str(local_batch_results)
                            )
                            logger.info(
                                "Successfully downloaded batch_results.json to: {}",
                                local_batch_results,
                            )

                            # Extract enhanced text from results
                            results = self.json_handler.read_json(local_batch_results)
                            if results and len(results) > 0:
                                enhanced_text = results[0].get("upsampled_prompt", "")
                                logger.info(
                                    "Extracted enhanced text from batch_results.json (length: {} chars)",
                                    len(enhanced_text) if enhanced_text else 0,
                                )
                        except Exception as e:
                            logger.info("batch_results.json not available: {}", e)

                        # If batch_results.json failed, try prompt_upsampled.json
                        if not enhanced_text:
                            try:
                                logger.info(
                                    "Checking for prompt_upsampled.json at: {}",
                                    remote_prompt_upsampled,
                                )
                                self.file_transfer.download_file(
                                    remote_prompt_upsampled, str(local_prompt_upsampled)
                                )
                                logger.info(
                                    "Successfully downloaded prompt_upsampled.json to: {}",
                                    local_prompt_upsampled,
                                )

                                # Read single result format
                                single_result = self.json_handler.read_json(local_prompt_upsampled)
                                enhanced_text = single_result.get("upsampled_prompt", "")
                                # Convert to batch format for consistency
                                results = [single_result]
                                logger.info(
                                    "Extracted enhanced text from prompt_upsampled.json (length: {} chars)",
                                    len(enhanced_text) if enhanced_text else 0,
                                )
                            except Exception as e:
                                logger.info("prompt_upsampled.json not available: {}", e)

                        # If still no results, list directory and error
                        if not enhanced_text:
                            # List remote directory contents for debugging
                            try:
                                logger.error(
                                    "No results files found. Listing remote directory contents:"
                                )
                                list_cmd = f"ls -la {remote_output_dir}/"
                                _, stdout, _ = self.ssh_manager.execute_command(
                                    list_cmd, timeout=10
                                )
                                logger.info("Remote directory contents:\n{}", stdout)
                            except Exception as list_error:
                                logger.error("Failed to list remote directory: {}", list_error)

                            raise RuntimeError(
                                f"No enhancement results found in {remote_output_dir}. "
                                f"Expected batch_results.json or prompt_upsampled.json"
                            )

                        # Validate we got the enhanced text
                        if not enhanced_text:
                            logger.error(
                                "Enhanced text is empty or null in results: {}",
                                results[0] if results else "no results",
                            )
                            raise RuntimeError("Enhanced text is empty")

                        logger.info(
                            "Successfully extracted enhanced text (first 100 chars): {}...",
                            enhanced_text[:100] if len(enhanced_text) > 100 else enhanced_text,
                        )

                        # Use the existing data repository service
                        if not self.service:
                            raise RuntimeError("DataRepository service not initialized")

                        data_repo = self.service

                        # Handle prompt creation/update based on create_new flag
                        create_new = execution_config.get("create_new", True)
                        prompt_id = prompt["id"]
                        enhanced_prompt_id = None

                        if create_new:
                            # Create new enhanced prompt
                            name = prompt.get("parameters", {}).get("name", "unnamed")
                            enhanced_prompt = data_repo.create_prompt(
                                prompt_text=enhanced_text,
                                inputs=prompt.get("inputs", {}),
                                parameters={
                                    **prompt.get("parameters", {}),
                                    "name": f"{name}_enhanced",
                                    "enhanced": True,
                                    "parent_prompt_id": prompt_id,
                                },
                            )
                            enhanced_prompt_id = enhanced_prompt["id"]
                            logger.info(
                                "Created enhanced prompt {} from {} for run {}",
                                enhanced_prompt_id,
                                prompt_id,
                                run_id,
                            )
                        else:
                            # Update existing prompt
                            updated_params = {**prompt.get("parameters", {}), "enhanced": True}
                            data_repo.update_prompt(
                                prompt_id,
                                prompt_text=enhanced_text,
                                parameters=updated_params,
                            )
                            enhanced_prompt_id = prompt_id
                            logger.info(
                                "Updated prompt {} with enhanced text for run {}",
                                prompt_id,
                                run_id,
                            )

                        # Update run in database with results
                        logger.info("Updating database run {} with enhancement results", run_id)
                        outputs = {
                            "enhanced_text": enhanced_text,
                            "original_prompt_id": prompt_id,
                            "enhanced_prompt_id": enhanced_prompt_id,
                            "enhancement_model": model,
                            "enhanced_at": datetime.now(timezone.utc).isoformat(),
                        }
                        data_repo.update_run(run_id, outputs=outputs)
                        data_repo.update_run_status(run_id, "completed")
                        logger.info("Database updated successfully for run {}", run_id)

                        # Download any log files if they exist
                        try:
                            remote_log = f"{remote_output_dir}/run.log"
                            local_log = logs_dir / "enhancement.log"
                            self.file_transfer.download_file(remote_log, str(local_log))
                            logger.info("Downloaded run log to: {}", local_log)
                        except Exception as log_error:
                            logger.debug("No run log to download: {}", log_error)

                        # Return completed status with enhanced prompt ID
                        logger.info(
                            "Enhancement run {} completed successfully. Enhanced prompt: {}",
                            run_id,
                            enhanced_prompt_id,
                        )
                        return {
                            "status": "completed",
                            "message": "Enhancement completed successfully",
                            "run_id": run_id,
                            "enhanced_text": enhanced_text,
                            "enhanced_prompt_id": enhanced_prompt_id,
                            "original_prompt_id": prompt_id,
                            "log_path": str(logs_dir / "enhancement.log"),
                        }

                    else:
                        # Unexpected status
                        raise RuntimeError(
                            f"Unexpected enhancement status: {enhancement_result.get('status')}"
                        )

            except Exception as e:
                logger.error("Enhancement run {} failed: {}", run_id, e)
                raise RuntimeError(f"Enhancement failed: {e}") from e

    def run_prompt_upsampling(
        self,
        prompt_text: str,
        model: str = "pixtral",
        video_path: str | None = None,
    ) -> str:
        """Run prompt upsampling on remote GPU (legacy method).

        This method is kept for backward compatibility but internally
        creates a temporary run_id and uses the new implementation.

        Args:
            prompt_text: The prompt text to enhance
            model: Model to use (currently only "pixtral" supported)
            video_path: Optional path to video for visual context

        Returns:
            Enhanced prompt text string
        """
        # Generate temporary run_id for backward compatibility
        import uuid

        temp_run_id = f"enhance_{uuid.uuid4().hex[:8]}"

        return self._run_prompt_upsampling_internal(
            run_id=temp_run_id,
            prompt_text=prompt_text,
            model=model,
            video_path=video_path,
        )

    def _run_prompt_upsampling_internal(
        self,
        run_id: str,
        prompt_text: str,
        model: str = "pixtral",
        video_path: str | None = None,
    ) -> str:
        """Internal method for prompt upsampling with run_id support.

        Args:
            run_id: Run ID for tracking and directory creation
            prompt_text: The prompt text to enhance
            model: Model to use
            video_path: Optional video for context

        Returns:
            Enhanced prompt text
        """
        # Initialize services if not already done
        self._initialize_services()

        logger.info("Starting prompt upsampling for run {} using {} model", run_id, model)

        # Prepare batch data for the upsampler script
        batch_data = [
            {
                "name": "prompt",
                "prompt": prompt_text,
                "video_path": video_path or "",
            }
        ]

        # Create temporary batch file
        batch_filename = f"upsample_{run_id}.json"

        # Use temporary directory for batch file
        with tempfile.TemporaryDirectory() as temp_dir:
            local_batch_path = Path(temp_dir) / batch_filename
            self.json_handler.write_json(batch_data, local_batch_path)

            try:
                with self.ssh_manager:
                    remote_config = self.config_manager.get_remote_config()

                    # Clean all old run directories before starting
                    logger.info("Cleaning up old run directories...")
                    cleanup_cmd = (
                        f"rm -rf {remote_config.remote_dir}/outputs/run_* 2>/dev/null || true"
                    )
                    self.remote_executor.execute_command(cleanup_cmd)

                    # Upload batch file - upload_file will create directory automatically
                    remote_inputs_dir = f"{remote_config.remote_dir}/inputs"
                    self.file_transfer.upload_file(local_batch_path, remote_inputs_dir)

                    # Upload video if provided
                    if video_path and Path(video_path).exists():
                        remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                        # upload_file will create the directory automatically
                        logger.info("Uploading video for context: {}", video_path)
                        self.file_transfer.upload_file(Path(video_path), remote_videos_dir)

                    # Upload upsampler script - upload_file will create directory automatically
                    scripts_dir = f"{remote_config.remote_dir}/scripts"

                    local_script = (
                        Path(__file__).parent.parent.parent / "scripts" / "prompt_upsampler.py"
                    )
                    if not local_script.exists():
                        raise FileNotFoundError(f"Upsampler script not found at {local_script}")

                    self.file_transfer.upload_file(local_script, scripts_dir)

                    # Execute prompt enhancement via DockerExecutor wrapper
                    logger.info("Executing prompt upsampling on GPU...")

                    enhancement_result = self.docker_executor.run_prompt_enhancement(
                        batch_filename=batch_filename,
                        run_id=run_id,
                        offload=True,  # Memory efficient for single prompts
                        checkpoint_dir="/workspace/checkpoints",
                    )

                    if enhancement_result.get("log_path"):
                        logger.debug("Enhancement log path: {}", enhancement_result["log_path"])

                    if enhancement_result["status"] == "failed":
                        raise RuntimeError(
                            f"Prompt enhancement failed: {enhancement_result.get('error', 'Unknown error')}"
                        )

                    # Since it's now non-blocking, we need to wait for completion
                    # For now, we'll poll for the results file (Phase 2 will improve this)
                    remote_outputs_dir = f"{remote_config.remote_dir}/outputs/run_{run_id}"
                    remote_results_file = f"{remote_outputs_dir}/batch_results.json"
                    local_results_path = Path(temp_dir) / "results.json"

                    # Poll for results (max 120 seconds)
                    max_wait = 120
                    poll_interval = 5
                    elapsed = 0

                    logger.info("Waiting for prompt enhancement to complete...")
                    while elapsed < max_wait:
                        try:
                            # Check if results file exists
                            if self.file_transfer.file_exists_remote(remote_results_file):
                                # Download results
                                self.file_transfer.download_file(
                                    remote_results_file, str(local_results_path)
                                )
                                break
                        except Exception:
                            # File might not exist yet, continue polling
                            logger.debug("Results file not ready yet, continuing to poll...")

                        time.sleep(poll_interval)
                        elapsed += poll_interval

                    if elapsed >= max_wait:
                        logger.warning("Prompt enhancement timed out, returning original prompt")
                        return prompt_text

                    # Parse results
                    results = self.json_handler.read_json(local_results_path)

                    if results and len(results) > 0:
                        enhanced_text = results[0].get("upsampled_prompt", prompt_text)
                        logger.info("Successfully enhanced prompt")
                        return enhanced_text
                    else:
                        logger.warning("No results from upsampler, returning original prompt")
                        return prompt_text

            except Exception as e:
                logger.error("Prompt upsampling failed: {}", e)
                # Return original prompt on failure rather than raising
                return prompt_text

    def execute_upscaling_run(
        self,
        upscale_run: dict[str, Any],
        video_path: str,
        prompt_text: str | None = None,
    ) -> dict[str, Any]:
        """Execute upscaling as an independent database run.

        Args:
            upscale_run: The upscaling run with id and execution_config
            video_path: Path to the video file to upscale (local path)
            prompt_text: Optional prompt to guide the upscaling

        Returns:
            Dictionary with upscaled output and metadata
        """
        self._initialize_services()

        run_id = upscale_run["id"]
        execution_config = upscale_run["execution_config"]
        control_weight = execution_config["control_weight"]

        # Get source_run_id if this is from an existing run
        source_run_id = execution_config.get("source_run_id")

        # Create run directory
        run_dir = Path("outputs") / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = run_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        if source_run_id:
            logger.info("Executing upscaling run {} for parent run {}", run_id, source_run_id)
        else:
            logger.info("Executing upscaling run {} for video file {}", run_id, video_path)

        try:
            with self.ssh_manager:
                # Clean all old run directories before starting
                remote_config = self.config_manager.get_remote_config()
                logger.info("Cleaning up old run directories...")
                cleanup_cmd = f"rm -rf {remote_config.remote_dir}/outputs/run_* 2>/dev/null || true"
                self.remote_executor.execute_command(cleanup_cmd)

                # Upload bash scripts if not already present
                scripts_dir = Path(__file__).parent.parent.parent / "scripts"
                remote_scripts_dir = f"{remote_config.remote_dir}/bashscripts"

                # Upload upscale.sh script
                upscale_script = scripts_dir / "upscale.sh"
                if upscale_script.exists():
                    logger.info("Uploading upscale script to remote")
                    self.file_transfer.upload_file(upscale_script, remote_scripts_dir)
                else:
                    logger.warning("Upscale script not found at {}", upscale_script)

                # Determine the video source and ensure it's uploaded to remote
                local_video_path = Path(video_path)

                if source_run_id:
                    # Video is from a parent run - ensure it's uploaded to the expected location
                    remote_video_dir = f"{remote_config.remote_dir}/outputs/run_{source_run_id}"
                    remote_video_path = f"{remote_video_dir}/output.mp4"

                    # Check if video exists locally
                    if not local_video_path.exists():
                        raise FileNotFoundError(f"Video not found locally: {local_video_path}")

                    logger.info("Ensuring run output exists on remote for run {}", source_run_id)
                    self.remote_executor.execute_command(f"mkdir -p {remote_video_dir}")

                    # Upload the video to the expected parent run location
                    logger.info("Uploading run output video to remote")
                    self.file_transfer.upload_file(local_video_path, remote_video_dir)

                else:
                    # Video is a standalone file - upload to a staging area
                    remote_video_dir = f"{remote_config.remote_dir}/uploads/upscale_{run_id[:8]}"
                    remote_video_path = f"{remote_video_dir}/{local_video_path.name}"

                    # Check if video exists locally
                    if not local_video_path.exists():
                        raise FileNotFoundError(f"Video file not found: {local_video_path}")

                    logger.info("Uploading video file {} to remote", local_video_path.name)
                    self.remote_executor.execute_command(f"mkdir -p {remote_video_dir}")

                    # Upload the video file
                    self.file_transfer.upload_file(local_video_path, remote_video_dir)

                # Run upscaling synchronously with streaming output
                result = self.docker_executor.run_upscaling(
                    video_path=remote_video_path,
                    run_id=run_id,
                    control_weight=control_weight,
                    prompt=prompt_text,
                    stream_output=True,  # Enable streaming for CLI visibility
                )

                # Check the result status
                if result["status"] == "failed":
                    error_msg = result.get(
                        "error",
                        f"Upscaling failed with exit code {result.get('exit_code', 'unknown')}",
                    )
                    raise RuntimeError(error_msg)

                elif result["status"] == "completed":
                    # Upscaling completed successfully, download outputs immediately
                    logger.info("Upscaling completed for run {}, downloading outputs...", run_id)

                    try:
                        output_path = self._download_outputs(run_id, run_dir, upscaled=True)

                        # Build result data
                        result_data = {
                            "status": "completed",
                            "output_path": output_path.as_posix()
                            if isinstance(output_path, Path)
                            else str(output_path),
                            "message": "Upscaling completed successfully",
                            "run_id": run_id,
                            "log_path": (logs_dir / "upscaling.log").as_posix(),
                        }

                        # Add source_run_id if this was from an existing run
                        if source_run_id:
                            result_data["parent_run_id"] = source_run_id

                        return result_data

                    except Exception as download_error:
                        logger.error(
                            "Failed to download upscaled outputs for run {}: {}",
                            run_id,
                            download_error,
                        )
                        raise RuntimeError(
                            f"Upscaling completed but output download failed: {download_error}"
                        ) from download_error

                else:
                    # Unexpected status
                    raise RuntimeError(f"Unexpected upscaling status: {result.get('status')}")
        except Exception as e:
            logger.error("Upscaling run {} failed: {}", run_id, e)
            raise RuntimeError(f"Upscaling failed: {e}") from e

    # ========== Status and Container Management ==========

    def check_remote_status(self) -> dict[str, Any]:
        """Check remote GPU server status.

        Returns:
            Dictionary containing GPU status information including:
                - nvidia_smi output
                - running containers
                - available memory
                - GPU utilization
        """
        # Initialize services if not already done
        self._initialize_services()

        try:
            with self.ssh_manager:
                # Get NVIDIA SMI output
                nvidia_status = self.docker_executor.get_gpu_info()

                # Get Docker status
                docker_status = self.docker_executor.get_docker_status()

                # Get active container
                container = self.docker_executor.get_active_container()

                return {
                    "gpu_info": nvidia_status,
                    "docker_status": docker_status,
                    "container": container,
                    "ssh_status": "connected",
                }

        except Exception as e:
            logger.error("Failed to get GPU status: {}", e)
            return {
                "ssh_status": "error",
                "error": str(e),
            }

    def kill_container(self, container_id: str) -> bool:
        """Kill a specific Docker container on the GPU server.

        Args:
            container_id: The container ID or name to kill

        Returns:
            True if container was successfully killed, False otherwise
        """
        # Initialize services if not already done
        self._initialize_services()

        try:
            with self.ssh_manager:
                return self.docker_executor.kill_container(container_id)
        except Exception as e:
            logger.error("Failed to kill container {}: {}", container_id, e)
            return False

    def kill_all_containers(self) -> int:
        """Kill all running Docker containers on the GPU server.

        Returns:
            Number of containers killed
        """
        # Initialize services if not already done
        self._initialize_services()

        try:
            with self.ssh_manager:
                return self.docker_executor.kill_all_containers()
        except Exception as e:
            logger.error("Failed to kill all containers: {}", e)
            return 0
