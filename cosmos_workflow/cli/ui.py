"""UI command for launching Gradio interface."""

import logging
import socket
import subprocess
import time

import click

from cosmos_workflow.config import ConfigManager

logger = logging.getLogger(__name__)


def kill_process_on_port(port: int) -> bool:
    """Kill any process using the specified port (Windows only).

    Args:
        port: Port number to free up

    Returns:
        True if a process was killed, False otherwise
    """
    try:
        # Find PIDs using the port
        result = subprocess.run(
            f"netstat -ano | findstr :{port}", shell=True, capture_output=True, text=True
        )

        if not result.stdout:
            return False

        # Extract unique PIDs
        pids = set()
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 5 and f":{port}" in parts[1]:
                pid = parts[-1]
                if pid.isdigit():
                    pids.add(pid)

        # Kill processes
        killed = False
        for pid in pids:
            logger.info("Killing process %s on port %s", pid, port)
            click.echo(f"  Terminating process {pid}...")

            kill_result = subprocess.run(
                f"taskkill /F /PID {pid}", shell=True, capture_output=True, text=True
            )

            if "SUCCESS" in kill_result.stdout:
                killed = True

        if killed:
            time.sleep(1)  # Give time for port to be released

        return killed

    except Exception as e:
        logger.warning("Error killing process on port %s: %s", port, e)
        return False


def is_port_in_use(port: int, host: str = "0.0.0.0") -> bool:
    """Check if a port is currently in use.

    Args:
        port: Port number to check
        host: Host address to check

    Returns:
        True if port is in use, False otherwise
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            # Try to bind to the port
            if host == "0.0.0.0":
                s.bind(("", port))
            else:
                s.bind((host, port))
            return False
        except OSError:
            return True


@click.command()
@click.option("--port", default=None, type=int, help="Port number (default: from config.toml)")
@click.option("--host", default=None, help="Host to bind to (default: from config.toml)")
@click.option("--share", is_flag=True, help="Create public link")
def ui(port, host, share):
    """Launch web interface for workflow management."""
    from cosmos_workflow.ui.app import create_ui

    # Load configuration
    config = ConfigManager()
    ui_config = config._config_data.get("ui", {})

    # Use command line args if provided, otherwise use config
    port = port or ui_config.get("port", 7860)
    host = host or ui_config.get("host", "0.0.0.0")  # noqa: S104
    share = share or ui_config.get("share", False)

    # Check if port is in use and kill existing process if needed
    if is_port_in_use(port, host):
        click.echo(f"Port {port} is currently in use, attempting to free it...")
        logger.info("Port %s is in use, attempting to free it", port)

        if kill_process_on_port(port):
            click.echo(f"✓ Port {port} has been freed")
            logger.info("Port %s has been freed", port)
            time.sleep(1)  # Brief pause to ensure port is released
        else:
            click.echo(f"Warning: Could not automatically free port {port}")
            click.echo(
                "Please manually close any existing UI instances or use a different port with --port"
            )
            logger.warning("Could not automatically free port %s", port)
            return

    click.echo(f"Starting Cosmos Workflow Manager UI on {host}:{port}...")
    logger.info("Starting UI on %s:%s", host, port)

    if host == "0.0.0.0":  # noqa: S104
        click.echo(f"📌 Open browser to: http://localhost:{port} (or use machine's IP)")
    else:
        click.echo(f"📌 Open browser to: http://{host}:{port}")

    interface = create_ui()
    interface.launch(
        server_name=host,
        server_port=port,
        share=share,
        inbrowser=True,
        allowed_paths=["inputs/", "outputs/"],  # Allow serving video files
    )
