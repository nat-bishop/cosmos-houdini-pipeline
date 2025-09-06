"""Generate command for one-step video generation workflow."""

import click

from .base import CLIContext, handle_errors
from .completions import complete_video_dirs
from .helpers import console, display_success, format_id, create_progress_context


@click.command()
@click.argument("prompt_text")
@click.argument(
    "video_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    shell_complete=complete_video_dirs,
)
@click.option("--name", "-n", help="Name for the prompt (auto-generated if not provided)")
@click.option("--negative", help="Negative prompt for quality improvement")
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
@click.option(
    "--upscale/--no-upscale",
    default=False,
    help="Enable/disable 4K upscaling after inference (default: no upscale)",
)
@click.option(
    "--upscale-weight", default=0.5, help="Control weight for upscaling (0.0-1.0) (default: 0.5)"
)
@click.pass_context
@handle_errors
def generate(
    ctx,
    prompt_text,
    video_dir,
    name,
    negative,
    weights,
    steps,
    guidance,
    seed,
    upscale,
    upscale_weight,
):
    r"""Generate video in one step - create prompt, run, and execute.

    This is the simplest way to generate a video. It combines:
    1. Creating a prompt
    2. Creating a run specification
    3. Executing inference on GPU

    The VIDEO_DIR must contain at least color.mp4.

    \b
    Examples:
      cosmos generate "A futuristic city" inputs/videos/scene1
      cosmos generate "Anime style" videos/test --upscale
      cosmos generate "Cyberpunk" renders/scene --weights 0.3 0.3 0.2 0.2
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    with create_progress_context("[cyan]Generating video...") as progress:
        task = progress.add_task("[cyan]Creating and executing...", total=3)
        
        # Step 1: Create prompt
        progress.update(task, description="[cyan]Creating prompt...", completed=1)
        
        # Build weights dict
        weights_dict = {
            "vis": weights[0],
            "edge": weights[1],
            "depth": weights[2],
            "seg": weights[3],
        }
        
        # Step 2 & 3: Create and run in one operation
        progress.update(task, description="[cyan]Running inference...", completed=2)
        
        result = ops.create_and_run(
            prompt_text=prompt_text,
            video_dir=video_dir,
            name=name,
            negative_prompt=negative,
            weights=weights_dict,
            num_steps=steps,
            guidance=guidance,
            seed=seed,
            upscale=upscale,
            upscale_weight=upscale_weight,
        )
        
        progress.update(task, description="[cyan]Complete!", completed=3)

    # Display results
    results_data = {
        "Prompt ID": format_id(result["prompt_id"]),
        "Run ID": format_id(result["run_id"]),
        "Output": result.get("output_path", "N/A"),
        "Duration": f"{result.get('duration_seconds', 0):.1f}s",
    }

    display_success("Video generated successfully!", results_data)