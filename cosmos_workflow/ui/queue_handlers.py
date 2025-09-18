#!/usr/bin/env python3
"""Queue Management Handlers for Cosmos Workflow Manager.

This module contains the business logic for queue management in the UI.
"""

import logging
from typing import Any

from cosmos_workflow.services.queue_service import QueueService

logger = logging.getLogger(__name__)


class QueueHandlers:
    """Handlers for queue management operations."""

    def __init__(self, queue_service: QueueService):
        """Initialize queue handlers.

        Args:
            queue_service: QueueService instance to use
        """
        self.queue_service = queue_service

    def get_queue_display(self) -> tuple[str, list[list[Any]]]:
        """Get queue status for display.

        Returns:
            Tuple of (status_text, queue_data_for_table)
        """
        try:
            status = self.queue_service.get_queue_status()

            # Build status text
            queued_count = status["total_queued"]
            has_running = status["running"] is not None

            if has_running:
                status_text = f"📋 Queue Status: {queued_count} pending, 1 running"
            elif queued_count > 0:
                status_text = f"📋 Queue Status: {queued_count} pending"
            else:
                status_text = "📋 Queue Status: Empty"

            # Build table data
            table_data = []

            # Add running job first if exists
            if status["running"]:
                job = status["running"]
                table_data.append(
                    [
                        "🏃",  # Position/Status icon
                        job["id"],
                        job["type"],
                        "running",
                        f"{job.get('elapsed_time', 0)}s ago"
                        if job.get("elapsed_time")
                        else "just started",
                    ]
                )

            # Add queued jobs with positions
            for job in status["queued"]:
                table_data.append(
                    [
                        str(job["position"]),  # Queue position
                        job["id"],
                        job["type"],
                        "queued",
                        f"{job['prompt_count']} prompt(s)",
                    ]
                )

            return status_text, table_data

        except Exception as e:
            logger.error("Error getting queue display: %s", e)
            return f"❌ Error loading queue: {e}", []

    def cancel_job(self, job_id: str) -> str:
        """Cancel a queued job.

        Args:
            job_id: ID of job to cancel

        Returns:
            Status message
        """
        try:
            success = self.queue_service.cancel_job(job_id)
            if success:
                return f"✅ Cancelled job {job_id}"
            else:
                return f"❌ Could not cancel job {job_id} (may already be running)"
        except Exception as e:
            logger.error("Error cancelling job %s: %s", job_id, e)
            return f"❌ Error cancelling job: {e}"

    def get_job_details(self, job_id: str) -> str:
        """Get detailed information about a specific job.

        Args:
            job_id: ID of job to inspect

        Returns:
            Formatted job details
        """
        try:
            job_info = self.queue_service.get_job_status(job_id)
            if job_info.get("status") == "not_found":
                return f"Job {job_id} not found"

            # Use the returned dict directly
            # Get job type from either job_type or type field
            job_type = job_info.get("job_type") or job_info.get("type", "inference")

            details = f"""**Job ID:** {job_id}
**Type:** {job_type}
**Status:** {job_info.get("status", "unknown")}
**Priority:** {job_info.get("priority", 50)}
**Created:** {self._format_time(job_info.get("created_at"))}"""

            if job_info.get("started_at"):
                details += f"  \n**Started:** {self._format_time(job_info.get('started_at'))}"

            if job_info.get("completed_at"):
                details += f"  \n**Completed:** {self._format_time(job_info.get('completed_at'))}"

            if job_info.get("status") == "queued":
                position = self.queue_service.get_position(job_id)
                if position:
                    details += f"  \n**Queue Position:** #{position}"
                    # Estimate wait time (assuming ~2 minutes per job)
                    estimated_wait = position * 120
                    details += (
                        f"  \n**Estimated Wait:** ~{estimated_wait // 60}m {estimated_wait % 60}s"
                    )

            if job_info.get("result") and job_info.get("status") == "failed":
                error = job_info.get("result", {}).get("error", "Unknown error")
                details += f"  \n**Error:** {error}"

            return details

        except Exception as e:
            logger.error("Error getting job details for %s: %s", job_id, e)
            return f"❌ Error getting job details: {e}"

    def _format_time(self, timestamp) -> str:
        """Format timestamp for display.

        Args:
            timestamp: Datetime object or None

        Returns:
            Formatted time string
        """
        if not timestamp:
            return "—"

        try:
            # If it's a string, parse it
            from datetime import datetime

            if isinstance(timestamp, str):
                # Try parsing ISO format
                timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

            # Format as relative time if recent, otherwise absolute
            from datetime import datetime, timezone

            now = datetime.now(timezone.utc)
            if timestamp.tzinfo is None:
                # Assume UTC if no timezone
                timestamp = timestamp.replace(tzinfo=timezone.utc)

            delta = now - timestamp
            if delta.total_seconds() < 60:
                return "just now"
            elif delta.total_seconds() < 3600:
                minutes = int(delta.total_seconds() / 60)
                return f"{minutes}m ago"
            elif delta.total_seconds() < 86400:
                hours = int(delta.total_seconds() / 3600)
                return f"{hours}h ago"
            else:
                return timestamp.strftime("%Y-%m-%d %H:%M")

        except Exception:
            return str(timestamp)
