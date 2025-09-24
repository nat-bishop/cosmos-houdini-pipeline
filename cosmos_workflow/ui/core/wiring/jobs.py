"""Event wiring for Jobs tab components."""

import functools

import gradio as gr

from cosmos_workflow.ui.core.safe_wiring import safe_wire
from cosmos_workflow.ui.queue_handlers import QueueHandlers
from cosmos_workflow.ui.tabs.jobs_handlers import (
    cancel_kill_confirmation,
    cancel_selected_job,
    execute_kill_job,
    refresh_and_stream,
    show_kill_confirmation,
)
from cosmos_workflow.utils.logging import logger


def wire_jobs_events(components, api, simple_queue_service):
    """Wire events for the Jobs tab.

    Args:
        components: Dictionary of UI components
        api: CosmosAPI instance
        simple_queue_service: SimplifiedQueueService instance
    """
    wire_jobs_control_events(components, simple_queue_service)
    wire_queue_control_events(components, simple_queue_service)
    wire_queue_selection_events(components, simple_queue_service)
    wire_queue_timers(components, simple_queue_service)


def wire_jobs_control_events(components, simple_queue_service=None):
    """Wire job control events (stream, kill, etc).

    Args:
        components: Dictionary of UI components
        simple_queue_service: SimplifiedQueueService instance (optional, for cancel job)
    """
    # Stream button
    safe_wire(
        components.get("stream_btn"),
        "click",
        refresh_and_stream,
        inputs=None,
        outputs=[
            components.get("running_jobs_display"),
            components.get("job_status"),
            components.get("active_job_card"),
            components.get("jobs_log_display"),
        ],
    )

    # Kill job operations
    safe_wire(
        components.get("kill_job_btn"),
        "click",
        show_kill_confirmation,
        outputs=[
            components.get("kill_confirmation"),  # The confirmation dialog group
            components.get("kill_preview"),  # The preview text
        ],
    )

    safe_wire(
        components.get("confirm_kill_btn"),
        "click",
        execute_kill_job,
        outputs=[
            components.get("kill_confirmation"),  # Hide dialog
            components.get("job_status"),  # Status message
        ],
    )

    safe_wire(
        components.get("cancel_kill_btn"),
        "click",
        cancel_kill_confirmation,
        outputs=[
            components.get("kill_confirmation"),  # Hide dialog
        ],
    )

    # Additional job control events
    if "clear_logs_btn" in components:

        def clear_logs():
            """Clear the job logs display."""
            return gr.update(value="")

        safe_wire(
            components.get("clear_logs_btn"),
            "click",
            clear_logs,
            outputs=[components.get("jobs_log_display")],
        )

    if "auto_advance_toggle" in components:

        def toggle_auto_advance(enabled):
            """Toggle auto-advance for job logs."""
            return gr.update(value=f"Auto-advance: {'Enabled' if enabled else 'Disabled'}")

        components["auto_advance_toggle"].change(
            fn=toggle_auto_advance,
            inputs=[components["auto_advance_toggle"]],
            outputs=[components.get("auto_advance_status")],
        )

    if "batch_size" in components:

        def update_batch_size(size):
            """Update batch processing size."""
            logger.info(f"Batch size updated to: {size}")
            # Don't return anything if no output is expected

        if "batch_size" in components:
            components["batch_size"].change(
                fn=update_batch_size,
                inputs=[components["batch_size"]],
                outputs=None,  # No output expected
            )

    if "cancel_job_btn" in components and simple_queue_service:
        cancel_job_bound = functools.partial(
            cancel_selected_job, queue_service=simple_queue_service
        )
        components["cancel_job_btn"].click(
            fn=cancel_job_bound,
            inputs=[components.get("selected_job_id")],
            outputs=[
                components.get("job_status"),
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )


def wire_queue_timers(components, simple_queue_service):
    """Wire timer events for automatic queue refresh and processing.

    Args:
        components: Dictionary of UI components
        simple_queue_service: SimplifiedQueueService instance
    """
    queue_handlers = QueueHandlers(simple_queue_service)

    # Create timer for auto-refreshing queue display every 5 seconds
    if "queue_table" in components and "queue_status" in components:
        refresh_timer = gr.Timer(value=5, active=True)
        refresh_timer.tick(
            fn=queue_handlers.get_queue_display,
            outputs=[
                components["queue_status"],
                components["queue_table"],
            ],
        )
        logger.info("Queue auto-refresh timer created (5 seconds)")

    # Create timer for auto-processing queue every 2 seconds
    def auto_process_queue():
        """Process next job in queue automatically."""
        try:
            # Check if queue is paused
            if hasattr(simple_queue_service, "queue_paused") and simple_queue_service.queue_paused:
                logger.debug("Queue is paused, skipping processing")
                return  # Return nothing instead of None

            # Only process if there are actually jobs in the queue
            status = simple_queue_service.get_queue_status()
            queued_count = status.get("total_queued", 0)

            if queued_count > 0:
                logger.debug("Queue has {} jobs, attempting to process next", queued_count)
                result = simple_queue_service.process_next_job()
                if result:
                    logger.info("Processed job from queue")
                # Don't return the result since outputs=[] expects no return
        except Exception as e:
            logger.error("Error in auto_process_queue: {}", e)

    process_timer = gr.Timer(value=2, active=True)
    process_timer.tick(
        fn=auto_process_queue,
        outputs=[],  # No outputs needed
    )
    logger.info("Queue auto-process timer created (2 seconds)")


def wire_queue_control_events(components, simple_queue_service):
    """Wire queue control events (pause, resume, clear, etc)."""
    queue_handlers = QueueHandlers(simple_queue_service)

    # Queue pause checkbox handler
    if "queue_pause_checkbox" in components:

        def toggle_queue_pause(is_paused):
            """Toggle queue pause state."""
            simple_queue_service.set_queue_paused(is_paused)
            status_text = "⏸️ **Queue: Paused**" if is_paused else "✅ **Queue: Active**"
            logger.info("Queue {} by user", "paused" if is_paused else "resumed")

            # Get updated queue display
            status, table = queue_handlers.get_queue_display()
            return gr.update(value=status_text), status, table

        components["queue_pause_checkbox"].change(
            fn=toggle_queue_pause,
            inputs=[components["queue_pause_checkbox"]],
            outputs=[
                components.get("queue_status_indicator"),
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    # Legacy queue control buttons (if they exist)
    if "pause_queue_btn" in components:
        components["pause_queue_btn"].click(
            fn=lambda: simple_queue_service.set_queue_paused(True),
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    if "resume_queue_btn" in components:
        components["resume_queue_btn"].click(
            fn=lambda: simple_queue_service.set_queue_paused(False),
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    if "clear_failed_btn" in components:
        components["clear_failed_btn"].click(
            fn=queue_handlers.clear_failed,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    if "retry_failed_btn" in components:
        components["retry_failed_btn"].click(
            fn=queue_handlers.retry_failed,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )

    # Queue refresh
    if "refresh_queue_btn" in components:
        components["refresh_queue_btn"].click(
            fn=queue_handlers.get_queue_display,
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
            ],
        )


def wire_queue_selection_events(components, simple_queue_service):
    """Wire queue table selection events."""
    queue_handlers = QueueHandlers(simple_queue_service)

    # Queue table selection with fixed handler using df_utils
    if "queue_table" in components:
        from cosmos_workflow.ui.utils import dataframe as df_utils

        def handle_queue_select(table_data, evt: gr.SelectData):
            """Handle queue table selection with proper event format."""
            if evt is None or table_data is None:
                return "No selection", gr.update(visible=False), None

            # Get selected row index
            row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index

            # Use the existing utility function that handles both DataFrame and list formats
            job_id = df_utils.get_cell_value(table_data, row_idx, 1, default=None)

            if job_id:
                details = queue_handlers.get_job_details(job_id)
                # Also get the status to determine if we should show cancel button
                status = df_utils.get_cell_value(table_data, row_idx, 3, default=None)
                show_cancel = status == "queued"
                return details, gr.update(visible=show_cancel), job_id

            return "No selection", gr.update(visible=False), None

        components["queue_table"].select(
            fn=handle_queue_select,
            inputs=[components["queue_table"]],
            outputs=[
                components.get("job_details"),
                components.get("cancel_job_btn"),
                components.get("selected_job_id"),
            ],
        )

    # Queue item actions
    if "remove_queue_item_btn" in components:
        components["remove_queue_item_btn"].click(
            fn=queue_handlers.remove_item,
            inputs=[components.get("queue_selected_id")],
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
                components.get("queue_selected_info"),
                components.get("queue_actions_row"),
            ],
        )

    if "prioritize_queue_item_btn" in components:
        components["prioritize_queue_item_btn"].click(
            fn=queue_handlers.prioritize_item,
            inputs=[components.get("queue_selected_id")],
            outputs=[
                components.get("queue_status"),
                components.get("queue_table"),
                components.get("queue_selected_info"),
            ],
        )
