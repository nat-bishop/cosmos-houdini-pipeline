"""GPU execution module for running NVIDIA Cosmos models on remote GPU servers.

This module handles all GPU-related operations including inference,
batch processing, and prompt upsampling using remote Docker containers.
"""

import json
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
from cosmos_workflow.utils.logging import logger


class GPUExecutor:
    """Execute GPU operations on remote servers.

    This class manages GPU execution for the NVIDIA Cosmos workflow,
    including model inference, batch processing, and prompt upsampling.
    It coordinates SSH connections, file transfers, and Docker containers
    on remote GPU nodes.
    """

    def __init__(self, config_manager: ConfigManager | None = None):
        """Initialize GPU executor.

        Args:
            config_manager: Configuration manager instance. If None, creates default.
        """
        self.config_manager = config_manager or ConfigManager()
        self.ssh_manager = None
        self.file_transfer = None
        self.remote_executor = None
        self.docker_executor = None
        self._services_initialized = False

    def _initialize_services(self):
        """Initialize all required services for GPU execution.

        This method lazily initializes services on first use to avoid
        creating connections when not needed.
        """
        if self._services_initialized:
            return

        # Initialize SSH and related services
        self.ssh_manager = SSHManager(self.config_manager)
        self.file_transfer = FileTransferService(self.ssh_manager, self.config_manager)
        self.remote_executor = RemoteCommandExecutor(self.ssh_manager)
        self.docker_executor = DockerExecutor(
            self.remote_executor, self.config_manager, self.file_transfer
        )

        self._services_initialized = True

    # ========== Single Run Execution ==========

    def execute_run(
        self,
        run: dict[str, Any],
        prompt: dict[str, Any],
        upscale: bool = False,
        upscale_weight: float = 0.5,
    ) -> dict[str, Any]:
        """Execute a single run on the GPU.

        Args:
            run: Run dictionary containing id, execution_config, etc.
            prompt: Prompt dictionary containing prompt_text, inputs, etc.
            upscale: Whether to run 4K upscaling after inference
            upscale_weight: Control weight for upscaling (0-1)

        Returns:
            Dictionary containing execution results with output_path, duration, etc.

        Raises:
            RuntimeError: If GPU execution fails
        """
        # Initialize services if not already done
        self._initialize_services()

        run_id = run["id"]
        prompt_text = prompt["prompt_text"]
        execution_config = run["execution_config"]

        logger.info("Executing run %s on GPU", run_id)

        # Create local run directory
        run_dir = Path("outputs") / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # Prepare inputs for GPU execution
        inputs_dir = run_dir / "inputs"
        inputs_dir.mkdir(exist_ok=True)

        # Create batch file for this single run
        batch_data = [
            {
                "name": run_id,
                "prompt": prompt_text,
                "negative_prompt": prompt.get("parameters", {}).get("negative_prompt", ""),
                "weights": execution_config.get("weights", {}),
                "video_path": prompt.get("inputs", {}).get("video", ""),
            }
        ]

        batch_file = inputs_dir / "batch.json"
        with open(batch_file, "w") as f:
            json.dump(batch_data, f, indent=2)

        # Execute on GPU using DockerExecutor
        try:
            with self.ssh_manager:
                # Upload batch and any video files
                remote_config = self.config_manager.get_remote_config()
                remote_run_dir = f"{remote_config.remote_dir}/runs/{run_id}"

                # Upload batch file
                self.file_transfer.upload_file(batch_file, f"{remote_run_dir}/inputs")

                # Upload video if present
                video_path = prompt.get("inputs", {}).get("video")
                if video_path and Path(video_path).exists():
                    self.file_transfer.upload_file(
                        Path(video_path), f"{remote_run_dir}/inputs/videos"
                    )

                # Run inference
                inference_result = self.docker_executor.run_inference(
                    batch_filename=batch_file.name,
                    run_id=run_id,
                    execution_config=execution_config,
                )

                if inference_result["status"] == "failed":
                    raise RuntimeError(
                        f"Inference failed: {inference_result.get('error', 'Unknown error')}"
                    )

                # Handle upscaling if requested
                if upscale:
                    logger.info("Running 4K upscaling for run %s", run_id)
                    upscale_result = self.docker_executor.run_upscaling(
                        run_id=run_id,
                        control_weight=upscale_weight,
                    )

                    if upscale_result["status"] == "failed":
                        logger.warning("Upscaling failed: %s", upscale_result.get("error"))
                        # Continue with regular output even if upscale fails

                # Download outputs
                output_path = self._download_outputs(run_id, run_dir, upscale)

                return {
                    "output_path": str(output_path),
                    "duration_seconds": inference_result.get("duration_seconds", 0),
                    "remote_output": inference_result.get("remote_output"),
                    "log_path": str(run_dir / "logs" / "inference.log"),
                }

        except Exception as e:
            logger.error("GPU execution failed for run %s: %s", run_id, e)
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
            upscaled: Whether to download upscaled version

        Returns:
            Path to the downloaded output file
        """
        remote_config = self.config_manager.get_remote_config()
        outputs_dir = local_run_dir / "outputs"
        outputs_dir.mkdir(exist_ok=True)

        # Determine which file to download
        if upscaled:
            remote_file = f"{remote_config.remote_dir}/outputs/{run_id}_upscaled/output_4k.mp4"
            local_file = outputs_dir / "output_4k.mp4"
        else:
            remote_file = f"{remote_config.remote_dir}/outputs/{run_id}/output.mp4"
            local_file = outputs_dir / "output.mp4"

        # Download the file
        try:
            self.file_transfer.download_file(remote_file, str(local_file))
            logger.info("Downloaded output to %s", local_file)
            return local_file
        except Exception as e:
            logger.error("Failed to download output: %s", e)
            # Return path even if download failed (for status tracking)
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

        logger.info("Executing batch of %d runs on GPU", len(runs_and_prompts))

        # Generate batch name from first run ID
        batch_name = f"batch_{runs_and_prompts[0][0]['id'][:8]}_{len(runs_and_prompts)}"
        batch_dir = Path("outputs") / batch_name
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Prepare batch data
        batch_data = []
        for run_dict, prompt_dict in runs_and_prompts:
            batch_data.append(
                {
                    "name": run_dict["id"],
                    "prompt": prompt_dict["prompt_text"],
                    "negative_prompt": prompt_dict.get("parameters", {}).get("negative_prompt", ""),
                    "weights": run_dict["execution_config"].get("weights", {}),
                    "video_path": prompt_dict.get("inputs", {}).get("video", ""),
                }
            )

        # Create batch file
        batch_file = batch_dir / "batch.json"
        with open(batch_file, "w") as f:
            json.dump(batch_data, f, indent=2)

        # Execute batch on GPU
        try:
            with self.ssh_manager:
                # Upload batch file and videos
                remote_config = self.config_manager.get_remote_config()
                remote_batch_dir = f"{remote_config.remote_dir}/batches/{batch_name}"

                self.file_transfer.upload_file(batch_file, f"{remote_batch_dir}/inputs")

                # Upload any videos
                for _, prompt_dict in runs_and_prompts:
                    video_path = prompt_dict.get("inputs", {}).get("video")
                    if video_path and Path(video_path).exists():
                        self.file_transfer.upload_file(
                            Path(video_path), f"{remote_batch_dir}/inputs/videos"
                        )

                # Run batch inference using first run's execution config
                execution_config = runs_and_prompts[0][0]["execution_config"]
                batch_result = self.docker_executor.run_batch_inference(
                    batch_filename=batch_file.name,
                    batch_name=batch_name,
                    execution_config=execution_config,
                )

                if batch_result["status"] == "failed":
                    raise RuntimeError(f"Batch execution failed: {batch_result.get('error')}")

                # Split outputs to individual run directories
                output_mapping = self._split_batch_outputs(runs_and_prompts, batch_result)

                # Download outputs for each run
                for run_dict, _ in runs_and_prompts:
                    run_id = run_dict["id"]
                    if run_id in output_mapping and output_mapping[run_id]["status"] == "found":
                        run_dir = Path("outputs") / f"run_{run_id}"
                        run_dir.mkdir(parents=True, exist_ok=True)
                        # Download this run's output
                        self._download_outputs(run_id, run_dir)

                return {
                    "status": "success",
                    "batch_name": batch_name,
                    "output_mapping": output_mapping,
                    "duration_seconds": batch_result.get("duration_seconds", 0),
                }

        except Exception as e:
            logger.error("Batch execution failed: %s", e)
            return {
                "status": "failed",
                "batch_name": batch_name,
                "error": str(e),
                "started_at": datetime.now(timezone.utc).isoformat(),
            }

    @staticmethod
    def _split_batch_outputs(
        runs_and_prompts: list[tuple[dict[str, Any], dict[str, Any]]],
        batch_result: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        """Split batch output files to individual run folders.

        Args:
            runs_and_prompts: Original run/prompt pairs
            batch_result: Result from batch inference

        Returns:
            Mapping of run_id to output file info
        """
        output_mapping = {}
        output_files = batch_result.get("output_files", [])
        used_files = set()  # Track which files have been matched

        # Match output files to runs
        # NVIDIA batch inference typically names outputs with indices or prompt IDs
        for i, (run_dict, _) in enumerate(runs_and_prompts):
            run_id = run_dict["id"]

            # Try to find matching output file
            # Look for files with index or run_id in name
            matched_file = None
            for output_file in output_files:
                if output_file in used_files:
                    continue  # Skip already matched files

                file_name = Path(output_file).name
                # Check if file contains run_id or index
                if run_id in file_name or f"_{i:03d}_" in file_name or f"_{i}_" in file_name:
                    matched_file = output_file
                    used_files.add(output_file)
                    break

            if matched_file:
                output_mapping[run_id] = {
                    "remote_path": matched_file,
                    "batch_index": i,
                    "status": "found",
                }
            else:
                # If no match found, try sequential matching with unused files
                available_files = [f for f in output_files if f not in used_files]
                if available_files:
                    matched_file = available_files[0]
                    used_files.add(matched_file)
                    output_mapping[run_id] = {
                        "remote_path": matched_file,
                        "batch_index": i,
                        "status": "assumed",
                    }
                else:
                    output_mapping[run_id] = {
                        "remote_path": None,
                        "batch_index": i,
                        "status": "missing",
                    }

        return output_mapping

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
            Dictionary containing:
                - enhanced_text: The enhanced prompt text
                - original_prompt_id: The source prompt ID
                - duration_seconds: Execution time
                - log_path: Path to enhancement log

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

        logger.info("Executing enhancement run %s with model %s", run_id, model)

        # Create run directory structure
        run_dir = Path("outputs") / f"run_{run_id}"
        run_dir.mkdir(parents=True, exist_ok=True)
        logs_dir = run_dir / "logs"
        logs_dir.mkdir(exist_ok=True)

        # Use the internal method with run_id
        start_time = time.time()
        try:
            enhanced_text = self._run_prompt_upsampling_internal(
                run_id=run_id,
                prompt_text=prompt_text,
                model=model,
                video_path=video_path,
            )

            # Calculate actual duration
            duration_seconds = time.time() - start_time

            # Store results in run directory
            results_file = run_dir / "enhancement_results.json"
            results = {
                "enhanced_text": enhanced_text,
                "original_prompt_id": prompt["id"],
                "model": model,
                "duration_seconds": duration_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            with open(results_file, "w") as f:
                json.dump(results, f, indent=2)

            # Return in format expected by database
            return {
                "enhanced_text": enhanced_text,
                "original_prompt_id": prompt["id"],
                "duration_seconds": duration_seconds,
                "log_path": str(logs_dir / "enhancement.log"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error("Enhancement run %s failed: %s", run_id, e)
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

        logger.info("Starting prompt upsampling for run %s using %s model", run_id, model)

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
            with open(local_batch_path, "w") as f:
                json.dump(batch_data, f, indent=2)

            try:
                with self.ssh_manager:
                    remote_config = self.config_manager.get_remote_config()

                    # Upload batch file - upload_file will create directory automatically
                    remote_inputs_dir = f"{remote_config.remote_dir}/inputs"
                    self.file_transfer.upload_file(local_batch_path, remote_inputs_dir)

                    # Upload video if provided
                    if video_path and Path(video_path).exists():
                        remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                        # upload_file will create the directory automatically
                        logger.info("Uploading video for context: %s", video_path)
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
                        logger.debug("Enhancement log path: %s", enhancement_result["log_path"])

                    if enhancement_result["status"] == "failed":
                        raise RuntimeError(
                            f"Prompt enhancement failed: {enhancement_result.get('error', 'Unknown error')}"
                        )

                    # Since it's now non-blocking, we need to wait for completion
                    # For now, we'll poll for the results file (Phase 2 will improve this)
                    remote_outputs_dir = f"{remote_config.remote_dir}/outputs"
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
                    with open(local_results_path) as f:
                        results = json.load(f)

                    if results and len(results) > 0:
                        enhanced_text = results[0].get("upsampled_prompt", prompt_text)
                        logger.info("Successfully enhanced prompt")
                        return enhanced_text
                    else:
                        logger.warning("No results from upsampler, returning original prompt")
                        return prompt_text

            except Exception as e:
                logger.error("Prompt upsampling failed: %s", e)
                # Return original prompt on failure rather than raising
                return prompt_text

    # ========== Status and Container Management ==========

    def get_gpu_status(self) -> dict[str, Any]:
        """Get current GPU server status.

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
                nvidia_status = self.docker_executor.get_gpu_status()

                # Get running containers
                containers = self.docker_executor.get_containers()

                return {
                    "gpu_info": nvidia_status,
                    "containers": containers,
                    "status": "connected",
                }

        except Exception as e:
            logger.error("Failed to get GPU status: %s", e)
            return {
                "status": "error",
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
            logger.error("Failed to kill container %s: %s", container_id, e)
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
            logger.error("Failed to kill all containers: %s", e)
            return 0
