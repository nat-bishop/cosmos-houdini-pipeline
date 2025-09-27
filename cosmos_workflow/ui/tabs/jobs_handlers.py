#!/usr/bin/env python3
"""Active Jobs Tab Handlers for Cosmos Workflow Manager.

This module contains the business logic for the Active Jobs tab.
"""

import logging

import gradio as gr

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.ui.log_viewer import LogViewer

logger = logging.getLogger(__name__)

# Initialize log viewer instance
log_viewer = LogViewer(max_lines=2000)


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

                        # Update Run records for cancelled jobs
                        for prompt_id in job.prompt_ids:
                            try:
                                runs = api.service.list_runs(prompt_id=prompt_id, limit=10)
                                for run in runs:
                                    if run.get("status") in ["pending", "running", "uploading"]:
                                        api.service.update_run(
                                            run["id"],
                                            error_message="Container killed by user"
                                        )
                                        logger.info("Updated run %s to failed status", run["id"])
                            except Exception as e:
                                logger.error("Failed to update runs for prompt %s: %s", prompt_id, e)

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


def start_log_streaming(auto_start=False):
    """Generator that streams logs to the UI.

    Args:
        auto_start: If True, don't clear logs (useful for auto-start on tab switch)
    """
    if not auto_start:
        log_viewer.clear()

    try:
        ops = CosmosAPI()
        containers = ops.get_active_containers()

        if not containers:
            yield "No active containers found", log_viewer.get_text()
            return

        if len(containers) > 1:
            container_id = containers[0]["container_id"]
            message = f"Multiple containers found, streaming from {container_id}"
        else:
            container_id = containers[0]["container_id"]
            message = f"Streaming logs from container {container_id}"

        yield message, log_viewer.get_text()

        try:
            for log_line in ops.stream_logs_generator(container_id):
                log_viewer.add_from_stream(log_line)
                yield message, log_viewer.get_text()
        except KeyboardInterrupt:
            yield "Streaming stopped", log_viewer.get_text()

    except RuntimeError as e:
        yield f"Error: {e}", log_viewer.get_text()
    except Exception as e:
        yield f"Failed to start streaming: {e}", log_viewer.get_text()


def refresh_jobs_on_tab_select(tab_idx):
    """Refresh jobs status when switching to jobs tab."""
    if tab_idx == 3:
        # Refresh the jobs status
        jobs_result = check_running_jobs()
        return jobs_result[0], jobs_result[1], jobs_result[2], log_viewer.get_text()
    else:
        # No update for other tabs
        return gr.update(), gr.update(), gr.update(), gr.update()


def refresh_and_stream():
    """Refresh jobs status and start streaming if container is active."""
    # First refresh the jobs status
    jobs_result = check_running_jobs()

    # Check if there's an active container
    if "Ready to stream" in jobs_result[1]:
        # Start streaming automatically
        for status, logs in start_log_streaming(auto_start=True):
            yield jobs_result[0], status, jobs_result[2], logs
    else:
        # Just return the refreshed status without streaming
        yield jobs_result[0], jobs_result[1], jobs_result[2], log_viewer.get_text()


def check_running_jobs():
    """Check for active containers and system status on remote instance."""
    try:
        ops = CosmosAPI()
        # Get comprehensive status like CLI does
        status_info = ops.check_status()

        # Build container details display
        container_details_text = ""

        # SSH Status
        if status_info.get("ssh_status") == "connected":
            container_details_text += "SSH Connection     ✓ Connected\n"
        else:
            container_details_text += "SSH Connection     ✗ Failed\n"

        # Docker status
        docker_info = status_info.get("docker_status", {})
        if isinstance(docker_info, dict) and docker_info.get("docker_running"):
            container_details_text += "Docker Daemon      ✓ Running\n"
        else:
            container_details_text += "Docker Daemon      ✗ Not running\n"

        # GPU information
        gpu_info = status_info.get("gpu_info", {})
        if gpu_info:
            gpu_name = gpu_info.get("name", "Unknown")
            gpu_memory = gpu_info.get("memory_total", "Unknown")
            container_details_text += f"GPU                {gpu_name} ({gpu_memory})\n"
            container_details_text += (
                f"CUDA Version       {gpu_info.get('cuda_version', 'Unknown')}\n"
            )

            # Add GPU utilization metrics
            gpu_util = gpu_info.get("gpu_utilization")
            if gpu_util:
                container_details_text += f"GPU Usage          {gpu_util}\n"

            # Add memory usage details with actual percentage
            mem_used = gpu_info.get("memory_used")
            mem_total = gpu_info.get("memory_total")
            mem_percentage = gpu_info.get("memory_percentage", "0%")
            if mem_used and mem_total:
                container_details_text += (
                    f"Memory Usage       {mem_used} / {mem_total} ({mem_percentage})\n"
                )

            # Add temperature if available
            temperature = gpu_info.get("temperature")
            if temperature and temperature != "N/A":
                container_details_text += f"Temperature        {temperature}\n"

            # Add power metrics if available
            power_draw = gpu_info.get("power_draw")
            power_limit = gpu_info.get("power_limit")
            if power_draw and power_draw != "N/A" and power_limit and power_limit != "N/A":
                container_details_text += f"Power              {power_draw} / {power_limit}\n"

            # Add clock speeds if available
            clock_current = gpu_info.get("clock_current")
            clock_max = gpu_info.get("clock_max")
            if clock_current and clock_current != "N/A" and clock_max and clock_max != "N/A":
                container_details_text += f"Clock Speed        {clock_current} / {clock_max}\n"
        else:
            container_details_text += "GPU                Not detected\n"

        # Active run information
        active_run = status_info.get("active_run")
        active_job_display = ""

        if active_run:
            container_details_text += f"Active Operation   {active_run['model_type'].upper()}\n"
            container_details_text += f"  Run ID           {active_run['id']}\n"
            container_details_text += f"  Prompt ID        {active_run['prompt_id']}\n"
            if active_run.get("started_at"):
                container_details_text += f"  Started          {active_run['started_at']}\n"

            # Format active job card
            active_job_display = f"""**🟢 Active Job Running**

**Operation:** {active_run["model_type"].upper()}
**Run ID:** {active_run["id"]}
**Prompt ID:** {active_run["prompt_id"]}
**Status:** {active_run.get("status", "Running")}
"""
            if active_run.get("started_at"):
                active_job_display += f"**Started:** {active_run['started_at']}"

        # Container information
        container = status_info.get("container")
        if container:
            container_name = container.get("name", "Unknown")
            container_status = container.get("status", "Unknown")
            container_id = container.get("id_short", container.get("id", "Unknown")[:12])

            container_details_text += f"Running Container  {container_name}\n"
            container_details_text += f"  Status           {container_status}\n"
            container_details_text += f"  Container ID     {container_id}\n"

            # If no active run info, create basic active job display from container
            if not active_job_display:
                active_job_display = f"""**🟢 Container Running**

**Container:** {container_name}
**ID:** {container_id}
**Status:** {container_status}
"""

            status = "Ready to stream from active container"
        else:
            if active_run:
                # Run without container - zombie run
                container_details_text += (
                    "Running Container  Missing! (Database shows active run)\n"
                )
                active_job_display = f"""**⚠️ Zombie Run Detected**

**Run ID:** {active_run["id"]}
Container missing - may need cleanup
"""
                status = "Container missing but run active in database"
            else:
                container_details_text += "Running Container  None\n"
                active_job_display = """**No Active Job**

Currently idle - no jobs running"""
                status = "No containers to stream from"

        return container_details_text.strip(), status, active_job_display

    except Exception as e:
        error_display = f"""**⚠️ Error**

{e}"""
        return f"Error: {e}", "Error checking containers", error_display


def cancel_selected_job(job_id, queue_service):
    """Cancel the selected job and refresh the queue.

    Args:
        job_id: The ID of the job to cancel
        queue_service: The shared SimplifiedQueueService instance
    """
    # Handle None gracefully
    if not job_id:
        return "No job selected", None, []

    from cosmos_workflow.ui.queue_handlers import QueueHandlers

    # Use the shared queue service
    queue_handlers = QueueHandlers(queue_service)

    # Cancel the job
    result = queue_handlers.cancel_job(job_id)

    # Refresh queue display
    status_text, table_data = queue_handlers.get_queue_display()

    return result, status_text, table_data
