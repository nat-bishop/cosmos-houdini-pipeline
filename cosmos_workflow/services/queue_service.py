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
            logger.info("Added job %s to queue", job_id)
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
                    elapsed = (datetime.now(timezone.utc) - running_job.started_at).seconds

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
        session = self._get_session()
        try:
            # Get next queued job (FIFO)
            job = (
                session.query(JobQueue)
                .filter_by(status="queued")
                .order_by(JobQueue.created_at)
                .first()
            )

            if not job:
                return None

            # Mark as running
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            session.commit()

            logger.info("Processing job %s", job.id)

            try:
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

                logger.info("Completed job %s", job.id)

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

                logger.error("Failed job %s: %s", job.id, e)

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
        session = self._get_session()
        try:
            job = session.query(JobQueue).filter_by(id=job_id).first()

            if not job:
                return False

            # Can only cancel queued jobs
            if job.status != "queued":
                return False

            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            job.result = {"reason": "User cancelled"}
            session.commit()

            logger.info("Cancelled job %s", job_id)
            return True
        finally:
            if self.db_connection and not self.db_session:
                session.close()

    def clear_completed_jobs(self) -> int:
        """Clear completed jobs from the queue.

        Returns:
            Number of jobs cleared
        """
        session = self._get_session()
        try:
            # Delete completed and cancelled jobs
            count = (
                session.query(JobQueue)
                .filter(JobQueue.status.in_(["completed", "cancelled", "failed"]))
                .delete(synchronize_session=False)
            )

            session.commit()

            logger.info("Cleared %d completed jobs", count)
            return count
        finally:
            if self.db_connection and not self.db_session:
                session.close()

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
                logger.warning("Background processor already running")
                return

            self._stop_processor.clear()
            self._processor_thread = threading.Thread(
                target=self._process_queue_loop,
                daemon=True,
            )
            self._processor_thread.start()
            logger.info("Started background processor")

    def stop_background_processor(self) -> None:
        """Stop background processor thread."""
        with self._processor_lock:
            if not self._processor_thread:
                return

            self._stop_processor.set()
            if self._processor_thread.is_alive():
                self._processor_thread.join(timeout=5)

            self._processor_thread = None
            logger.info("Stopped background processor")

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

        while not self._stop_processor.is_set():
            try:
                # Process next job
                result = self.process_next_job()

                if result:
                    logger.info("Processed job: %s", result["job_id"])
                else:
                    # No jobs, sleep briefly
                    time.sleep(2)

            except Exception as e:
                logger.error("Error in background processor: %s", e, exc_info=True)
                time.sleep(5)  # Back off on error

        logger.info("Background processor loop stopped")
