"""Create command group for prompts and run specifications."""

from pathlib import Path

import click

# These imports are for mocking in tests
from cosmos_workflow.services.workflow_service import PromptNotFoundError
from cosmos_workflow.utils.smart_naming import generate_smart_name

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
    default="The video captures a game playing, with bad crappy graphics and cartoonish frames. It represents a recording of old outdated games. The lighting looks very fake. The textures are very raw and basic. The geometries are very primitive. The images are very pixelated and of poor CG quality. There are many subtitles in the footage. Overall, the video is unrealistic at all.",
    help="Negative prompt for quality improvement (default: provided)",
)
@click.pass_context
@handle_errors
def create_prompt(ctx, prompt_text, video_dir, name, negative):
    r"""Create a new prompt specification.

    Creates a prompt in the database for use with Cosmos Transfer inference.
    The VIDEO_DIR must contain the video files (color.mp4, depth.mp4, segmentation.mp4).
    Use 'cosmos prompt-enhance' to create enhanced versions of existing prompts.

    \b
    Examples:
      cosmos create prompt "A futuristic city at night" inputs/videos/scene1
      cosmos create prompt "Transform to anime style" /path/to/video_dir
      cosmos create prompt "Cyberpunk street scene" renders/my_scene
    """
    ctx_obj: CLIContext = ctx.obj

    with console.status("[bold green]Creating prompt specification..."):
        # Auto-generate name if not provided
        if name is None:
            name = generate_smart_name(prompt_text, max_length=30)
            console.print(f"[cyan]Generated name:[/cyan] {name}")

        # Build video paths from directory
        video_dir_path = Path(video_dir)

        # Validate video files exist
        color_path = video_dir_path / "color.mp4"
        depth_path = video_dir_path / "depth.mp4"
        seg_path = video_dir_path / "segmentation.mp4"

        missing_files = []
        if not color_path.exists():
            missing_files.append("color.mp4")
        if not depth_path.exists():
            missing_files.append("depth.mp4")
        if not seg_path.exists():
            missing_files.append("segmentation.mp4")

        if missing_files:
            raise FileNotFoundError(
                f"Missing required video files in {video_dir}: {', '.join(missing_files)}"
            )

        # Build inputs dictionary
        inputs = {
            "video": str(color_path),
            "depth": str(depth_path),
            "seg": str(seg_path),
        }

        # Build parameters
        parameters = {
            "negative_prompt": negative,
            "name": name,
        }

        # Get service and create prompt
        try:
            # Use the get_workflow_service from context
            service = ctx_obj.get_workflow_service()

            # Create the prompt using service
            prompt = service.create_prompt(
                model_type="transfer",
                prompt_text=prompt_text,
                inputs=inputs,
                parameters=parameters,
            )
        except Exception as e:
            raise Exception(f"Database error: {e!s}")

    # Display success with rich formatting
    results_data = {
        "ID": format_id(prompt["id"]),
        "Name": name,
        "Model Type": prompt["model_type"],
        "Video": str(color_path),
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
@click.option("--output", help="Custom output path")
@click.pass_context
@handle_errors
def create_run(ctx, prompt_id, weights, steps, guidance, seed, fps, output):
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

    with console.status("[bold green]Creating run specification..."):
        # Validate weights
        if not all(0 <= w <= 1 for w in weights):
            raise ValueError("All weights must be between 0 and 1")
        if not (0.99 <= sum(weights) <= 1.01):  # Allow small floating point error
            raise ValueError(f"Weights must sum to 1.0, got {sum(weights)}")

        # Build control weights
        weights_dict = {
            "vis": weights[0],
            "edge": weights[1],
            "depth": weights[2],
            "seg": weights[3],
        }

        # Build execution config
        execution_config = {
            "weights": weights_dict,
            "num_steps": steps,
            "guidance": guidance,
            "sigma_max": 70.0,
            "blur_strength": "medium",
            "canny_threshold": "medium",
            "fps": fps,
            "seed": seed,
        }

        if output:
            execution_config["output_path"] = output

        # Get service
        try:
            # Use the get_workflow_service from context
            service = ctx_obj.get_workflow_service()

            # Get prompt to verify it exists
            prompt = service.get_prompt(prompt_id)
            if not prompt:
                raise ValueError(f"Prompt not found: {prompt_id}")

            # Create the run
            run = service.create_run(
                prompt_id=prompt_id,
                execution_config=execution_config,
                metadata={},
            )
        except PromptNotFoundError:
            raise ValueError(f"Prompt not found: {prompt_id}")
        except ValueError:
            raise  # Re-raise validation errors as-is
        except Exception as e:
            raise Exception(f"Database error: {e!s}")

    # Display success
    from .helpers import format_weights

    results_data = {
        "Run ID": format_id(run["id"]),
        "Prompt": prompt.get("parameters", {}).get("name", prompt_id),
        "Weights": format_weights(weights_dict),
        "Steps": steps,
    }

    display_success("Run created successfully!", results_data)
    display_next_step(f"cosmos inference {run['id']}")
