"""Delete commands for removing prompts and runs."""

import logging
from typing import Any

import click
from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()


def get_service() -> Any:
    """Get the workflow service from context.

    Returns:
        WorkflowService: The workflow service instance.
    """
    ctx = click.get_current_context()
    return ctx.obj.get_workflow_service()


@click.group(name="delete")
def delete_group():
    """Delete prompts and runs from the system."""
    pass


@delete_group.command(name="prompt")
@click.argument("prompt_id")
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def delete_prompt(ctx: click.Context, prompt_id: str, force: bool) -> None:
    """Delete a prompt and all associated runs.

    This will permanently delete:
    - The prompt from the database
    - All runs associated with the prompt
    - All output directories for those runs

    Examples:
        cosmos delete prompt ps_abc123
        cosmos delete prompt ps_abc123 --force
    """
    service = get_service()

    # Preview what will be deleted
    preview = service.preview_prompt_deletion(prompt_id)

    # Check if prompt exists
    if preview.get("error"):
        console.print(f"[red]Error: {preview['error']}[/red]")
        ctx.exit(1)

    # Display preview
    console.print("\n[yellow]Preview of deletion:[/yellow]")

    prompt_info = preview["prompt"]
    prompt_text = prompt_info.get("prompt_text", "")
    if len(prompt_text) > 100:
        prompt_text = prompt_text[:100] + "..."

    panel_text = f"[bold]Prompt:[/bold] {prompt_info['id']}\n"
    panel_text += f"[bold]Text:[/bold] {prompt_text}"
    if "model_type" in prompt_info:
        panel_text += f"\n[bold]Type:[/bold] {prompt_info['model_type']}"

    console.print(Panel(panel_text, title="Prompt to Delete", border_style="yellow"))

    runs = preview.get("runs", [])
    if runs:
        console.print(f"\n[yellow]This will also delete {len(runs)} run(s):[/yellow]")
        for run in runs[:5]:  # Show first 5 runs
            status_color = "green" if run.get("status") == "completed" else "yellow"
            console.print(
                f"  - {run['id']} ([{status_color}]{run.get('status', 'unknown')}[/{status_color}])"
            )
        if len(runs) > 5:
            console.print(f"  ... and {len(runs) - 5} more")

    directories = preview.get("directories_to_delete", [])
    if directories:
        console.print("\n[yellow]Output directories to delete:[/yellow]")
        for dir_path in directories[:3]:
            console.print(f"  - {dir_path}")
        if len(directories) > 3:
            console.print(f"  ... and {len(directories) - 3} more")

    # Confirm deletion unless --force is used
    if not force:
        console.print("\n[bold red]This action cannot be undone![/bold red]")
        if not click.confirm("Are you sure you want to delete this prompt and all its runs?"):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    # Perform deletion
    result = service.delete_prompt(prompt_id)

    if not result["success"]:
        console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
        ctx.exit(1)

    # Display success message
    deleted = result["deleted"]
    console.print("\n[green]Successfully deleted:[/green]")
    console.print(f"  - Prompt: {deleted['prompt_id']}")
    console.print(f"  - {len(deleted['run_ids'])} run(s)")
    console.print(f"  - {len(deleted['directories'])} output director(ies)")


@delete_group.command(name="run")
@click.argument("run_id")
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.pass_context
def delete_run(ctx: click.Context, run_id: str, force: bool) -> None:
    """Delete a run and its output directory.

    This will permanently delete:
    - The run from the database
    - The output directory for the run

    The associated prompt will NOT be deleted.

    Examples:
        cosmos delete run rs_xyz789
        cosmos delete run rs_xyz789 --force
    """
    service = get_service()

    # Preview what will be deleted
    preview = service.preview_run_deletion(run_id)

    # Check if run exists
    if preview.get("error"):
        console.print(f"[red]Error: {preview['error']}[/red]")
        ctx.exit(1)

    # Display preview
    console.print("\n[yellow]Preview of deletion:[/yellow]")

    run_info = preview["run"]
    status_color = "green" if run_info.get("status") == "completed" else "yellow"

    console.print(
        Panel(
            f"[bold]Run:[/bold] {run_info['id']}\n"
            f"[bold]Status:[/bold] [{status_color}]{run_info.get('status', 'unknown')}[/{status_color}]\n"
            f"[bold]Prompt:[/bold] {run_info.get('prompt_id', 'unknown')}",
            title="Run to Delete",
            border_style="yellow",
        )
    )

    if preview.get("directory_to_delete"):
        console.print("\n[yellow]Output directory to delete:[/yellow]")
        console.print(f"  - {preview['directory_to_delete']}")

    # Warn if run is active
    if run_info.get("status") in ("running", "uploading"):
        console.print("\n[bold red]WARNING: This run appears to be active![/bold red]")
        console.print("[yellow]Deleting active runs may cause issues.[/yellow]")

    # Confirm deletion unless --force is used
    if not force:
        console.print("\n[bold red]This action cannot be undone![/bold red]")
        if not click.confirm("Are you sure you want to delete this run?"):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    # Perform deletion
    result = service.delete_run(run_id)

    if not result["success"]:
        console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
        ctx.exit(1)

    # Display success message
    deleted = result["deleted"]
    console.print("\n[green]Successfully deleted:[/green]")
    console.print(f"  - Run: {deleted['run_id']}")
    if deleted.get("directory"):
        console.print(f"  - Output directory: {deleted['directory']}")

    # Display any warnings
    if result.get("warnings"):
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result["warnings"]:
            console.print(f"  [yellow]Warning: {warning}[/yellow]")
