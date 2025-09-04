#!/usr/bin/env python3
"""Workflow orchestrator for Cosmos-Transfer1.
Coordinates all services to run complete workflows with proper error handling and logging.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.command_builder import DockerCommandBuilder
from cosmos_workflow.execution.docker_executor import DockerExecutor
from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
from cosmos_workflow.prompts.schemas import DirectoryManager, PromptSpec
from cosmos_workflow.transfer.file_transfer import FileTransferService
from cosmos_workflow.utils.smart_naming import generate_smart_name

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

    def run(
        self,
        prompt_file: Path,
        videos_subdir: str | None = None,
        inference: bool = True,
        upscale: bool = False,
        upload: bool = True,
        download: bool = True,
        upscale_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> dict[str, Any]:
        """Run workflow with configurable steps.

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

        start_time = datetime.now(timezone.utc)
        prompt_name = prompt_file.stem

        # Determine workflow type for logging
        workflow_type = self._get_workflow_type(inference, upscale, upload, download)

        logger.info("Starting %s workflow for {prompt_name}", workflow_type)
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

                end_time = datetime.now(timezone.utc)
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
            end_time = datetime.now(timezone.utc)
            duration = end_time - start_time

            logger.error("Workflow failed: %s", e)
            print(f"\n[ERROR] Workflow failed: {e}")

            # Log failed workflow
            self._log_workflow_failure(prompt_file, str(e), duration)

            raise RuntimeError(f"Workflow failed: {e}") from e

    def run_full_cycle(
        self,
        prompt_file: Path,
        videos_subdir: str | None = None,
        no_upscale: bool = False,
        upscale_weight: float = 0.5,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> dict[str, Any]:
        """Run complete workflow: upload → inference → upscaling → download.

        Convenience method that configures all steps for a full pipeline execution.
        Used by CLI for the 'run' command without additional flags.
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
        videos_subdir: str | None = None,
        num_gpu: int = 1,
        cuda_devices: str = "0",
    ) -> dict[str, Any]:
        """Run only inference without upscaling.

        Convenience method for running inference-only workflows.
        Useful for quick generation without 4K upscaling overhead.
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
    ) -> dict[str, Any]:
        """Run only upscaling on existing inference output.

        Convenience method for upscaling previously generated videos.
        Assumes inference output already exists on the remote server.
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

    def _get_video_directories(self, prompt_file: Path, videos_subdir: str | None) -> list:
        """Get video directories to upload."""
        if videos_subdir:
            return [Path(f"inputs/videos/{videos_subdir}")]

        # Try to load the file to get video paths
        try:
            from cosmos_workflow.prompts.schemas import PromptSpec, RunSpec

            # Try loading as PromptSpec first
            prompt_spec = None
            try:
                prompt_spec = PromptSpec.load(prompt_file)
            except (json.JSONDecodeError, KeyError, TypeError):
                # Not a PromptSpec, might be a RunSpec
                pass

            # If not a PromptSpec, check if this is a RunSpec file
            if not prompt_spec and (
                prompt_file.stem.endswith("_rs_") or "_rs_" in prompt_file.stem
            ):
                # This is a RunSpec, load it to get the PromptSpec
                run_spec = RunSpec.load(prompt_file)

                # Find the corresponding PromptSpec by loading files and checking ID
                # Since hash is no longer in filename, we need to search by content
                prompt_spec_files = []
                for pf in Path("inputs/prompts").rglob("*.json"):
                    try:
                        with open(pf) as f:
                            data = json.load(f)
                            if data.get("id") == run_spec.prompt_id:
                                prompt_spec_files.append(pf)
                                break
                    except (OSError, json.JSONDecodeError):
                        continue
                if prompt_spec_files:
                    prompt_spec = PromptSpec.load(prompt_spec_files[0])

            # If we have a prompt_spec (either directly loaded or from RunSpec), get video directory
            if prompt_spec and prompt_spec.input_video_path:
                video_path = Path(prompt_spec.input_video_path)
                if video_path.parent.exists():
                    return [video_path.parent]

                # Try to find the video directory by name
                video_dir_name = video_path.parent.name
                video_dir = Path(f"inputs/videos/{video_dir_name}")
                if video_dir.exists():
                    return [video_dir]

        except Exception as e:
            logger.warning("Could not load PromptSpec/RunSpec to find videos: %s", e)

        # Default behavior: use prompt file stem
        prompt_name = prompt_file.stem
        return [Path(f"inputs/videos/{prompt_name}")]

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

    def _log_workflow_completion(
        self, prompt_file: Path, upscaled: bool, upscale_weight: float, num_gpu: int
    ) -> None:
        """Log successful workflow completion."""
        local_config = self.config_manager.get_local_config()
        remote_config = self.config_manager.get_remote_config()

        # Ensure notes directory exists
        local_config.notes_dir.mkdir(parents=True, exist_ok=True)

        # Create log entry
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
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

        logger.info("Workflow logged to %s", run_history_file)

    def _log_workflow_failure(self, prompt_file: Path, error: str, duration) -> None:
        """Log failed workflow."""
        local_config = self.config_manager.get_local_config()

        # Ensure notes directory exists
        local_config.notes_dir.mkdir(parents=True, exist_ok=True)

        # Create failure log entry
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        log_entry = (
            f"{timestamp} | FAILED | prompt={prompt_file.name} | "
            f"error={error} | duration={duration}\n"
        )

        # Append to run history
        run_history_file = local_config.notes_dir / "run_history.log"
        with open(run_history_file, "a") as f:
            f.write(log_entry)

        logger.info("Workflow failure logged to %s", run_history_file)

    # ========== Upsampling Methods (formerly in UpsampleWorkflowMixin) ==========

    def run_prompt_upsampling(
        self,
        prompt_specs: list[PromptSpec],
        preprocess_videos: bool = True,
        max_resolution: int = 480,
        num_frames: int = 2,
        num_gpu: int = 1,
        cuda_devices: str | None = None,
    ) -> dict[str, Any]:
        """Run batch prompt upsampling on remote GPU.

        Args:
            prompt_specs: List of PromptSpec objects to upsample
            preprocess_videos: Whether to preprocess videos to avoid vocab errors
            max_resolution: Maximum resolution for video preprocessing
            num_frames: Number of frames to extract from videos
            num_gpu: Number of GPUs to use
            cuda_devices: Specific CUDA devices (e.g., "0,1")

        Returns:
            Dictionary with upsampling results and metadata
        """
        import json
        import os

        # Initialize services if not already done
        self._initialize_services()

        logger.info("Starting prompt upsampling for %s prompts", len(prompt_specs))

        # Prepare batch data
        batch_data = []
        for spec in prompt_specs:
            batch_data.append(
                {
                    "name": spec.name,
                    "prompt": spec.prompt,
                    "video_path": spec.input_video_path,
                    "spec_id": spec.id,
                }
            )

        # Create temporary batch file
        batch_filename = (
            f"upsample_batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
        )
        local_config = self.config_manager.get_local_config()
        local_batch_path = local_config.prompts_dir / batch_filename

        # Save batch file locally
        os.makedirs(local_batch_path.parent, exist_ok=True)
        with open(local_batch_path, "w") as f:
            json.dump(batch_data, f, indent=2)

        # Upload batch file to remote
        remote_config = self.config_manager.get_remote_config()
        remote_inputs_dir = f"{remote_config.remote_dir}/inputs"
        logger.info("Uploading batch file to %s", remote_inputs_dir)
        self.file_transfer.upload_file(local_batch_path, remote_inputs_dir)

        # Upload any associated videos
        for spec in prompt_specs:
            if spec.input_video_path and os.path.exists(spec.input_video_path):
                remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                logger.info("Uploading video: %s", spec.input_video_path)
                self.file_transfer.upload_file(Path(spec.input_video_path), remote_videos_dir)

        # First, upload the working upsampler script
        scripts_dir = f"{remote_config.remote_dir}/scripts"
        self.ssh_manager.execute_command_success(f"mkdir -p {scripts_dir}")

        # Upload the working upsampler script
        local_script = Path(__file__).parent.parent.parent / "scripts" / "prompt_upsampler.py"
        if local_script.exists():
            remote_script_path = f"{scripts_dir}/prompt_upsampler.py"
            logger.info("Uploading upsampler script to %s", remote_script_path)
            self.file_transfer.upload_file(local_script, scripts_dir)
        else:
            logger.error("Upsampler script not found at %s", local_script)
            return {"success": False, "error": "Upsampler script not found"}

        # Create output directory on remote
        remote_outputs_dir = f"{remote_config.remote_dir}/outputs"
        self.ssh_manager.execute_command_success(f"mkdir -p {remote_outputs_dir}")

        # Build Docker command using the same pattern as inference
        docker_image = remote_config.docker_image

        # Build command using DockerCommandBuilder
        builder = DockerCommandBuilder(docker_image)
        builder.with_gpu(cuda_devices or "0")
        builder.add_option("--ipc=host")
        builder.add_option("--shm-size=8g")
        builder.add_volume(remote_config.remote_dir, "/workspace")
        builder.add_volume("$HOME/.cache/huggingface", "/root/.cache/huggingface")

        # Set environment for VLLM
        builder.add_environment("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
        builder.add_environment("CUDA_VISIBLE_DEVICES", cuda_devices or "0")

        # Build the command to run the upsampler
        upsample_cmd = (
            f"python /workspace/scripts/prompt_upsampler.py "
            f"--batch /workspace/inputs/{batch_filename} "
            f"--output-dir /workspace/outputs "
            f"--checkpoint-dir /workspace/checkpoints"
            # Omit the flag to enable offloading by default
        )
        builder.set_command(upsample_cmd)

        # Get the full Docker command
        cmd = builder.build()

        # Execute upsampling
        logger.info("Executing prompt upsampling on remote GPU...")
        try:
            # Add sudo prefix for Docker command
            full_cmd = f"sudo {cmd}"
            self.ssh_manager.execute_command_success(full_cmd, timeout=1200)  # 20 min timeout
            exit_code = 0
            stderr = ""
        except RuntimeError as e:
            exit_code = 1
            stderr = str(e)

        if exit_code != 0:
            logger.error("Upsampling failed with exit code %s", exit_code)
            logger.error("Error output: %s", stderr)
            return {"success": False, "error": stderr, "exit_code": exit_code}

        # Download results JSON file
        remote_results_file = f"{remote_outputs_dir}/batch_results.json"
        local_output_path = local_config.outputs_dir / f"upsampled_{batch_filename}"
        os.makedirs(local_output_path.parent, exist_ok=True)

        logger.info("Downloading results from %s", remote_results_file)
        try:
            self.file_transfer.download_file(remote_results_file, str(local_output_path))
        except Exception as e:
            logger.error("Failed to download results: %s", e)
            return {"success": False, "error": f"Failed to download results: {e}"}

        # Load and process results
        with open(local_output_path) as f:
            upsampled_results = json.load(f)

        # Update PromptSpecs with upsampled prompts
        updated_specs = []
        for result in upsampled_results:
            # Find matching spec - try spec_id first, fall back to name
            spec_id = result.get("spec_id")
            name = result.get("name")
            matching_spec = next(
                (s for s in prompt_specs if s.id == spec_id or s.name == name), None
            )

            if matching_spec:
                # Create new spec with upsampled prompt using PromptSpecManager
                upsampled_prompt = result.get("upsampled_prompt", matching_spec.prompt)

                # Generate smart name from enhanced prompt content
                enhanced_name = generate_smart_name(upsampled_prompt, max_length=30)

                # Get config and create DirectoryManager for PromptSpecManager
                local_config = self.config_manager.get_local_config()
                dir_manager = DirectoryManager(local_config.prompts_dir, local_config.runs_dir)

                # Create spec using manager for proper handling
                spec_manager = PromptSpecManager(dir_manager)
                updated_spec = spec_manager.create_prompt_spec(
                    name=enhanced_name,  # Use smart name instead of "_enhanced" suffix
                    prompt_text=upsampled_prompt,
                    negative_prompt=matching_spec.negative_prompt,
                    input_video_path=matching_spec.input_video_path,
                    control_inputs=matching_spec.control_inputs,
                    is_upsampled=True,
                    parent_prompt_text=matching_spec.prompt,
                )
                updated_specs.append(updated_spec)

        logger.info("Successfully upsampled %s prompts", len(updated_specs))

        return {
            "success": True,
            "updated_specs": updated_specs,
            "results_file": str(local_output_path),
            "num_upsampled": len(updated_specs),
        }

    def run_single_prompt_upsampling(self, prompt_spec: PromptSpec, **kwargs) -> dict[str, Any]:
        """Convenience method to upsample a single prompt.

        Args:
            prompt_spec: Single PromptSpec to upsample
            **kwargs: Additional arguments passed to run_prompt_upsampling

        Returns:
            Dictionary with upsampling result
        """
        result = self.run_prompt_upsampling([prompt_spec], **kwargs)

        if result["success"] and result["updated_specs"]:
            result["updated_spec"] = result["updated_specs"][0]

        return result
