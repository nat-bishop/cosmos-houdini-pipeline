"""List commands for viewing prompts and runs."""

import json
import logging
from datetime import datetime

import click
from rich.console import Console
from rich.table import Table

from .base import CLIContext

logger = logging.getLogger(__name__)
console = Console()


@click.group(name="list")
def list_group():
    """List prompts and runs."""
    pass


@list_group.command(name="prompts")
@click.option(
    "--model",
    type=click.Choice(["transfer", "enhancement", "reason", "predict"], case_sensitive=False),
    help="Filter by model type",
)
@click.option(
    "--limit",
    type=int,
    default=50,
    help="Maximum number of results to show (default: 50)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_context
def list_prompts(ctx: click.Context, model: str | None, limit: int, output_json: bool) -> None:
    """List all prompts in the database.

    Examples:
        cosmos list prompts
        cosmos list prompts --model transfer
        cosmos list prompts --limit 10
        cosmos list prompts --json
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    try:
        prompts = ops.list_prompts(model_type=model, limit=limit)

        if output_json:
            # Output as JSON
            click.echo(json.dumps(prompts, indent=2))
        else:
            # Output as rich table
            if not prompts:
                console.print("[yellow]No prompts found[/yellow]")
                return

            table = Table(title=f"Prompts ({len(prompts)} found)")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Model", style="magenta")
            table.add_column("Prompt", style="white", max_width=50)
            table.add_column("Created", style="green")

            for prompt in prompts:
                # Truncate long prompts
                prompt_text = prompt["prompt_text"]
                if len(prompt_text) > 50:
                    prompt_text = prompt_text[:47] + "..."

                # Format timestamp
                created_at = prompt["created_at"]
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        created_at = dt.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        pass  # Keep original string if parsing fails

                table.add_row(
                    prompt["id"],
                    prompt["model_type"],
                    prompt_text,
                    created_at,
                )

            console.print(table)

    except Exception as e:
        logger.error("Failed to list prompts: {}", e)
        console.print(f"[red]Error: Failed to list prompts - {e}[/red]")
        ctx.exit(1)


@list_group.command(name="runs")
@click.option(
    "--status",
    type=click.Choice(["pending", "running", "completed", "failed"], case_sensitive=False),
    help="Filter by run status",
)
@click.option(
    "--prompt",
    help="Filter by prompt ID",
)
@click.option(
    "--limit",
    type=int,
    default=50,
    help="Maximum number of results to show (default: 50)",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format",
)
@click.pass_context
def list_runs(
    ctx: click.Context, status: str | None, prompt: str | None, limit: int, output_json: bool
) -> None:
    """List all runs in the database.

    Examples:
        cosmos list runs
        cosmos list runs --status completed
        cosmos list runs --prompt ps_abc123
        cosmos list runs --status failed --prompt ps_abc123
        cosmos list runs --json
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    try:
        runs = ops.list_runs(status=status, prompt_id=prompt, limit=limit)

        if output_json:
            # Output as JSON
            click.echo(json.dumps(runs, indent=2))
        else:
            # Output as rich table
            if not runs:
                console.print("[yellow]No runs found[/yellow]")
                return

            table = Table(title=f"Runs ({len(runs)} found)")
            table.add_column("Run ID", style="cyan", no_wrap=True)
            table.add_column("Prompt ID", style="blue", no_wrap=True)
            table.add_column("Status", style="white")
            table.add_column("Model", style="magenta")
            table.add_column("Created", style="green")

            for run in runs:
                # Color code status
                status_text = run["status"]
                if status_text == "completed":
                    status_text = f"[green]{status_text}[/green]"
                elif status_text == "failed":
                    status_text = f"[red]{status_text}[/red]"
                elif status_text == "running":
                    status_text = f"[yellow]{status_text}[/yellow]"
                else:  # pending
                    status_text = f"[dim]{status_text}[/dim]"

                # Format timestamp
                created_at = run["created_at"]
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                        created_at = dt.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        pass  # Keep original string if parsing fails

                table.add_row(
                    run["id"],
                    run["prompt_id"],
                    status_text,
                    run["model_type"],
                    created_at,
                )

            console.print(table)

    except Exception as e:
        logger.error("Failed to list runs: {}", e)
        console.print(f"[red]Error: Failed to list runs - {e}[/red]")
        ctx.exit(1)
