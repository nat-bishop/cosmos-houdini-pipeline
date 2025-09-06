"""Data integrity verification command."""

from pathlib import Path

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
    service = ctx_obj.get_workflow_service()

    console.print("[bold cyan]Verifying data integrity...[/bold cyan]\n")

    issues = []
    warnings = []
    stats = {
        "total_runs": 0,
        "checked_runs": 0,
        "missing_files": 0,
        "orphaned_dirs": 0,
    }

    # Check all runs in database
    console.print("[cyan]Checking database runs...[/cyan]")
    runs = service.list_runs(limit=None)
    stats["total_runs"] = len(runs)

    for run in runs:
        run_id = run["id"]
        run_dir = Path(f"outputs/run_{run_id}")
        outputs = run.get("outputs", {})

        # Check if run directory exists
        if not run_dir.exists():
            if run["status"] == "completed":
                issues.append(f"Missing directory for completed run: {run_id}")
                stats["missing_files"] += 1
            continue

        stats["checked_runs"] += 1

        # Check output_path if specified
        output_path = outputs.get("output_path")
        if output_path and not Path(output_path).exists():
            issues.append(f"Missing file: {output_path} (Run: {run_id})")
            stats["missing_files"] += 1

        # For completed video generation runs, check expected files
        if run["status"] == "completed" and outputs.get("type") != "text_enhancement":
            expected_files = ["output.mp4"]
            if outputs.get("upscaled"):
                expected_files.append("output_upscaled.mp4")

            for filename in expected_files:
                file_path = run_dir / filename
                if not file_path.exists():
                    # Check if it might be using old naming
                    old_name = filename.replace("output", "result")
                    old_path = run_dir / old_name
                    if old_path.exists():
                        warnings.append(
                            f"Using old filename '{old_name}' instead of '{filename}' (Run: {run_id})"
                        )
                    else:
                        issues.append(f"Missing expected file: {file_path} (Run: {run_id})")
                        stats["missing_files"] += 1

    # Check for orphaned directories
    console.print("[cyan]Checking for orphaned directories...[/cyan]")
    outputs_dir = Path("outputs")
    if outputs_dir.exists():
        for dir_path in outputs_dir.glob("run_*"):
            if dir_path.is_dir():
                # Extract run ID from directory name
                run_id = dir_path.name.replace("run_", "")

                # Check if run exists in database
                try:
                    existing_run = service.get_run(run_id)
                    if not existing_run:
                        issues.append(f"Orphaned directory: {dir_path} (no database entry)")
                        stats["orphaned_dirs"] += 1
                except Exception:
                    # Run not found in database
                    issues.append(f"Orphaned directory: {dir_path} (no database entry)")
                    stats["orphaned_dirs"] += 1

    # Display results
    console.print("\n[bold]Verification Results:[/bold]\n")

    # Statistics table
    stats_table = Table(title="Statistics", show_header=True)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="white")

    stats_table.add_row("Total runs in database", str(stats["total_runs"]))
    stats_table.add_row("Runs with directories", str(stats["checked_runs"]))
    stats_table.add_row("Missing files", str(stats["missing_files"]))
    stats_table.add_row("Orphaned directories", str(stats["orphaned_dirs"]))

    console.print(stats_table)
    console.print()

    # Display issues
    if issues:
        console.print(f"[bold red]Found {len(issues)} issue(s):[/bold red]")
        for issue in issues:
            console.print(f"  [red]✗[/red] {issue}")
    else:
        console.print("[bold green]✓ No integrity issues found![/bold green]")

    # Display warnings
    if warnings:
        console.print(f"\n[bold yellow]Found {len(warnings)} warning(s):[/bold yellow]")
        for warning in warnings:
            console.print(f"  [yellow]⚠[/yellow] {warning}")

    # Fix mode (future implementation)
    if fix and issues:
        console.print("\n[dim]Note: Auto-fix functionality not yet implemented[/dim]")

    # Summary
    console.print("\n[bold]Summary:[/bold]")
    if not issues and not warnings:
        console.print("[green]✓ Database and filesystem are in sync[/green]")
    elif not issues:
        console.print("[yellow]⚠ Some warnings found but no critical issues[/yellow]")
    else:
        console.print(f"[red]✗ Found {len(issues)} issue(s) that need attention[/red]")

    return len(issues)  # Return count for scripting
