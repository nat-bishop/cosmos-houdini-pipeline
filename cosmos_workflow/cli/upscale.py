"""CLI command for upscaling video outputs to 4K resolution."""

from pathlib import Path

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
@click.option(
    "--from-run",
    "-r",
    "run_id",
    help="Upscale output from an existing run ID",
)
@click.option(
    "--video",
    "-v",
    "video_path",
    type=click.Path(exists=True, path_type=Path),
    help="Upscale a video file from disk",
)
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
    run_id: str | None,
    video_path: Path | None,
    prompt: str | None,
    weight: float,
    dry_run: bool,
):
    """Upscale video to 4K resolution using AI-powered enhancement.

    You must specify either --from-run OR --video as the source.

    \b
    Examples:
      # From existing run
      cosmos upscale --from-run rs_abc123
      cosmos upscale --from-run rs_abc123 --weight 0.7
      cosmos upscale --from-run rs_abc123 --prompt "cinematic quality"

      # From video file
      cosmos upscale --video path/to/video.mp4
      cosmos upscale --video video.mp4 --weight 0.3
      cosmos upscale --video video.mp4 --prompt "8K ultra HD"

      # Preview without executing
      cosmos upscale --from-run rs_abc123 --dry-run
      cosmos upscale --video video.mp4 --dry-run

    The upscaling process:
      1. Validates the video source (run or file)
      2. Creates a new upscaling run in the database
      3. Executes 4K upscaling on the GPU
      4. Downloads the upscaled output

    Monitor progress with: cosmos status --stream
    """
    ops = ctx.get_operations()

    # Validate that exactly one source is provided
    if not run_id and not video_path:
        display_error("You must specify either --from-run or --video")
        raise click.Exit(1)

    if run_id and video_path:
        display_error("Cannot specify both --from-run and --video")
        raise click.Exit(1)

    # Validate run ID format if provided
    if run_id and not run_id.startswith("rs_") and not run_id.startswith("run_"):
        display_error(f"Invalid run ID format: {run_id}")
        raise click.Exit(1)

    # Handle dry-run mode
    if dry_run:
        console.print("[cyan]Dry-run mode - Preview only[/cyan]\n")

        if run_id:
            # Get run info for preview
            run = ops.get_run(run_id)
            if not run:
                display_error(f"Run not found: {run_id}")
                raise click.Exit(1)

            console.print(f"[bold]Would upscale from run:[/bold] {format_id(run_id)}")
            console.print(f"[bold]Run status:[/bold] {run['status']}")
            if run.get("outputs"):
                console.print(
                    f"[bold]Run output:[/bold] {run['outputs'].get('output_path', 'N/A')}"
                )
        else:
            console.print(f"[bold]Would upscale video:[/bold] {video_path}")
            console.print(
                f"[bold]File size:[/bold] {video_path.stat().st_size / (1024 * 1024):.2f} MB"
            )

        console.print(f"[bold]Control weight:[/bold] {weight}")
        if prompt:
            console.print(f"[bold]Prompt:[/bold] {prompt}")
        console.print("\n[yellow]No changes made (dry-run)[/yellow]")
        return

    # Determine source description for progress messages
    if run_id:
        source_desc = f"run {format_id(run_id)}"
    else:
        source_desc = f"video {video_path.name}"

    # Execute upscaling
    with create_progress_context(f"[cyan]Starting upscaling for {source_desc}...") as progress:
        task = progress.add_task(
            f"[cyan]Upscaling with control weight {weight}...",
            total=None,
        )

        try:
            # Call the appropriate method based on source
            if run_id:
                result = ops.upscale(
                    video_source=run_id,
                    control_weight=weight,
                    prompt=prompt,
                )
            else:
                result = ops.upscale(
                    video_source=str(video_path),
                    control_weight=weight,
                    prompt=prompt,
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
    if result["status"] in ["success", "started", "completed"]:
        results_data = {
            "Upscale Run ID": format_id(result["upscale_run_id"]),
            "Control Weight": str(weight),
            "Status": "Completed",
        }

        if run_id:
            results_data["Source Run"] = format_id(run_id)
        else:
            results_data["Source Video"] = str(video_path)

        if prompt:
            results_data["Prompt"] = prompt[:50] + "..." if len(prompt) > 50 else prompt

        if result.get("output_path"):
            results_data["Output Path"] = result["output_path"]

        display_success("Upscaling completed successfully!", results_data)

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
        raise click.Exit(1)
