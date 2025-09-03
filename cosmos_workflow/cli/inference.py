"""Inference command for running Cosmos Transfer on remote GPU."""

import json
from pathlib import Path

import click

from cosmos_workflow.prompts.schemas import PromptSpec

from .base import CLIContext, handle_errors
from .completions import complete_prompt_specs, complete_video_dirs
from .helpers import (
    console,
    create_info_table,
    create_progress_context,
    display_dry_run_footer,
    display_dry_run_header,
    display_success,
    format_prompt_text,
)


@click.command()
@click.argument(
    "spec_file",
    type=click.Path(exists=True, path_type=Path),
    shell_complete=complete_prompt_specs,
)
@click.option(
    "--videos-dir",
    help="Custom videos directory",
    shell_complete=complete_video_dirs,
)
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
def inference(ctx, spec_file, videos_dir, upscale, upscale_weight, dry_run):
    r"""Run Cosmos Transfer inference with optional upscaling.

    By default, this command runs both inference and 4K upscaling.
    Use --no-upscale to run inference only.
    Use --dry-run to preview what would happen without executing.

    \b
    Examples:
      cosmos inference prompt_spec.json              # Inference + upscaling
      cosmos inference prompt_spec.json --no-upscale # Inference only
      cosmos inference prompt_spec.json --dry-run    # Preview only
      cosmos inference prompt_spec.json --upscale-weight 0.7
    """
    ctx_obj: CLIContext = ctx.obj

    # Handle dry-run mode
    if dry_run:
        display_dry_run_header()

        # Load and display prompt spec info
        prompt_spec = PromptSpec.load(Path(spec_file))

        # Show what would happen
        dry_run_data = {
            "Would load": f"Prompt: {prompt_spec.name}",
            "Prompt text": format_prompt_text(prompt_spec.prompt),
            "Input video": prompt_spec.input_video_path,
        }

        if videos_dir:
            dry_run_data["Videos from"] = videos_dir

        dry_run_data["Would upload"] = "Prompt spec and video files to remote GPU"

        if upscale:
            dry_run_data["Would execute"] = "Inference + 4K upscaling"
            dry_run_data["Upscale weight"] = str(upscale_weight)
        else:
            dry_run_data["Would execute"] = "Inference only (no upscaling)"

        dry_run_data["Would download"] = "Generated video results"

        table = create_info_table(dry_run_data)
        console.print(table)

        display_dry_run_footer()
        return

    with create_progress_context(
        f"[cyan]Running {'inference + upscaling' if upscale else 'inference'}..."
    ) as progress:
        workflow_desc = "inference + upscaling" if upscale else "inference"
        task = progress.add_task(f"[cyan]Running {workflow_desc}...", total=None)

        orchestrator = ctx_obj.get_orchestrator()

        if upscale:
            # Run full cycle with inference and upscaling
            result = orchestrator.run_full_cycle(
                prompt_file=Path(spec_file),
                videos_subdir=videos_dir,
                no_upscale=False,
                upscale_weight=upscale_weight,
                num_gpu=1,
                cuda_devices="0",
            )
        else:
            # Run inference only
            result = orchestrator.run_inference_only(
                prompt_file=Path(spec_file),
                videos_subdir=videos_dir,
                num_gpu=1,
                cuda_devices="0",
            )

        progress.update(task, completed=True)

    display_success(f"{workflow_desc.capitalize()} completed!")

    if ctx_obj.verbose:
        console.print("\n[cyan]Results:[/cyan]")
        console.print_json(json.dumps(result, indent=2))
