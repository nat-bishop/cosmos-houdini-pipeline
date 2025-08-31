"""
Upsampling integration for WorkflowOrchestrator.
Adds prompt upsampling capabilities to the workflow system.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from cosmos_workflow.execution.docker_executor import DockerExecutor
from cosmos_workflow.prompts.schemas import PromptSpec
from cosmos_workflow.transfer.file_transfer import FileTransferService

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
        prompt_specs: List[PromptSpec],
        preprocess_videos: bool = True,
        max_resolution: int = 480,
        num_frames: int = 2,
        num_gpu: int = 1,
        cuda_devices: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run batch prompt upsampling on remote GPU.

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
        log.info(f"Starting prompt upsampling for {len(prompt_specs)} prompts")

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
        batch_filename = f"upsample_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        local_config = self.config_manager.get_local_config()
        local_batch_path = local_config.prompts_dir / batch_filename

        # Save batch file locally
        os.makedirs(local_batch_path.parent, exist_ok=True)
        with open(local_batch_path, "w") as f:
            json.dump(batch_data, f, indent=2)

        # Upload batch file to remote
        remote_config = self.config_manager.get_remote_config()
        remote_batch_path = f"{remote_config.remote_dir}/inputs/{batch_filename}"
        log.info(f"Uploading batch file to {remote_batch_path}")
        self.file_transfer.upload_file(str(local_batch_path), remote_batch_path)

        # Upload any associated videos
        for spec in prompt_specs:
            if spec.input_video_path and os.path.exists(spec.input_video_path):
                remote_video_path = f"{remote_config.remote_dir}/inputs/videos/"
                log.info(f"Uploading video: {spec.input_video_path}")
                self.file_transfer.upload_file(spec.input_video_path, remote_video_path)

        # Prepare output path
        output_filename = f"upsampled_{batch_filename}"
        remote_output_path = f"{remote_config.remote_dir}/outputs/{output_filename}"

        # Build Docker command
        docker_cmd = [
            "bash",
            "/home/ubuntu/NatsFS/cosmos-transfer1/scripts/upsample_prompt.sh",
            remote_batch_path,
            remote_output_path,
            str(preprocess_videos).lower(),
            str(max_resolution),
            str(num_frames),
            str(num_gpu),
        ]

        # Set environment variables
        environment = {}
        if cuda_devices:
            environment["CUDA_VISIBLE_DEVICES"] = cuda_devices

        # Execute upsampling
        log.info("Executing prompt upsampling on remote GPU...")
        exit_code, stdout, stderr = self.docker_executor.execute(
            command=docker_cmd, working_dir=remote_config.remote_dir, environment=environment
        )

        if exit_code != 0:
            log.error(f"Upsampling failed with exit code {exit_code}")
            log.error(f"Error output: {stderr}")
            return {"success": False, "error": stderr, "exit_code": exit_code}

        # Download results
        local_output_path = local_config.outputs_dir / output_filename
        log.info(f"Downloading results to {local_output_path}")
        self.file_transfer.download_file(remote_output_path, str(local_output_path))

        # Load and process results
        with open(local_output_path, "r") as f:
            upsampled_results = json.load(f)

        # Update PromptSpecs with upsampled prompts
        updated_specs = []
        for result in upsampled_results:
            # Find matching spec
            matching_spec = next((s for s in prompt_specs if s.id == result.get("spec_id")), None)

            if matching_spec:
                # Create new spec with upsampled prompt
                updated_spec = PromptSpec(
                    name=matching_spec.name,
                    prompt=result.get("upsampled_prompt", matching_spec.prompt),
                    negative_prompt=matching_spec.negative_prompt,
                    input_video_path=matching_spec.input_video_path,
                    control_inputs=matching_spec.control_inputs,
                    metadata={
                        **matching_spec.metadata,
                        "original_prompt": result.get("original_prompt"),
                        "upsampled": True,
                        "upsampled_at": datetime.now().isoformat(),
                        "upsampling_params": {
                            "max_resolution": max_resolution,
                            "num_frames": num_frames,
                            "preprocessed": preprocess_videos,
                        },
                    },
                )
                updated_specs.append(updated_spec)

        log.info(f"Successfully upsampled {len(updated_specs)} prompts")

        return {
            "success": True,
            "updated_specs": updated_specs,
            "results_file": str(local_output_path),
            "num_upsampled": len(updated_specs),
        }

    def run_single_prompt_upsampling(self, prompt_spec: PromptSpec, **kwargs) -> Dict[str, Any]:
        """
        Convenience method to upsample a single prompt.

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
    ) -> Dict[str, Any]:
        """
        Upsample all prompts from a directory.

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
            log.error(f"Directory not found: {prompts_dir}")
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
                    log.info(f"Skipping already upsampled prompt: {spec.name}")
            except Exception as e:
                log.warning(f"Failed to load {prompt_file}: {e}")

        if not prompt_specs:
            log.info("No prompts found to upsample")
            return {"success": True, "num_upsampled": 0, "message": "No prompts needed upsampling"}

        log.info(f"Found {len(prompt_specs)} prompts to upsample")
        return self.run_prompt_upsampling(prompt_specs, **kwargs)
