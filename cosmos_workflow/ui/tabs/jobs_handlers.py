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
        # Check if there's actually an active job
        api = CosmosAPI()
        containers = api.get_active_containers()

        if containers and len(containers) > 0:
            container = containers[0]
            preview_text = f"This will kill container: {container['container_id'][:12]}..."
            return (
                gr.update(visible=True),  # Show confirmation dialog
                preview_text,  # Update preview text
            )
        else:
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
    return gr.update(visible=False)


def execute_kill_job():
    """Execute the kill job operation and update job status in database."""
    try:
        api = CosmosAPI()

        # First get the active containers to find the run IDs
        containers = api.get_active_containers()
        run_ids = []
        if containers:
            for container in containers:
                # Extract run ID from container name (format: cosmos_*_rs_xxxxx)
                container_name = container.get("name", "")
                if "_rs_" in container_name:
                    run_id = "rs_" + container_name.split("_rs_")[1][:32]
                    run_ids.append(run_id)

        # Kill the containers
        result = api.kill_containers()

        if result["status"] == "success":
            # Update the database to mark runs as cancelled
            from cosmos_workflow.database.connection import DatabaseConnection
            from cosmos_workflow.services.queue_service import QueueService

            database_path = "outputs/cosmos.db"
            db_connection = DatabaseConnection(database_path)
            queue_service = QueueService(db_connection=db_connection)

            # Mark any running jobs as cancelled
            if run_ids:
                for run_id in run_ids:
                    # Find the job with this run_id and mark it as cancelled
                    jobs = queue_service.get_all_jobs()
                    for job in jobs:
                        if job.get("result", {}).get("run_id") == run_id:
                            queue_service.update_job_status(job["id"], "cancelled")
                            logger.info("Marked job %s as cancelled for run %s", job["id"], run_id)

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
