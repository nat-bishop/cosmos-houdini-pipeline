"""Inference command for running Cosmos Transfer on remote GPU."""

import json

import click

from .base import CLIContext, handle_errors
from .helpers import (
    console,
    create_info_table,
    create_progress_context,
    display_dry_run_footer,
    display_dry_run_header,
    display_success,
    format_id,
    format_prompt_text,
)


@click.command()
@click.argument("run_id")
@click.option(
    "--upscale/--no-upscale",
    default=True,
    help="Enable/disable 4K upscaling after inference (default: --upscale)",
)
@click.option(
    "--upscale-weight", default=0.5, help="Control weight for upscaling (0.0-1.0) (default: 0.5)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without executing",
)
@click.pass_context
@handle_errors
def inference(ctx, run_id, upscale, upscale_weight, dry_run):
    r"""Run Cosmos Transfer inference with optional upscaling.

    Uses a run ID from the database to execute inference on a remote GPU.
    By default, this command runs both inference and 4K upscaling.
    Use --no-upscale to run inference only.
    Use --dry-run to preview what would happen without executing.

    \b
    Examples:
      cosmos inference rs_abc123              # Inference + upscaling
      cosmos inference rs_abc123 --no-upscale # Inference only
      cosmos inference rs_abc123 --dry-run    # Preview only
      cosmos inference rs_abc123 --upscale-weight 0.7
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    # Get run and prompt data
    run = ops.get_run(run_id)
    if not run:
        raise ValueError(f"Run not found: {run_id}")

    prompt = ops.get_prompt(run["prompt_id"])
    if not prompt:
        raise ValueError(f"Prompt not found: {run['prompt_id']}")

    # Handle dry-run mode
    if dry_run:
        display_dry_run_header()

        # Show what would happen
        dry_run_data = {
            "Run ID": format_id(run["id"]),
            "Prompt ID": format_id(prompt["id"]),
            "Status": run["status"],
            "Prompt text": format_prompt_text(prompt["prompt_text"]),
            "Input video": prompt["inputs"].get("video", "N/A"),
            "Model type": run["model_type"],
        }

        # Show weights if available
        if "weights" in run.get("execution_config", {}):
            weights = run["execution_config"]["weights"]
            dry_run_data["Weights"] = (
                f"vis={weights.get('vis', 0.25)}, edge={weights.get('edge', 0.25)}, depth={weights.get('depth', 0.25)}, seg={weights.get('seg', 0.25)}"
            )

        dry_run_data["Would upload"] = "Prompt data and video files to remote GPU"

        if upscale:
            dry_run_data["Would execute"] = "Inference + 4K upscaling"
            dry_run_data["Upscale weight"] = str(upscale_weight)
        else:
            dry_run_data["Would execute"] = "Inference only (no upscaling)"

        dry_run_data["Would download"] = "Generated video results"
        dry_run_data["Would update"] = "Run status to 'completed' in database"

        table = create_info_table(dry_run_data)
        console.print(table)

        display_dry_run_footer()
        return

    with create_progress_context(
        f"[cyan]Running {'inference + upscaling' if upscale else 'inference'}..."
    ) as progress:
        workflow_desc = "inference + upscaling" if upscale else "inference"
        task = progress.add_task(f"[cyan]Running {workflow_desc}...", total=None)

        # Execute the run using operations
        result = ops.execute_run(
            run_id=run_id,
            upscale=upscale,
            upscale_weight=upscale_weight,
        )

        progress.update(task, completed=True)

    # Display results
    results_data = {
        "Run ID": format_id(run_id),
        "Status": "Completed",
        "Output": result.get("output_path", "N/A"),
    }

    display_success(f"{workflow_desc.capitalize()} completed!", results_data)

    if ctx_obj.verbose:
        console.print("\n[cyan]Full results:[/cyan]")
        console.print_json(json.dumps(result, indent=2))
