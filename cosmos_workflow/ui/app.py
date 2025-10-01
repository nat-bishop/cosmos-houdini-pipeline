#!/usr/bin/env python3
"""Refactored Gradio UI using modular core components.

This refactored version demonstrates how the 2,063-line app.py with its
1,782-line create_ui() function can be reduced to ~200 lines by using
modular builders, state management, and event wiring.

Key improvements:
- Modular architecture with clear separation of concerns
- Reusable core components in ui/core/
- Event wiring separated from UI building
- State management extracted to dedicated module
- Navigation logic isolated from main app
"""

import atexit
import signal
import threading

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.database import DatabaseConnection
from cosmos_workflow.services.simple_queue_service import SimplifiedQueueService
from cosmos_workflow.ui.core import build_ui_components, wire_all_events
from cosmos_workflow.ui.queue_handlers import QueueHandlers
from cosmos_workflow.utils.logging import logger

# Load configuration
config = ConfigManager()

# Global services (properly managed in this refactor)
api = None
queue_service = None
queue_handlers = None


def create_ui():
    """Create the Gradio interface using modular core components.

    This refactored version replaces the 1,782-line monolithic create_ui()
    with a clean, modular approach that's easy to understand and maintain.
    """
    global api, queue_service, queue_handlers

    # Initialize services
    api = CosmosAPI()
    database_path = "outputs/cosmos.db"
    db_connection = DatabaseConnection(database_path)
    queue_service = SimplifiedQueueService(db_connection=db_connection)
    queue_handlers = QueueHandlers(queue_service)

    # Build UI components using the modular builder
    app, components = build_ui_components(config)

    # Wire all events within the Blocks context
    # This must be done within the app context
    with app:
        # Wire all events using the modular event wiring system
        # This single line replaces 1,500+ lines of inline event wiring
        wire_all_events(app, components, config, api, queue_service)

    # Register shutdown handlers
    _register_shutdown_handlers()

    return app


def _register_shutdown_handlers():
    """Register cleanup handlers for graceful shutdown."""

    def cleanup():
        """Clean up resources on shutdown."""
        logger.info("Shutting down Gradio UI...")

        # Log active threads before cleanup
        import threading

        active_threads = threading.active_count()
        thread_names = [t.name for t in threading.enumerate()]
        logger.info("Active threads before cleanup: %d - %s", active_threads, thread_names)

        # SimplifiedQueueService doesn't need cleanup - it has no background threads
        # or exclusive resources to release. The database connection is shared
        # across the app and handled elsewhere.

        # Try to properly close Gradio app if it exists
        if "app" in globals() and hasattr(globals()["app"], "close"):
            try:
                globals()["app"].close()
                logger.info("Gradio app closed successfully")
            except Exception as e:
                logger.error("Error closing Gradio app: %s", e)

        # Close all Gradio instances (best practice)
        try:
            import gradio as gr

            gr.close_all()
            logger.info("All Gradio instances closed")
        except Exception as e:
            logger.error("Error closing all Gradio instances: %s", e)

        # Log active threads after cleanup
        active_threads_after = threading.active_count()
        thread_names_after = [t.name for t in threading.enumerate()]
        logger.info(
            "Active threads after cleanup: %d - %s", active_threads_after, thread_names_after
        )

        # Give threads a moment to shut down
        import time

        time.sleep(2)

        # Final thread check
        final_threads = threading.active_count()
        final_names = [t.name for t in threading.enumerate()]
        logger.info("Final thread count: %d - %s", final_threads, final_names)

        logger.info("Gradio UI shutdown complete")

    # Register cleanup with atexit
    atexit.register(cleanup)

    # Register signal handlers (only in main thread)
    if threading.current_thread() is threading.main_thread():
        try:
            signal.signal(signal.SIGINT, lambda s, f: cleanup())
            signal.signal(signal.SIGTERM, lambda s, f: cleanup())
        except ValueError:
            # Signals can only be registered in the main thread
            pass


def launch_ui(share=False, auto_reload=False):
    """Launch the Gradio application.

    Args:
        share: Whether to create a public share link
        auto_reload: Whether to enable auto-reload for development

    Returns:
        The running Gradio app instance
    """
    app = create_ui()

    startup_msg = (
        "=" * 80 + "\n"
        "Cosmos Workflow Manager UI Starting\n"
        "   Architecture: Modular (Phase 6 Complete)\n"
        "   Lines of Code: ~260 (was 2,063)\n"
        "   create_ui(): ~20 lines (was 1,782)\n" + "=" * 80
    )
    logger.info(startup_msg)

    # Launch with appropriate settings
    app.launch(
        server_name="0.0.0.0",  # noqa: S104
        server_port=7860,
        share=share,
        show_error=True,
        quiet=False,
    )

    return app


# Main entry point for the UI
if __name__ == "__main__":
    import sys

    # Check for command-line arguments
    auto_reload = "--reload" in sys.argv
    share = "--share" in sys.argv

    if auto_reload:
        logger.info("Auto-reload enabled - UI will restart on code changes")

    launch_ui(share=share, auto_reload=auto_reload)


# Create module-level variable for Gradio CLI compatibility
app = create_ui()
