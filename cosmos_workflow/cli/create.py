"""Create command group for prompts."""

import click

from .base import CLIContext, handle_errors
from .completions import complete_video_dirs
from .helpers import console, display_next_step, display_success, format_id


@click.group()
@click.pass_context
def create(ctx):
    """Create prompts for Cosmos Transfer workflows.

    Use these commands to create prompts in the database for
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
    display_next_step(f"cosmos inference {prompt['id']}")
