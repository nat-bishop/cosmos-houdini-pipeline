#!/usr/bin/env python3
"""Comprehensive Gradio UI for Cosmos Workflow - Full Featured Application.

This module provides a complete web-based interface for the Cosmos Workflow System,
featuring advanced run management, filtering capabilities, and professional design.

Key Features:
- **Run History Management**: Comprehensive filtering, search, and batch operations
- **Enhanced Status Indicators**: Visual indicators for AI-enhanced prompts
- **Multi-tab Run Details**: General, Parameters, Logs, and Output information
- **Professional Design System**: Gradient animations and glassmorphism effects
- **Advanced Filtering**: Multi-criteria filtering with real-time search
- **Batch Operations**: Select and manage multiple runs simultaneously

Interface Tabs:
- Inputs: Video browser with prompt creation and multimodal preview
- Prompts: Unified prompt management with enhanced status indicators
- Outputs: Generated video gallery with comprehensive metadata
- Run History: Advanced run filtering, statistics, and batch management
- Active Jobs: Real-time container monitoring with auto-refresh and log streaming

The interface integrates with CosmosAPI for all operations, providing a complete
workflow management system from input preparation to output generation.
"""

import atexit
import signal
import threading
from datetime import timezone
from functools import partial
from pathlib import Path

import gradio as gr

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.simple_queue_service import SimplifiedQueueService

# Import modular UI components
from cosmos_workflow.ui.components.header import create_header_ui
from cosmos_workflow.ui.queue_handlers import QueueHandlers
from cosmos_workflow.ui.styles_simple import get_custom_css
from cosmos_workflow.ui.tabs.inputs_handlers import (
    create_prompt,
    load_input_gallery,
    on_input_select,
)
from cosmos_workflow.ui.tabs.inputs_ui import create_inputs_tab_ui
from cosmos_workflow.ui.tabs.jobs_handlers import (
    cancel_kill_confirmation,
    check_running_jobs,
    execute_kill_job,
    refresh_and_stream,
    refresh_jobs_on_tab_select,
    show_kill_confirmation,
)
from cosmos_workflow.ui.tabs.jobs_ui import create_jobs_tab_ui
from cosmos_workflow.ui.tabs.prompts_handlers import (
    cancel_delete_prompts,
    clear_selection,
    confirm_delete_prompts,
    get_selected_prompt_ids,
    load_ops_prompts,
    on_prompt_row_select,
    preview_delete_prompts,
    select_all_prompts,
)
from cosmos_workflow.ui.tabs.prompts_handlers import (
    run_enhance_on_selected as run_enhance_on_selected_base,
)
from cosmos_workflow.ui.tabs.prompts_handlers import (
    run_inference_on_selected as run_inference_on_selected_base,
)
from cosmos_workflow.ui.tabs.prompts_handlers import (
    update_selection_count as prompts_update_selection_count,
)
from cosmos_workflow.ui.tabs.prompts_ui import create_prompts_tab_ui
from cosmos_workflow.ui.tabs.runs_handlers import (
    cancel_delete_run,
    confirm_delete_run,
    handle_runs_tab_default,
    handle_runs_tab_with_filter,
    handle_runs_tab_with_pending_data,
    load_run_logs,
    load_runs_data,
    load_runs_data_with_version_filter,
    load_runs_with_filters,
    on_runs_gallery_select,
    on_runs_table_select,
    preview_delete_run,
    update_runs_selection_info,
)
from cosmos_workflow.ui.tabs.runs_ui import create_runs_tab_ui
from cosmos_workflow.ui.utils import dataframe as df_utils
from cosmos_workflow.utils.logging import logger

# Load configuration
config = ConfigManager()

# Initialize log viewer (reusing existing component)

# Initialize Queue Service for UI use
queue_service = None
queue_handlers = None


# Simple shutdown cleanup using existing methods
def cleanup_on_shutdown(signum=None, frame=None):
    """Kill containers and cleanup running jobs on shutdown."""
    global queue_service

    if signum:
        logger.info("Shutting down gracefully...")

    # Mark any running jobs as cancelled before stopping queue processor
    # This prevents zombie jobs that can't complete without the app
    # Try queue_service first, but fall back to direct database access
    db_cleaned = False

    if queue_service:
        try:
            from datetime import datetime, timezone

            from cosmos_workflow.database.models import JobQueue

            # Get a database session
            # SimplifiedQueueService doesn't have db_session attribute
            if hasattr(queue_service, "db_connection") and queue_service.db_connection:
                session = queue_service.db_connection.SessionLocal()
            else:
                # Skip cleanup if no db connection
                return

            try:
                # Find and cancel all running jobs
                running_jobs = session.query(JobQueue).filter(JobQueue.status == "running").all()

                if running_jobs:
                    for job in running_jobs:
                        job.status = "cancelled"
                        job.completed_at = datetime.now(timezone.utc)
                        job.result = {"reason": "Application shutdown"}
                        logger.info("Marking running job {} as cancelled due to shutdown", job.id)

                    session.commit()
                    logger.info("Cancelled {} running job(s) on shutdown", len(running_jobs))
                    db_cleaned = True

            finally:
                session.close()

        except Exception as e:
            logger.error("Error cancelling running jobs via queue_service: {}", e)

    # Fallback: Try direct database access if queue_service wasn't available or failed
    if not db_cleaned:
        try:
            from datetime import datetime, timezone
            from pathlib import Path

            from cosmos_workflow.database import DatabaseConnection
            from cosmos_workflow.database.models import JobQueue

            # Try to connect directly to the database
            db_path = Path("outputs/cosmos.db")
            if db_path.exists():
                db_connection = DatabaseConnection(str(db_path))
                # Use SessionLocal instead of Session
                session = db_connection.SessionLocal()

                try:
                    # Find and cancel all running jobs
                    running_jobs = (
                        session.query(JobQueue).filter(JobQueue.status == "running").all()
                    )

                    if running_jobs:
                        for job in running_jobs:
                            job.status = "cancelled"
                            job.completed_at = datetime.now(timezone.utc)
                            job.result = {"reason": "Application shutdown (fallback cleanup)"}
                            logger.info("Marking running job {} as cancelled (fallback)", job.id)

                        session.commit()
                        logger.info(
                            "Cancelled {} running job(s) via fallback method", len(running_jobs)
                        )

                finally:
                    session.close()

        except Exception as e:
            logger.error("Error in fallback job cancellation: {}", e)

    # No background processor to stop in simplified version
    # Queue processing is handled by Gradio timer

    # Check config to see if we should cleanup containers
    ui_config = config.get_ui_config()
    should_cleanup = ui_config.get("cleanup_containers_on_exit", False)

    if not should_cleanup:
        logger.info("Container cleanup disabled in config - leaving containers running")
        return

    try:
        ops = CosmosAPI()
        result = ops.kill_containers()
        if result["killed_count"] > 0:
            logger.info("Killed {} container(s)", result["killed_count"])
    except Exception as e:
        logger.debug("Cleanup error (expected on shutdown): {}", e)

    # Shutdown thumbnail executor thread pool to prevent resource leak
    try:
        from cosmos_workflow.ui.tabs.runs_handlers import THUMBNAIL_EXECUTOR

        THUMBNAIL_EXECUTOR.shutdown(wait=False)
        logger.info("Thumbnail executor shutdown completed")
    except Exception as e:
        logger.debug("Error shutting down thumbnail executor: {}", e)


# Register cleanup - reuse existing kill_containers() method
atexit.register(cleanup_on_shutdown)
# Only register signal handlers in main thread
if threading.current_thread() is threading.main_thread():
    signal.signal(signal.SIGINT, cleanup_on_shutdown)
    signal.signal(signal.SIGTERM, cleanup_on_shutdown)

# Get paths from config
local_config = config.get_local_config()
inputs_dir = Path(local_config.videos_dir)  # This is already "inputs/videos" from config
outputs_dir = Path(local_config.outputs_dir)


# ============================================================================
# Phase 1: Input Browser Functions
# ============================================================================


# ============================================================================
# Phase 2: Prompt Management Functions
# ============================================================================


# ============================================================================
# Helper Functions
# ============================================================================


def update_selection_count(dataframe_data):
    """Wrapper for prompts_update_selection_count to avoid name conflict."""
    return prompts_update_selection_count(dataframe_data)


# ============================================================================
# Existing Log Streaming Functions (keeping from original)
# ============================================================================


# ============================================================================
# Main UI Creation
# ============================================================================


def create_ui():
    """Create the comprehensive Gradio interface using modular components."""
    global queue_service, queue_handlers

    # Initialize Queue Service with database
    database_path = "outputs/cosmos.db"
    db_connection = DatabaseConnection(database_path)
    queue_service = SimplifiedQueueService(db_connection=db_connection)
    queue_handlers = QueueHandlers(queue_service)

    # Create partial functions with queue_service bound
    # This is the Pythonic way to inject dependencies without global state
    run_inference_on_selected = partial(run_inference_on_selected_base, queue_service=queue_service)
    run_enhance_on_selected = partial(run_enhance_on_selected_base, queue_service=queue_service)

    # Get custom CSS from styles module
    custom_css = get_custom_css()

    # Initialize component registry
    components = {}

    # Helper to safely get component lists
    def get_components(*keys):
        """Get a list of components, skipping any that don't exist."""
        result = []
        for key in keys:
            if key in components:
                result.append(components[key])
        # Return the list if we have all requested components
        return result if len(result) == len(keys) else None

    with gr.Blocks(title="Cosmos Workflow Manager", css=custom_css) as app:
        # Create header with refresh controls
        header_components = create_header_ui(config)
        components.update(header_components)

        # Create tabs
        with gr.Tabs() as tabs:
            # Create each tab UI
            inputs_components = create_inputs_tab_ui(config)
            components.update(inputs_components)

            prompts_components = create_prompts_tab_ui()
            components.update(prompts_components)

            runs_components = create_runs_tab_ui()
            components.update(runs_components)

            jobs_components = create_jobs_tab_ui()
            components.update(jobs_components)

        components["tabs"] = tabs

        # ============================================
        # Navigation State Management
        # ============================================
        # State for cross-tab navigation and filtering
        navigation_state = gr.State(
            value={
                "filter_type": None,  # "prompt_ids" or None
                "filter_values": [],  # List of IDs being filtered
                "source_tab": None,  # Where navigation originated from
            }
        )
        components["navigation_state"] = navigation_state

        # State to store selected prompt IDs (avoids dataframe preprocessing issues)
        selected_prompt_ids_state = gr.State(value=[])
        components["selected_prompt_ids_state"] = selected_prompt_ids_state

        # State to hold pending navigation data (prevents race condition)
        pending_nav_data = gr.State(value=None)
        components["pending_nav_data"] = pending_nav_data

        # State to track last selected run ID to avoid unnecessary scrolling
        last_selected_run_id = gr.State(value=None)
        components["last_selected_run_id"] = last_selected_run_id

        # ============================================
        # Event Handlers
        # ============================================

        # Unified filter handler that respects navigation state for persistent prompt filtering

        # Helper functions for tab navigation
        def _handle_jobs_tab_refresh():
            """Handle Jobs tab refresh when switching to it."""
            logger.info("Switching to Jobs tab - refreshing status")
            jobs_result = check_running_jobs()

            if "Ready to stream" in jobs_result[1]:
                logger.info("Active container detected - starting log stream")

            return (
                gr.update(),  # runs_gallery - no update
                gr.update(),  # runs_table - no update
                gr.update(),  # runs_stats - no update
                gr.update(),  # runs_nav_filter_row - no update
                gr.update(),  # runs_prompt_filter - no update
                jobs_result[0],  # Update container details
                jobs_result[1],  # Update job status
                jobs_result[2],  # Update active job card
            )

        # Tab navigation handler - check for navigation state when switching tabs
        def handle_tab_select(tab_index, nav_state, pending_data):
            """Handle tab selection and apply navigation filters."""
            # tab_index is now directly a number
            logger.info(
                "handle_tab_select called: tab={}, nav_state={}, has_pending={}",
                tab_index,
                nav_state,
                pending_data is not None,
            )

            # Auto-refresh Jobs tab when switching to it (index 3)
            if tab_index == 3:
                updates = _handle_jobs_tab_refresh()
                return (nav_state, pending_data, *updates)

            # Check if there's pending navigation data (from View Runs button)
            if tab_index == 2 and pending_data is not None:
                updates = handle_runs_tab_with_pending_data(pending_data)
                return (nav_state, None, *updates)

            # Check if we're navigating to Runs tab (index 2) with pending filter
            elif tab_index == 2 and nav_state and nav_state.get("filter_type") == "prompt_ids":
                updates = handle_runs_tab_with_filter(nav_state)
                return (nav_state, None, *updates)

            # Check if we're navigating to Runs tab without filter - load default data
            elif tab_index == 2 and (not nav_state or nav_state.get("filter_type") is None):
                updates = handle_runs_tab_default()
                final_nav_state = (
                    nav_state
                    if nav_state
                    else {
                        "filter_type": None,
                        "filter_values": [],
                        "source_tab": None,
                    }
                )
                return (final_nav_state, None, *updates)

            # No navigation action needed for other tabs
            return (
                nav_state,  # Keep current navigation state
                None,  # Clear pending data
                gr.update(),  # Don't change gallery
                gr.update(),  # Don't change table
                gr.update(),  # Don't change stats
                gr.update(),  # Don't change filter indicator
                gr.update(),  # Don't change filter dropdown
                gr.update(),  # Don't change running_jobs_display
                gr.update(),  # Don't change job_status
                gr.update(),  # Don't change active_job_card
            )

        # Create a number component to track selected tab index
        selected_tab_index = gr.Number(value=0, visible=False)

        def update_tab_index(evt: gr.SelectData):
            """Update the selected tab index when tabs change."""
            return evt.index

        tabs.select(
            fn=update_tab_index,
            inputs=[],
            outputs=[selected_tab_index],
        ).then(
            fn=handle_tab_select,
            inputs=[selected_tab_index, navigation_state, pending_nav_data],
            outputs=[
                navigation_state,
                pending_nav_data,  # Clear pending data after use
                components.get("runs_gallery"),
                components.get("runs_table"),
                components.get("runs_stats"),
                components.get("runs_nav_filter_row"),
                components.get("runs_prompt_filter"),
                components.get("running_jobs_display"),  # Add Jobs tab outputs
                components.get("job_status"),
                components.get("active_job_card"),
            ],
        ).then(
            # Auto-refresh when switching to Jobs tab
            fn=refresh_jobs_on_tab_select,
            inputs=[selected_tab_index],
            outputs=[
                components.get("running_jobs_display"),
                components.get("job_status"),
                components.get("active_job_card"),
                components.get("log_display"),
            ]
            if all(
                k in components
                for k in ["running_jobs_display", "job_status", "active_job_card", "log_display"]
            )
            else [],
        )

        # Import additional functions for runs tab

        # Global refresh function
        def global_refresh_all(
            # Inputs tab filters
            inputs_search="",
            inputs_date_filter="all",
            inputs_sort="name_asc",
            # Prompts tab filters
            prompts_search="",
            prompts_enhanced_filter="all",
            prompts_runs_filter="all",
            prompts_date_filter="all",
            # Runs tab filters
            runs_status_filter="all",
            runs_date_filter="all",
            runs_type_filter="all",
            runs_search="",
            runs_limit=50,
        ):
            """Refresh all data across all tabs while preserving filters.

            Args:
                inputs_search: Search text for inputs
                inputs_date_filter: Date filter for inputs
                inputs_sort: Sort order for inputs
                prompts_search: Search text for prompts filtering
                prompts_enhanced_filter: Enhanced status filter for prompts
                prompts_runs_filter: Run status filter for prompts
                prompts_date_filter: Date range filter for prompts
                runs_status_filter: Status filter for runs
                runs_date_filter: Date filter for runs
                runs_search: Search text for runs
                runs_limit: Max results for runs
            """
            from datetime import datetime

            try:
                # Get current status
                status = f"✅ Connected | Last refresh: {datetime.now(timezone.utc).strftime('%H:%M:%S')}"

                # Load all data with filter parameters
                inputs_data, inputs_count = load_input_gallery(
                    inputs_dir,
                    inputs_search,
                    inputs_date_filter,
                    inputs_sort,
                )
                prompts_data = load_ops_prompts(
                    50,
                    prompts_search,
                    prompts_enhanced_filter,
                    prompts_runs_filter,
                    prompts_date_filter,
                )
                jobs_result = check_running_jobs()
                jobs_data = (jobs_result[0], jobs_result[1])  # Keep compatibility for other uses

                # Load runs data with filters
                runs_gallery, runs_table, runs_stats = load_runs_data(
                    runs_status_filter,
                    runs_date_filter,
                    runs_type_filter,
                    runs_search,
                    runs_limit,
                    "all",
                )

                return (
                    status,  # refresh_status
                    inputs_data,  # input_gallery
                    inputs_count,  # inputs_results_count
                    prompts_data,  # ops_prompts_table
                    jobs_data[0],  # running_jobs_display
                    jobs_data[1],  # job_status
                    runs_gallery,  # runs_gallery
                    runs_table,  # runs_table
                    runs_stats,  # runs_stats
                )
            except Exception as e:
                logger.error("Error during global refresh: {}", str(e))
                return (
                    "❌ Error - Check logs",
                    [],
                    "**0** directories found",
                    [],
                    "Error loading data",
                    "Error",
                    [],
                    [],
                    "Error loading data",
                )

        # Header/Manual Refresh Events

        if "manual_refresh_btn" in components:
            # Manual refresh: preserve filters
            manual_refresh_inputs = []

            # Add Inputs tab filter inputs
            if "inputs_search" in components:
                manual_refresh_inputs.append(components["inputs_search"])
            if "inputs_date_filter" in components:
                manual_refresh_inputs.append(components["inputs_date_filter"])
            if "inputs_sort" in components:
                manual_refresh_inputs.append(components["inputs_sort"])

            # Add Prompts tab filter inputs
            if "prompts_search" in components:
                manual_refresh_inputs.append(components["prompts_search"])
            if "prompts_enhanced_filter" in components:
                manual_refresh_inputs.append(components["prompts_enhanced_filter"])
            if "prompts_runs_filter" in components:
                manual_refresh_inputs.append(components["prompts_runs_filter"])
            if "prompts_date_filter" in components:
                manual_refresh_inputs.append(components["prompts_date_filter"])

            # Add Runs tab filter inputs
            if "runs_status_filter" in components:
                manual_refresh_inputs.append(components["runs_status_filter"])
            if "runs_date_filter" in components:
                manual_refresh_inputs.append(components["runs_date_filter"])
            if "runs_type_filter" in components:
                manual_refresh_inputs.append(components["runs_type_filter"])
            if "runs_search" in components:
                manual_refresh_inputs.append(components["runs_search"])
            if "runs_limit" in components:
                manual_refresh_inputs.append(components["runs_limit"])

            # Build outputs list including all tab components
            manual_refresh_outputs = []
            if "refresh_status" in components:
                manual_refresh_outputs.append(components["refresh_status"])
            if "input_gallery" in components:
                manual_refresh_outputs.append(components["input_gallery"])
            if "inputs_results_count" in components:
                manual_refresh_outputs.append(components["inputs_results_count"])
            if "ops_prompts_table" in components:
                manual_refresh_outputs.append(components["ops_prompts_table"])
            if "running_jobs_display" in components:
                manual_refresh_outputs.append(components["running_jobs_display"])
            if "job_status" in components:
                manual_refresh_outputs.append(components["job_status"])
            if "runs_gallery" in components:
                manual_refresh_outputs.append(components["runs_gallery"])
            if "runs_table" in components:
                manual_refresh_outputs.append(components["runs_table"])
            if "runs_stats" in components:
                manual_refresh_outputs.append(components["runs_stats"])

            # Create the handler with proper parameter unpacking
            def manual_refresh_handler(*args):
                # Unpack arguments based on what's available
                idx = 0

                # Inputs filters
                i_search = args[idx] if len(args) > idx else ""
                idx += 1
                i_date = args[idx] if len(args) > idx else "all"
                idx += 1
                i_sort = args[idx] if len(args) > idx else "name_asc"
                idx += 1

                # Prompts filters
                p_search = args[idx] if len(args) > idx else ""
                idx += 1
                p_enhanced = args[idx] if len(args) > idx else "all"
                idx += 1
                p_runs = args[idx] if len(args) > idx else "all"
                idx += 1
                p_date = args[idx] if len(args) > idx else "all"
                idx += 1

                # Runs filters
                r_status = args[idx] if len(args) > idx else "all"
                idx += 1
                r_date = args[idx] if len(args) > idx else "all"
                idx += 1
                r_type = args[idx] if len(args) > idx else "all"
                idx += 1
                r_search = args[idx] if len(args) > idx else ""
                idx += 1
                r_limit = args[idx] if len(args) > idx else 50

                return global_refresh_all(
                    inputs_search=i_search,
                    inputs_date_filter=i_date,
                    inputs_sort=i_sort,
                    prompts_search=p_search,
                    prompts_enhanced_filter=p_enhanced,
                    prompts_runs_filter=p_runs,
                    prompts_date_filter=p_date,
                    runs_status_filter=r_status,
                    runs_date_filter=r_date,
                    runs_type_filter=r_type,
                    runs_search=r_search,
                    runs_limit=r_limit,
                )

            components["manual_refresh_btn"].click(
                fn=manual_refresh_handler,
                inputs=manual_refresh_inputs,
                outputs=manual_refresh_outputs,
            )

        # Inputs Tab Events
        if "input_gallery" in components:
            # Create wrapper function for on_input_select
            def handle_input_select(evt: gr.SelectData, gallery_data):
                return on_input_select(evt, gallery_data, inputs_dir)

            components["input_gallery"].select(
                fn=handle_input_select,
                inputs=[components["input_gallery"]],
                outputs=[
                    components["selected_dir_path"],
                    components["preview_group"],
                    components["input_tabs_group"],
                    components["input_name"],
                    components["input_path"],
                    components["input_created"],
                    components["input_resolution"],
                    components["input_duration"],
                    components["input_fps"],
                    components["input_codec"],
                    components["input_files"],
                    components["video_preview_gallery"],
                    components["create_video_dir"],
                ],
            )

        # Inputs filtering events
        if all(
            k in components
            for k in [
                "inputs_search",
                "inputs_date_filter",
                "inputs_sort",
            ]
        ):
            filter_inputs = [
                components["inputs_search"],
                components["inputs_date_filter"],
                components["inputs_sort"],
            ]
            filter_outputs = [
                components["input_gallery"],
                components["inputs_results_count"],
            ]

            # Search box with debouncing (responds to text changes)
            if "inputs_search" in components:
                components["inputs_search"].change(
                    fn=lambda search, date_f, sort: load_input_gallery(
                        inputs_dir, search, date_f, sort
                    ),
                    inputs=filter_inputs,
                    outputs=filter_outputs,
                )

            # Dropdown filters respond immediately

            if "inputs_date_filter" in components:
                components["inputs_date_filter"].change(
                    fn=lambda search, date_f, sort: load_input_gallery(
                        inputs_dir, search, date_f, sort
                    ),
                    inputs=filter_inputs,
                    outputs=filter_outputs,
                )

            # Sort dropdown
            if "inputs_sort" in components:
                components["inputs_sort"].change(
                    fn=lambda search, date_f, sort: load_input_gallery(
                        inputs_dir, search, date_f, sort
                    ),
                    inputs=filter_inputs,
                    outputs=filter_outputs,
                )

        if "create_prompt_btn" in components:
            # Create prompt with Gradio's built-in progress indicator
            components["create_prompt_btn"].click(
                fn=create_prompt,
                inputs=[
                    components["create_prompt_text"],
                    components["create_video_dir"],
                    components["create_name"],
                    components["create_negative"],
                ],
                outputs=[components.get("create_progress_area")],  # Invisible area for spinner
                show_progress="full",  # This enables Gradio's built-in button spinner
                queue=True,  # Explicitly enable queue for progress to work
            )

        # Prompts Tab Events
        if "ops_prompts_table" in components:
            outputs = get_components(
                "selected_prompt_id",
                "selected_prompt_name",
                "selected_prompt_text",
                "selected_prompt_negative",
                "selected_prompt_created",
                "selected_prompt_video_dir",
                "selected_prompt_enhanced",
                "selected_prompt_runs_stats",
                "selected_prompt_rating",
                "selected_prompt_video_thumb",
            )
            if outputs:
                components["ops_prompts_table"].select(
                    fn=on_prompt_row_select,
                    inputs=[components["ops_prompts_table"]],
                    outputs=outputs,
                )

            if "selection_count" in components:
                components["ops_prompts_table"].change(
                    fn=update_selection_count,
                    inputs=[components["ops_prompts_table"]],
                    outputs=[components["selection_count"]],
                )

        # Prompts filtering events
        prompts_filter_inputs = get_components(
            "ops_limit",
            "prompts_search",
            "prompts_enhanced_filter",
            "prompts_runs_filter",
            "prompts_date_filter",
        )
        if prompts_filter_inputs and "ops_prompts_table" in components:
            # Connect all filter controls to update the table
            for filter_component in [
                "prompts_search",
                "prompts_enhanced_filter",
                "prompts_runs_filter",
                "prompts_date_filter",
            ]:
                if filter_component in components:
                    components[filter_component].change(
                        fn=load_ops_prompts,
                        inputs=prompts_filter_inputs,
                        outputs=[components["ops_prompts_table"]],
                    )

        # Prompts selection controls
        if "select_all_btn" in components:
            components["select_all_btn"].click(
                fn=select_all_prompts,
                inputs=[components["ops_prompts_table"]],
                outputs=[
                    components["ops_prompts_table"],
                    components["selection_count"],
                ],
            )

        if "clear_selection_btn" in components:
            components["clear_selection_btn"].click(
                fn=clear_selection,
                inputs=[components["ops_prompts_table"]],
                outputs=[
                    components["ops_prompts_table"],
                    components["selection_count"],
                ],
            )

        # Prompts delete operations - Two-step process with preview
        if "delete_selected_btn" in components and "ops_prompts_table" in components:
            # Step 1: Show preview when delete button is clicked
            components["delete_selected_btn"].click(
                fn=preview_delete_prompts,
                inputs=[components["ops_prompts_table"]],
                outputs=[
                    components.get("prompts_delete_dialog"),
                    components.get("prompts_delete_preview"),
                    components.get("prompts_delete_outputs_checkbox"),
                    components.get("prompts_delete_ids_hidden"),
                ],
                scroll_to_output=True,  # Scroll to the delete confirmation dialog
            )

            # Step 2: Confirm deletion
            if "prompts_confirm_delete_btn" in components:
                components["prompts_confirm_delete_btn"].click(
                    fn=confirm_delete_prompts,
                    inputs=[
                        components.get("prompts_delete_ids_hidden"),
                        components.get("prompts_delete_outputs_checkbox"),
                    ],
                    outputs=[
                        components.get("selection_count"),
                        components.get("prompts_delete_dialog"),
                    ],
                ).then(
                    fn=load_ops_prompts,
                    inputs=[components.get("ops_limit")],
                    outputs=[components.get("ops_prompts_table")],
                )

            # Cancel deletion
            if "prompts_cancel_delete_btn" in components:
                components["prompts_cancel_delete_btn"].click(
                    fn=cancel_delete_prompts,
                    inputs=[],
                    outputs=[
                        components.get("selection_count"),
                        components.get("prompts_delete_dialog"),
                    ],
                )

        # Navigation to Runs tab with filtering
        # NOTE: tabs is a variable, not a component - we just need to check it exists
        if (
            "view_runs_btn" in components
            and tabs is not None  # Check tabs variable exists, not in components
            and "runs_gallery" in components
            and "runs_table" in components
            and "runs_stats" in components
            and "runs_nav_filter_row" in components
            and "runs_prompt_filter" in components
        ):

            def prepare_runs_navigation(selected_ids):
                """Navigate to Runs tab with filtering - sets pending data to avoid race condition."""
                from cosmos_workflow.ui.tabs.runs_handlers import load_runs_for_multiple_prompts
                from cosmos_workflow.utils.logging import logger

                # Selected IDs are now passed directly from state
                logger.info(f"prepare_runs_navigation called with selected_ids: {selected_ids}")

                if not selected_ids:
                    return (
                        {
                            "filter_type": None,
                            "filter_values": [],
                            "source_tab": None,
                        },  # Clear navigation state
                        None,  # No pending data
                        "⚠️ Please select at least one prompt before viewing runs.",
                        gr.update(),  # Don't switch tabs (keep current)
                        gr.update(),  # Don't update runs_gallery
                        gr.update(),  # Don't update runs_table
                        gr.update(),  # Don't update runs_stats
                        gr.update(),  # Don't update runs_nav_filter_row
                        gr.update(),  # Don't update runs_prompt_filter
                    )

                # Cap at 20 prompts for performance
                if len(selected_ids) > 20:
                    selected_ids = selected_ids[:20]
                    status_msg = f"✅ Navigating to Runs tab with first 20 of {len(selected_ids)} selected prompts..."
                else:
                    status_msg = (
                        f"✅ Navigating to Runs tab with {len(selected_ids)} selected prompt(s)..."
                    )

                # Load filtered data
                logger.info(f"Loading runs data for prompts: {selected_ids}")
                gallery_data, table_data, stats, prompt_names = load_runs_for_multiple_prompts(
                    selected_ids, "all", "all", "all", "", 50
                )

                # Ensure table_data is a list for Gradio dataframe
                if table_data is None:
                    table_data = []
                elif isinstance(table_data, dict):
                    table_data = table_data.get("data", [])

                logger.info(
                    f"Loaded {len(table_data) if table_data else 0} runs for filtered prompts"
                )

                # Set navigation state with filter information
                nav_state_with_filter = {
                    "filter_type": "prompt_ids",  # Fixed: was "prompts", now matches line 1450 check
                    "filter_values": selected_ids,
                    "source_tab": "prompts",
                }

                # Prepare pending data that will be consumed by handle_tab_select
                pending_data = {
                    "gallery": gallery_data if gallery_data else [],
                    "table": table_data if table_data else [],
                    "stats": stats if stats else "No data",
                    "prompt_names": prompt_names if prompt_names else [],
                }

                # Return navigation state and pending data
                # The actual components will be updated by handle_tab_select when it consumes pending_data
                return (
                    nav_state_with_filter,  # Set navigation state
                    pending_data,  # Set pending data for handle_tab_select to consume
                    status_msg,
                    2,  # Switch to Runs tab (index 2)
                    gr.update(),  # Don't update gallery yet
                    gr.update(),  # Don't update table yet
                    gr.update(),  # Don't update stats yet
                    gr.update(),  # Don't update filter row yet
                    gr.update(),  # Don't update filter dropdown yet
                )

            # Combined navigation and data loading to avoid race conditions
            # Use the state that tracks selected IDs properly
            components["view_runs_btn"].click(
                fn=prepare_runs_navigation,
                inputs=[selected_prompt_ids_state],
                outputs=[
                    navigation_state,  # Update navigation state
                    pending_nav_data,  # Set pending data for handle_tab_select
                    components["selection_count"],  # Update status message
                    selected_tab_index,  # Update selected tab index (hidden number component)
                    components["runs_gallery"],  # Update runs gallery with filtered data
                    components["runs_table"],  # Update runs table with filtered data
                    components["runs_stats"],  # Update runs stats
                    components["runs_nav_filter_row"],  # Show/hide filter indicator
                    components["runs_prompt_filter"],  # Update filter dropdown
                ],
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[2]?.click(); }, 100); return []; }",
                queue=False,
            )

        # Navigation from Inputs to Prompts tab
        if "view_prompts_for_input_btn" in components and "selected_dir_path" in components:

            def prepare_prompts_navigation_from_input(input_name):
                """Navigate to Prompts tab with search filter for input directory."""
                from cosmos_workflow.utils.logging import logger

                logger.info(
                    f"prepare_prompts_navigation_from_input called with input_name: {input_name}"
                )

                if not input_name:
                    return (
                        "⚠️ Please select an input directory first.",
                        gr.update(),  # Don't change search
                        gr.update(),  # Don't switch tabs
                    )

                # Extract just the directory name (remove any path prefixes)
                search_term = input_name.split("/")[-1] if "/" in input_name else input_name
                search_term = search_term.split("\\")[-1] if "\\" in search_term else search_term

                logger.info(f"Navigating to Prompts tab with search: {search_term}")

                return (
                    f"✅ Navigating to Prompts tab to show prompts using '{search_term}'...",
                    gr.update(value=search_term),  # Update search field
                    1,  # Switch to Prompts tab (index 1)
                )

            components["view_prompts_for_input_btn"].click(
                fn=prepare_prompts_navigation_from_input,
                inputs=[
                    components["selected_dir_path"]
                ],  # Use the State component which stores the path
                outputs=[
                    components["refresh_status"],  # Status message (reuse refresh status)
                    components["prompts_search"],  # Update search field in prompts tab
                    selected_tab_index,  # Update selected tab index
                ],
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[1]?.click(); }, 100); return []; }",
                queue=False,
            ).then(
                # After updating search, reload the prompts table with the new search term
                fn=lambda search_term: load_ops_prompts(50, search_term, "all", "all"),
                inputs=[components["prompts_search"]],
                outputs=[components["ops_prompts_table"]],
            )

        # Navigation from Inputs to Runs tab
        if "view_runs_for_input_btn" in components and "selected_dir_path" in components:

            def prepare_runs_navigation_from_input(input_path):
                """Navigate to Runs tab with filtering by input directory."""
                from cosmos_workflow.api.cosmos_api import CosmosAPI
                from cosmos_workflow.utils.logging import logger

                logger.info(
                    f"prepare_runs_navigation_from_input called with input_path: {input_path}"
                )

                if not input_path:
                    return (
                        gr.update(),  # navigation_state - no update
                        gr.update(),  # pending_nav_data - no update
                        "⚠️ Please select an input directory first.",  # status message
                        gr.update(),  # selected_tab_index - no update
                        gr.update(),  # runs_gallery - no update
                        gr.update(),  # runs_table - no update
                        gr.update(),  # runs_stats - no update
                        gr.update(visible=False),  # runs_nav_filter_row - keep hidden
                        gr.update(),  # runs_prompt_filter - no update
                    )

                # Get all prompts and filter by input directory (same logic as View Prompts)
                ops = CosmosAPI()
                all_prompts = ops.list_prompts(limit=1000)

                # Extract directory name from path
                input_name = input_path.split("/")[-1] if "/" in input_path else input_path
                input_name = input_name.split("\\")[-1] if "\\" in input_name else input_name

                # Find prompts that use this input directory
                matching_prompt_ids = []
                for prompt in all_prompts:
                    inputs = prompt.get("inputs", {})
                    video_path = inputs.get("video", "")
                    # Check if the input name appears in the video path
                    if input_name in video_path:
                        matching_prompt_ids.append(prompt.get("id"))

                logger.info(
                    f"Found {len(matching_prompt_ids)} prompts using input directory '{input_name}'"
                )

                if not matching_prompt_ids:
                    return (
                        gr.update(),  # navigation_state
                        gr.update(),  # pending_nav_data
                        f"No prompts found using input '{input_name}'",  # status
                        gr.update(),  # selected_tab_index
                        gr.update(),  # runs_gallery
                        gr.update(),  # runs_table
                        gr.update(),  # runs_stats
                        gr.update(visible=False),  # runs_nav_filter_row
                        gr.update(),  # runs_prompt_filter
                    )

                # Now call the existing prepare_runs_navigation with these prompt IDs
                # This will handle all the filtering and navigation properly
                return prepare_runs_navigation(matching_prompt_ids)

            components["view_runs_for_input_btn"].click(
                fn=prepare_runs_navigation_from_input,
                inputs=[components["selected_dir_path"]],
                outputs=[
                    navigation_state,  # Update navigation state
                    pending_nav_data,  # Set pending data for handle_tab_select
                    components["refresh_status"],  # Status message
                    selected_tab_index,  # Update selected tab index
                    components["runs_gallery"],  # Update runs gallery with filtered data
                    components["runs_table"],  # Update runs table with filtered data
                    components["runs_stats"],  # Update runs stats
                    components["runs_nav_filter_row"],  # Show filter indicator
                    components["runs_prompt_filter"],  # Show filter text
                ],
                js="() => { setTimeout(() => { document.querySelectorAll('.tab-nav button, button[role=\"tab\"]')[2]?.click(); }, 100); return []; }",
                queue=False,
            )

        # Update selection count when selection changes
        if "ops_prompts_table" in components:

            def update_selection_and_state(table_data):
                """Update selection count and store selected IDs in state."""
                from cosmos_workflow.utils.logging import logger

                # Get selection count display
                count_display = prompts_update_selection_count(table_data)

                # Get selected IDs for state
                selected_ids = get_selected_prompt_ids(table_data)
                logger.info(f"update_selection_and_state: selected_ids={selected_ids}")

                return count_display, selected_ids

            # Track both row selection and checkbox changes
            components["ops_prompts_table"].select(
                fn=update_selection_and_state,
                inputs=[components["ops_prompts_table"]],
                outputs=[components["selection_count"], selected_prompt_ids_state],
            )

            # Also track when checkboxes are changed
            components["ops_prompts_table"].change(
                fn=update_selection_and_state,
                inputs=[components["ops_prompts_table"]],
                outputs=[components["selection_count"], selected_prompt_ids_state],
            )

        if "run_inference_btn" in components and "ops_prompts_table" in components:
            inputs = get_components(
                "ops_prompts_table",
                "weight_vis",
                "weight_edge",
                "weight_depth",
                "weight_seg",
                "inf_steps",
                "inf_guidance",
                "inf_seed",
                "inf_fps",
                "inf_sigma_max",
                "inf_blur_strength",
                "inf_canny_threshold",
            )
            outputs = get_components("inference_status")
            if inputs and outputs:
                # Run inference and then update Jobs & Queue status
                components["run_inference_btn"].click(
                    fn=run_inference_on_selected,
                    inputs=inputs,
                    outputs=outputs,
                ).then(
                    # Update Jobs & Queue tab to show the running container
                    fn=check_running_jobs,
                    inputs=[],
                    outputs=[
                        components.get("running_jobs_display"),
                        components.get("job_status"),
                        components.get("active_job_card"),
                    ],
                )

        if "run_enhance_btn" in components:
            inputs = get_components(
                "ops_prompts_table",
                "enhance_create_new",
                "enhance_force",
            )
            outputs = get_components("enhance_status")
            if inputs and outputs:
                components["run_enhance_btn"].click(
                    fn=run_enhance_on_selected,
                    inputs=inputs,
                    outputs=outputs,
                )

        # Runs Tab Events
        # Runs filters - trigger data reload
        if all(
            k in components
            for k in [
                "runs_status_filter",
                "runs_date_filter",
                "runs_type_filter",
                "runs_search",
                "runs_limit",
                "runs_rating_filter",
                "runs_version_filter",
            ]
        ):
            filter_inputs = [
                components["runs_status_filter"],
                components["runs_date_filter"],
                components["runs_type_filter"],
                components["runs_search"],
                components["runs_limit"],
                components["runs_rating_filter"],  # Rating filter from runs tab
                components["runs_version_filter"],  # Version filter
            ]
            # Update gallery, table and stats with unified filter handler
            # Now includes navigation_state for persistent prompt filtering
            filter_outputs = get_components(
                "runs_gallery",
                "runs_table",
                "runs_stats",
                "navigation_state",  # Add navigation state to outputs
                "runs_nav_filter_row",  # Add filter indicator visibility
                "runs_prompt_filter",  # Add filter text display
            )
            if filter_outputs:
                # Add navigation_state to inputs for unified filtering
                unified_filter_inputs = [*filter_inputs, navigation_state]

                for filter_component in [
                    "runs_status_filter",
                    "runs_date_filter",
                    "runs_type_filter",
                    "runs_search",
                    "runs_limit",
                    "runs_rating_filter",
                    "runs_version_filter",  # Add version filter
                ]:
                    if filter_component in components and components[filter_component] is not None:
                        components[filter_component].change(
                            fn=load_runs_with_filters,  # Use unified filter handler
                            inputs=unified_filter_inputs,
                            outputs=filter_outputs,
                        )

        # Runs table selection
        if "runs_table" in components:
            runs_output_keys = [
                "runs_details_group",
                "runs_detail_id",
                "runs_detail_status",
                # Content block visibility
                "runs_main_content_transfer",
                "runs_main_content_enhance",
                "runs_main_content_upscale",
                # Transfer content components
                "runs_input_video_1",
                "runs_input_video_2",
                "runs_input_video_3",
                "runs_input_video_4",
                "runs_output_video",
                "runs_prompt_text",
                # Enhancement content components
                "runs_original_prompt_enhance",
                "runs_enhanced_prompt_enhance",
                "runs_enhance_stats",
                # Upscale content components
                "runs_output_video_upscale",
                "runs_original_video_upscale",
                "runs_upscale_stats",
                "runs_upscale_prompt",
                # Info tab components
                "runs_info_id",
                "runs_info_prompt_id",
                "runs_info_status",
                "runs_info_duration",
                "runs_info_type",
                "runs_info_prompt_name",
                # Star buttons
                "star_1",
                "star_2",
                "star_3",
                "star_4",
                "star_5",
                "runs_info_rating",
                "runs_info_created",
                "runs_info_completed",
                "runs_info_output_path",
                "runs_info_input_paths",
                # Parameters and Logs
                "runs_params_json",
                "runs_log_path",
                "runs_log_output",
                # Upscale button and selection tracking
                "runs_upscale_selected_btn",
                "runs_selected_id",
                "runs_selected_info",
                # New components for upscaled output
                "runs_output_video_upscaled",
                "runs_upscaled_tab",
            ]
            outputs = get_components(*runs_output_keys)
            if outputs:
                logger.info("Connecting runs_table.select with {} outputs", len(outputs))
                components["runs_table"].select(
                    fn=on_runs_table_select,
                    inputs=[components["runs_table"]],
                    outputs=outputs,
                    # Note: scroll_to_output removed to prevent scrolling when tab loads
                )
            else:
                missing_runs = [k for k in runs_output_keys if k not in components]
                logger.warning("Missing components for runs table select: {}", missing_runs)
                # Try to connect with whatever components we have
                available_outputs = [components[k] for k in runs_output_keys if k in components]
                if available_outputs:
                    logger.info(
                        "Connecting with {} available outputs (partial)", len(available_outputs)
                    )
                    components["runs_table"].select(
                        fn=on_runs_table_select,
                        inputs=[components["runs_table"]],
                        outputs=available_outputs,
                        # Note: scroll_to_output removed to prevent scrolling when tab loads
                    )

            # Update selection info when a row is selected
            if "runs_selected_info" in components and "runs_selected_id" in components:
                components["runs_table"].select(
                    fn=update_runs_selection_info,
                    inputs=[components["runs_table"]],  # Pass table data
                    outputs=[components["runs_selected_info"], components["runs_selected_id"]],
                )

        # Runs gallery selection - reuse same outputs as table
        if "runs_gallery" in components:
            runs_output_keys = [
                "runs_details_group",
                "runs_detail_id",
                "runs_detail_status",
                # Content block visibility
                "runs_main_content_transfer",
                "runs_main_content_enhance",
                "runs_main_content_upscale",
                # Transfer content components
                "runs_input_video_1",
                "runs_input_video_2",
                "runs_input_video_3",
                "runs_input_video_4",
                "runs_output_video",
                "runs_prompt_text",
                # Enhancement content components
                "runs_original_prompt_enhance",
                "runs_enhanced_prompt_enhance",
                "runs_enhance_stats",
                # Upscale content components
                "runs_output_video_upscale",
                "runs_original_video_upscale",
                "runs_upscale_stats",
                "runs_upscale_prompt",
                # Info tab components
                "runs_info_id",
                "runs_info_prompt_id",
                "runs_info_status",
                "runs_info_duration",
                "runs_info_type",
                "runs_info_prompt_name",
                # Star buttons
                "star_1",
                "star_2",
                "star_3",
                "star_4",
                "star_5",
                "runs_info_rating",
                "runs_info_created",
                "runs_info_completed",
                "runs_info_output_path",
                "runs_info_input_paths",
                # Parameters and Logs
                "runs_params_json",
                "runs_log_path",
                "runs_log_output",
                # Upscale button and selection tracking
                "runs_upscale_selected_btn",
                "runs_selected_id",
                "runs_selected_info",
                # New components for upscaled output
                "runs_output_video_upscaled",
                "runs_upscaled_tab",
            ]
            outputs = get_components(*runs_output_keys)
            if outputs:
                logger.info("Connecting runs_gallery.select with {} outputs", len(outputs))
                # Add the selected_index state as an output
                outputs_with_index = [*outputs, components.get("runs_selected_index")]

                # Modified handler that also tracks the index
                def on_gallery_select_with_index(evt: gr.SelectData):
                    result = on_runs_gallery_select(evt)
                    # Add the selected index to the results
                    return [*result, evt.index if evt else 0]

                components["runs_gallery"].select(
                    fn=on_gallery_select_with_index,
                    inputs=[],
                    outputs=outputs_with_index,
                    # Note: scroll_to_output removed to prevent scrolling when tab loads
                )

        # Navigation buttons for gallery
        if (
            "runs_prev_btn" in components
            and "runs_next_btn" in components
            and "runs_selected_index" in components
        ):
            # Previous button handler
            def navigate_gallery_prev(current_index):
                """Navigate to previous item in gallery."""
                new_index = max(0, current_index - 1)
                return gr.update(selected_index=new_index), new_index

            # Next button handler
            def navigate_gallery_next(current_index):
                """Navigate to next item in gallery."""
                # We don't know the max, so just increment and let Gradio handle bounds
                new_index = current_index + 1
                return gr.update(selected_index=new_index), new_index

            components["runs_prev_btn"].click(
                fn=navigate_gallery_prev,
                inputs=[components["runs_selected_index"]],
                outputs=[components["runs_gallery"], components["runs_selected_index"]],
            )

            components["runs_next_btn"].click(
                fn=navigate_gallery_next,
                inputs=[components["runs_selected_index"]],
                outputs=[components["runs_gallery"], components["runs_selected_index"]],
            )

        # Delete selected run operation - Two-step process with preview
        if "runs_delete_selected_btn" in components and "runs_selected_id" in components:
            # Step 1: Show preview when delete button is clicked
            components["runs_delete_selected_btn"].click(
                fn=preview_delete_run,
                inputs=[components["runs_selected_id"]],
                outputs=[
                    components.get("runs_delete_dialog"),
                    components.get("runs_delete_preview"),
                    components.get("runs_delete_outputs_checkbox"),
                    components.get("runs_delete_id_hidden"),
                ],
            )

            # Step 2: Confirm deletion
            if "runs_confirm_delete_btn" in components:
                components["runs_confirm_delete_btn"].click(
                    fn=confirm_delete_run,
                    inputs=[
                        components.get("runs_delete_id_hidden"),
                        components.get("runs_delete_outputs_checkbox"),
                    ],
                    outputs=[
                        components.get("runs_selected_info"),
                        components.get("runs_delete_dialog"),
                    ],
                ).then(
                    fn=load_runs_with_filters,  # Use unified filter to maintain prompt filtering
                    inputs=[
                        components.get("runs_status_filter"),
                        components.get("runs_date_filter"),
                        components.get("runs_type_filter"),
                        components.get("runs_search"),
                        components.get("runs_limit"),
                        components.get("runs_rating_filter"),
                        components.get("runs_version_filter"),  # Add version filter
                        components.get("navigation_state"),  # Include navigation state
                    ],
                    outputs=[
                        components.get("runs_gallery"),
                        components.get("runs_table"),
                        components.get("runs_stats"),
                        components.get("navigation_state"),  # Update navigation state
                        components.get("runs_nav_filter_row"),  # Update filter indicator
                        components.get("runs_prompt_filter"),  # Update filter text
                    ],
                )

            # Cancel deletion
            if "runs_cancel_delete_btn" in components:
                components["runs_cancel_delete_btn"].click(
                    fn=cancel_delete_run,
                    inputs=[],
                    outputs=[
                        components.get("runs_selected_info"),
                        components.get("runs_delete_dialog"),
                    ],
                )

        # ========== Upscale Operations ==========
        # Import upscale handlers
        from cosmos_workflow.ui.tabs.runs_handlers import (
            cancel_upscale,
            execute_upscale,
            show_upscale_dialog,
        )

        # Upscale button - show dialog
        if "runs_upscale_selected_btn" in components and "runs_selected_id" in components:
            components["runs_upscale_selected_btn"].click(
                fn=show_upscale_dialog,
                inputs=[components["runs_selected_id"]],
                outputs=[
                    components.get("runs_upscale_dialog"),
                    components.get("runs_upscale_preview"),
                    components.get("runs_upscale_id_hidden"),
                ],
            )

        # Confirm upscale
        if "runs_confirm_upscale_btn" in components:
            components["runs_confirm_upscale_btn"].click(
                fn=execute_upscale,
                inputs=[
                    components.get("runs_upscale_id_hidden"),
                    components.get("runs_upscale_weight"),
                    components.get("runs_upscale_prompt_input"),
                ],
                outputs=[
                    components.get("runs_upscale_dialog"),
                    components.get("runs_selected_info"),
                ],
            ).then(
                # Refresh the display after queuing
                fn=load_runs_data_with_version_filter,
                inputs=[
                    components.get("runs_status_filter"),
                    components.get("runs_date_filter"),
                    components.get("runs_type_filter"),
                    components.get("runs_search"),
                    components.get("runs_limit"),
                    components.get("runs_rating_filter"),
                    components.get("runs_version_filter"),
                ],
                outputs=[
                    components.get("runs_gallery"),
                    components.get("runs_table"),
                    components.get("runs_stats"),
                ],
            )

        # Cancel upscale
        if "runs_cancel_upscale_btn" in components:
            components["runs_cancel_upscale_btn"].click(
                fn=cancel_upscale, outputs=[components.get("runs_upscale_dialog")]
            )

        # Clear navigation filter button
        if "clear_nav_filter_btn" in components:

            def clear_prompt_filter_and_reload(
                status, date, type_, search, limit, rating, version_filter
            ):
                """Clear the prompt filter in navigation state and reload runs."""

                # Clear navigation state
                cleared_state = {
                    "filter_type": None,
                    "filter_values": [],
                    "source_tab": None,
                }

                # Load runs without prompt filter but with version filter
                gallery, table, stats = load_runs_data_with_version_filter(
                    status, date, type_, search, limit, rating, version_filter
                )

                return (
                    gallery,
                    table,
                    stats,
                    cleared_state,  # Reset navigation state
                    gr.update(visible=False),  # Hide filter indicator
                    gr.update(value=""),  # Clear filter text
                )

            components["clear_nav_filter_btn"].click(
                fn=clear_prompt_filter_and_reload,
                inputs=[
                    components.get("runs_status_filter"),
                    components.get("runs_date_filter"),
                    components.get("runs_type_filter"),
                    components.get("runs_search"),
                    components.get("runs_limit"),
                    components.get("runs_rating_filter"),
                    components.get("runs_version_filter"),
                ],
                outputs=[
                    components.get("runs_gallery"),
                    components.get("runs_table"),
                    components.get("runs_stats"),
                    components.get("navigation_state"),  # Update navigation state
                    components.get("runs_nav_filter_row"),  # Hide filter indicator
                    components.get("runs_prompt_filter"),  # Clear filter text
                ],
            )

        # Load logs button
        if all(k in components for k in ["runs_load_logs_btn", "runs_log_path", "runs_log_output"]):
            components["runs_load_logs_btn"].click(
                fn=load_run_logs,
                inputs=[components["runs_log_path"]],
                outputs=[components["runs_log_output"]],
            )

        # Star rating button handlers
        if all(
            k in components
            for k in [
                "star_1",
                "star_2",
                "star_3",
                "star_4",
                "star_5",
                "runs_info_rating",
                "runs_info_id",
                "runs_status_filter",
                "runs_date_filter",
                "runs_type_filter",
                "runs_search",
                "runs_limit",
                "runs_rating_filter",
                "runs_version_filter",
                "runs_gallery",
                "runs_table",
                "runs_stats",
            ]
        ):
            # Function to handle star clicks and update display
            def handle_star_click(
                star_value,
                run_id,
                status_filter,
                date_filter,
                type_filter,
                search_text,
                limit,
                rating_filter,
                version_filter,
            ):
                """Handle star button click and save rating."""
                if not run_id:
                    # No run selected, return unchanged
                    return [gr.update()] * 10

                # Save the rating
                ops = CosmosAPI()
                if ops:
                    ops.set_run_rating(run_id, star_value)
                    logger.info("Set rating {} for run {}", star_value, run_id)

                # Refresh the runs display with version filter support
                gallery_data, table_data, stats = load_runs_data_with_version_filter(
                    status_filter,
                    date_filter,
                    type_filter,
                    search_text,
                    limit,
                    rating_filter,
                    version_filter,
                )

                # Update star button displays
                star_updates = []
                for i in range(1, 6):
                    if i <= star_value:
                        star_updates.append(
                            gr.update(value="★", elem_classes=["star-btn", "filled"])
                        )
                    else:
                        star_updates.append(gr.update(value="☆", elem_classes=["star-btn"]))

                return [
                    *star_updates,  # 5 star buttons
                    gr.update(value=star_value),  # runs_info_rating
                    gallery_data,  # runs_gallery
                    table_data,  # runs_table
                    stats,  # runs_stats
                ]

            # Connect each star button
            for i in range(1, 6):
                star_btn = components[f"star_{i}"]
                star_btn.click(
                    fn=lambda run_id, sf, df, tf, st, lm, rf, vf, star_val=i: handle_star_click(
                        star_val, run_id, sf, df, tf, st, lm, rf, vf
                    ),
                    inputs=[
                        components["runs_info_id"],
                        components["runs_status_filter"],
                        components["runs_date_filter"],
                        components["runs_type_filter"],
                        components["runs_search"],
                        components["runs_limit"],
                        components.get("runs_rating_filter"),
                        components.get("runs_version_filter"),
                    ],
                    outputs=[
                        components["star_1"],
                        components["star_2"],
                        components["star_3"],
                        components["star_4"],
                        components["star_5"],
                        components["runs_info_rating"],
                        components["runs_gallery"],
                        components["runs_table"],
                        components["runs_stats"],
                    ],
                )

        # Active Jobs Tab Events
        # Add stream button handler for manual refresh
        if "stream_btn" in components:

            def manual_refresh_jobs():
                """Manual refresh and stream for jobs tab."""
                yield from refresh_and_stream()

            outputs = get_components(
                "running_jobs_display", "job_status", "active_job_card", "log_display"
            )
            if outputs:
                components["stream_btn"].click(
                    fn=manual_refresh_jobs,
                    outputs=outputs,
                )

        # Clear logs button
        if "clear_logs_btn" in components and "log_viewer" in components:
            components["clear_logs_btn"].click(
                fn=lambda: (components["log_viewer"].clear(), components["log_viewer"].get_text()),
                outputs=[components.get("log_display")],
            )

        # Queue Control Events
        if "kill_job_btn" in components:
            # Kill job button shows confirmation
            components["kill_job_btn"].click(
                fn=show_kill_confirmation,
                outputs=[
                    components.get("kill_confirmation"),
                    components.get("kill_preview"),
                ],
            )

            # Cancel kill button
            components["cancel_kill_btn"].click(
                fn=cancel_kill_confirmation,
                outputs=components.get("kill_confirmation"),
            )

            # Confirm kill button
            components["confirm_kill_btn"].click(
                fn=execute_kill_job,
                outputs=[
                    components.get("kill_confirmation"),
                    components.get("job_status"),
                ],
            ).then(
                fn=check_running_jobs,
                outputs=[
                    components.get("running_jobs_display"),
                    components.get("job_status"),
                    components.get("active_job_card"),
                ],
            )

        # Queue pause/resume control
        if "queue_pause_checkbox" in components and "queue_status_indicator" in components:

            def toggle_queue_pause(paused):
                """Toggle queue pause state and update UI."""
                global queue_service
                if queue_service:
                    queue_service.set_queue_paused(paused)
                    if paused:
                        return "⏸️ **Queue: Paused**"
                    else:
                        return "✅ **Queue: Active**"
                return "❓ **Queue: Unknown**"

            components["queue_pause_checkbox"].change(
                fn=toggle_queue_pause,
                inputs=[components["queue_pause_checkbox"]],
                outputs=[components["queue_status_indicator"]],
            )

        # Batch size control
        if "batch_size" in components:

            def update_batch_size(size):
                """Safely update batch size with error handling."""
                if queue_service and size is not None:
                    try:
                        batch_size_int = int(float(size))  # Handle both int and float inputs
                        if 1 <= batch_size_int <= 16:  # Validate range
                            queue_service.set_batch_size(batch_size_int)
                        else:
                            logger.warning("Batch size %s out of range (1-16)", size)
                    except (ValueError, TypeError) as e:
                        logger.debug("Invalid batch size value: %s - %s", size, e)
                return None

            components["batch_size"].change(
                fn=update_batch_size,
                inputs=components["batch_size"],
            )

        # Queue Display Events
        if "refresh_queue_btn" in components and queue_handlers:
            # Refresh queue display
            components["refresh_queue_btn"].click(
                fn=queue_handlers.get_queue_display,
                outputs=[
                    components.get("queue_status"),
                    components.get("queue_table"),
                ],
            )

            # Auto-advance toggle
            if "auto_advance_toggle" in components:

                def toggle_auto_advance(enabled):
                    """Toggle auto-advance for queue processing."""
                    global queue_service
                    queue_service.set_auto_advance(enabled)

                components["auto_advance_toggle"].change(
                    fn=toggle_auto_advance, inputs=[components["auto_advance_toggle"]], outputs=[]
                )

            # Cancel selected job
            if "cancel_job_btn" in components and "selected_job_id" in components:

                def cancel_selected_job(job_id):
                    """Cancel the selected job and refresh the queue."""
                    # Handle None gracefully - minimal fix for the error
                    if not job_id:
                        return "No job selected", None, []

                    # Cancel the job
                    result = queue_handlers.cancel_job(job_id)

                    # Refresh queue display
                    status_text, table_data = queue_handlers.get_queue_display()

                    # Return updated displays
                    return result, status_text, table_data

                components["cancel_job_btn"].click(
                    fn=cancel_selected_job,
                    inputs=components["selected_job_id"],
                    outputs=[
                        components.get("job_status"),
                        components.get("queue_status"),
                        components.get("queue_table"),
                    ],
                )

            # Auto-refresh queue every 5 seconds when on jobs tab
            def auto_refresh_queue():
                """Auto-refresh queue display."""
                return queue_handlers.get_queue_display()

            # Set up a timer for auto-refresh
            # Create a timer that triggers every 5 seconds (less frequent to avoid conflicts)
            timer = gr.Timer(value=5, active=True)
            timer.tick(
                fn=auto_refresh_queue,
                outputs=[
                    components.get("queue_status"),
                    components.get("queue_table"),
                ],
            )

        # Queue table select handler (outside the refresh button check)
        if "queue_table" in components and "job_details" in components and queue_handlers:

            def on_queue_table_select(table_data, evt: gr.SelectData):
                """Handle selection of a job from the queue table."""
                try:
                    logger.info("Queue table select event triggered")

                    # Get selected row index
                    row_idx = evt.index[0] if isinstance(evt.index, list | tuple) else evt.index
                    logger.info("Selected row index: {}", row_idx)

                    # Extract job ID from table (column 1 has Job ID)
                    job_id = df_utils.get_cell_value(table_data, row_idx, 1, default=None)

                    logger.info("Selected job ID: {}", job_id)

                    if not job_id:
                        return gr.update(value="No job selected"), gr.update(visible=False), None

                    # Get job details
                    details = queue_handlers.get_job_details(job_id)

                    # Check if this is a queued job (to show cancel button)
                    # Extract status from the table data to determine if cancellable
                    status = df_utils.get_cell_value(table_data, row_idx, 3, default=None)

                    # Show cancel button only for queued jobs
                    show_cancel = status == "queued"

                    return gr.update(value=details), gr.update(visible=show_cancel), job_id

                except Exception as e:
                    logger.error("Error selecting job from queue: {}", e)
                    return (
                        gr.update(value=f"Error loading job details: {e}"),
                        gr.update(visible=False),
                        None,
                    )

            # Connect queue table select event
            components["queue_table"].select(
                fn=on_queue_table_select,
                inputs=[components["queue_table"]],
                outputs=[
                    components.get("job_details"),
                    components.get("cancel_job_btn"),
                    components.get("selected_job_id"),
                ],
            )

        # Load initial data
        initial_outputs = get_components(
            "input_gallery",
            "inputs_results_count",
            "ops_prompts_table",
            "running_jobs_display",
            "job_status",
        )

        # Debug: Check which components are missing
        required_components = [
            "input_gallery",
            "inputs_results_count",
            "ops_prompts_table",
            "running_jobs_display",
            "job_status",
        ]
        missing = [k for k in required_components if k not in components]
        if missing:
            logger.warning("Missing components for initial load: {}", missing)

        if initial_outputs:
            logger.info("Setting up initial data load with {} outputs", len(initial_outputs))

            def load_initial_data():
                """Load initial data efficiently."""
                gallery_data, results_text = load_input_gallery(inputs_dir)
                prompts_data = load_ops_prompts(50)
                # Only call check_running_jobs once
                try:
                    jobs_result = check_running_jobs()
                    jobs_display = jobs_result[0]
                    job_status = jobs_result[1]
                    # Note: active_job_card (jobs_result[2]) is not used here for initial load
                except Exception as e:
                    logger.debug("Could not check running jobs: {}", e)
                    jobs_display = "No containers"
                    job_status = "Not connected"
                return gallery_data, results_text, prompts_data, jobs_display, job_status

            app.load(
                fn=load_initial_data,
                outputs=initial_outputs,
            )
        else:
            logger.warning("Could not set up initial data load - missing components")

        # Set up automatic queue processing using a timer component
        # This replaces the background thread from the old QueueService
        def auto_process_queue():
            """Process next job in queue automatically."""
            global queue_service

            if queue_service is None:
                logger.warning("Queue service not initialized")
                return None

            try:
                # Check if queue is paused
                if hasattr(queue_service, "queue_paused") and queue_service.queue_paused:
                    logger.debug("Queue is paused, skipping processing")
                    return None

                # Only process if there are actually jobs in the queue
                status = queue_service.get_queue_status()
                queued_count = status.get("total_queued", 0)

                if queued_count > 0:
                    logger.debug("Queue has {} jobs, attempting to process next", queued_count)
                    result = queue_service.process_next_job()
                    if result:
                        logger.info(
                            "Auto-processed job: {} ({})",
                            result.get("job_id", "unknown"),
                            result.get("status", "unknown"),
                        )
                else:
                    # Only log this at debug level to avoid spam
                    logger.debug("Queue empty, nothing to process")

            except Exception as e:
                logger.error("Error in auto_process_queue: {}", e)

            return None

        # Create timer for automatic queue processing (inside gr.Blocks context)
        timer = gr.Timer(2)  # Trigger every 2 seconds
        timer.tick(fn=auto_process_queue, outputs=[])

    # Enable queue for long-running operations (prevents timeout)
    app.queue(
        max_size=100,  # Maximum number of queued requests
        default_concurrency_limit=1,  # Process one inference at a time
    )

    return app


# ============================================================================
# Application Entry Point
# ============================================================================
# For Gradio auto-reload CLI compatibility
# ============================================================================

# Lazy initialization to avoid creating UI on every import
_demo = None


def get_demo():
    """Get or create the demo instance."""
    global _demo
    if _demo is None:
        _demo = create_ui()
    return _demo


# Create the demo variable that Gradio CLI expects
demo = get_demo()

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860)  # noqa: S104
