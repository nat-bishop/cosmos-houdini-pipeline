#!/usr/bin/env python3
"""GPU execution orchestrator for Cosmos-Transfer1.

THIS IS NOT THE MAIN FACADE - This is an internal component that handles
GPU-specific execution tasks (inference, upscaling, enhancement).

For the main interface, use CosmosAPI from cosmos_workflow.api

This component:
- Manages SSH connections to GPU instances
- Executes Docker containers on remote GPUs
- Handles file transfers to/from remote systems
- NO direct database access (takes dictionaries as input)

Used internally by CosmosAPI facade.
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.docker_executor import DockerExecutor
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.utils import nvidia_format
from cosmos_workflow.utils.logging import logger


class GPUExecutor:
    """GPU execution component for Cosmos-Transfer1 workflows.

    NOT THE MAIN FACADE - This is an internal execution component.
    Use CosmosAPI from cosmos_workflow.api as the main interface.

    This class handles GPU-specific operations only:
    - SSH connections and remote command execution
    - Docker container management on GPU instances
    - File transfers (uploads/downloads)
    - NVIDIA format conversions for GPU scripts

    Does NOT handle:
    - Database operations (use DataRepository)
    - High-level workflow orchestration (use CosmosAPI)
    """

    def __init__(self, config_file: str | None = None, service=None):
        self.config_manager = ConfigManager(config_file)
        self.ssh_manager: SSHManager | None = None
        self.file_transfer: FileTransferService | None = None
        self.docker_executor: DockerExecutor | None = None
        self.service = service  # Optional DataRepository for database updates

    def _initialize_services(self):
        """Initialize all workflow services."""
        if not self.ssh_manager:
            remote_config = self.config_manager.get_remote_config()
            ssh_options = self.config_manager.get_ssh_options()

            self.ssh_manager = SSHManager(ssh_options)
            self.file_transfer = FileTransferService(self.ssh_manager, remote_config.remote_dir)
            self.docker_executor = DockerExecutor(
                self.ssh_manager, remote_config.remote_dir, remote_config.docker_image
            )

    def execute_run(
        self,
        run_dict: dict[str, Any],
        prompt_dict: dict[str, Any],
        upscale: bool = False,
        upscale_weight: float = 0.5,
    ) -> dict[str, Any]:
        """Execute a run on GPU infrastructure.

        This method handles ONLY GPU execution - no data persistence.
        It receives run and prompt data as dictionaries and executes the workflow.

        Args:
            run_dict: Run data from database
            prompt_dict: Prompt data from database
            upscale: Whether to run upscaling
            upscale_weight: Weight for upscaling (0.0-1.0)

        Returns:
            Dictionary with execution results including output paths
        """
        self._initialize_services()

        start_time = datetime.now(timezone.utc)
        prompt_name = f"run_{run_dict['id']}"
        run_id = run_dict["id"]

        logger.info("Executing run %s for prompt %s", run_id, prompt_name)

        try:
            with self.ssh_manager:
                # Convert to NVIDIA Cosmos format
                if upscale:
                    cosmos_json = nvidia_format.to_cosmos_upscale_json(
                        prompt_dict, run_dict, upscale_weight
                    )
                else:
                    cosmos_json = nvidia_format.to_cosmos_inference_json(prompt_dict, run_dict)

                # Write to temporary file
                with tempfile.TemporaryDirectory() as temp_dir:
                    temp_path = Path(temp_dir) / f"{prompt_name}.json"
                    nvidia_format.write_cosmos_json(cosmos_json, temp_path)

                    # Upload prompt JSON
                    remote_config = self.config_manager.get_remote_config()
                    remote_prompts_dir = f"{remote_config.remote_dir}/inputs/prompts"
                    self.ssh_manager.execute_command_success(f"mkdir -p {remote_prompts_dir}")
                    self.file_transfer.upload_file(temp_path, remote_prompts_dir)

                    # Upload video files if they exist
                    inputs = prompt_dict.get("inputs", {})
                    for _input_type, input_path in inputs.items():
                        if input_path and Path(input_path).exists():
                            remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                            self.ssh_manager.execute_command_success(
                                f"mkdir -p {remote_videos_dir}"
                            )
                            self.file_transfer.upload_file(Path(input_path), remote_videos_dir)

                # Upload scripts if they exist
                scripts_dir = Path("scripts")
                if scripts_dir.exists():
                    remote_scripts_dir = f"{remote_config.remote_dir}/bashscripts"
                    self.ssh_manager.execute_command_success(f"mkdir -p {remote_scripts_dir}")
                    for script in scripts_dir.glob("*.sh"):
                        self.file_transfer.upload_file(script, remote_scripts_dir)
                    # Make scripts executable
                    self.ssh_manager.execute_command_success(
                        f"chmod +x {remote_scripts_dir}/*.sh || true"
                    )

                # Build prompt file path for scripts
                prompt_file = Path(f"inputs/prompts/{prompt_name}.json")

                # Run inference - always pass run_id for logging
                logger.info("Running inference on GPU for run %s", run_dict["id"])
                result = self.docker_executor.run_inference(
                    prompt_file, run_id=run_id, num_gpu=1, cuda_devices="0"
                )

                # Store log path if available
                if result.get("log_path") and self.service:
                    self.service.update_run(run_id, log_path=result["log_path"])
                    logger.debug("Log path for run %s: %s", run_id, result["log_path"])

                # Run upscaling if requested
                if upscale:
                    logger.info("Running upscaling with weight %s", upscale_weight)
                    upscale_result = self.docker_executor.run_upscaling(
                        prompt_file,
                        run_id=run_id,
                        control_weight=upscale_weight,
                        num_gpu=1,
                        cuda_devices="0",
                    )
                    if upscale_result.get("log_path"):
                        if self.service:
                            self.service.update_run(run_id, log_path=upscale_result["log_path"])
                        logger.debug(
                            f"Upscaling log path for run {run_id}: {upscale_result['log_path']}"
                        )

                # Download results
                self.file_transfer.download_results(prompt_file)

                end_time = datetime.now(timezone.utc)
                duration = end_time - start_time

                # Return execution results
                output_path = f"outputs/{prompt_name}/output.mp4"
                if upscale:
                    output_path = f"outputs/{prompt_name}/output_upscaled.mp4"

                return {
                    "status": "success",
                    "type": "video_generation",  # Operation type for filtering
                    "output_dir": f"outputs/{prompt_name}/",  # Directory containing all outputs
                    "primary_output": "output.mp4"
                    if not upscale
                    else "output_upscaled.mp4",  # Just filename
                    "output_path": output_path,  # Full path for compatibility
                    "upscaled": upscale,
                    "upscale_weight": upscale_weight if upscale else None,
                    "duration_seconds": duration.total_seconds(),
                    "started_at": start_time.isoformat(),
                    "completed_at": end_time.isoformat(),
                }

        except Exception as e:
            logger.error("Execution failed for run %s: %s", run_dict["id"], e)
            if self.service:
                self.service.update_run(run_dict["id"], error_message=str(e))
            return {
                "status": "failed",
                "error": str(e),
                "started_at": start_time.isoformat(),
            }

    def check_remote_status(self) -> dict[str, Any]:
        """Check remote instance and Docker status."""
        self._initialize_services()

        try:
            with self.ssh_manager:
                # Check SSH connection
                ssh_status = "connected"

                # Check Docker status
                docker_status = self.docker_executor.get_docker_status()

                # Get GPU information
                gpu_info = self.docker_executor.get_gpu_info()

                # Get active container
                container = self.docker_executor.get_active_container()

                # Check remote directory
                remote_config = self.config_manager.get_remote_config()
                remote_dir_exists = self.file_transfer.file_exists_remote(remote_config.remote_dir)

                return {
                    "ssh_status": ssh_status,
                    "docker_status": docker_status,
                    "gpu_info": gpu_info,
                    "container": container,
                    "remote_directory_exists": remote_dir_exists,
                    "remote_directory": remote_config.remote_dir,
                }

        except Exception as e:
            return {"ssh_status": "failed", "error": str(e)}

    def execute_batch_runs(
        self,
        runs_and_prompts: list[tuple[dict[str, Any], dict[str, Any]]],
        batch_name: str | None = None,
    ) -> dict[str, Any]:
        """Execute multiple runs as a batch on GPU infrastructure.

        Args:
            runs_and_prompts: List of (run_dict, prompt_dict) tuples
            batch_name: Optional batch name, generated if not provided

        Returns:
            Dictionary with batch execution results
        """
        self._initialize_services()

        if not batch_name:
            batch_name = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        start_time = datetime.now(timezone.utc)
        logger.info("Starting batch execution %s with %d runs", batch_name, len(runs_and_prompts))

        try:
            with self.ssh_manager:
                # Convert runs to JSONL format
                batch_data = nvidia_format.to_cosmos_batch_inference_jsonl(runs_and_prompts)

                # Write to temporary JSONL file
                with tempfile.TemporaryDirectory() as temp_dir:
                    jsonl_filename = f"{batch_name}.jsonl"
                    temp_jsonl_path = Path(temp_dir) / jsonl_filename

                    # Write JSONL file
                    nvidia_format.write_batch_jsonl(batch_data, temp_jsonl_path)

                    # Upload JSONL to remote
                    remote_config = self.config_manager.get_remote_config()
                    remote_batch_dir = f"{remote_config.remote_dir}/inputs/batches"
                    self.ssh_manager.execute_command_success(f"mkdir -p {remote_batch_dir}")
                    self.file_transfer.upload_file(temp_jsonl_path, remote_batch_dir)

                    # Upload all referenced video files
                    for _run_dict, prompt_dict in runs_and_prompts:
                        inputs = prompt_dict.get("inputs", {})
                        for _input_type, input_path in inputs.items():
                            if input_path and Path(input_path).exists():
                                remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                                self.ssh_manager.execute_command_success(
                                    f"mkdir -p {remote_videos_dir}"
                                )
                                self.file_transfer.upload_file(Path(input_path), remote_videos_dir)

                # Upload batch_inference.sh script if it exists
                batch_script = Path("scripts/batch_inference.sh")
                if batch_script.exists():
                    remote_scripts_dir = f"{remote_config.remote_dir}/scripts"
                    self.ssh_manager.execute_command_success(f"mkdir -p {remote_scripts_dir}")
                    self.file_transfer.upload_file(batch_script, remote_scripts_dir)
                    # Make script executable
                    self.ssh_manager.execute_command_success(
                        f"chmod +x {remote_scripts_dir}/batch_inference.sh"
                    )

                # Run batch inference
                logger.info("Running batch inference on GPU for %s", batch_name)
                batch_result = self.docker_executor.run_batch_inference(
                    batch_name, jsonl_filename, num_gpu=1, cuda_devices="0"
                )

                # Split outputs to individual run folders
                output_mapping = self._split_batch_outputs(runs_and_prompts, batch_result)

                # Download all outputs
                for run_id, output_info in output_mapping.items():
                    remote_file = output_info["remote_path"]
                    local_dir = Path(f"outputs/run_{run_id}")
                    local_dir.mkdir(parents=True, exist_ok=True)
                    local_file = local_dir / "output.mp4"

                    self.file_transfer.download_file(remote_file, str(local_file))
                    output_info["local_path"] = str(local_file)

                end_time = datetime.now(timezone.utc)
                duration = end_time - start_time

                return {
                    "status": "success",
                    "batch_name": batch_name,
                    "num_runs": len(runs_and_prompts),
                    "output_mapping": output_mapping,
                    "duration_seconds": duration.total_seconds(),
                    "started_at": start_time.isoformat(),
                    "completed_at": end_time.isoformat(),
                }

        except Exception as e:
            logger.error("Batch execution failed: %s", e)
            return {
                "status": "failed",
                "batch_name": batch_name,
                "error": str(e),
                "started_at": start_time.isoformat(),
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

    def run_prompt_upsampling(
        self,
        prompt_text: str,
        model: str = "pixtral",
        video_path: str | None = None,
    ) -> str:
        """Run prompt upsampling on remote GPU using Pixtral model.

        This method handles GPU-based prompt enhancement using the NVIDIA Cosmos
        Pixtral model which takes both text and optional video context.

        Args:
            prompt_text: The prompt text to enhance
            model: Model to use (currently only "pixtral" supported)
            video_path: Optional path to video for visual context

        Returns:
            Enhanced prompt text string
        """

        # Initialize services if not already done
        self._initialize_services()

        logger.info("Starting prompt upsampling using %s model", model)

        # Prepare batch data for the upsampler script
        batch_data = [
            {
                "name": "prompt",
                "prompt": prompt_text,
                "video_path": video_path or "",
            }
        ]

        # Create temporary batch file
        from datetime import datetime, timezone

        batch_filename = f"upsample_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

        # Use temporary directory for batch file
        with tempfile.TemporaryDirectory() as temp_dir:
            local_batch_path = Path(temp_dir) / batch_filename
            with open(local_batch_path, "w") as f:
                json.dump(batch_data, f, indent=2)

            try:
                with self.ssh_manager:
                    remote_config = self.config_manager.get_remote_config()

                    # Create directories using wrapper's remote executor
                    remote_inputs_dir = f"{remote_config.remote_dir}/inputs"
                    self.docker_executor.remote_executor.create_directory(remote_inputs_dir)

                    # Upload batch file
                    self.file_transfer.upload_file(local_batch_path, remote_inputs_dir)

                    # Upload video if provided
                    if video_path and Path(video_path).exists():
                        remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                        self.docker_executor.remote_executor.create_directory(remote_videos_dir)
                        logger.info("Uploading video for context: %s", video_path)
                        self.file_transfer.upload_file(Path(video_path), remote_videos_dir)

                    # Create scripts directory and upload upsampler script
                    scripts_dir = f"{remote_config.remote_dir}/scripts"
                    self.docker_executor.remote_executor.create_directory(scripts_dir)

                    local_script = (
                        Path(__file__).parent.parent.parent / "scripts" / "prompt_upsampler.py"
                    )
                    if not local_script.exists():
                        raise FileNotFoundError(f"Upsampler script not found at {local_script}")

                    self.file_transfer.upload_file(local_script, scripts_dir)

                    # Execute prompt enhancement via DockerExecutor wrapper
                    logger.info("Executing prompt upsampling on GPU...")
                    import uuid
                    from datetime import datetime

                    # Generate a temporary run_id for now (Phase 2 will create proper database runs)
                    temp_run_id = f"enhance_{uuid.uuid4().hex[:8]}"

                    enhancement_result = self.docker_executor.run_prompt_enhancement(
                        batch_filename=batch_filename,
                        run_id=temp_run_id,  # Changed from operation_id to run_id
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
                    import time

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
