#!/usr/bin/env python3
"""
Workflow orchestrator for Cosmos-Transfer1.
Coordinates all services to run complete workflows with proper error handling and logging.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.docker_executor import DockerExecutor
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.workflows.upsample_integration import UpsampleWorkflowMixin

logger = logging.getLogger(__name__)


class WorkflowOrchestrator(UpsampleWorkflowMixin):
    """Orchestrates complete Cosmos-Transfer1 workflows."""

    def __init__(self, config_file: str = "cosmos_workflow/config/config.toml"):
        self.config_manager = ConfigManager(config_file)
        self.ssh_manager: Optional[SSHManager] = None
        self.file_transfer: Optional[FileTransferService] = None
        self.docker_executor: Optional[DockerExecutor] = None

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

    def run(
        self,
        prompt_file: Path,
        videos_subdir: Optional[str] = None,
        inference: bool = True,
        upscale: bool = False,
        upload: bool = True,
        download: bool = True,
        upscale_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> Dict[str, Any]:
        """
        Run workflow with configurable steps.

        Args:
            prompt_file: Path to prompt JSON file
            videos_subdir: Optional override for video directory
            inference: Run inference step
            upscale: Run upscaling step
            upload: Upload files before processing
            download: Download results after processing
            upscale_weight: Control weight for upscaling
            num_gpu: Number of GPUs to use
            cuda_devices: CUDA device IDs to use

        Returns:
            Workflow execution results
        """
        self._initialize_services()

        start_time = datetime.now()
        prompt_name = prompt_file.stem

        # Determine workflow type for logging
        workflow_type = self._get_workflow_type(inference, upscale, upload, download)

        logger.info(f"Starting {workflow_type} workflow for {prompt_name}")
        print(f"[INFO] Starting {workflow_type} workflow for {prompt_name}")

        try:
            with self.ssh_manager:
                steps_performed = []

                # Step 1: Upload files (if needed)
                if upload:
                    print("\n[UPLOAD] Uploading prompt and videos...")
                    video_dirs = self._get_video_directories(prompt_file, videos_subdir)
                    self.file_transfer.upload_prompt_and_videos(prompt_file, video_dirs)
                    steps_performed.append("upload")

                # Step 2: Run inference (if needed)
                if inference:
                    print(f"\n[INFERENCE] Running inference with {num_gpu} GPU(s)...")
                    self.docker_executor.run_inference(prompt_file, num_gpu, cuda_devices)
                    steps_performed.append("inference")

                # Step 3: Run upscaling (if needed)
                if upscale:
                    print(f"\n[UPSCALE] Running 4K upscaling with weight {upscale_weight}...")
                    self.docker_executor.run_upscaling(
                        prompt_file, upscale_weight, num_gpu, cuda_devices
                    )
                    steps_performed.append("upscale")

                # Step 4: Download results (if needed)
                if download:
                    print("\n[DOWNLOAD] Downloading results...")
                    self.file_transfer.download_results(prompt_file)
                    steps_performed.append("download")

                # Log workflow completion
                if inference or upscale:
                    self._log_workflow_completion(prompt_file, upscale, upscale_weight, num_gpu)

                end_time = datetime.now()
                duration = end_time - start_time

                print(f"\n[SUCCESS] {workflow_type} workflow completed successfully!")
                print(f"[TIME] Total duration: {duration}")

                return {
                    "status": "success",
                    "prompt_name": prompt_name,
                    "workflow_type": workflow_type,
                    "steps_performed": steps_performed,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration.total_seconds(),
                    "upscaled": upscale,
                    "upscale_weight": upscale_weight if upscale else None,
                    "num_gpu": num_gpu,
                    "cuda_devices": cuda_devices,
                }

        except Exception as e:
            end_time = datetime.now()
            duration = end_time - start_time

            logger.error(f"Workflow failed: {e}")
            print(f"\n[ERROR] Workflow failed: {e}")

            # Log failed workflow
            self._log_workflow_failure(prompt_file, str(e), duration)

            raise RuntimeError(f"Workflow failed: {e}") from e

    def run_full_cycle(
        self,
        prompt_file: Path,
        videos_subdir: Optional[str] = None,
        no_upscale: bool = False,
        upscale_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> Dict[str, Any]:
        """
        Run complete workflow: upload → inference → upscaling → download.
        Legacy method for backward compatibility.
        """
        return self.run(
            prompt_file=prompt_file,
            videos_subdir=videos_subdir,
            inference=True,
            upscale=not no_upscale,
            upload=True,
            download=True,
            upscale_weight=upscale_weight,
            num_gpu=num_gpu,
            cuda_devices=cuda_devices,
        )

    def run_inference_only(
        self,
        prompt_file: Path,
        videos_subdir: Optional[str] = None,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> Dict[str, Any]:
        """
        Run only inference without upscaling.
        Legacy method for backward compatibility.
        """
        return self.run(
            prompt_file=prompt_file,
            videos_subdir=videos_subdir,
            inference=True,
            upscale=False,
            upload=True,
            download=True,
            num_gpu=num_gpu,
            cuda_devices=cuda_devices,
        )

    def run_upscaling_only(
        self,
        prompt_file: Path,
        upscale_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> Dict[str, Any]:
        """
        Run only upscaling on existing inference output.
        Legacy method for backward compatibility.
        """
        return self.run(
            prompt_file=prompt_file,
            inference=False,
            upscale=True,
            upload=False,
            download=True,
            upscale_weight=upscale_weight,
            num_gpu=num_gpu,
            cuda_devices=cuda_devices,
        )

    def _get_workflow_type(
        self, inference: bool, upscale: bool, upload: bool, download: bool
    ) -> str:
        """Determine workflow type based on enabled steps."""
        if inference and upscale:
            return "full cycle"
        elif inference and not upscale:
            return "inference only"
        elif not inference and upscale:
            return "upscaling only"
        else:
            return "custom"

    def _get_video_directories(self, prompt_file: Path, videos_subdir: Optional[str]) -> list:
        """Get video directories to upload."""
        if videos_subdir:
            return [Path(f"inputs/videos/{videos_subdir}")]

        # Check if this is a RunSpec file
        if prompt_file.stem.endswith("_rs_") or "_rs_" in prompt_file.stem:
            # This is a RunSpec, load it to get the PromptSpec
            try:
                from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec

                run_spec = RunSpec.load(prompt_file)

                # Find the corresponding PromptSpec
                prompt_spec_files = list(
                    Path("inputs/prompts").rglob(f"*{run_spec.prompt_id}*.json")
                )
                if prompt_spec_files:
                    prompt_spec = PromptSpec.load(prompt_spec_files[0])

                    # Extract video directory from the video path
                    if prompt_spec.input_video_path:
                        video_path = Path(prompt_spec.input_video_path)
                        if video_path.parent.exists():
                            return [video_path.parent]

                        # Try to find the video directory by name
                        video_dir_name = video_path.parent.name
                        video_dir = Path(f"inputs/videos/{video_dir_name}")
                        if video_dir.exists():
                            return [video_dir]
            except Exception as e:
                logger.warning(f"Could not load RunSpec/PromptSpec to find videos: {e}")

        # Default behavior: use prompt file stem
        prompt_name = prompt_file.stem
        return [Path(f"inputs/videos/{prompt_name}")]

    def check_remote_status(self) -> Dict[str, Any]:
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

    def _log_workflow_completion(
        self, prompt_file: Path, upscaled: bool, upscale_weight: float, num_gpu: int
    ) -> None:
        """Log successful workflow completion."""
        local_config = self.config_manager.get_local_config()
        remote_config = self.config_manager.get_remote_config()

        # Ensure notes directory exists
        local_config.notes_dir.mkdir(parents=True, exist_ok=True)

        # Create log entry
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        prompt_name = prompt_file.stem

        log_entry = (
            f"{timestamp} | prompt={prompt_file.name} | "
            f"outputs=outputs/{prompt_name} | host={remote_config.host} | "
            f"num_gpu={num_gpu} | upscaled={upscaled} | "
            f"upscale_weight={upscale_weight}\n"
        )

        # Append to run history
        run_history_file = local_config.notes_dir / "run_history.log"
        with open(run_history_file, "a") as f:
            f.write(log_entry)

        logger.info(f"Workflow logged to {run_history_file}")

    def _log_workflow_failure(self, prompt_file: Path, error: str, duration) -> None:
        """Log failed workflow."""
        local_config = self.config_manager.get_local_config()

        # Ensure notes directory exists
        local_config.notes_dir.mkdir(parents=True, exist_ok=True)

        # Create failure log entry
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        prompt_name = prompt_file.stem

        log_entry = (
            f"{timestamp} | FAILED | prompt={prompt_file.name} | "
            f"error={error} | duration={duration}\n"
        )

        # Append to run history
        run_history_file = local_config.notes_dir / "run_history.log"
        with open(run_history_file, "a") as f:
            f.write(log_entry)

        logger.info(f"Workflow failure logged to {run_history_file}")
