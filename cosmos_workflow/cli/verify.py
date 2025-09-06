"""Data integrity verification command."""

import click
from rich.console import Console
from rich.table import Table

from .base import CLIContext, handle_errors

console = Console()


@click.command("verify")
@click.option(
    "--fix",
    is_flag=True,
    help="Attempt to fix issues (currently only reports)",
)
@click.pass_context
@handle_errors
def verify(ctx, fix):
    r"""Verify database-filesystem integrity.

    Checks for:
    - Database paths that point to non-existent files
    - Orphaned directories without database entries
    - Missing output files for completed runs

    \b
    Examples:
      cosmos verify
      cosmos verify --fix  # Future: auto-fix issues
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    console.print("[bold cyan]Verifying data integrity...[/bold cyan]\n")

    # Use the new verify_integrity operation
    result = ops.verify_integrity()

    issues = result["issues"]
    warnings = result["warnings"]
    stats = result["stats"]

    # Display statistics
    stats_table = Table(title="Verification Statistics", box=None)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="white")

    stats_table.add_row("Total Runs", str(stats["total_runs"]))
    stats_table.add_row("Checked Runs", str(stats["checked_runs"]))
    stats_table.add_row("Missing Files", str(stats["missing_files"]))
    stats_table.add_row("Orphaned Directories", str(stats["orphaned_dirs"]))

    console.print(stats_table)
    console.print()

    # Display issues
    if issues:
        console.print(f"[red]Found {len(issues)} issues:[/red]\n")

        for i, issue in enumerate(issues, 1):
            if issue["type"] == "missing_output":
                console.print(
                    f"  {i}. [yellow]Missing output file[/yellow] for run "
                    f"[cyan]{issue['run_id']}[/cyan]: {issue['path']}"
                )
            elif issue["type"] == "missing_input":
                console.print(
                    f"  {i}. [yellow]Missing input directory[/yellow] for prompt "
                    f"[cyan]{issue['prompt_id']}[/cyan]: {issue['path']}"
                )
            else:
                console.print(f"  {i}. [yellow]{issue['type']}[/yellow]: {issue}")

        if fix:
            console.print("\n[yellow]Note: Auto-fix not yet implemented[/yellow]")
    else:
        console.print("[green]✓ No integrity issues found![/green]")

    # Display warnings
    if warnings:
        console.print(f"\n[yellow]Warnings ({len(warnings)}):[/yellow]")
        for warning in warnings:
            console.print(f"  - {warning}")

    # Summary
    console.print()
    if issues:
        console.print(f"[bold red]Verification complete: {len(issues)} issues found[/bold red]")
    else:
        console.print("[bold green]Verification complete: All checks passed[/bold green]")
