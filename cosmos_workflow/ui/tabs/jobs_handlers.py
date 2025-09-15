#!/usr/bin/env python3
"""Jobs & Queue Tab Handlers for Cosmos Workflow Manager.

This module contains the business logic for the Jobs & Queue tab.
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
    """Execute the kill job operation."""
    try:
        api = CosmosAPI()
        result = api.kill_containers()

        if result["status"] == "success":
            message = f"Successfully killed {result['killed_count']} container(s)"
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


def show_clear_confirmation():
    """Show the clear queue confirmation dialog."""
    try:
        # Check how many pending runs exist
        api = CosmosAPI()
        pending_runs = api.list_runs(status="pending", limit=100)

        if pending_runs and len(pending_runs) > 0:
            preview_text = f"This will cancel {len(pending_runs)} pending run(s)"
            return (
                gr.update(visible=True),  # Show confirmation dialog
                preview_text,  # Update preview text
            )
        else:
            return (
                gr.update(visible=False),  # Keep dialog hidden
                "No pending runs in queue",
            )
    except Exception as e:
        logger.error("Error showing clear confirmation: %s", e)
        return (
            gr.update(visible=False),
            f"Error: {e}",
        )


def cancel_clear_confirmation():
    """Cancel the clear queue confirmation."""
    return gr.update(visible=False)


def execute_clear_queue():
    """Execute the clear queue operation."""
    try:
        api = CosmosAPI()
        pending_runs = api.list_runs(status="pending", limit=100)

        if not pending_runs:
            return (
                gr.update(visible=False),
                "No pending runs to clear",
            )

        # Cancel each pending run by updating its status to "cancelled"
        cancelled_count = 0
        for run in pending_runs:
            try:
                # Note: We may need to add a cancel_run method to CosmosAPI
                # For now, we'll update the status directly
                run_id = run.get("id")
                if run_id:
                    # This is a simplified approach - may need proper API method
                    api.data_repo.update_run_status(run_id, "cancelled")
                    cancelled_count += 1
            except Exception as e:
                logger.error("Error cancelling run %s: %s", run.get("id"), e)

        message = f"Cancelled {cancelled_count} pending run(s)"
        logger.info(message)
        return (
            gr.update(visible=False),  # Hide confirmation dialog
            message,  # Status message
        )
    except Exception as e:
        logger.error("Error clearing queue: %s", e)
        return (
            gr.update(visible=False),
            f"Error: {e}",
        )


def get_pending_queue():
    """Get the list of pending runs for the queue table."""
    try:
        api = CosmosAPI()
        pending_runs = api.list_runs(status="pending", limit=50)

        # Format for table display
        table_data = []
        for i, run in enumerate(pending_runs, 1):
            run_id = run.get("id", "")[:8]
            prompt = run.get("prompt", {})
            prompt_name = prompt.get("parameters", {}).get("name", "Unknown")
            table_data.append(
                [
                    i,  # Position in queue
                    run_id,
                    prompt_name,
                ]
            )

        return table_data
    except Exception as e:
        logger.error("Error getting pending queue: %s", e)
        return []
