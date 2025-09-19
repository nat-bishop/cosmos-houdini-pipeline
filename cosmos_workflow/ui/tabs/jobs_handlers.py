#!/usr/bin/env python3
"""Active Jobs Tab Handlers for Cosmos Workflow Manager.

This module contains the business logic for the Active Jobs tab.
"""

import logging

import gradio as gr

from cosmos_workflow.api.cosmos_api import CosmosAPI

logger = logging.getLogger(__name__)


def show_kill_confirmation():
    """Show the kill job confirmation dialog."""
    try:
        logger.debug("Showing kill confirmation dialog")
        # Check if there's actually an active job
        api = CosmosAPI()
        containers = api.get_active_containers()

        if containers and len(containers) > 0:
            container = containers[0]
            container_id = container["container_id"][:12]
            logger.info("Preparing to kill container: %s", container_id)
            preview_text = f"This will kill container: {container_id}..."
            return (
                gr.update(visible=True),  # Show confirmation dialog
                preview_text,  # Update preview text
            )
        else:
            logger.debug("No active containers found to kill")
            return (
                gr.update(visible=False),  # Keep dialog hidden
                "No active containers to kill",
            )
    except Exception as e:
        logger.error("Error showing kill confirmation: %s", e)
        return (
            gr.update(visible=False),
            f"Error: {e}",
        )


def cancel_kill_confirmation():
    """Cancel the kill job confirmation."""
    logger.debug("Kill confirmation cancelled by user")
    return gr.update(visible=False)


def execute_kill_job():
    """Execute the kill job operation and update job status in database."""
    try:
        logger.info("Executing kill job operation")
        api = CosmosAPI()

        # First get the active containers to find the run IDs
        containers = api.get_active_containers()
        run_ids = []
        if containers:
            logger.debug("Found %d active containers", len(containers))
            for container in containers:
                # Extract run ID from container name (format: cosmos_*_rs_xxxxx)
                container_name = container.get("name", "")
                if "_rs_" in container_name:
                    run_id = "rs_" + container_name.split("_rs_")[1][:32]
                    run_ids.append(run_id)
                    logger.debug("Extracted run ID: %s from container: %s", run_id, container_name)

        # Kill the containers
        result = api.kill_containers()

        if result["status"] == "success":
            # Update the database to mark ALL running jobs as cancelled
            # This ensures we don't leave any zombie jobs
            from datetime import datetime, timezone

            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker

            from cosmos_workflow.database.models import JobQueue

            database_path = "outputs/cosmos.db"
            engine = create_engine(f"sqlite:///{database_path}")
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                # Find and cancel ALL running jobs, not just those matching run IDs
                # This is safer since containers might be killed but jobs still marked as running
                running_jobs = session.query(JobQueue).filter(JobQueue.status == "running").all()

                if running_jobs:
                    for job in running_jobs:
                        job.status = "cancelled"
                        job.completed_at = datetime.now(timezone.utc)
                        job.result = {"reason": "Container killed by user"}
                        logger.info("Marked job %s as cancelled", job.id)

                    session.commit()
                    logger.info(
                        "Cancelled %d running job(s) after killing containers", len(running_jobs)
                    )

            finally:
                session.close()

            message = (
                f"Successfully killed {result['killed_count']} container(s) and updated job status"
            )
            logger.info(message)
            return (
                gr.update(visible=False),  # Hide confirmation dialog
                message,  # Status message
            )
        else:
            error_msg = f"Failed to kill containers: {result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return (
                gr.update(visible=False),
                error_msg,
            )
    except Exception as e:
        logger.error("Error killing containers: %s", e)
        return (
            gr.update(visible=False),
            f"Error: {e}",
        )
