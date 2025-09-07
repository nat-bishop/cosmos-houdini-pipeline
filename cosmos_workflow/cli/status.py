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
    ops = ctx_obj.get_operations()

    # Handle streaming mode
    if stream:
        with create_progress_context("[cyan]Connecting to remote instance...") as progress:
            task = progress.add_task("[cyan]Connecting to remote instance...", total=None)
            progress.update(task, completed=True)

        console.print("\n[bold][STREAMING] Docker Container Logs[/bold]\n")

        try:
            # Stream logs using operations
            ops.stream_logs()
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

        # Use operations to check status
        status_info = ops.check_status()

        progress.update(task, completed=True)

    # Build status information table
    status_data = {}

    # SSH status
    if status_info.get("ssh_status") == "connected":
        status_data["SSH Connection"] = "[green]✓ Connected[/green]"
    else:
        status_data["SSH Connection"] = "[red]✗ Failed[/red]"

    # Docker status
    docker_info = status_info.get("docker_status", {})
    if isinstance(docker_info, dict) and docker_info.get("docker_running"):
        status_data["Docker Daemon"] = "[green]✓ Running[/green]"
    else:
        status_data["Docker Daemon"] = "[red]✗ Not running[/red]"

    # GPU information
    gpu_info = status_info.get("gpu_info", {})
    if gpu_info:
        gpu_name = gpu_info.get("name", "Unknown")
        gpu_memory = gpu_info.get("memory_total", "Unknown")
        status_data["GPU"] = f"{gpu_name} ({gpu_memory})"
        status_data["CUDA Version"] = gpu_info.get("cuda_version", "Unknown")
    else:
        status_data["GPU"] = "[yellow]Not detected[/yellow]"

    # Container information
    containers = status_info.get("containers", [])
    if containers:
        status_data["Running Containers"] = f"[cyan]{len(containers)}[/cyan]"
        for i, container in enumerate(containers[:3]):  # Show first 3
            name = container.get("name", "unknown")
            state = container.get("state", "unknown")
            status_data[f"  Container {i + 1}"] = f"{name} ({state})"
    else:
        status_data["Running Containers"] = "[yellow]None[/yellow]"

    # Display the table
    console.print("\n[bold cyan]Remote GPU Status[/bold cyan]")
    table = create_info_table(status_data)
    console.print(table)

    # Show tips based on status
    if status_info.get("ssh_status") != "connected":
        console.print(
            "\n[yellow]Tip:[/yellow] Check your SSH configuration and network connection."
        )
    elif status_info.get("docker_status") != "running":
        console.print("\n[yellow]Tip:[/yellow] Docker may not be running on the remote instance.")
    elif not gpu_info:
        console.print("\n[yellow]Tip:[/yellow] GPU drivers may not be properly installed.")
    elif not containers:
        console.print("\n[yellow]Tip:[/yellow] Use 'cosmos inference' to start a container.")
