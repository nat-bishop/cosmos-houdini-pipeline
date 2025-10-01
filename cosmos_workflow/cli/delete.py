"""Delete commands for removing prompts and runs."""

import logging

import click
from rich.console import Console
from rich.panel import Panel

from .base import CLIContext

logger = logging.getLogger(__name__)
console = Console()


@click.group(name="delete")
def delete_group():
    """Delete prompts and runs from the system."""
    pass


@delete_group.command(name="prompt")
@click.argument("prompt_id", required=False)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--all",
    is_flag=True,
    help="Delete all prompts (cannot be used with PROMPT_ID)",
)
@click.option(
    "--keep-outputs",
    is_flag=True,
    help="Keep output files (default: delete outputs)",
)
@click.pass_context
def delete_prompt(
    ctx: click.Context, prompt_id: str, force: bool, all: bool, keep_outputs: bool
) -> None:
    """Delete a prompt and all associated runs.

    This will permanently delete:
    - The prompt from the database
    - All runs associated with the prompt
    - All output directories for those runs (unless --keep-outputs is used)

    Examples:
        cosmos delete prompt ps_abc123
        cosmos delete prompt ps_abc123 --force
        cosmos delete prompt ps_abc123 --keep-outputs
        cosmos delete prompt --all
    """
    # Check for mutually exclusive options
    if prompt_id and all:
        console.print("[red]Error: Cannot specify both a prompt ID and --all[/red]")
        ctx.exit(2)

    if not prompt_id and not all:
        console.print("[red]Error: Must specify either a prompt ID or --all[/red]")
        ctx.exit(2)

    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    # Handle --all flag
    if all:
        preview = ops.preview_all_prompts_deletion()

        prompts = preview.get("prompts", [])
        if not prompts:
            console.print("[yellow]No prompts found to delete[/yellow]")
            return

        # Display bulk deletion preview
        console.print(
            f"\n[bold red]This will delete ALL {preview['total_prompt_count']} prompts[/bold red]"
        )
        if preview.get("total_run_count"):
            console.print(f"[yellow]and {preview['total_run_count']} associated runs[/yellow]")

        # Show warning for active runs
        if preview.get("total_active_runs", 0) > 0:
            console.print(
                f"\n[bold red]WARNING: {preview['total_active_runs']} ACTIVE RUNS WILL BE DELETED![/bold red]"
            )
            console.print(
                "[red]These runs appear to be running or uploading. Deletion will proceed anyway.[/red]"
            )

        if preview.get("total_size") and not keep_outputs:
            console.print(f"[yellow]Total output size: {preview['total_size']}[/yellow]")

        # Show sample of prompts
        console.print("\n[yellow]Sample of prompts to delete:[/yellow]")
        for prompt in prompts[:5]:
            console.print(f"  - {prompt['id']}: {prompt.get('prompt_text', '')[:50]}...")
        if len(prompts) > 5:
            console.print(f"  ... and {len(prompts) - 5} more")

        # Extra confirmation for bulk delete
        if not force:
            console.print("\n[bold red]This action cannot be undone![/bold red]")
            confirmation = click.prompt("Type 'DELETE ALL' to confirm")
            if confirmation != "DELETE ALL":
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        # Perform bulk deletion
        result = ops.delete_all_prompts(keep_outputs=keep_outputs)

        if not result["success"]:
            console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
            ctx.exit(1)

        deleted = result["deleted"]
        console.print(
            f"\n[green]Successfully deleted {len(deleted['prompt_ids'])} prompt(s)[/green]"
        )
        if deleted.get("run_ids"):
            console.print(f"  - {len(deleted['run_ids'])} associated run(s)")
        if not keep_outputs and deleted.get("directories"):
            console.print(f"  - {len(deleted['directories'])} output directory(ies)")
        return

    # Preview what will be deleted
    preview = ops.preview_prompt_deletion(prompt_id, keep_outputs=keep_outputs)

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

    console.print(Panel(panel_text, title="Prompt to Delete", border_style="yellow"))

    runs = preview.get("runs", [])
    if runs:
        console.print(f"\n[yellow]This will also delete {len(runs)} run(s):[/yellow]")

        # Check for active runs and show warning
        active_runs = [r for r in runs if r.get("status") in ("running", "uploading")]
        if active_runs:
            console.print(
                f"\n[bold red]WARNING: {len(active_runs)} ACTIVE RUNS WILL BE DELETED![/bold red]"
            )
            console.print(
                "[red]These runs appear to be running or uploading. Deletion will proceed anyway.[/red]"
            )

        for run in runs[:5]:  # Show first 5 runs
            status_color = (
                "green"
                if run.get("status") == "completed"
                else "red"
                if run.get("status") in ("running", "uploading")
                else "yellow"
            )
            console.print(
                f"  - {run['id']} ([{status_color}]{run.get('status', 'unknown')}[/{status_color}])"
            )
        if len(runs) > 5:
            console.print(f"  ... and {len(runs) - 5} more")

    # Show output handling
    if keep_outputs:
        console.print("\n[green]Output files: KEPT[/green]")
    else:
        directories = preview.get("directories_to_delete", [])
        if directories:
            console.print("\n[yellow]Output directories to delete:[/yellow]")
            for dir_path in directories[:3]:
                console.print(f"  - {dir_path}")
            if len(directories) > 3:
                console.print(f"  ... and {len(directories) - 3} more")

        # Enhanced file preview if available
        if preview.get("files_summary"):
            summary = preview["files_summary"]
            console.print(
                f"\n[yellow]Total files to delete: {summary['total_files']} files ({summary['total_size']})[/yellow]"
            )
            for file_type, info in summary.get("by_type", {}).items():
                console.print(f"  - {info['count']} {file_type} files ({info['size']})")

    # Confirm deletion unless --force is used
    if not force:
        console.print("\n[bold red]This action cannot be undone![/bold red]")
        if not click.confirm("Are you sure you want to delete this prompt and all its runs?"):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    # Perform deletion
    result = ops.delete_prompt(prompt_id, keep_outputs=keep_outputs)

    if not result["success"]:
        console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
        ctx.exit(1)

    # Display success message
    deleted = result["deleted"]
    console.print("\n[green]Successfully deleted:[/green]")
    console.print(f"  - Prompt: {deleted['prompt_id']}")
    console.print(f"  - {len(deleted['run_ids'])} run(s)")
    console.print(f"  - {len(deleted['directories'])} output directory(ies)")


@delete_group.command(name="run")
@click.argument("run_id", required=False)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--all",
    is_flag=True,
    help="Delete all runs (cannot be used with RUN_ID)",
)
@click.option(
    "--keep-outputs",
    is_flag=True,
    help="Keep output files (default: delete outputs)",
)
@click.pass_context
def delete_run(ctx: click.Context, run_id: str, force: bool, all: bool, keep_outputs: bool) -> None:
    """Delete a run and its output directory.

    This will permanently delete:
    - The run from the database
    - The output directory for the run (unless --keep-outputs is used)

    The associated prompt will NOT be deleted.

    Examples:
        cosmos delete run rs_xyz789
        cosmos delete run rs_xyz789 --force
        cosmos delete run rs_xyz789 --keep-outputs
        cosmos delete run --all
    """
    # Check for mutually exclusive options
    if run_id and all:
        console.print("[red]Error: Cannot specify both a run ID and --all[/red]")
        ctx.exit(2)

    if not run_id and not all:
        console.print("[red]Error: Must specify either a run ID or --all[/red]")
        ctx.exit(2)

    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    # Handle --all flag
    if all:
        preview = ops.preview_all_runs_deletion()

        runs = preview.get("runs", [])
        if not runs:
            console.print("[yellow]No runs found to delete[/yellow]")
            return

        # Display bulk deletion preview
        console.print(f"\n[bold red]This will delete ALL {preview['total_count']} runs[/bold red]")

        # Show warning for active runs
        if preview.get("total_active_runs", 0) > 0:
            console.print(
                f"\n[bold red]WARNING: {preview['total_active_runs']} ACTIVE RUNS WILL BE DELETED![/bold red]"
            )
            console.print(
                "[red]These runs appear to be running or uploading. Deletion will proceed anyway.[/red]"
            )

        if preview.get("total_size"):
            if keep_outputs:
                console.print(f"[yellow]Total output size: {preview['total_size']}[/yellow]")
            else:
                console.print(
                    f"[yellow]Total output size to delete: {preview['total_size']}[/yellow]"
                )

        # Show sample of runs
        console.print("\n[yellow]Sample of runs to delete:[/yellow]")
        for run in runs[:5]:
            status_color = (
                "green"
                if run.get("status") == "completed"
                else "red"
                if run.get("status") in ("running", "uploading")
                else "yellow"
            )
            console.print(
                f"  - {run['id']} ([{status_color}]{run.get('status', 'unknown')}[/{status_color}])"
            )
        if len(runs) > 5:
            console.print(f"  ... and {len(runs) - 5} more")

        # Extra confirmation for bulk delete
        if not force:
            console.print("\n[bold red]This action cannot be undone![/bold red]")
            confirmation = click.prompt("Type 'DELETE ALL' to confirm")
            if confirmation != "DELETE ALL":
                console.print("[yellow]Deletion cancelled[/yellow]")
                return

        # Perform bulk deletion
        result = ops.delete_all_runs(keep_outputs=keep_outputs)

        if not result["success"]:
            console.print(f"[red]Error: {result.get('error', 'Unknown error')}[/red]")
            ctx.exit(1)

        deleted = result["deleted"]
        console.print(f"\n[green]Successfully deleted {len(deleted['run_ids'])} run(s)[/green]")
        if not keep_outputs and deleted.get("directories"):
            console.print(f"  - {len(deleted['directories'])} output directory(ies)")
        return

    # Preview what will be deleted
    preview = ops.preview_run_deletion(run_id, keep_outputs=keep_outputs)

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

    # Show output handling
    if keep_outputs:
        console.print("\n[green]Output files: KEPT[/green]")
    else:
        if preview.get("directory_to_delete"):
            console.print("\n[yellow]Output directory to delete:[/yellow]")
            console.print(f"  - {preview['directory_to_delete']}")

        # Enhanced file preview if available
        if preview.get("files"):
            console.print(
                f"\n[yellow]Output directory: {preview.get('directory_to_delete', 'outputs/')}[/yellow]"
            )
            total_files = preview.get("total_files", 0)
            total_size = preview.get("total_size", "0 B")

            for file_type, file_info in preview["files"].items():
                console.print(
                    f"  - {file_info['count']} {file_type} files ({file_info['total_size']})"
                )
                for file_detail in file_info.get("files", [])[:3]:
                    console.print(f"    • {file_detail['name']} ({file_detail['size']})")
                if file_info.get("files") and len(file_info["files"]) > 3:
                    console.print(f"    ... and {len(file_info['files']) - 3} more")

            console.print(f"\n[yellow]Total: {total_files} files ({total_size})[/yellow]")

    # Warn if run is active
    if run_info.get("status") in ("running", "uploading"):
        console.print("\n[bold red]WARNING: THIS RUN IS CURRENTLY ACTIVE![/bold red]")
        console.print(f"[red]Status: {run_info.get('status')}. Deletion will proceed anyway.[/red]")

    # Confirm deletion unless --force is used
    if not force:
        console.print("\n[bold red]This action cannot be undone![/bold red]")
        if not click.confirm("Are you sure you want to delete this run?"):
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    # Perform deletion
    result = ops.delete_run(run_id, keep_outputs=keep_outputs)

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
