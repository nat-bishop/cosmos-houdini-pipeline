"""Simplified Queue Service for managing job queues in the Gradio UI.

This is the recommended replacement for the legacy QueueService, using database
transactions for atomicity instead of application-level locks. It eliminates
race conditions by design and reduces complexity from ~680 lines to ~400 lines.

Key improvements over legacy QueueService:
- No threading complexity or background threads
- Database-level concurrency control using SELECT ... FOR UPDATE SKIP LOCKED
- Single warm container strategy preventing accumulation
- Fresh database sessions preventing stale data
- Simple, linear execution flow
- Timer-based processing using Gradio Timer component
- More reliable and easier to debug
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from cosmos_workflow.database import DatabaseConnection, JobQueue
from cosmos_workflow.utils.logging import logger

if TYPE_CHECKING:
    from cosmos_workflow.api import CosmosAPI


class SimplifiedQueueService:
    """Simplified database-backed queue service.

    Uses database transactions for atomic job claiming instead of
    application-level locks. Designed to work with Gradio's built-in
    background processing or timer-based auto-processing.
    """

    def __init__(
        self,
        cosmos_api: "CosmosAPI | None" = None,
        db_connection: DatabaseConnection | None = None,
    ):
        """Initialize SimplifiedQueueService.

        Args:
            cosmos_api: CosmosAPI instance for job execution
            db_connection: Database connection for queue persistence
        """
        if cosmos_api is None:
            # Lazy import to avoid circular dependency
            from cosmos_workflow.api import CosmosAPI

            self.cosmos_api = CosmosAPI()
        else:
            self.cosmos_api = cosmos_api

        self.db_connection = db_connection
        self._warm_container = None
        self.batch_size = 4  # Default batch size for GPU processing
        self.queue_paused = False  # Control flag for queue processing

        # Smart batching state
        self._smart_batch_analysis = None
        self._analysis_queue_size = 0

        # Clean up any orphaned jobs from previous session
        self._cleanup_orphaned_jobs()

        logger.info("SimplifiedQueueService initialized")

    def set_batch_size(self, size: int) -> None:
        """Update the batch size for GPU processing.

        Args:
            size: Batch size (number of videos to process simultaneously)
        """
        if size < 1:
            raise ValueError("Batch size must be at least 1")
        if size > 16:
            logger.warning("Batch size {} may exceed GPU memory limits", size)

        old_size = self.batch_size
        self.batch_size = size
        logger.info("Updated batch size from {} to {}", old_size, size)

    def set_queue_paused(self, paused: bool) -> None:
        """Pause or resume queue processing.

        When paused, no new jobs will be claimed from the queue.
        Currently running jobs will continue to completion.

        Args:
            paused: True to pause queue, False to resume
        """
        self.queue_paused = paused
        logger.info("Queue processing {}", "paused" if paused else "resumed")

    def is_queue_paused(self) -> bool:
        """Check if queue processing is paused.

        Returns:
            True if queue is paused, False otherwise
        """
        return self.queue_paused

    def claim_next_job(self) -> str | None:
        """Atomically claim the next job in the queue.

        Uses database-level locking (SELECT ... FOR UPDATE) to ensure
        only one process can claim a job at a time.

        Returns:
            Job ID if a job was claimed, None if queue is empty or paused
        """
        # Check if queue is paused
        if self.queue_paused:
            logger.debug("Queue is paused, not claiming new jobs")
            return None

        with self.db_connection.get_session() as session:
            # Force fresh read from database
            session.expire_all()

            # Atomically claim next job using database lock
            # skip_locked=True means if another process has locked a row,
            # we skip it instead of waiting (prevents deadlock)
            job = (
                session.query(JobQueue)
                .filter_by(status="queued")
                .order_by(JobQueue.created_at)
                .with_for_update(skip_locked=True)
                .first()
            )

            if job:
                # Check if GPU is actually available
                try:
                    active_containers = self.cosmos_api.get_active_containers()
                    if active_containers:
                        container_id = active_containers[0].get("container_id", "unknown")
                        logger.debug(
                            "Skipping job claim - container {} is running on GPU",
                            container_id,
                        )
                        return None
                except Exception as e:
                    logger.warning("Could not check active containers: {}", e)
                    # Continue anyway - let it fail downstream if there's an issue

                # Mark as running
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)
                session.commit()

                logger.info("Claimed job {} (type: {})", job.id, job.job_type)
                return job.id

            return None

    def process_next_job(self) -> dict[str, Any] | None:
        """Process the next job in the queue.

        This is the main entry point called by Gradio timer or button.
        Claims a job atomically and executes it.

        Returns:
            Result dictionary with status and details, or None if no jobs
        """
        job_id = self.claim_next_job()
        if job_id:
            return self.execute_job(job_id)
        return None

    def ensure_container(self) -> str | None:
        """Ensure a warm container is available for job execution.

        This simplified version just checks if a container is running.
        The actual container management is handled by CosmosAPI methods.

        Returns:
            Container ID if available, None if no container
        """
        try:
            # Just check if a container is running
            containers = self.cosmos_api.get_active_containers()
            if containers:
                container_id = containers[0].get("container_id", "unknown")
                logger.debug("Found active container {}", container_id)
                return container_id
            else:
                logger.debug("No active containers")
                return None

        except Exception as e:
            logger.error("Failed to check container status: {}", e)
            return None

    def execute_job(self, job_id: str) -> dict[str, Any]:
        """Execute a specific job.

        Args:
            job_id: Job ID to execute

        Returns:
            Dictionary with job execution status and results
        """
        with self.db_connection.get_session() as session:
            job = session.query(JobQueue).filter_by(id=job_id).first()

            if not job:
                logger.warning("Job {} not found", job_id)
                return {"status": "not_found", "job_id": job_id}

            try:
                logger.info("Executing {} job {}", job.job_type, job_id)

                # Execute based on job type
                if job.job_type == "inference":
                    result = self._execute_inference(job)
                elif job.job_type == "batch_inference":
                    result = self._execute_batch_inference(job)
                elif job.job_type == "enhancement":
                    result = self._execute_enhancement(job)
                elif job.job_type == "upscale":
                    result = self._execute_upscale(job)
                else:
                    raise ValueError(f"Unknown job type: {job.job_type}")

                # Mark as completed
                job.status = "completed"
                job.completed_at = datetime.now(timezone.utc)
                job.result = result
                session.commit()

                # Calculate elapsed time
                elapsed = (
                    (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
                )
                logger.info("Completed job {} in {:.1f} seconds", job.id, elapsed)

                # Delete completed job (run record has all details)
                session.delete(job)
                session.commit()

                return {
                    "job_id": job.id,
                    "status": "completed",
                    "result": result,
                    "elapsed_seconds": elapsed,
                }

            except Exception as e:
                # Mark as failed
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.result = {"error": str(e)}
                session.commit()

                logger.error("Failed job {} (type: {}): {}", job.id, job.job_type, e, exc_info=True)

                return {
                    "job_id": job.id,
                    "status": "failed",
                    "error": str(e),
                }

    # Job execution methods (copied from QueueService with minimal changes)

    def _execute_inference(self, job: JobQueue) -> dict[str, Any]:
        """Execute single inference job."""
        if not job.prompt_ids:
            raise ValueError("No prompt IDs provided")

        prompt_id = job.prompt_ids[0]
        config = job.config or {}

        # Execute inference
        result = self.cosmos_api.quick_inference(
            prompt_id=prompt_id,
            weights=config.get("weights"),
            stream_output=False,
            num_steps=config.get("num_steps", 25),
            guidance_scale=config.get("guidance_scale", 4.0),
            seed=config.get("seed", 42),
            fps=config.get("fps", 8),
            sigma_max=config.get("sigma_max", 1000.0),
            blur_strength=config.get("blur_strength", 0.5),
            canny_threshold=config.get("canny_threshold", 0.1),
        )

        return result

    def _execute_batch_inference(self, job: JobQueue) -> dict[str, Any]:
        """Execute batch inference job with support for weights_list."""
        if not job.prompt_ids:
            raise ValueError("No prompt IDs provided")

        config = job.config or {}

        # Handle both new weights_list and legacy shared weights formats
        if "weights_list" in config:
            # New format: individual weights per prompt
            weights_list = config["weights_list"]
            logger.debug("Executing batch with %d different weight configs", len(weights_list))
        elif "weights" in config:
            # Legacy format: same weights for all prompts
            weights_list = [config["weights"]] * len(job.prompt_ids)
            logger.debug("Legacy batch: using same weights for %d prompts", len(job.prompt_ids))
        else:
            # No weights specified - create empty dicts
            weights_list = [{}] * len(job.prompt_ids)
            logger.warning("No weights specified for batch inference job %s", job.id)

        # Build kwargs with weights_list
        kwargs = {
            "prompt_ids": job.prompt_ids,
            "weights_list": weights_list,
            "num_steps": config.get("num_steps", 25),
            "batch_size": self.batch_size,
        }

        # Add optional parameters with proper mapping
        # Map guidance_scale from UI to guidance for API
        if "guidance_scale" in config:
            kwargs["guidance"] = config["guidance_scale"]

        # Add other optional parameters (these must be the same for all prompts)
        optional_params = [
            "seed",
            "fps",
            "sigma_max",
            "blur_strength",
            "canny_threshold",
        ]
        for param in optional_params:
            if param in config and param not in ["weights", "weights_list"]:
                kwargs[param] = config[param]

        # Execute batch
        result = self.cosmos_api.batch_inference(**kwargs)
        return result

    def _execute_enhancement(self, job: JobQueue) -> dict[str, Any]:
        """Execute enhancement job."""
        if not job.prompt_ids:
            raise ValueError("No prompt IDs provided")

        prompt_id = job.prompt_ids[0]
        config = job.config or {}

        # Build kwargs
        kwargs = {"prompt_id": prompt_id}

        if "create_new" in config:
            kwargs["create_new"] = config["create_new"]
        if "model" in config:
            kwargs["enhancement_model"] = config["model"]
        if "force_overwrite" in config:
            kwargs["force_overwrite"] = config["force_overwrite"]

        # Execute enhancement
        result = self.cosmos_api.enhance_prompt(**kwargs)
        return result

    def _execute_upscale(self, job: JobQueue) -> dict[str, Any]:
        """Execute upscale job."""
        config = job.config or {}

        # Map video_source to run_id for backward compatibility
        run_id = config.get("run_id") or config.get("video_source")

        # Build kwargs with correct parameter name
        kwargs = {"run_id": run_id}

        if "control_weight" in config:
            kwargs["control_weight"] = config["control_weight"]
        if "prompt" in config:
            kwargs["prompt"] = config["prompt"]

        # Validate
        if not run_id:
            raise ValueError("No run_id provided for upscale job")

        # Execute upscale
        result = self.cosmos_api.upscale(**kwargs)
        return result

    # Public API methods for UI (keep same interface as QueueService)

    def add_job(
        self,
        prompt_ids: list[str],
        job_type: str,
        config: dict[str, Any],
        priority: int = 50,
    ) -> str:
        """Add a job to the queue.

        Args:
            prompt_ids: List of prompt IDs to process
            job_type: Type of job (inference, batch_inference, enhancement)
            config: Job configuration parameters
            priority: Job priority (not used in simplified version)

        Returns:
            Job ID for tracking
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"

        logger.info("Adding {} job to queue with {} prompts", job_type, len(prompt_ids))

        job = JobQueue(
            id=job_id,
            prompt_ids=prompt_ids,
            job_type=job_type,
            status="queued",
            config=config,
            priority=priority,
        )

        with self.db_connection.get_session() as session:
            session.add(job)
            session.commit()
            logger.info("Added job {} to queue", job_id)

        return job_id

    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status.

        Returns:
            Dictionary with queue information
        """
        with self.db_connection.get_session() as session:
            # Force fresh read
            session.expire_all()

            # Get queued jobs
            queued_jobs = (
                session.query(JobQueue)
                .filter_by(status="queued")
                .order_by(JobQueue.created_at)
                .all()
            )

            # Get running job
            running_job = session.query(JobQueue).filter_by(status="running").first()

            # Format status
            status = {
                "total_queued": len(queued_jobs),
                "queued": [],
                "running": None,
                "paused": self.queue_paused,  # Include pause state
            }

            # Add queued job details
            for i, job in enumerate(queued_jobs, 1):
                status["queued"].append(
                    {
                        "id": job.id,
                        "position": i,
                        "type": job.job_type,
                        "prompt_count": len(job.prompt_ids),
                    }
                )

            # Add running job details
            if running_job:
                elapsed = None
                if running_job.started_at:
                    started_at = running_job.started_at
                    if started_at.tzinfo is None:
                        started_at = started_at.replace(tzinfo=timezone.utc)
                    elapsed = (datetime.now(timezone.utc) - started_at).seconds

                status["running"] = {
                    "id": running_job.id,
                    "type": running_job.job_type,
                    "prompt_count": len(running_job.prompt_ids),
                    "elapsed_time": elapsed,
                }

            return status

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get detailed status of a specific job.

        Args:
            job_id: Job ID to check

        Returns:
            Job details including status and result
        """
        with self.db_connection.get_session() as session:
            job = session.query(JobQueue).filter_by(id=job_id).first()

            if not job:
                return {"status": "not_found"}

            return {
                "id": job.id,
                "status": job.status,
                "type": job.job_type,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "result": job.result,
            }

    def get_position(self, job_id: str) -> int | None:
        """Get job's position in the queue.

        Args:
            job_id: Job ID to check

        Returns:
            Position in queue (1-based), None if not queued
        """
        with self.db_connection.get_session() as session:
            queued_jobs = (
                session.query(JobQueue)
                .filter_by(status="queued")
                .order_by(JobQueue.created_at)
                .all()
            )

            for i, job in enumerate(queued_jobs, 1):
                if job.id == job_id:
                    return i

            return None

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False if not cancellable
        """
        with self.db_connection.get_session() as session:
            job = session.query(JobQueue).filter_by(id=job_id).first()

            if not job:
                logger.warning("Cannot cancel job {}: not found", job_id)
                return False

            # Can only cancel queued jobs
            if job.status != "queued":
                logger.warning("Cannot cancel job {}: status is {}", job_id, job.status)
                return False

            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            job.result = {"reason": "User cancelled"}
            session.commit()

            logger.info("Cancelled job {}", job_id)
            return True

    def get_estimated_wait_time(self, job_id: str) -> int | None:
        """Estimate wait time for a job in seconds.

        Args:
            job_id: Job ID to estimate

        Returns:
            Estimated wait time in seconds, None if not queued
        """
        position = self.get_position(job_id)
        if not position:
            return None

        # Simple estimate: 120 seconds per job
        avg_job_time = 120
        return position * avg_job_time

    def _cleanup_orphaned_jobs(self) -> None:
        """Mark jobs that were running when app closed as failed.

        This runs on startup to clean up any jobs that were interrupted
        by application restart, crash, or unexpected shutdown.
        """
        if not self.db_connection:
            logger.debug("No database connection available for cleanup")
            return

        # First, clean up orphaned JobQueue entries
        self._cleanup_orphaned_job_queue()

        # Second, clean up orphaned Run records that may not have associated jobs
        self._cleanup_orphaned_runs()

    def _cleanup_orphaned_job_queue(self) -> None:
        """Clean up JobQueue entries stuck in running state."""
        with self.db_connection.get_session() as session:
            # Find jobs that were left in running state
            orphaned_jobs = session.query(JobQueue).filter_by(status="running").all()

            if not orphaned_jobs:
                logger.debug("No orphaned jobs found on startup")
                return

            logger.info("Found {} orphaned job(s) from previous session", len(orphaned_jobs))

            for job in orphaned_jobs:
                # Mark job as failed
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.result = {"error": "Job interrupted by application restart"}

                logger.info("Marking orphaned job {} (type: {}) as failed", job.id, job.job_type)

                # Also mark associated runs as failed
                # This ensures the Run records match the job status
                for prompt_id in job.prompt_ids:
                    try:
                        # Get runs for this prompt
                        runs = self.cosmos_api.service.list_runs(prompt_id=prompt_id)

                        for run in runs:
                            # Only update runs that were in progress
                            if run.get("status") in ["pending", "running", "uploading"]:
                                run_id = run.get("id")
                                logger.info(
                                    "Marking orphaned run {} (status: {}) as failed",
                                    run_id,
                                    run.get("status"),
                                )

                                # Use update_run to set error message
                                # This automatically sets status to failed and completed_at
                                self.cosmos_api.service.update_run(
                                    run_id, error_message="Job interrupted by application restart"
                                )
                    except Exception as e:
                        logger.error("Error updating runs for prompt {}: {}", prompt_id, e)
                        # Continue with other prompts even if one fails

            session.commit()
            logger.info("Cleaned up {} orphaned job(s) on startup", len(orphaned_jobs))

    def _cleanup_orphaned_runs(self) -> None:
        """Clean up Run records stuck in pending/running/uploading state.

        This handles runs that may not have associated JobQueue entries,
        such as runs created via CLI or runs whose jobs were already deleted.
        """
        try:
            from datetime import datetime, timedelta, timezone

            # Get all runs that are stuck in incomplete states
            # We'll check if they're older than 10 minutes (reasonable timeout)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)

            orphaned_runs = self.cosmos_api.service.list_runs(limit=1000)
            cleanup_count = 0

            for run in orphaned_runs:
                # Check if run is stuck in an incomplete state
                if run.get("status") in ["pending", "running", "uploading"]:
                    # Check if it's old enough to be considered orphaned
                    created_at = run.get("created_at")
                    if created_at:
                        # Parse the timestamp
                        if isinstance(created_at, str):
                            # Handle ISO format timestamps
                            created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        else:
                            created_dt = created_at

                        # Ensure timezone awareness
                        if created_dt.tzinfo is None:
                            created_dt = created_dt.replace(tzinfo=timezone.utc)

                        # If older than cutoff, mark as failed
                        if created_dt < cutoff_time:
                            run_id = run.get("id")
                            logger.info(
                                "Marking orphaned run {} (status: {}, age: {}) as failed",
                                run_id,
                                run.get("status"),
                                datetime.now(timezone.utc) - created_dt,
                            )

                            # Use update_run to set error message
                            self.cosmos_api.service.update_run(
                                run_id, error_message="Run orphaned - no active job or container"
                            )
                            cleanup_count += 1

            if cleanup_count > 0:
                logger.info("Cleaned up {} orphaned run(s) on startup", cleanup_count)
            else:
                logger.debug("No orphaned runs found on startup")

        except Exception as e:
            logger.error("Error cleaning up orphaned runs: {}", e)
            # Don't fail startup if run cleanup fails

    # Smart Batching Methods

    def analyze_queue_for_smart_batching(self, mix_controls: bool = False) -> dict[str, Any] | None:
        """Analyze queued jobs for batching opportunities.

        Args:
            mix_controls: If True, use mixed mode (master batch approach).
                         If False, use strict mode (identical controls only).

        Returns:
            Analysis dictionary with batches and efficiency metrics, or None if empty
        """
        from cosmos_workflow.utils.smart_batching import (
            calculate_batch_efficiency,
            filter_batchable_jobs,
            group_runs_mixed,
            group_runs_strict,
        )

        with self.db_connection.get_session() as session:
            # Get all queued jobs
            queued_jobs = (
                session.query(JobQueue)
                .filter_by(status="queued")
                .order_by(JobQueue.created_at)
                .all()
            )

            # Filter to only batchable jobs
            batchable_jobs = filter_batchable_jobs(queued_jobs)

            if not batchable_jobs:
                self._smart_batch_analysis = None
                self._analysis_queue_size = 0
                return None

            # Use user's batch size directly - trust their GPU capacity
            logger.debug("Using batch size: %d", self.batch_size)

            # Group runs based on mode
            if mix_controls:
                batches = group_runs_mixed(batchable_jobs, self.batch_size)
                mode = "mixed"
                mode_desc = "Mixed (allows different controls, may run slower)"
            else:
                batches = group_runs_strict(batchable_jobs, self.batch_size)
                mode = "strict"
                mode_desc = "Strict (identical controls only, faster execution)"

            # Calculate efficiency metrics
            efficiency = calculate_batch_efficiency(batches, batchable_jobs, mode)

            # Create human-readable preview
            total_runs = efficiency["total_runs"]
            total_batches = efficiency["total_batches"]
            speedup = efficiency["speedup"]

            preview_lines = [
                f"⚡ Smart Batching Analysis ({mode.capitalize()} Mode):",
                "- {} runs from {} jobs → {} batches".format(
                    total_runs, efficiency["original_jobs"], total_batches
                ),
                f"- Estimated speedup: {speedup:.1f}x",
                f"- Mode: {mode_desc}",
                f"- Batch size: {self.batch_size} runs/batch",
            ]

            if mix_controls and total_batches > 0:
                preview_lines.append(
                    "⚠️ Mixed mode may run slower per batch but needs fewer batches"
                )

            if batches:
                preview_lines.append("\nBatch breakdown:")
                for i, batch in enumerate(batches, 1):
                    num_runs = len(batch["prompt_ids"])
                    num_source_jobs = len(batch["source_job_ids"])

                    # Get control types from weights_list
                    control_types = set()
                    for weights in batch["config"].get("weights_list", []):
                        control_types.update(weights.keys())

                    controls_desc = (
                        ", ".join(sorted(control_types)) if control_types else "no controls"
                    )

                    preview_lines.append(
                        f"  Batch {i}: {num_runs} runs from {num_source_jobs} jobs ({controls_desc})"
                    )

            preview = "\n".join(preview_lines)

            # Store analysis for later execution
            analysis = {
                "batches": batches,
                "efficiency": efficiency,
                "preview": preview,
                "mode": mode,
            }

            logger.info(
                "Smart batch analysis complete: %d batches from %d jobs (%s mode)",
                len(batches),
                len(batchable_jobs),
                mode,
            )

            self._smart_batch_analysis = analysis
            self._analysis_queue_size = len(queued_jobs)

            return analysis

    def execute_smart_batches(self) -> dict[str, Any]:
        """Reorganize the queue based on smart batch analysis (does NOT execute jobs).

        This method creates new optimized JobQueue entries and deletes the originals.
        The queue remains paused and jobs remain in 'queued' status.

        Returns:
            Results dictionary with reorganization metrics
        """
        # Check if analysis exists
        if not self._smart_batch_analysis:
            logger.error("No smart batch analysis available for execution")
            return {"error": "No analysis available. Run analyze_queue_for_smart_batching first."}

        # Check if queue has changed (simple size check)
        with self.db_connection.get_session() as session:
            current_queue_size = session.query(JobQueue).filter_by(status="queued").count()

            if current_queue_size != self._analysis_queue_size:
                logger.warning(
                    "Queue has changed since analysis: was %d, now %d",
                    self._analysis_queue_size,
                    current_queue_size,
                )
                return {"error": "Analysis is stale - queue has changed. Please re-analyze."}

        # Get batches and mode from analysis
        batches = self._smart_batch_analysis["batches"]
        mode = self._smart_batch_analysis.get("mode", "unknown")

        logger.info("Starting queue reorganization: %d batches in %s mode", len(batches), mode)

        with self.db_connection.get_session() as session:
            all_source_job_ids = set()
            created_job_ids = []

            # Create new optimized jobs
            for _i, batch in enumerate(batches):
                all_source_job_ids.update(batch["source_job_ids"])

                # Generate new job ID
                job_id = f"job_opt_{uuid4().hex[:8]}"

                # Create new JobQueue entry with reorganized runs
                new_job = JobQueue(
                    id=job_id,
                    prompt_ids=batch["prompt_ids"],
                    job_type="batch_inference",
                    status="queued",  # Keep as queued!
                    config=batch["config"],  # Contains weights_list
                    created_at=datetime.now(timezone.utc),
                )
                session.add(new_job)
                created_job_ids.append(job_id)

                logger.info(
                    "Created %s batch job %s: %d runs from %d original jobs",
                    mode,
                    job_id,
                    len(batch["prompt_ids"]),
                    len(batch["source_job_ids"]),
                )

            # Delete original jobs
            deleted_count = 0
            for job_id in all_source_job_ids:
                result = session.query(JobQueue).filter_by(id=job_id).delete()
                if result:
                    deleted_count += 1
                    logger.debug("Deleted original job %s", job_id)

            # Commit all changes atomically
            session.commit()

            logger.info(
                "Queue reorganization complete: %d jobs deleted, %d batches created",
                deleted_count,
                len(created_job_ids),
            )

        # Capture speedup before clearing analysis
        speedup = self._smart_batch_analysis["efficiency"].get("speedup", 1.0)

        # Clear analysis after successful reorganization
        self._smart_batch_analysis = None
        self._analysis_queue_size = 0

        return {
            "jobs_deleted": len(all_source_job_ids),
            "batches_created": len(created_job_ids),
            "speedup": speedup,
            "mode": mode,
            "message": f"Queue reorganized successfully. {len(all_source_job_ids)} jobs → {len(created_job_ids)} batches",
        }

    def get_smart_batch_preview(self) -> str:
        """Get human-readable preview of stored analysis.

        Returns:
            Preview string, or empty string if no analysis or stale
        """
        if not self._smart_batch_analysis:
            return ""

        # Check if analysis is still valid
        with self.db_connection.get_session() as session:
            current_queue_size = session.query(JobQueue).filter_by(status="queued").count()

            if current_queue_size != self._analysis_queue_size:
                return ""

        return self._smart_batch_analysis.get("preview", "")
