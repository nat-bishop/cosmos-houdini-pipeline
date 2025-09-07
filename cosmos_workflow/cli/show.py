"""Show command for displaying detailed prompt information."""

import json
import logging
from datetime import datetime
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


def get_operations() -> Any:
    """Get the workflow operations from context.

    Returns:
        CosmosAPI: The workflow operations instance.
    """
    ctx = click.get_current_context()
    return ctx.obj.get_operations()


@click.command(name="show")
@click.argument("prompt_id")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_context
def show_command(ctx: click.Context, prompt_id: str, output_json: bool) -> None:
    """Show detailed information about a prompt and its runs.

    Displays complete prompt details including all associated runs,
    their status, and outputs.

    Examples:
        cosmos show ps_abc123
        cosmos show ps_abc123 --json
    """
    ops = get_operations()

    try:
        prompt_data = ops.get_prompt_with_runs(prompt_id)

        if not prompt_data:
            console.print(f"[yellow]Prompt not found: {prompt_id}[/yellow]")
            return

        if output_json:
            # Output as JSON
            click.echo(json.dumps(prompt_data, indent=2))
        else:
            # Output as rich formatted display

            # Format timestamps
            created_at = prompt_data["created_at"]
            if isinstance(created_at, str):
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

            # Create prompt info panel
            prompt_info = f"""[bold cyan]ID:[/bold cyan] {prompt_data["id"]}
[bold cyan]Model:[/bold cyan] {prompt_data["model_type"]}
[bold cyan]Created:[/bold cyan] {created_at}

[bold cyan]Prompt Text:[/bold cyan]
{prompt_data["prompt_text"]}"""

            # Add inputs if present
            if prompt_data.get("inputs"):
                inputs_str = json.dumps(prompt_data["inputs"], indent=2)
                prompt_info += f"\n\n[bold cyan]Inputs:[/bold cyan]\n{inputs_str}"

            # Add parameters if present
            if prompt_data.get("parameters"):
                params_str = json.dumps(prompt_data["parameters"], indent=2)
                prompt_info += f"\n\n[bold cyan]Parameters:[/bold cyan]\n{params_str}"

            console.print(Panel(prompt_info, title="Prompt Details", border_style="blue"))

            # Display runs if any
            runs = prompt_data.get("runs", [])
            if runs:
                console.print(f"\n[bold]Associated Runs ({len(runs)} total):[/bold]")

                # Create runs table
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Run ID", style="cyan", no_wrap=True)
                table.add_column("Status", style="white")
                table.add_column("Created", style="green")
                table.add_column("Duration", style="yellow")
                table.add_column("Output", style="dim")

                for run in runs:
                    # Format status with color
                    status = run["status"]
                    if status == "completed":
                        status_text = f"[green]{status}[/green]"
                    elif status == "failed":
                        status_text = f"[red]{status}[/red]"
                    elif status == "running":
                        status_text = f"[yellow]{status}[/yellow]"
                    else:  # pending
                        status_text = f"[dim]{status}[/dim]"

                    # Format created timestamp
                    created = run["created_at"]
                    if isinstance(created, str):
                        try:
                            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                            created = dt.strftime("%m-%d %H:%M")
                        except ValueError:
                            pass

                    # Calculate duration if completed
                    duration = "-"
                    if run.get("started_at") and run.get("completed_at"):
                        try:
                            start = datetime.fromisoformat(run["started_at"].replace("Z", "+00:00"))
                            end = datetime.fromisoformat(run["completed_at"].replace("Z", "+00:00"))
                            delta = end - start
                            minutes = int(delta.total_seconds() / 60)
                            seconds = int(delta.total_seconds() % 60)
                            duration = f"{minutes}m {seconds}s"
                        except (ValueError, TypeError):
                            pass

                    # Get output path if available
                    output = "-"
                    if run.get("outputs"):
                        if "video_path" in run["outputs"]:
                            output = run["outputs"]["video_path"]
                            # Truncate long paths
                            if len(output) > 40:
                                output = "..." + output[-37:]
                        elif "enhanced_prompt_id" in run["outputs"]:
                            output = f"Enhanced: {run['outputs']['enhanced_prompt_id']}"

                    table.add_row(
                        run["id"],
                        status_text,
                        created,
                        duration,
                        output,
                    )

                console.print(table)
            else:
                console.print("\n[yellow]No runs found for this prompt[/yellow]")

    except Exception as e:
        logger.error("Failed to show prompt details: %s", e)
        console.print(f"[red]Error: Failed to show prompt details - {e}[/red]")
        ctx.exit(1)
