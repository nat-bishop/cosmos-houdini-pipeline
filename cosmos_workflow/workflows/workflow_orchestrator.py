#!/usr/bin/env python3
"""Workflow orchestrator for Cosmos-Transfer1.
Handles GPU execution for inference and upscaling workflows.
"""

import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.command_builder import DockerCommandBuilder
from cosmos_workflow.execution.docker_executor import DockerExecutor
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.utils import nvidia_format

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates complete Cosmos-Transfer1 workflows."""

    def __init__(self, config_file: str = "cosmos_workflow/config/config.toml"):
        self.config_manager = ConfigManager(config_file)
        self.ssh_manager: SSHManager | None = None
        self.file_transfer: FileTransferService | None = None
        self.docker_executor: DockerExecutor | None = None

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
                    for input_type, input_path in inputs.items():
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

                # Run inference
                logger.info("Running inference on GPU for run %s", run_dict["id"])
                self.docker_executor.run_inference(prompt_file, num_gpu=1, cuda_devices="0")

                # Run upscaling if requested
                if upscale:
                    logger.info("Running upscaling with weight %s", upscale_weight)
                    self.docker_executor.run_upscaling(
                        prompt_file, upscale_weight, num_gpu=1, cuda_devices="0"
                    )

                # Download results
                self.file_transfer.download_results(prompt_file)

                end_time = datetime.now(timezone.utc)
                duration = end_time - start_time

                # Return execution results
                output_path = f"outputs/{prompt_name}/result.mp4"
                if upscale:
                    output_path = f"outputs/{prompt_name}/result_upscaled.mp4"

                return {
                    "status": "success",
                    "output_path": output_path,
                    "upscaled": upscale,
                    "upscale_weight": upscale_weight if upscale else None,
                    "duration_seconds": duration.total_seconds(),
                    "started_at": start_time.isoformat(),
                    "completed_at": end_time.isoformat(),
                }

        except Exception as e:
            logger.error("Execution failed for run %s: %s", run_dict["id"], e)
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

                # Check remote directory
                remote_config = self.config_manager.get_remote_config()
                remote_dir_exists = self.file_transfer.file_exists_remote(remote_config.remote_dir)

                return {
                    "ssh_status": ssh_status,
                    "docker_status": docker_status,
                    "remote_directory_exists": remote_dir_exists,
                    "remote_directory": remote_config.remote_dir,
                }

        except Exception as e:
            return {"ssh_status": "failed", "error": str(e)}

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
        batch_filename = f"upsample_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

        # Use temporary directory for batch file
        with tempfile.TemporaryDirectory() as temp_dir:
            local_batch_path = Path(temp_dir) / batch_filename
            with open(local_batch_path, "w") as f:
                json.dump(batch_data, f, indent=2)

            try:
                with self.ssh_manager:
                    remote_config = self.config_manager.get_remote_config()

                    # Upload batch file
                    remote_inputs_dir = f"{remote_config.remote_dir}/inputs"
                    self.ssh_manager.execute_command_success(f"mkdir -p {remote_inputs_dir}")
                    self.file_transfer.upload_file(local_batch_path, remote_inputs_dir)

                    # Upload video if provided
                    if video_path and Path(video_path).exists():
                        remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                        self.ssh_manager.execute_command_success(f"mkdir -p {remote_videos_dir}")
                        logger.info("Uploading video for context: %s", video_path)
                        self.file_transfer.upload_file(Path(video_path), remote_videos_dir)

                    # Upload upsampler script
                    scripts_dir = f"{remote_config.remote_dir}/scripts"
                    self.ssh_manager.execute_command_success(f"mkdir -p {scripts_dir}")

                    local_script = (
                        Path(__file__).parent.parent.parent / "scripts" / "prompt_upsampler.py"
                    )
                    if not local_script.exists():
                        raise FileNotFoundError(f"Upsampler script not found at {local_script}")

                    self.file_transfer.upload_file(local_script, scripts_dir)

                    # Create output directory
                    remote_outputs_dir = f"{remote_config.remote_dir}/outputs"
                    self.ssh_manager.execute_command_success(f"mkdir -p {remote_outputs_dir}")

                    # Build Docker command
                    builder = DockerCommandBuilder(remote_config.docker_image)
                    builder.with_gpu("0")
                    builder.add_option("--ipc=host")
                    builder.add_option("--shm-size=8g")
                    builder.add_volume(remote_config.remote_dir, "/workspace")
                    builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")
                    builder.add_environment("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
                    builder.add_environment("CUDA_VISIBLE_DEVICES", "0")

                    # Run upsampler
                    upsample_cmd = (
                        f"python /workspace/scripts/prompt_upsampler.py "
                        f"--batch /workspace/inputs/{batch_filename} "
                        f"--output-dir /workspace/outputs "
                        f"--checkpoint-dir /workspace/checkpoints"
                    )
                    builder.set_command(upsample_cmd)

                    # Execute on GPU
                    logger.info("Executing prompt upsampling on GPU...")
                    full_cmd = f"sudo {builder.build()}"
                    self.ssh_manager.execute_command_success(
                        full_cmd, timeout=600
                    )  # 10 min timeout

                    # Download results
                    remote_results_file = f"{remote_outputs_dir}/batch_results.json"
                    local_results_path = Path(temp_dir) / "results.json"

                    self.file_transfer.download_file(remote_results_file, str(local_results_path))

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
