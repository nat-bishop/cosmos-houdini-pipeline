#!/usr/bin/env python3
"""Start the Cosmos Workflow UI with optional auto-reload support.

This script handles launching the Gradio UI either directly or through
the Gradio CLI for auto-reload functionality based on configuration.
"""

import subprocess
import sys
from pathlib import Path

from cosmos_workflow.config import ConfigManager
from cosmos_workflow.utils.logging import logger


def main():
    """Launch the UI based on configuration settings."""
    # Load configuration
    config = ConfigManager()
    ui_config = config._config_data.get("ui", {})

    # Check if auto-reload is enabled
    auto_reload = ui_config.get("auto_reload", False)
    watch_dirs = ui_config.get("watch_dirs", ["cosmos_workflow"])
    port = ui_config.get("port", 7860)
    host = ui_config.get("host", "127.0.0.1")

    # Path to the app module
    app_path = Path(__file__).parent / "app.py"

    if auto_reload:
        # Use gradio CLI for auto-reload
        logger.info("Starting UI with auto-reload enabled")
        logger.info(f"Watching directories: {watch_dirs}")

        # Build the command
        cmd = ["gradio", str(app_path)]

        # Add watch directories
        for watch_dir in watch_dirs:
            cmd.extend(["--watch-dirs", watch_dir])

        # Note: gradio CLI doesn't support custom host/port directly
        # Those are configured in the app.py file itself
        logger.info(f"Running command: {' '.join(cmd)}")

        try:
            # Run the gradio CLI
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start UI with auto-reload: {e}")
            sys.exit(1)
        except FileNotFoundError:
            logger.error("Gradio CLI not found. Please ensure gradio is installed.")
            logger.info("You can install it with: pip install gradio")
            sys.exit(1)
    else:
        # Run directly without auto-reload
        logger.info("Starting UI without auto-reload")
        logger.info(f"Server will run on {host}:{port}")

        # Import and run the app directly
        from cosmos_workflow.ui.app import create_ui

        app = create_ui()

        # Configure queue for synchronous execution
        app.queue(
            max_size=50,
            default_concurrency_limit=1,
            status_update_rate="auto",
        ).launch(
            share=ui_config.get("share", False),
            server_name=host,
            server_port=port,
            show_error=True,
            inbrowser=True,
        )


if __name__ == "__main__":
    main()
