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
    format_weights,
)


@click.command()
@click.argument("prompt_ids", nargs=-1, required=True)
@click.option(
    "--prompts-file",
    type=click.File("r"),
    help="File containing prompt IDs, one per line",
)
@click.option(
    "--weights",
    "-w",
    nargs=4,
    type=float,
    default=[0.25, 0.25, 0.25, 0.25],
    help="Control weights: VIS EDGE DEPTH SEG (default: 0.25 0.25 0.25 0.25)",
)
@click.option("--steps", default=35, help="Number of inference steps (default: 35)")
@click.option("--guidance", default=7.0, help="Guidance scale (CFG) (default: 7.0)")
@click.option("--seed", default=1, help="Random seed for reproducibility (default: 1)")
@click.option("--fps", default=24, help="Output video FPS (default: 24)")
@click.option("--sigma-max", default=70.0, help="Maximum noise level (default: 70.0)")
@click.option(
    "--blur-strength",
    default="medium",
    type=click.Choice(["very_low", "low", "medium", "high", "very_high"]),
    help="Blur strength (default: medium)",
)
@click.option(
    "--canny-threshold",
    default="medium",
    type=click.Choice(["very_low", "low", "medium", "high", "very_high"]),
    help="Canny edge threshold (default: medium)",
)
@click.option(
    "--batch-name",
    default=None,
    help="Custom name for batch processing (auto-generated if not provided)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without executing",
)
@click.pass_context
@handle_errors
def inference(
    ctx,
    prompt_ids,
    prompts_file,
    weights,
    steps,
    guidance,
    seed,
    fps,
    sigma_max,
    blur_strength,
    canny_threshold,
    batch_name,
    dry_run,
):
    r"""Run Cosmos Transfer inference on one or more prompts.

    Accepts prompt IDs directly and creates runs automatically during execution.
    Supports both single and batch inference.

    \b
    Examples:
      cosmos inference ps_abc123                           # Single prompt
      cosmos inference ps_abc123 ps_def456                 # Multiple prompts
      cosmos inference ps_abc123 --weights 0.3 0.3 0.2 0.2 # Custom weights
      cosmos inference --prompts-file prompts.txt          # From file
      cosmos inference ps_abc123 --dry-run                 # Preview only

    For 4K upscaling, use: cosmos upscale <run_id>
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    # Gather all prompt IDs
    all_prompts = list(prompt_ids)
    if prompts_file:
        all_prompts.extend([line.strip() for line in prompts_file if line.strip()])

    if not all_prompts:
        raise click.UsageError("No prompt IDs provided. Use arguments or --prompts-file")

    # Build control weights dict
    weights_dict = {
        "vis": weights[0],
        "edge": weights[1],
        "depth": weights[2],
        "seg": weights[3],
    }

    # Handle dry-run mode
    if dry_run:
        display_dry_run_header()

        if len(all_prompts) == 1:
            # Single prompt dry run
            prompt = ops.get_prompt(all_prompts[0])
            if not prompt:
                raise ValueError(f"Prompt not found: {all_prompts[0]}")

            dry_run_data = {
                "Prompt ID": format_id(prompt["id"]),
                "Prompt text": format_prompt_text(prompt["prompt_text"]),
                "Input video": prompt["inputs"].get("video", "N/A"),
                "Weights": format_weights(weights_dict),
                "Steps": str(steps),
                "Would create": "Run specification internally",
                "Would upload": "Prompt data and video files to remote GPU",
            }

            dry_run_data["Would execute"] = "Inference"
            dry_run_data["Would download"] = "Generated video results"
        else:
            # Batch dry run
            dry_run_data = {
                "Number of prompts": str(len(all_prompts)),
                "Batch name": batch_name or "auto-generated",
                "Weights": format_weights(weights_dict),
                "Steps": str(steps),
            }

            # Show first few prompts
            for i, prompt_id in enumerate(all_prompts[:3], 1):
                prompt = ops.get_prompt(prompt_id)
                if prompt:
                    dry_run_data[f"Prompt {i}"] = (
                        f"{format_id(prompt_id)} - {format_prompt_text(prompt['prompt_text'][:50])}"
                    )

            if len(all_prompts) > 3:
                dry_run_data["..."] = f"and {len(all_prompts) - 3} more prompts"

            dry_run_data["Would create"] = f"{len(all_prompts)} run specifications internally"
            dry_run_data["Would execute"] = "Batch inference on GPU"
            dry_run_data["Would download"] = "All generated videos"

        table = create_info_table(dry_run_data)
        console.print(table)

        display_dry_run_footer()
        return

    # Execute inference
    if len(all_prompts) == 1:
        # Single prompt inference
        with create_progress_context("[cyan]Running inference...") as progress:
            task = progress.add_task("[cyan]Running inference...", total=None)

            # Use quick_inference for single prompt
            result = ops.quick_inference(
                prompt_id=all_prompts[0],
                weights=weights_dict,
                num_steps=steps,
                guidance=guidance,
                seed=seed,
                fps=fps,
                sigma_max=sigma_max,
                blur_strength=blur_strength,
                canny_threshold=canny_threshold,
            )

            progress.update(task, completed=True)

        # Display results
        results_data = {
            "Prompt ID": format_id(all_prompts[0]),
            "Run ID": format_id(result["run_id"]),
            "Status": "Completed",
        }

        # Add output path if available
        if "output_path" in result:
            results_data["Output"] = result["output_path"]

        display_success("Inference completed successfully!", results_data)

    else:
        # Batch inference for multiple prompts
        from datetime import datetime, timezone

        if not batch_name:
            batch_name = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        with create_progress_context(
            f"[cyan]Running batch inference for {len(all_prompts)} prompts..."
        ) as progress:
            task = progress.add_task(
                f"[cyan]Processing batch '{batch_name}' with {len(all_prompts)} prompts...",
                total=None,
            )

            # Use batch_inference for multiple prompts
            result = ops.batch_inference(
                prompt_ids=all_prompts,
                shared_weights=weights_dict,
                num_steps=steps,
                guidance=guidance,
                seed=seed,
                fps=fps,
                sigma_max=sigma_max,
                blur_strength=blur_strength,
                canny_threshold=canny_threshold,
                batch_name=batch_name,
            )

            progress.update(task, completed=True)

        # Display batch results
        successful = result.get("successful", 0)
        failed = result.get("failed", 0)

        results_data = {
            "Batch name": batch_name,
            "Total prompts": str(len(all_prompts)),
            "Successful": str(successful),
            "Failed": str(failed),
        }

        # Show some run IDs
        if result.get("run_ids"):
            sample_runs = result["run_ids"][:3]
            for i, run_id in enumerate(sample_runs, 1):
                results_data[f"Run {i}"] = format_id(run_id)

            if len(result["run_ids"]) > 3:
                results_data["..."] = f"and {len(result['run_ids']) - 3} more runs"

        display_success(f"Batch inference started for {batch_name}!", results_data)

        # Show monitoring instructions
        console.print("\n[cyan]Monitor progress with:[/cyan]")
        console.print("  cosmos status --stream")

    if ctx_obj.verbose:
        console.print("\n[cyan]Full results:[/cyan]")
        console.print_json(json.dumps(result, indent=2))
