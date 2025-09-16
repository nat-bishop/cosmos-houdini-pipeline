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
