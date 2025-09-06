"""Unified workflow operations interface.

This module provides a single, consistent interface for all workflow operations,
combining service and orchestrator functionality into high-level operations that
match user intentions.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.database import init_database
from cosmos_workflow.services import WorkflowService
from cosmos_workflow.utils.smart_naming import generate_smart_name
from cosmos_workflow.workflows import WorkflowOrchestrator

logger = logging.getLogger(__name__)

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
    """Unified interface for all workflow operations.

    This class provides high-level operations that combine database operations
    (via WorkflowService) with GPU execution (via WorkflowOrchestrator) into
    simple, user-focused methods.
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
        self.orchestrator = WorkflowOrchestrator()

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
    ) -> dict[str, Any]:
        """Enhance an existing prompt using AI.

        Args:
            prompt_id: ID of prompt to enhance
            create_new: If True, creates new enhanced prompt. If False, updates existing.
            enhancement_model: Model to use for enhancement (default: "pixtral")

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

    # ========== Run Operations ==========

    def create_run(
        self,
        prompt_id: str,
        weights: dict[str, float] | None = None,
        num_steps: int = 35,
        guidance: float = 7.0,
        seed: int = 1,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a run for a prompt (low-level method for advanced use).

        Note: Most users should use quick_inference() or batch_inference() instead,
        which handle run creation internally. This method is for advanced workflows
        that need explicit control over run creation.

        Args:
            prompt_id: ID of the prompt to run
            weights: Control weights dict (vis, edge, depth, seg)
            num_steps: Number of inference steps
            guidance: Guidance scale (CFG)
            seed: Random seed
            **kwargs: Additional execution config parameters

        Returns:
            Dictionary containing run data with 'id' key

        Raises:
            ValueError: If prompt not found or invalid parameters
        """
        # Validate prompt exists
        prompt = self.service.get_prompt(prompt_id)
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_id}")

        # Default weights if not provided
        if weights is None:
            weights = {"vis": 0.25, "edge": 0.25, "depth": 0.25, "seg": 0.25}

        # Validate weights
        if not all(0 <= w <= 1 for w in weights.values()):
            raise ValueError("All weights must be between 0 and 1")
        if not (0.99 <= sum(weights.values()) <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {sum(weights.values())}")

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

        # Create run
        run = self.service.create_run(
            prompt_id=prompt_id,
            execution_config=execution_config,
        )

        logger.info("Created run %s for prompt %s", run["id"], prompt_id)
        return run

    def execute_run(
        self,
        run_id: str,
        upscale: bool = False,
        upscale_weight: float = 0.5,
    ) -> dict[str, Any]:
        """Execute a run on GPU (low-level method for advanced use).

        Note: Most users should use quick_inference() or batch_inference() instead,
        which handle both run creation and execution. This method is for advanced
        workflows that need explicit control over run execution.

        Args:
            run_id: ID of the run to execute
            upscale: Whether to run 4K upscaling
            upscale_weight: Weight for upscaling (0.0-1.0)

        Returns:
            Dictionary containing execution results

        Raises:
            ValueError: If run not found
            Exception: If execution fails
        """
        logger.info("Executing run %s", run_id)

        # Get run and prompt
        run = self.service.get_run(run_id)
        if not run:
            raise ValueError(f"Run not found: {run_id}")

        prompt = self.service.get_prompt(run["prompt_id"])
        if not prompt:
            raise ValueError(f"Prompt not found for run: {run['prompt_id']}")

        # Update status to running
        self.service.update_run_status(run_id, "running")

        try:
            # Execute on GPU
            result = self.orchestrator.execute_run(
                run,
                prompt,
                upscale=upscale,
                upscale_weight=upscale_weight,
            )

            # Update run with results
            self.service.update_run(run_id, outputs=result)
            self.service.update_run_status(run_id, "completed")

            logger.info("Run %s completed successfully", run_id)
            return result

        except Exception as e:
            logger.error("Run %s failed: %s", run_id, e)
            self.service.update_run_status(run_id, "failed")
            raise

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

        # Create run
        run = self.create_run(
            prompt_id=prompt["id"],
            weights=weights,
            num_steps=num_steps,
            guidance=guidance,
            **kwargs,
        )

        # Execute immediately
        result = self.execute_run(
            run_id=run["id"],
            upscale=upscale,
            upscale_weight=upscale_weight,
        )

        return {
            "prompt_id": prompt["id"],
            "run_id": run["id"],
            "output_path": result.get("output_path"),
            "duration_seconds": result.get("duration_seconds"),
            "status": "success",
        }

    def quick_inference(
        self,
        prompt_id: str,
        weights: dict[str, float] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Primary inference method - creates run internally and executes.

        This is the main method users should call for running inference on a prompt.
        It handles run creation internally, simplifying the workflow.

        Args:
            prompt_id: ID of prompt to run
            weights: Control weights
            **kwargs: Additional execution parameters (num_steps, guidance, seed, 
                     upscale, upscale_weight, etc.)

        Returns:
            Dictionary containing execution results with run_id for tracking

        Raises:
            ValueError: If prompt not found
        """
        logger.info("Quick inference for prompt %s", prompt_id)

        # Validate prompt exists
        prompt = self.service.get_prompt(prompt_id)
        if not prompt:
            raise ValueError(f"Prompt not found: {prompt_id}")

        # Extract upscale params if present (not part of execution config)
        upscale = kwargs.pop("upscale", False)
        upscale_weight = kwargs.pop("upscale_weight", 0.5)

        # Create run with remaining kwargs
        run = self.create_run(prompt_id, weights=weights, **kwargs)

        # Execute immediately with upscale params
        result = self.execute_run(run["id"], upscale=upscale, upscale_weight=upscale_weight)

        return {
            "run_id": run["id"],
            "output_path": result.get("output_path"),
            "duration_seconds": result.get("duration_seconds"),
            "status": "success",
        }

    def batch_inference(
        self,
        prompt_ids: list[str],
        shared_weights: dict[str, float] | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Batch inference on multiple prompts - creates runs internally.

        This method accepts a list of prompt IDs and creates runs internally
        for each prompt before executing them as a batch.

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

        # Create runs for all prompts
        runs_and_prompts = []
        for prompt_id in prompt_ids:
            prompt = self.service.get_prompt(prompt_id)
            if not prompt:
                logger.warning("Skipping missing prompt: %s", prompt_id)
                continue

            # Use shared_weights if provided, otherwise use defaults
            weights = shared_weights if shared_weights is not None else None
            run = self.create_run(prompt_id, weights=weights, **kwargs)
            runs_and_prompts.append((run, prompt))

        # Execute as batch
        batch_result = self.orchestrator.execute_batch_runs(runs_and_prompts)

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