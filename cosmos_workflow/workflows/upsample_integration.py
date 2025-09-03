"""Upsampling integration for WorkflowOrchestrator.
Adds prompt upsampling capabilities to the workflow system.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.execution.command_builder import DockerCommandBuilder
from cosmos_workflow.prompts.schemas import PromptSpec

log = logging.getLogger(__name__)


class UpsampleWorkflowMixin:
    """Mixin class to add upsampling capabilities to WorkflowOrchestrator.

    This mixin expects the parent class to have:
    - config_manager: ConfigManager instance
    - file_transfer: FileTransferService instance
    - docker_executor: DockerExecutor instance
    """

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
        # Initialize services if not already done
        if hasattr(self, "_initialize_services"):
            self._initialize_services()

        log.info("Starting prompt upsampling for %s prompts", len(prompt_specs))

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
        log.info("Uploading batch file to %s", remote_inputs_dir)
        self.file_transfer.upload_file(local_batch_path, remote_inputs_dir)

        # Upload any associated videos
        for spec in prompt_specs:
            if spec.input_video_path and os.path.exists(spec.input_video_path):
                remote_videos_dir = f"{remote_config.remote_dir}/inputs/videos"
                log.info("Uploading video: %s", spec.input_video_path)
                self.file_transfer.upload_file(Path(spec.input_video_path), remote_videos_dir)

        # Prepare paths for later use

        # First, upload the working upsampler script
        scripts_dir = f"{remote_config.remote_dir}/scripts"
        self.ssh_manager.execute_command_success(f"mkdir -p {scripts_dir}")

        # Upload the working upsampler script
        local_script = (
            Path(__file__).parent.parent.parent / "scripts" / "working_prompt_upsampler.py"
        )
        if local_script.exists():
            remote_script_path = f"{scripts_dir}/working_prompt_upsampler.py"
            log.info("Uploading upsampler script to %s", remote_script_path)
            self.file_transfer.upload_file(local_script, scripts_dir)
        else:
            log.error("Working upsampler script not found at %s", local_script)
            return {"success": False, "error": "Working upsampler script not found"}

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
        # Note: The script uses --no-offload flag, not --offload
        # By default (without flag) it offloads, with --no-offload it keeps model in memory
        upsample_cmd = (
            f"python /workspace/scripts/working_prompt_upsampler.py "
            f"--batch /workspace/inputs/{batch_filename} "
            f"--output-dir /workspace/outputs "
            f"--checkpoint-dir /workspace/checkpoints"
            # Omit the flag to enable offloading by default
        )
        builder.set_command(upsample_cmd)

        # Get the full Docker command
        cmd = builder.build()

        # Execute upsampling
        log.info("Executing prompt upsampling on remote GPU...")
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
            log.error("Upsampling failed with exit code %s", exit_code)
            log.error("Error output: %s", stderr)
            return {"success": False, "error": stderr, "exit_code": exit_code}

        # Download results JSON file
        remote_results_file = f"{remote_outputs_dir}/batch_results.json"
        local_output_path = local_config.outputs_dir / f"upsampled_{batch_filename}"
        os.makedirs(local_output_path.parent, exist_ok=True)

        log.info("Downloading results from %s", remote_results_file)
        try:
            self.file_transfer.download_file(remote_results_file, str(local_output_path))
        except Exception as e:
            log.error("Failed to download results: %s", e)
            return {"success": False, "error": f"Failed to download results: {e}"}

        # Load and process results
        with open(local_output_path) as f:
            upsampled_results = json.load(f)

        # Update PromptSpecs with upsampled prompts
        updated_specs = []
        for result in upsampled_results:
            # Find matching spec
            matching_spec = next((s for s in prompt_specs if s.id == result.get("spec_id")), None)

            if matching_spec:
                # Create new spec with upsampled prompt
                # Generate a new ID for the enhanced prompt
                from cosmos_workflow.prompts.schemas import SchemaUtils

                enhanced_id = SchemaUtils.generate_prompt_id(
                    result.get("upsampled_prompt", matching_spec.prompt),
                    matching_spec.input_video_path,
                    matching_spec.control_inputs,
                )

                updated_spec = PromptSpec(
                    id=enhanced_id,
                    name=f"{matching_spec.name}_enhanced",
                    prompt=result.get("upsampled_prompt", matching_spec.prompt),
                    negative_prompt=matching_spec.negative_prompt,
                    input_video_path=matching_spec.input_video_path,
                    control_inputs=matching_spec.control_inputs,
                    timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    is_upsampled=True,
                    parent_prompt_text=matching_spec.prompt,
                )
                updated_specs.append(updated_spec)

        log.info("Successfully upsampled %s prompts", len(updated_specs))

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

    def run_prompt_upsampling_from_directory(
        self, prompts_dir: str, pattern: str = "*.json", **kwargs
    ) -> dict[str, Any]:
        """Upsample all prompts from a directory.

        Args:
            prompts_dir: Directory containing PromptSpec JSON files
            pattern: Glob pattern for finding prompt files
            **kwargs: Additional arguments passed to run_prompt_upsampling

        Returns:
            Dictionary with batch upsampling results
        """
        from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
        from cosmos_workflow.prompts.schemas import DirectoryManager

        # Load all prompt specs from directory
        prompt_specs = []
        prompts_path = Path(prompts_dir)

        if not prompts_path.exists():
            log.error("Directory not found: %s", prompts_dir)
            return {"success": False, "error": f"Directory not found: {prompts_dir}"}

        # Create managers for loading
        dir_manager = DirectoryManager(
            prompts_dir=str(prompts_path.parent),
            runs_dir=str(prompts_path.parent),
            videos_dir=str(prompts_path.parent),
        )
        spec_manager = PromptSpecManager(dir_manager)

        # Find and load all prompt files
        for prompt_file in prompts_path.glob(pattern):
            try:
                spec = spec_manager.load(str(prompt_file))
                # Only upsample if not already upsampled
                if not spec.metadata.get("upsampled", False):
                    prompt_specs.append(spec)
                else:
                    log.info("Skipping already upsampled prompt: %s", spec.name)
            except Exception as e:
                log.warning("Failed to load %s: %s", prompt_file, e)

        if not prompt_specs:
            log.info("No prompts found to upsample")
            return {"success": True, "num_upsampled": 0, "message": "No prompts needed upsampling"}

        log.info("Found %s prompts to upsample", len(prompt_specs))
        return self.run_prompt_upsampling(prompt_specs, **kwargs)
