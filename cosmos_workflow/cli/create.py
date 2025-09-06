"""Create command group for prompts and run specifications."""

from pathlib import Path

import click

from .base import CLIContext, handle_errors
from .completions import complete_video_dirs
from .helpers import console, display_next_step, display_success, format_id


@click.group()
@click.pass_context
def create(ctx):
    """Create prompts and run specifications.

    Use these commands to create prompts and runs in the database for
    Cosmos Transfer inference and upscaling workflows.
    """


@create.command("prompt")
@click.argument("prompt_text")
@click.argument(
    "video_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    shell_complete=complete_video_dirs,
)
@click.option("--name", "-n", help="Name for the prompt (auto-generated if not provided)")
@click.option(
    "--negative",
    help="Negative prompt for quality improvement",
)
@click.pass_context
@handle_errors
def create_prompt(ctx, prompt_text, video_dir, name, negative):
    r"""Create a new prompt specification.

    Creates a prompt in the database for use with Cosmos Transfer inference.
    The VIDEO_DIR must contain at least color.mp4. Depth and segmentation videos are optional.

    \b
    Examples:
      cosmos create prompt "A futuristic city at night" inputs/videos/scene1
      cosmos create prompt "Transform to anime style" /path/to/video_dir
      cosmos create prompt "Cyberpunk street scene" renders/my_scene
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    with console.status("[bold green]Creating prompt specification..."):
        # Create prompt using operations
        prompt = ops.create_prompt(
            prompt_text=prompt_text,
            video_dir=video_dir,
            name=name,
            negative_prompt=negative,
        )

        # Get the name from the created prompt
        prompt_name = prompt.get("parameters", {}).get("name", "unnamed")

    # Display success with rich formatting
    results_data = {
        "ID": format_id(prompt["id"]),
        "Name": prompt_name,
        "Model Type": prompt["model_type"],
        "Video Dir": str(video_dir),
    }

    display_success("Prompt created successfully!", results_data)
    display_next_step(f"cosmos create run {prompt['id']}")


@create.command("run")
@click.argument("prompt_id")
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
@click.pass_context
@handle_errors
def create_run(ctx, prompt_id, weights, steps, guidance, seed, fps, sigma_max, blur_strength, canny_threshold):
    r"""Create a run specification for a prompt.

    Creates a run in the database for the specified prompt ID.
    The run can then be executed using 'cosmos inference'.

    \b
    Examples:
      cosmos create run ps_abc123
      cosmos create run ps_abc123 --weights 0.3 0.3 0.2 0.2
      cosmos create run ps_abc123 --steps 50 --guidance 8.0
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    with console.status("[bold green]Creating run specification..."):
        # Build control weights dict
        weights_dict = {
            "vis": weights[0],
            "edge": weights[1],
            "depth": weights[2],
            "seg": weights[3],
        }

        # Create run using operations
        run = ops.create_run(
            prompt_id=prompt_id,
            weights=weights_dict,
            num_steps=steps,
            guidance=guidance,
            seed=seed,
            fps=fps,
            sigma_max=sigma_max,
            blur_strength=blur_strength,
            canny_threshold=canny_threshold,
        )

        # Get prompt for display
        prompt = ops.get_prompt(prompt_id)
        prompt_name = prompt.get("parameters", {}).get("name", prompt_id) if prompt else prompt_id

    # Display success
    from .helpers import format_weights

    results_data = {
        "Run ID": format_id(run["id"]),
        "Prompt": prompt_name,
        "Weights": format_weights(weights_dict),
        "Steps": steps,
    }

    display_success("Run created successfully!", results_data)
    display_next_step(f"cosmos inference {run['id']}")
