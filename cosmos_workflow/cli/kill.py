#!/usr/bin/env python3
"""Kill running Cosmos containers on the GPU instance."""

import click
from rich.console import Console
from rich.table import Table

from cosmos_workflow.api import CosmosAPI
from cosmos_workflow.utils.logging import logger


@click.command()
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def kill(force: bool) -> None:
    """Kill all running Cosmos containers on the GPU instance.

    This command will:
    - Connect to the GPU instance
    - Find all running containers for the Cosmos docker image
    - Kill them immediately (docker kill, not graceful stop)
    - Report how many containers were killed

    Warning: This will terminate any running inference or upscaling jobs!
    """
    console = Console()

    # Show warning and get confirmation unless --force is used
    if not force:
        console.print(
            "\n[yellow]⚠️  WARNING:[/yellow] This will kill ALL running Cosmos containers!"
        )
        console.print("Any running inference or upscaling jobs will be terminated immediately.")
        console.print("Logs may be incomplete for terminated jobs.\n")

        if not click.confirm("Are you sure you want to continue?"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

    try:
        console.print("\n[cyan]Connecting to GPU instance...[/cyan]")
        ops = CosmosAPI()

        # Kill containers
        console.print("[cyan]Searching for running containers...[/cyan]")
        result = ops.kill_containers()

        if result["status"] == "success":
            if result["killed_count"] == 0:
                console.print("\n[green]✓[/green] No running containers found.")
            else:
                # Show results in a table
                table = Table(title="Killed Containers", show_header=True)
                table.add_column("Container ID", style="cyan")
                table.add_column("Status", style="green")

                for container_id in result["killed_containers"]:
                    table.add_row(container_id[:12], "Killed")

                console.print("\n")
                console.print(table)
                console.print(
                    f"\n[green]✓[/green] Successfully killed {result['killed_count']} container(s)."
                )

                if result.get("message"):
                    console.print(f"[dim]{result['message']}[/dim]")
        else:
            error_msg = result.get("error", "Unknown error")
            console.print(f"\n[red]✗[/red] Failed to kill containers: {error_msg}")
            logger.error("Kill containers failed: %s", error_msg)

    except Exception as e:
        console.print(f"\n[red]✗[/red] Error: {e}")
        logger.error("Kill command failed: %s", e)
        raise click.ClickException(str(e)) from e


if __name__ == "__main__":
    kill()
