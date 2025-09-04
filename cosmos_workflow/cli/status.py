"""Status command for checking remote GPU instance."""

import click

from .base import CLIContext, handle_errors
from .helpers import console, create_info_table, create_progress_context


@click.command()
@click.option(
    "--stream",
    is_flag=True,
    help="Stream container logs in real-time instead of showing status",
)
@click.pass_context
@handle_errors
def status(ctx, stream):
    """Check remote GPU instance status or stream container logs.

    Shows SSH connectivity, Docker status, and available resources
    on the configured remote GPU instance.

    Use --stream to stream logs from the most recent container in real-time.
    """
    ctx_obj: CLIContext = ctx.obj

    # Handle streaming mode
    if stream:
        with create_progress_context("[cyan]Connecting to remote instance...") as progress:
            task = progress.add_task("[cyan]Connecting to remote instance...", total=None)

            orchestrator = ctx_obj.get_orchestrator()
            orchestrator._initialize_services()

            progress.update(task, completed=True)

        console.print("\n[bold][STREAMING] Docker Container Logs[/bold]\n")

        try:
            # Stream logs from most recent container
            with orchestrator.ssh_manager:
                orchestrator.docker_executor.stream_container_logs()
        except RuntimeError as e:
            console.print(f"\n[red]Error:[/red] {e}")
            console.print(
                "[yellow]Tip:[/yellow] Make sure a container is running. Use 'cosmos inference' to start one."
            )
        except KeyboardInterrupt:
            # Already handled in stream_container_logs, just exit cleanly
            pass

        return  # Exit after streaming

    # Regular status check
    with create_progress_context("[cyan]Checking remote status...") as progress:
        task = progress.add_task("[cyan]Checking remote status...", total=None)

        orchestrator = ctx_obj.get_orchestrator()
        status_info = orchestrator.check_remote_status()

        progress.update(task, completed=True)

    # Display status
    console.print("\n[bold]Remote Instance Status[/bold]")

    # Build status data for table
    status_data = {}

    if status_info["ssh_status"] == "connected":
        status_data["SSH Status"] = "[green]Connected[/green]"
        status_data["Remote Directory"] = status_info.get("remote_directory", "N/A")
        status_data["Directory Exists"] = (
            "[green]Yes[/green]" if status_info.get("remote_directory_exists") else "[red]No[/red]"
        )

        docker_status = status_info.get("docker_status", {})
        status_data["Docker Running"] = (
            "[green]Yes[/green]" if docker_status.get("docker_running") else "[red]No[/red]"
        )

        if ctx_obj.verbose and docker_status.get("docker_running"):
            status_data["Docker Images"] = (
                f"{len(docker_status.get('available_images', []))} available"
            )
            status_data["Running Containers"] = str(docker_status.get("running_containers", "0"))
    else:
        status_data["SSH Status"] = "[red]Disconnected[/red]"
        status_data["Error"] = status_info.get("error", "Unknown error")

    # Display the table
    table = create_info_table(status_data)
    console.print(table)
