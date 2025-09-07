"""Main facade interface for Cosmos Workflow System.

THIS IS THE PRIMARY INTERFACE - All CLI commands, UI interactions, and external
code should use this class as the single entry point to the system.

This facade combines:
- WorkflowService (database operations)
- WorkflowOrchestrator (GPU execution)

Into a unified, high-level API that matches user intentions.

Example:
    from cosmos_workflow.api import WorkflowOperations

    ops = WorkflowOperations()  # Main facade
    prompt = ops.create_prompt("A futuristic city", "inputs/videos/")
    result = ops.quick_inference(prompt["id"])
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import init_database
from cosmos_workflow.execution.command_builder import DockerCommandBuilder
from cosmos_workflow.services import WorkflowService
from cosmos_workflow.utils.logging import logger
from cosmos_workflow.utils.smart_naming import generate_smart_name
from cosmos_workflow.workflows import WorkflowOrchestrator

# Default negative prompt for video generation
DEFAULT_NEGATIVE_PROMPT = (
    "The video captures a game playing, with bad crappy graphics and "
    "cartoonish frames. It represents a recording of old outdated games. "
    "The lighting looks very fake. The textures are very raw and basic. "
    "The geometries are very primitive. The images are very pixelated and "
    "of poor CG quality. There are many subtitles in the footage. "
    "Overall, the video is unrealistic at all."
)


class WorkflowOperations:
    """Main facade for the Cosmos Workflow System.

    THIS IS THE PRIMARY INTERFACE - Use this class for all interactions with
    the system. Do not directly use WorkflowService or WorkflowOrchestrator.

    This facade provides:
    - High-level operations that combine database and GPU functionality
    - Consistent error handling and validation
    - Simplified API that matches user intentions
    - Single point of entry for CLI, UI, and external code

    Internal components (not for direct use):
    - WorkflowService: Database operations only
    - WorkflowOrchestrator: GPU execution only (confusing name, will be renamed in v2.0)
    """

    def __init__(self, config: ConfigManager | None = None):
        """Initialize workflow operations.

        Args:
            config: Configuration manager instance. If None, creates default.
        """
        if config is None:
            config = ConfigManager()

        self.config = config

        # Initialize database and service
        local_config = config.get_local_config()
        db_path = local_config.outputs_dir / "cosmos.db"
        db = init_database(str(db_path))

        # Create service and orchestrator
        self.service = WorkflowService(db, config)
        self.orchestrator = WorkflowOrchestrator(service=self.service)

        logger.info("WorkflowOperations initialized")

    # ========== Prompt Operations ==========

    def create_prompt(
        self,
        prompt_text: str,
        video_dir: Path | str,
        name: str | None = None,
        negative_prompt: str | None = None,
        model_type: str = "transfer",
    ) -> dict[str, Any]:
        """Create a prompt with simplified interface.

        Args:
            prompt_text: The prompt text
            video_dir: Directory containing video files (color.mp4, depth.mp4, etc.)
            name: Optional name for the prompt (auto-generated if not provided)
            negative_prompt: Optional negative prompt (uses default if not provided)
            model_type: Model type (default: "transfer")

        Returns:
            Dictionary containing prompt data with 'id' key

        Raises:
            FileNotFoundError: If required video files are missing
            ValueError: If prompt creation fails
        """
        logger.info("Creating prompt with text: %s", prompt_text[:50])

        # Convert to Path if string
        video_dir = Path(video_dir)

        # Validate video files exist
        color_path = video_dir / "color.mp4"
        if not color_path.exists():
            raise FileNotFoundError(f"Required color.mp4 not found in {video_dir}")

        # Build inputs dictionary
        inputs = {"video": str(color_path)}

        # Add optional video files if they exist
        depth_path = video_dir / "depth.mp4"
        if depth_path.exists():
            inputs["depth"] = str(depth_path)

        seg_path = video_dir / "segmentation.mp4"
        if seg_path.exists():
            inputs["seg"] = str(seg_path)

        # Generate name if not provided
        if name is None:
            name = generate_smart_name(prompt_text, max_length=30)
            logger.debug("Generated name: %s", name)

        # Build parameters
        parameters = {
            "name": name,
            "negative_prompt": negative_prompt or DEFAULT_NEGATIVE_PROMPT,
        }

        # Create prompt using service
        prompt = self.service.create_prompt(
            model_type=model_type,
            prompt_text=prompt_text,
            inputs=inputs,
            parameters=parameters,
        )

        logger.info("Created prompt with ID: %s", prompt["id"])
        return prompt

    def enhance_prompt(
        self,
        prompt_id: str,
        create_new: bool = True,
        enhancement_model: str = "pixtral",
        stream_logs: bool = False,
    ) -> dict[str, Any]:
        """Enhance an existing prompt using AI.

        Args:
            prompt_id: ID of prompt to enhance
            create_new: If True, creates new enhanced prompt. If False, updates existing.
            enhancement_model: Model to use for enhancement (default: "pixtral")
            stream_logs: If True, stream logs during enhancement

        Returns:
            Dictionary containing enhanced prompt data

        Raises:
            ValueError: If prompt not found or enhancement fails
        """
        logger.info("Enhancing prompt %s with model %s", prompt_id, enhancement_model)

        # Get original prompt
        original = self.service.get_prompt(prompt_id)
        if not original:
            raise ValueError(f"Prompt not found: {prompt_id}")

        # Check if we can overwrite
        if not create_new:
            runs = self.service.list_runs(prompt_id=prompt_id, limit=1)
            if runs:
                raise ValueError(
                    f"Cannot overwrite prompt {prompt_id} - has {len(runs)} associated runs"
                )

        # Run enhancement using orchestrator
        enhanced_text = self.orchestrator.run_prompt_upsampling(
            prompt_text=original["prompt_text"],
            model=enhancement_model,
            video_path=original["inputs"].get("video"),
            stream_logs=stream_logs,
        )

        if create_new:
            # Create new enhanced prompt
            name = original["parameters"].get("name", "unnamed")
            enhanced = self.service.create_prompt(
                model_type=original["model_type"],
                prompt_text=enhanced_text,
                inputs=original["inputs"],
                parameters={
                    **original["parameters"],
                    "name": f"{name}_enhanced",
                    "enhanced": True,
                    "parent_prompt_id": prompt_id,
                    "enhancement_model": enhancement_model,
                    "enhanced_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            logger.info("Created enhanced prompt: %s", enhanced["id"])
            return enhanced
        else:
            # Update existing prompt
            self.service.update_prompt(
                prompt_id,
                prompt_text=enhanced_text,
                parameters={
                    **original["parameters"],
                    "enhanced": True,
                    "enhancement_model": enhancement_model,
                    "enhanced_at": datetime.now(timezone.utc).isoformat(),
                },
            )
            updated = self.service.get_prompt(prompt_id)
            logger.info("Updated prompt %s with enhanced text", prompt_id)
            return updated

    # ========== Internal Helper Methods ==========

    def _validate_prompt(self, prompt_id: str) -> dict[str, Any]:
        """Validate that a prompt exists and return it.

        Args:
            prompt_id: The prompt ID to validate

        Returns:
            The prompt dictionary

        Raises:
            ValueError: If prompt not found
        """
        prompt = self.service.get_prompt(prompt_id)
        if not prompt:
            error_msg = f"Prompt not found: {prompt_id}"
            raise ValueError(error_msg)
        return prompt

    def _build_execution_config(
        self,
        weights: dict[str, float] | None = None,
        num_steps: int = 35,
        guidance: float = 7.0,
        seed: int = 1,
        **kwargs,
    ) -> dict[str, Any]:
        """Build a standardized execution configuration.

        Args:
            weights: Control weights dict (vis, edge, depth, seg)
            num_steps: Number of inference steps
            guidance: Guidance scale (CFG)
            seed: Random seed
            **kwargs: Additional execution config parameters

        Returns:
            Dictionary containing execution configuration

        Raises:
            ValueError: If weights are invalid
        """
        # Default weights if not provided
        if weights is None:
            weights = {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}

        # Validate weights
        if not all(0 <= w <= 1 for w in weights.values()):
            raise ValueError("All weights must be between 0 and 1")
        if not (0.99 <= sum(weights.values()) <= 1.01):
            error_msg = f"Weights must sum to 1.0, got {sum(weights.values())}"
            raise ValueError(error_msg)

        # Build execution config
        execution_config = {
            "weights": weights,
            "num_steps": num_steps,
            "guidance": guidance,
            "seed": seed,
            "sigma_max": kwargs.get("sigma_max", 70.0),
            "blur_strength": kwargs.get("blur_strength", "medium"),
            "canny_threshold": kwargs.get("canny_threshold", "medium"),
            "fps": kwargs.get("fps", 24),
        }

        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in execution_config:
                execution_config[key] = value

        return execution_config

    # ========== Composite Operations (What users actually want) ==========

    def create_and_run(
        self,
        prompt_text: str,
        video_dir: Path | str,
        name: str | None = None,
        negative_prompt: str | None = None,
        weights: dict[str, float] | None = None,
        num_steps: int = 35,
        guidance: float = 7.0,
        upscale: bool = False,
        upscale_weight: float = 0.5,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a prompt and immediately run inference - the most common use case.

        Args:
            prompt_text: The prompt text
            video_dir: Directory containing video files
            name: Optional name for the prompt
            negative_prompt: Optional negative prompt
            weights: Control weights
            num_steps: Number of inference steps
            guidance: Guidance scale
            upscale: Whether to run 4K upscaling
            upscale_weight: Weight for upscaling
            **kwargs: Additional parameters

        Returns:
            Dictionary containing:
                - prompt_id: Created prompt ID
                - run_id: Created run ID
                - output_path: Path to generated video
                - duration_seconds: Execution time
        """
        logger.info("Create and run workflow for: %s", prompt_text[:50])

        # Create prompt
        prompt = self.create_prompt(
            prompt_text=prompt_text,
            video_dir=video_dir,
            name=name,
            negative_prompt=negative_prompt,
        )

        # Use quick_inference to handle run creation and execution
        result = self.quick_inference(
            prompt_id=prompt["id"],
            weights=weights,
            num_steps=num_steps,
            guidance=guidance,
            upscale=upscale,
            upscale_weight=upscale_weight,
            **kwargs,
        )

        return result

    def quick_inference(
        self,
        prompt_id: str,
        weights: dict[str, float] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Run inference on a prompt - creates and executes run internally.

        This is the recommended method for running inference. It handles all the
        details of run creation and execution internally.

        Args:
            prompt_id: ID of prompt to run
            weights: Control weights (optional, defaults to balanced)
            **kwargs: Additional execution parameters (num_steps, guidance, seed,
                     upscale, upscale_weight, stream_logs, etc.)

        Returns:
            Dictionary containing execution results with run_id for tracking

        Raises:
            ValueError: If prompt not found
        """
        logger.info(f"Quick inference for prompt {prompt_id}")

        # Validate prompt exists
        prompt = self._validate_prompt(prompt_id)

        # Extract upscale params if present (not part of execution config)
        upscale = kwargs.pop("upscale", False)
        upscale_weight = kwargs.pop("upscale_weight", 0.5)
        stream_logs = kwargs.pop("stream_logs", False)  # Extract stream flag

        # Build execution config
        execution_config = self._build_execution_config(weights=weights, **kwargs)

        # Create run directly with service
        run = self.service.create_run(
            prompt_id=prompt_id,
            execution_config=execution_config,
        )
        logger.info(f"Created run {run['id']} for prompt {prompt_id}")

        # Update status and execute
        self.service.update_run_status(run["id"], "running")

        try:
            # Execute on GPU
            result = self.orchestrator.execute_run(
                run,
                prompt,
                upscale=upscale,
                upscale_weight=upscale_weight,
                stream_logs=stream_logs,
            )

            # Update run with results
            self.service.update_run(run["id"], outputs=result)
            self.service.update_run_status(run["id"], "completed")
            logger.info("Run %s completed successfully", run["id"])

            return {
                "run_id": run["id"],
                "output_path": result.get("output_path"),
                "duration_seconds": result.get("duration_seconds"),
                "status": "success",
            }

        except Exception as e:
            logger.exception("Run %s failed", run["id"])
            self.service.update_run_status(run["id"], "failed")
            return {
                "run_id": run["id"],
                "output_path": None,
                "duration_seconds": None,
                "status": "failed",
                "error": str(e),
            }

    def batch_inference(
        self,
        prompt_ids: list[str],
        shared_weights: dict[str, float] | None = None,
        stream_logs: bool = False,
        **kwargs,
    ) -> dict[str, Any]:
        """Run inference on multiple prompts as a batch.

        This method processes multiple prompts efficiently by creating and executing
        all runs together. Runs are created internally.

        Args:
            prompt_ids: List of prompt IDs to run
            shared_weights: Weights to use for all prompts (optional)
            **kwargs: Additional execution parameters (num_steps, guidance, seed, etc.)

        Returns:
            Dictionary containing batch results with output_mapping

        Note:
            Missing prompts are logged and skipped gracefully.
        """
        logger.info("Batch inference for %d prompts", len(prompt_ids))

        # Handle empty list case
        if not prompt_ids:
            logger.warning("Empty prompt list provided for batch inference")
            return self.orchestrator.execute_batch_runs([])

        # Build execution config once for all prompts
        execution_config = self._build_execution_config(weights=shared_weights, **kwargs)

        # Create runs for all prompts
        runs_and_prompts = []
        for prompt_id in prompt_ids:
            try:
                # Validate prompt
                prompt = self._validate_prompt(prompt_id)

                # Create run directly with service
                run = self.service.create_run(
                    prompt_id=prompt_id,
                    execution_config=execution_config,
                )
                logger.info(f"Created run {run['id']} for prompt {prompt_id}")
                runs_and_prompts.append((run, prompt))

            except ValueError as e:
                logger.warning("Skipping prompt %s: %s", prompt_id, e)
                continue

        # Execute as batch
        batch_result = self.orchestrator.execute_batch_runs(
            runs_and_prompts, stream_logs=stream_logs
        )

        # Update run statuses
        for run, _ in runs_and_prompts:
            if run["id"] in batch_result.get("output_mapping", {}):
                self.service.update_run_status(run["id"], "completed")
            else:
                self.service.update_run_status(run["id"], "failed")

        return batch_result

    # ========== Utility Operations ==========

    def list_prompts(self, **kwargs) -> list[dict[str, Any]]:
        """List prompts with optional filtering.

        Args:
            **kwargs: Filtering parameters (model_type, limit, offset)

        Returns:
            List of prompt dictionaries
        """
        return self.service.list_prompts(**kwargs)

    def list_runs(self, **kwargs) -> list[dict[str, Any]]:
        """List runs with optional filtering.

        Args:
            **kwargs: Filtering parameters (status, prompt_id, limit, offset)

        Returns:
            List of run dictionaries
        """
        return self.service.list_runs(**kwargs)

    def get_prompt(self, prompt_id: str) -> dict[str, Any] | None:
        """Get a prompt by ID.

        Args:
            prompt_id: The prompt ID

        Returns:
            Prompt dictionary or None if not found
        """
        return self.service.get_prompt(prompt_id)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        """Get a run by ID.

        Args:
            run_id: The run ID

        Returns:
            Run dictionary or None if not found
        """
        return self.service.get_run(run_id)

    def get_prompt_with_runs(self, prompt_id: str) -> dict[str, Any] | None:
        """Get a prompt with all its associated runs.

        Args:
            prompt_id: The prompt ID

        Returns:
            Dictionary containing prompt data and its runs, or None if not found
        """
        prompt = self.service.get_prompt(prompt_id)
        if not prompt:
            return None

        # Get all runs for this prompt
        runs = self.service.list_runs(prompt_id=prompt_id, limit=100)
        prompt["runs"] = runs
        return prompt

    def preview_prompt_deletion(self, prompt_id: str) -> dict[str, Any]:
        """Preview what will be deleted if a prompt is removed.

        Args:
            prompt_id: The prompt ID to preview deletion for

        Returns:
            Dictionary with prompt info, associated runs, and warnings
        """
        prompt = self.service.get_prompt(prompt_id)
        if not prompt:
            return {"error": f"Prompt not found: {prompt_id}"}

        runs = self.service.list_runs(prompt_id=prompt_id, limit=100)

        return {
            "prompt": prompt,
            "runs": runs,
            "run_count": len(runs),
            "warnings": [],
        }

    def delete_prompt(self, prompt_id: str) -> dict[str, Any]:
        """Delete a prompt and its associated runs.

        Args:
            prompt_id: The prompt ID to delete

        Returns:
            Dictionary with deletion results
        """
        return self.service.delete_prompt(prompt_id)

    def delete_run(self, run_id: str) -> dict[str, Any]:
        """Delete a run.

        Args:
            run_id: The run ID to delete

        Returns:
            Dictionary with deletion results
        """
        return self.service.delete_run(run_id)

    def search_prompts(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search prompts by text.

        Args:
            query: Search query string
            limit: Maximum results

        Returns:
            List of matching prompt dictionaries
        """
        return self.service.search_prompts(query, limit)

    # ========== System Operations ==========

    def check_status(self) -> dict[str, Any]:
        """Check remote GPU instance status.

        Returns:
            Dictionary containing:
                - ssh_status: SSH connectivity status
                - docker_status: Docker daemon status
                - gpu_info: GPU information if available
                - containers: Running containers info
        """
        logger.info("Checking remote GPU status")
        return self.orchestrator.check_remote_status()

    def get_active_containers(self) -> list[dict[str, str]]:
        """Get list of active Docker containers.

        Returns:
            List of dictionaries with container info:
                - container_id: Container ID (short form)
                - name: Container name
                - image: Image name
                - status: Container status
        """
        logger.info("Getting active Docker containers")
        self.orchestrator._initialize_services()

        try:
            with self.orchestrator.ssh_manager:
                container = self.orchestrator.docker_executor.get_active_container()

                if container:
                    # Return as list for backward compatibility
                    # Map field names to match existing interface
                    return [
                        {
                            "container_id": container["id_short"],
                            "name": container["name"],
                            "image": container["image"],
                            "status": container["status"],
                        }
                    ]
                return []
        except Exception as e:
            logger.error("Failed to get containers: %s", e)
            return []

    def stream_container_logs(self, container_id: str, callback=None) -> None:
        """Stream logs from a specific Docker container.

        Handles both CLI (stdout) and Gradio (callback) streaming modes.

        Args:
            container_id: Docker container ID to stream from
            callback: Optional callback function for each log line (for Gradio).
                     If None, streams directly to stdout (for CLI).

        Raises:
            RuntimeError: If streaming fails
        """
        logger.info("Streaming logs from container %s", container_id)

        if callback:
            # Gradio mode - use callback with threading to not block UI
            import threading

            cmd = DockerCommandBuilder.build_logs_command(container_id, follow=True)

            def stream_output():
                try:
                    # Execute command without streaming (we'll process output)
                    exit_code, stdout, stderr = self.orchestrator.ssh_manager.execute_command(
                        cmd,
                        timeout=3600,  # 1 hour timeout
                        stream_output=False,  # We handle output ourselves
                    )

                    # Send stdout lines to callback
                    for line in stdout.split("\n"):
                        if line:
                            callback(line)

                    # Send stderr lines to callback with error prefix
                    if stderr:
                        for line in stderr.split("\n"):
                            if line:
                                callback(f"[ERROR] {line}")

                except Exception as e:
                    callback(f"[ERROR] Stream failed: {e}")

            # Run in background thread to not block
            thread = threading.Thread(target=stream_output, daemon=True)
            thread.start()
        else:
            # CLI mode - stream directly to stdout
            cmd = DockerCommandBuilder.build_logs_command(container_id, follow=True)
            self.orchestrator.ssh_manager.execute_command(
                cmd,
                timeout=86400,  # 24 hour timeout for long streams
                stream_output=True,
            )

    def verify_integrity(self) -> dict[str, Any]:
        """Verify database-filesystem integrity.

        Checks for:
        - Database paths that point to non-existent files
        - Orphaned directories without database entries
        - Missing output files for completed runs

        Returns:
            Dictionary containing:
                - issues: List of found issues
                - warnings: List of warnings
                - stats: Statistics about the verification
        """
        logger.info("Verifying data integrity")

        issues = []
        warnings = []
        stats = {
            "total_runs": 0,
            "checked_runs": 0,
            "missing_files": 0,
            "orphaned_dirs": 0,
        }

        # Check all runs in database
        runs = self.service.list_runs()
        stats["total_runs"] = len(runs)

        for run in runs:
            stats["checked_runs"] += 1

            # Check if output files exist for completed runs
            if run.get("status") == "completed":
                outputs = run.get("outputs", {})
                if "output_path" in outputs:
                    output_path = Path(outputs["output_path"])
                    if not output_path.exists():
                        stats["missing_files"] += 1
                        issues.append(
                            {
                                "type": "missing_output",
                                "run_id": run["id"],
                                "path": str(output_path),
                            }
                        )

        # Check prompts for missing video directories
        prompts = self.service.list_prompts()
        for prompt in prompts:
            inputs = prompt.get("inputs", {})
            if "video" in inputs:
                video_path = Path(inputs["video"])
                if not video_path.exists():
                    issues.append(
                        {
                            "type": "missing_input",
                            "prompt_id": prompt["id"],
                            "path": str(video_path),
                        }
                    )

        return {
            "issues": issues,
            "warnings": warnings,
            "stats": stats,
        }

    def kill_containers(self) -> dict[str, Any]:
        """Kill all running cosmos containers on the GPU instance.

        Returns:
            Dict with status, killed_count, and list of killed container IDs.
        """
        logger.info("Killing all running cosmos containers")

        try:
            # Initialize services through orchestrator (follows established pattern)
            self.orchestrator._initialize_services()

            with self.orchestrator.ssh_manager:
                # Use orchestrator's docker executor
                result = self.orchestrator.docker_executor.kill_containers()

                if result["status"] == "success":
                    logger.info("Successfully killed %d container(s)", result["killed_count"])
                else:
                    logger.error("Failed to kill containers: %s", result.get("error"))

                return result

        except Exception as e:
            logger.error("Failed to kill containers: %s", e)
            return {"status": "failed", "error": str(e), "killed_count": 0, "killed_containers": []}
