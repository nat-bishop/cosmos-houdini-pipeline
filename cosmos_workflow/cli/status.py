"""Status command for checking remote GPU instance."""

import click

from .base import CLIContext, handle_errors
from .helpers import console, create_info_table, create_progress_context


@click.command()
@click.option(
    "--stream",
    "-s",
    is_flag=True,
    help="Stream logs from active container after showing status",
)
@click.pass_context
@handle_errors
def status(ctx, stream):
    """Check remote GPU instance status.

    Shows SSH connectivity, Docker status, and available resources
    on the configured remote GPU instance.

    With --stream, will also stream logs from any active container.
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

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

        # Add GPU utilization metrics if available
        gpu_util = gpu_info.get("gpu_utilization")
        if gpu_util:
            status_data["GPU Usage"] = gpu_util

        # Add memory usage details if available
        mem_used = gpu_info.get("memory_used")
        mem_total = gpu_info.get("memory_total")
        mem_util = gpu_info.get("memory_utilization")
        if mem_used and mem_total and mem_util:
            status_data["Memory Usage"] = f"{mem_used} / {mem_total} ({mem_util})"
    else:
        status_data["GPU"] = "[yellow]Not detected[/yellow]"

    # Active run information (Phase 4: show what's actually running)
    active_run = status_info.get("active_run")
    if active_run:
        status_data["Active Operation"] = f"[green]{active_run['model_type'].upper()}[/green]"
        status_data["  Run ID"] = active_run["id"][:8]  # Show first 8 chars
        status_data["  Prompt"] = active_run["prompt_id"]
        if active_run.get("started_at"):
            status_data["  Started"] = active_run["started_at"]

    # Container information (now expecting single container)
    container = status_info.get("container")
    if container:
        if not active_run:
            # Container without run - shouldn't happen but report it
            status_data["Running Container"] = f"[yellow]{container['name']} (orphaned)[/yellow]"
            console.print(
                "\n[yellow]Warning:[/yellow] Container running without active run in database"
            )
        else:
            status_data["Running Container"] = f"[cyan]{container['name']}[/cyan]"
        status_data["  Status"] = container["status"]
        status_data["  Container ID"] = container["id_short"]
        # Show warning if multiple containers detected
        if "warning" in container:
            console.print(f"\n[yellow]Warning:[/yellow] {container['warning']}")
    else:
        if active_run:
            # Run without container - zombie run
            status_data["Running Container"] = "[red]Missing![/red]"
            console.print("\n[red]Error:[/red] Database shows active run but no container found")
        else:
            status_data["Running Container"] = "[yellow]None[/yellow]"

    # Display the table
    console.print("\n[bold cyan]Remote GPU Status[/bold cyan]")
    table = create_info_table(status_data)
    console.print(table)

    # Show tips based on status
    if status_info.get("ssh_status") != "connected":
        console.print(
            "\n[yellow]Tip:[/yellow] Check your SSH configuration and network connection."
        )
    elif isinstance(docker_info, dict) and not docker_info.get("docker_running"):
        console.print("\n[yellow]Tip:[/yellow] Docker may not be running on the remote instance.")
    elif not gpu_info:
        console.print("\n[yellow]Tip:[/yellow] GPU drivers may not be properly installed.")
    elif not container:
        console.print("\n[yellow]Tip:[/yellow] Use 'cosmos inference' to start a container.")

    # Stream logs if requested and container is running
    if stream and container:
        console.print("\n[cyan]Starting log stream...[/cyan]")
        console.print("[dim]Press Ctrl+C to stop streaming[/dim]\n")

        # We already have the container info from status check
        container_id = container["id"]

        try:
            ops.stream_container_logs(container_id)
        except RuntimeError as e:
            console.print(f"[red]Error streaming logs:[/red] {e}")
        except KeyboardInterrupt:
            console.print("\n[cyan]Stopped streaming logs[/cyan]")
    elif stream and not container:
        console.print("\n[yellow]No container running to stream logs from.[/yellow]")
