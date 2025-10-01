"""CLI command for upscaling video outputs to 4K resolution."""

import sys

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
    "--prompt",
    "-p",
    help="Optional prompt to guide the upscaling process",
)
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
def upscale(
    ctx: CLIContext,
    run_id: str,
    prompt: str | None,
    weight: float,
    dry_run: bool,
):
    """Upscale the output of a completed inference run to 4K resolution.

    RUN_ID must be a valid run ID (rs_xxx or run_xxx) from a completed inference.

    \b
    Examples:
      # Basic upscaling
      cosmos upscale rs_abc123

      # With custom control weight
      cosmos upscale rs_abc123 --weight 0.7

      # With guiding prompt
      cosmos upscale rs_abc123 --prompt "cinematic quality"

      # Preview without executing
      cosmos upscale rs_abc123 --dry-run

    The upscaling process:
      1. Validates the run exists and is completed
      2. Creates a new upscaling run in the database
      3. Executes 4K upscaling on the GPU
      4. Downloads the upscaled output

    Note:
      To upscale external video files, first create a prompt and run
      inference with the video, then upscale the resulting run output.

    Monitor progress with: cosmos status --stream
    """
    ops = ctx.get_operations()

    # Validate run ID format
    if not run_id.startswith("rs_") and not run_id.startswith("run_"):
        display_error(
            f"Invalid run ID format: {run_id}\n"
            f"Expected format: rs_xxx or run_xxx\n\n"
            f"To upscale external video files, first create a prompt and run "
            f"inference with the video, then upscale the resulting run output."
        )
        sys.exit(1)

    # Handle dry-run mode
    if dry_run:
        console.print("[cyan]Dry-run mode - Preview only[/cyan]\n")

        # Get run info for preview
        run = ops.get_run(run_id)
        if not run:
            display_error(f"Run not found: {run_id}")
            sys.exit(1)

        console.print(f"[bold]Would upscale from run:[/bold] {format_id(run_id)}")
        console.print(f"[bold]Run status:[/bold] {run['status']}")
        if run.get("outputs"):
            console.print(f"[bold]Run output:[/bold] {run['outputs'].get('output_path', 'N/A')}")

        console.print(f"[bold]Control weight:[/bold] {weight}")
        if prompt:
            console.print(f"[bold]Prompt:[/bold] {prompt}")
        console.print("\n[yellow]No changes made (dry-run)[/yellow]")
        return

    # Execute upscaling
    with create_progress_context(
        f"[cyan]Starting upscaling for run {format_id(run_id)}..."
    ) as progress:
        task = progress.add_task(
            f"[cyan]Upscaling with control weight {weight}...",
            total=None,
        )

        try:
            # Call the upscale method with run_id
            result = ops.upscale(
                run_id=run_id,
                control_weight=weight,
                prompt=prompt,
            )

            progress.update(task, completed=True)

        except ValueError as e:
            progress.stop()
            display_error(str(e))
            sys.exit(1)
        except Exception as e:
            progress.stop()
            display_error(f"Upscaling failed: {e}")
            sys.exit(1)

    # Display results
    if result["status"] in ["success", "started", "completed"]:
        results_data = {
            "Upscale Run ID": format_id(result["upscale_run_id"]),
            "Control Weight": str(weight),
            "Status": "Completed",
        }

        results_data["Source Run"] = format_id(run_id)

        if prompt:
            results_data["Prompt"] = prompt[:50] + "..." if len(prompt) > 50 else prompt

        if result.get("output_path"):
            results_data["Output Path"] = result["output_path"]

        display_success("Upscaling completed successfully!", results_data)

    else:
        display_error(f"Upscaling failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


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
                result = ops.upscale(
                    video_source=run_id,
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
        sys.exit(1)
