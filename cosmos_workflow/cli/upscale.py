"""CLI command for upscaling inference run outputs (Phase 3)."""

import click

from cosmos_workflow.cli.base import CLIContext
from cosmos_workflow.cli.helpers import (
    console,
    create_progress_context,
    display_error,
    display_success,
    format_id,
)


@click.command(name="upscale")
@click.argument("run_id", required=True)
@click.option(
    "--weight",
    "-w",
    type=click.FloatRange(0.0, 1.0),
    default=0.5,
    help="Control weight for upscaling (0.0-1.0)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview the upscaling operation without executing",
)
@click.pass_obj
def upscale(ctx: CLIContext, run_id: str, weight: float, dry_run: bool):
    """Upscale the output of a completed inference run.

    Creates a new database run with model_type="upscale" that operates
    on the output video from the specified inference run.

    \b
    Examples:
      cosmos upscale rs_abc123                  # Upscale with default weight
      cosmos upscale rs_abc123 --weight 0.7     # Upscale with custom weight
      cosmos upscale rs_abc123 -w 0.3           # Using shorthand
      cosmos upscale rs_abc123 --dry-run        # Preview without executing

    The upscaling process:
      1. Validates the parent run is completed
      2. Creates a new upscaling run in the database
      3. Executes 4K upscaling on the GPU
      4. Downloads the upscaled output

    Monitor progress with: cosmos status --stream
    """
    ops = ctx.get_operations()

    # Validate run ID format
    if not run_id.startswith("rs_") and not run_id.startswith("run_"):
        display_error(f"Invalid run ID format: {run_id}")
        raise click.Exit(1)

    # Handle dry-run mode
    if dry_run:
        console.print("[cyan]Dry-run mode - Preview only[/cyan]\n")

        # Get run info for preview
        run = ops.get_run(run_id)
        if not run:
            display_error(f"Run not found: {run_id}")
            raise click.Exit(1)

        console.print(f"[bold]Would upscale run:[/bold] {format_id(run_id)}")
        console.print(f"[bold]Status:[/bold] {run['status']}")
        if run.get("outputs"):
            console.print(f"[bold]Output:[/bold] {run['outputs'].get('output_path', 'N/A')}")
        console.print(f"[bold]Control weight:[/bold] {weight}")
        console.print("\n[yellow]No changes made (dry-run)[/yellow]")
        return

    # Execute upscaling
    with create_progress_context(
        f"[cyan]Starting upscaling for {format_id(run_id)}..."
    ) as progress:
        task = progress.add_task(
            f"[cyan]Upscaling with control weight {weight}...",
            total=None,
        )

        try:
            result = ops.upscale_run(
                run_id=run_id,
                control_weight=weight,
            )

            progress.update(task, completed=True)

        except ValueError as e:
            progress.stop()
            display_error(str(e))
            raise click.Exit(1) from e
        except Exception as e:
            progress.stop()
            display_error(f"Upscaling failed: {e}")
            raise click.Exit(1) from e

    # Display results
    if result["status"] == "success":
        results_data = {
            "Upscale Run ID": format_id(result["upscale_run_id"]),
            "Parent Run ID": format_id(run_id),
            "Control Weight": str(weight),
            "Status": "Started in background",
        }

        if result.get("output_path"):
            results_data["Output Path"] = result["output_path"]

        display_success("Upscaling started successfully!", results_data)

        # Show monitoring instructions
        console.print("\n[cyan]Monitor progress with:[/cyan]")
        console.print("  cosmos status --stream")
        console.print("\n[cyan]Check upscaling run:[/cyan]")
        console.print(f"  cosmos show run {result['upscale_run_id']}")

    else:
        display_error(f"Upscaling failed: {result.get('error', 'Unknown error')}")
        raise click.Exit(1)


# Support batch upscaling (multiple runs)
@click.command(name="upscale-batch", hidden=True)
@click.argument("run_ids", nargs=-1, required=True)
@click.option(
    "--weight",
    "-w",
    type=click.FloatRange(0.0, 1.0),
    default=0.5,
    help="Control weight for all upscaling operations",
)
@click.pass_obj
def upscale_batch(ctx: CLIContext, run_ids: tuple[str, ...], weight: float):
    """Upscale multiple inference runs (batch mode).

    Hidden command for batch upscaling operations.
    """
    ops = ctx.get_operations()

    results = []
    failures = []

    with create_progress_context(f"[cyan]Upscaling {len(run_ids)} runs...") as progress:
        for run_id in run_ids:
            task = progress.add_task(
                f"[cyan]Upscaling {format_id(run_id)}...",
                total=None,
            )

            try:
                result = ops.upscale_run(
                    run_id=run_id,
                    control_weight=weight,
                )

                if result["status"] == "success":
                    results.append(result)
                else:
                    failures.append((run_id, result.get("error", "Unknown error")))

            except Exception as e:
                failures.append((run_id, str(e)))

            progress.update(task, completed=True)

    # Display summary
    if results:
        console.print(
            f"\n[green]✓ Successfully started {len(results)} upscaling operations[/green]"
        )
        for result in results:
            console.print(f"  • {format_id(result['upscale_run_id'])}")

    if failures:
        console.print(f"\n[red]✗ Failed to upscale {len(failures)} runs:[/red]")
        for run_id, error in failures:
            console.print(f"  • {format_id(run_id)}: {error}")

    if failures:
        raise click.Exit(1)
