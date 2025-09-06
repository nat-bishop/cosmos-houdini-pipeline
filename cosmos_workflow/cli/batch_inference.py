"""Batch inference command for running multiple Cosmos Transfer jobs on remote GPU."""

import json
from datetime import datetime, timezone

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


@click.command("batch-inference")
@click.argument("run_ids", nargs=-1, required=True)
@click.option(
    "--batch-name",
    default=None,
    help="Custom name for the batch (default: auto-generated with timestamp)",
)
@click.option(
    "--num-gpu",
    default=1,
    type=click.IntRange(min=1, max=8),
    help="Number of GPUs to use for batch processing (default: 1)",
)
@click.option(
    "--cuda-devices",
    default="0",
    help="CUDA device IDs to use, comma-separated (default: '0')",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without executing",
)
@click.pass_context
@handle_errors
def batch_inference(ctx, run_ids, batch_name, num_gpu, cuda_devices, dry_run) -> None:
    r"""Run batch inference for multiple runs using NVIDIA Cosmos Transfer.

    Executes multiple inference jobs together for improved performance.
    Processes runs in parallel on GPU, reducing initialization overhead.
    Automatically splits outputs into individual run folders.

    \b
    Examples:
      cosmos batch-inference rs_001 rs_002 rs_003
      cosmos batch-inference rs_001 rs_002 --num-gpu 2 --cuda-devices "0,1"
      cosmos batch-inference rs_001 rs_002 --batch-name "my_batch"
      cosmos batch-inference rs_001 rs_002 --dry-run
    """
    ctx_obj: CLIContext = ctx.obj

    # Generate batch name if not provided
    if not batch_name:
        batch_name = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # Get service and load runs/prompts
    try:
        service = ctx_obj.get_workflow_service()

        # Collect all runs and prompts
        runs_and_prompts = []
        for run_id in run_ids:
            # Get run
            run = service.get_run(run_id)
            if not run:
                raise ValueError(f"Run not found: {run_id}")

            # Get associated prompt
            prompt = service.get_prompt(run["prompt_id"])
            if not prompt:
                raise ValueError(f"Prompt not found for run {run_id}: {run['prompt_id']}")

            runs_and_prompts.append((run, prompt))

    except Exception as e:
        if "not found" in str(e).lower():
            raise ValueError(str(e)) from e
        raise Exception(f"Database error: {e!s}") from e

    # Handle dry-run mode
    if dry_run:
        display_dry_run_header()

        # Show batch summary
        dry_run_data = {
            "Batch name": batch_name,
            "Number of runs": str(len(runs_and_prompts)),
            "GPU configuration": f"{num_gpu} GPU(s) on device(s) {cuda_devices}",
        }

        # Show run details
        for i, (run, prompt) in enumerate(runs_and_prompts, 1):
            dry_run_data[f"Run {i}"] = (
                f"{format_id(run['id'])} - {format_prompt_text(prompt['prompt_text'][:50])}"
            )

        dry_run_data["Would generate"] = "JSONL batch file with all runs"
        dry_run_data["Would upload"] = "Batch JSONL, videos, and batch script to remote GPU"
        dry_run_data["Would execute"] = f"Batch inference on {num_gpu} GPU(s)"
        dry_run_data["Would download"] = "All generated videos"
        dry_run_data["Would split"] = "Batch outputs into individual run folders"
        dry_run_data["Would update"] = f"All {len(runs_and_prompts)} runs to 'completed' status"

        table = create_info_table(dry_run_data)
        console.print(table)

        display_dry_run_footer()
        return

    with create_progress_context(
        f"[cyan]Running batch inference for {len(runs_and_prompts)} runs..."
    ) as progress:
        task = progress.add_task(
            f"[cyan]Processing batch '{batch_name}' with {len(runs_and_prompts)} runs...",
            total=None,
        )

        try:
            # Update all runs to running status
            for run, _ in runs_and_prompts:
                service.update_run_status(run["id"], "running")

            # Get orchestrator
            orchestrator = ctx_obj.get_orchestrator()

            # Execute batch runs
            result = orchestrator.execute_batch_runs(
                runs_and_prompts,
                batch_name=batch_name,
                num_gpu=num_gpu,
                cuda_devices=cuda_devices,
            )

            # Update runs with outputs
            outputs = result.get("outputs", {})
            for run_id, output_path in outputs.items():
                service.update_run(
                    run_id,
                    outputs={
                        "video_path": output_path,
                        "batch_name": batch_name,
                        "batch_inference": True,
                    },
                )
                service.update_run_status(run_id, "completed")

            # Handle runs without outputs (if any failed)
            for run, _ in runs_and_prompts:
                if run["id"] not in outputs:
                    service.update_run_status(run["id"], "failed")
                    service.update_run(
                        run["id"],
                        outputs={
                            "error": "No output generated in batch",
                            "batch_name": batch_name,
                        },
                    )

        except Exception as e:
            # Update all runs to failed status
            try:
                for run, _ in runs_and_prompts:
                    service.update_run_status(run["id"], "failed")
                    service.update_run(
                        run["id"],
                        outputs={
                            "error": str(e),
                            "batch_name": batch_name,
                        },
                    )
            except Exception:  # noqa: S110
                pass  # Don't fail on status update error
            raise

        progress.update(task, completed=True)

    # Display results
    successful_runs = len(outputs)
    failed_runs = len(runs_and_prompts) - successful_runs

    results_data = {
        "Batch name": batch_name,
        "Total runs": str(len(runs_and_prompts)),
        "Successful": str(successful_runs),
        "Failed": str(failed_runs),
    }

    if successful_runs > 0:
        # Show first few output paths
        sample_outputs = list(outputs.items())[:3]
        for run_id, output_path in sample_outputs:
            results_data[f"Output {format_id(run_id)}"] = output_path

        if len(outputs) > 3:
            results_data["..."] = f"and {len(outputs) - 3} more outputs"

    display_success(f"Batch inference completed for {batch_name}!", results_data)

    if ctx_obj.verbose:
        console.print("\n[cyan]Full results:[/cyan]")
        console.print_json(json.dumps(result, indent=2))
