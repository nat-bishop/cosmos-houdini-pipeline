"""UI command for launching Gradio interface."""

import click

from cosmos_workflow.config import ConfigManager


@click.command()
@click.option("--port", default=None, type=int, help="Port number (default: from config.toml)")
@click.option("--host", default=None, help="Host to bind to (default: from config.toml)")
@click.option("--share", is_flag=True, help="Create public link")
def ui(port, host, share):
    """Launch web interface for workflow management."""
    from cosmos_workflow.ui.app import create_ui

    # Load configuration
    config = ConfigManager()
    ui_config = config.config.get("ui", {})

    # Use command line args if provided, otherwise use config
    port = port or ui_config.get("port", 7860)
    host = host or ui_config.get("host", "0.0.0.0")  # noqa: S104
    share = share or ui_config.get("share", False)

    click.echo(f"Starting Gradio UI on {host}:{port}...")
    if host == "0.0.0.0":  # noqa: S104
        click.echo(f"Open browser to: http://localhost:{port} (or use machine's IP)")
    else:
        click.echo(f"Open browser to: http://{host}:{port}")

    interface = create_ui()
    interface.launch(
        server_name=host,
        server_port=port,
        share=share,
        inbrowser=True,
        allowed_paths=["inputs/", "outputs/"],  # Allow serving video files
    )
