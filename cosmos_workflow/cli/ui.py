"""UI command for launching Gradio interface."""

import click


@click.command()
@click.option("--port", default=7860, help="Port number")
@click.option("--share", is_flag=True, help="Create public link")
def ui(port, share):
    """Launch web interface for workflow management."""
    from cosmos_workflow.ui.app import create_interface

    click.echo(f"Starting Gradio UI on port {port}...")
    click.echo(f"Open browser to: http://localhost:{port}")

    interface = create_interface()
    interface.launch(
        server_port=port,
        share=share,
        inbrowser=True,
        allowed_paths=["inputs/", "outputs/"],  # Allow serving video files
    )
