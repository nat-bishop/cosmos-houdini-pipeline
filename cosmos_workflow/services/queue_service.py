"""Queue Service for managing job queues in the Gradio UI.

THIS IS ONLY FOR THE GRADIO UI - The CLI continues to use direct CosmosAPI calls.
This service wraps CosmosAPI to add queuing capabilities for better UI experience.
"""

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import Session

from cosmos_workflow.database import DatabaseConnection, JobQueue
from cosmos_workflow.utils.logging import logger

if TYPE_CHECKING:
    from cosmos_workflow.api import CosmosAPI


class QueueService:
    """Service for managing queued jobs in the Gradio UI.

    Wraps CosmosAPI to provide queue visibility and control while maintaining
    the same synchronous execution model underneath.
    """

    def __init__(
        self,
        cosmos_api: "CosmosAPI | None" = None,
        db_session: Session | None = None,
        db_connection: DatabaseConnection | None = None,
    ):
        """Initialize QueueService.

        Args:
            cosmos_api: CosmosAPI instance to use for execution
            db_session: Database session for queue persistence
            db_connection: Database connection for session management
        """
        if cosmos_api is None:
            # Lazy import at runtime to avoid circular dependency
            from cosmos_workflow.api import CosmosAPI

            self.cosmos_api = CosmosAPI()
        else:
            self.cosmos_api = cosmos_api
        self.db_session = db_session
        self.db_connection = db_connection

        # Background processor state
        self._processor_thread = None
        self._stop_processor = threading.Event()
        self._processor_lock = threading.Lock()

        # Lock for job processing to prevent race conditions
        self._job_processing_lock = threading.Lock()

        logger.info("QueueService initialized")

    def _get_session(self) -> Session:
        """Get database session, using provided session or creating new one."""
        if self.db_session:
            return self.db_session
        elif self.db_connection:
            # Create a new session for thread safety
            # Use the existing SessionLocal from DatabaseConnection
            return self.db_connection.SessionLocal()
        else:
            # For testing with mocks
            raise RuntimeError("No database session available")

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
            priority: Job priority (higher = more important)

        Returns:
            Job ID for tracking
        """
        job_id = f"job_{uuid.uuid4().hex[:12]}"

        logger.info("Adding {} job to queue with {} prompts", job_type, len(prompt_ids))
        logger.debug("Job config: {}", config)

        job = JobQueue(
            id=job_id,
            prompt_ids=prompt_ids,
            job_type=job_type,
            status="queued",
            config=config,
            priority=priority,
        )

        session = self._get_session()
        try:
            session.add(job)
            session.commit()
            logger.info(
                "Added job {} to queue (type: {}, prompts: {})", job_id, job_type, len(prompt_ids)
            )
            return job_id
        finally:
            # Close session if it was created by us
            if self.db_connection and not self.db_session:
                session.close()

    def get_position(self, job_id: str) -> int | None:
        """Get job's position in the queue.

        Args:
            job_id: Job ID to check

        Returns:
            Position in queue (1-based), None if not queued
        """
        session = self._get_session()
        try:
            # Get all queued jobs ordered by creation time
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
        finally:
            if self.db_connection and not self.db_session:
                session.close()

    def get_queue_status(self) -> dict[str, Any]:
        """Get current queue status.

        Returns:
            Dictionary with queue information
        """
        session = self._get_session()
        try:
            # Get queued jobs
            queued_jobs = (
                session.query(JobQueue)
                .filter_by(status="queued")
                .order_by(JobQueue.created_at)
                .all()
            )

            # Get running job
            running_job = session.query(JobQueue).filter_by(status="running").first()

            # Format queue status
            status = {
                "total_queued": len(queued_jobs),
                "queued": [],
                "running": None,
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
                    # Ensure started_at has timezone info
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
        finally:
            if self.db_connection and not self.db_session:
                session.close()

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get detailed status of a specific job.

        Args:
            job_id: Job ID to check

        Returns:
            Job details including status and result
        """
        session = self._get_session()
        try:
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
        finally:
            if self.db_connection and not self.db_session:
                session.close()

    def process_next_job(self) -> dict[str, Any] | None:
        """Process the next job in the queue.

        Returns:
            Result dictionary with job_id and status
        """
        # Use lock to prevent race condition when checking and claiming jobs
        with self._job_processing_lock:
            logger.debug("Checking for next job to process")
            # CRITICAL: Check for actual running containers first
            # This ensures we don't start jobs while GPU is busy
            try:
                active_containers = self.cosmos_api.get_active_containers()
                if active_containers:
                    container_id = active_containers[0].get("container_id", "unknown")
                    logger.debug(
                        "Skipping processing - container {} is running on GPU",
                        container_id,
                    )
                    # Don't log at INFO level to avoid spam during long operations
                    return None
                logger.debug("No active containers, GPU is available")
            except Exception as e:
                logger.warning("Could not check active containers: %s", e)
                # Continue anyway - let it fail downstream if there's an issue

            session = self._get_session()
            try:
                # Force read of latest data from database
                session.expire_all()

                # Check if there's already a running job (only one at a time)
                running_job = session.query(JobQueue).filter_by(status="running").first()
                if running_job:
                    logger.debug("Skipping processing - job %s is already running", running_job.id)
                    return None

                # Get next queued job (FIFO)
                job = (
                    session.query(JobQueue)
                    .filter_by(status="queued")
                    .order_by(JobQueue.created_at)
                    .first()
                )

                if not job:
                    logger.debug("No queued jobs found")
                    return None

                logger.info("Found queued job {} (type: {})", job.id, job.job_type)

                # Mark as running with immediate commit to prevent race conditions
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)
                session.commit()
                session.flush()  # Ensure changes are written
                logger.info("Marked job {} as running", job.id)

                # Store job info for processing outside the lock
                job_id = job.id

            except Exception as e:
                if self.db_connection and not self.db_session:
                    session.close()
                raise e

            finally:
                if self.db_connection and not self.db_session:
                    session.close()

        # Now process the job outside the lock so other threads can check status
        session = self._get_session()
        try:
            logger.info(
                "Processing job {} (type: {})",
                job_id,
                job.job_type if "job" in locals() else "unknown",
            )
            job = session.query(JobQueue).filter_by(id=job_id).first()

            try:
                # Execute based on job type
                logger.debug(
                    "Executing {} job {} with config: {}", job.job_type, job_id, job.config
                )
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

                elapsed = (
                    (job.completed_at - job.started_at).total_seconds() if job.started_at else 0
                )
                logger.info("Completed job {} in {:.1f} seconds", job.id, elapsed)

                # Delete successful job immediately - run record has all the info
                session.delete(job)
                session.commit()
                logger.info("Cleaned up completed job {} from queue", job.id)

                return {
                    "job_id": job.id,
                    "status": "completed",
                    "result": result,
                }

            except Exception as e:
                # Mark as failed
                job.status = "failed"
                job.completed_at = datetime.now(timezone.utc)
                job.result = {"error": str(e)}
                session.commit()

                logger.error("Failed job {} (type: {}): {}", job.id, job.job_type, e, exc_info=True)

                # Trim old failed/cancelled jobs to keep only recent ones
                self._trim_failed_jobs(session, max_keep=50)

                return {
                    "job_id": job.id,
                    "status": "failed",
                    "error": str(e),
                }
        finally:
            if self.db_connection and not self.db_session:
                session.close()

    def _execute_inference(self, job: JobQueue) -> dict[str, Any]:
        """Execute single inference job."""
        if not job.prompt_ids:
            raise ValueError("No prompt IDs provided")

        prompt_id = job.prompt_ids[0]
        config = job.config or {}

        # Extract parameters from config
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
        """Execute batch inference job."""
        if not job.prompt_ids:
            raise ValueError("No prompt IDs provided")

        config = job.config or {}

        # Build kwargs with only the parameters provided in config
        kwargs = {
            "prompt_ids": job.prompt_ids,
            "shared_weights": config.get("weights"),
            "num_steps": config.get("num_steps", 25),
        }

        # Add optional parameters only if they're in the config
        optional_params = [
            "guidance_scale",
            "seed",
            "fps",
            "sigma_max",
            "blur_strength",
            "canny_threshold",
        ]
        for param in optional_params:
            if param in config:
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

        # Build kwargs with only the parameters provided in config
        kwargs = {
            "prompt_id": prompt_id,
        }

        # Add parameters from config, using the right key names
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

        # Build kwargs with parameters from config
        kwargs = {
            "video_source": config.get("video_source"),
        }

        # Add optional parameters
        if "control_weight" in config:
            kwargs["control_weight"] = config["control_weight"]
        if "prompt" in config:
            kwargs["prompt"] = config["prompt"]

        # Validate required parameters
        if not kwargs["video_source"]:
            raise ValueError("No video_source provided for upscale job")

        # Execute upscale
        result = self.cosmos_api.upscale(**kwargs)

        return result

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a queued job.

        Args:
            job_id: Job ID to cancel

        Returns:
            True if cancelled, False if not cancellable
        """
        logger.debug("Attempting to cancel job %s", job_id)
        session = self._get_session()
        try:
            job = session.query(JobQueue).filter_by(id=job_id).first()

            if not job:
                logger.warning("Cannot cancel job {}: not found", job_id)
                return False

            # Can only cancel queued jobs
            if job.status != "queued":
                logger.warning(
                    "Cannot cancel job {}: status is {} (not queued)", job_id, job.status
                )
                return False

            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            job.result = {"reason": "User cancelled"}
            session.commit()

            logger.info(
                "Cancelled job {} (was position {} in queue)",
                job_id,
                self.get_position(job_id) or 0,
            )

            # Trim old failed/cancelled jobs to keep only recent ones
            self._trim_failed_jobs(session, max_keep=50)

            return True
        finally:
            if self.db_connection and not self.db_session:
                session.close()

    def _trim_failed_jobs(self, session, max_keep: int = 50) -> int:
        """Trim failed and cancelled jobs to keep only the most recent ones.

        Args:
            session: Database session to use
            max_keep: Maximum number of failed/cancelled jobs to keep

        Returns:
            Number of jobs deleted
        """
        try:
            # Get IDs of jobs to keep (most recent N failed/cancelled jobs)
            keep_jobs = (
                session.query(JobQueue.id)
                .filter(JobQueue.status.in_(["failed", "cancelled"]))
                .order_by(JobQueue.created_at.desc())
                .limit(max_keep)
                .subquery()
            )

            # Delete older failed/cancelled jobs not in the keep list
            deleted_count = (
                session.query(JobQueue)
                .filter(JobQueue.status.in_(["failed", "cancelled"]), ~JobQueue.id.in_(keep_jobs))
                .delete(synchronize_session=False)
            )

            if deleted_count > 0:
                logger.info("Trimmed {} old failed/cancelled jobs", deleted_count)

            return deleted_count
        except Exception as e:
            logger.error("Error trimming failed jobs: %s", e)
            return 0

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
        # In production, this would use historical data
        avg_job_time = 120
        return position * avg_job_time

    def start_background_processor(self) -> None:
        """Start background thread to process queue."""
        with self._processor_lock:
            if self._processor_thread and self._processor_thread.is_alive():
                logger.warning(
                    "Background processor already running (thread: {})", self._processor_thread.name
                )
                return

            self._stop_processor.clear()
            self._processor_thread = threading.Thread(
                target=self._process_queue_loop,
                daemon=True,
                name="QueueProcessor",
            )
            self._processor_thread.start()
            logger.info("Started background processor thread: {}", self._processor_thread.name)

    def stop_background_processor(self) -> None:
        """Stop background processor thread."""
        with self._processor_lock:
            if not self._processor_thread:
                logger.debug("Background processor not running, nothing to stop")
                return

            logger.info("Stopping background processor thread: {}", self._processor_thread.name)
            self._stop_processor.set()
            if self._processor_thread.is_alive():
                self._processor_thread.join(timeout=5)
                if self._processor_thread.is_alive():
                    logger.warning("Background processor thread did not stop within 5 seconds")
                else:
                    logger.info("Background processor thread stopped successfully")

            self._processor_thread = None

    def is_processor_running(self) -> bool:
        """Check if background processor is running.

        Returns:
            True if processor is running
        """
        with self._processor_lock:
            return (
                self._processor_thread is not None
                and self._processor_thread.is_alive()
                and not self._stop_processor.is_set()
            )

    def _process_queue_loop(self) -> None:
        """Background loop to process queued jobs."""
        logger.info("Background processor loop started")
        idle_cycles = 0

        while not self._stop_processor.is_set():
            try:
                # Process next job
                result = self.process_next_job()

                if result:
                    logger.info(
                        "Processed job: {} with status {}", result["job_id"], result["status"]
                    )
                    idle_cycles = 0
                else:
                    # No jobs, sleep briefly
                    idle_cycles += 1
                    if idle_cycles % 30 == 1:  # Log every ~60 seconds of idle time
                        logger.debug("Queue processor idle (no jobs or GPU busy)")
                    time.sleep(2)

            except Exception as e:
                logger.error("Error in background processor: {}", e, exc_info=True)
                time.sleep(5)  # Back off on error

        logger.info("Background processor loop stopped")
