"""Create command group for prompts and run specifications."""

from datetime import datetime, timezone
from pathlib import Path

import click

from cosmos_workflow.prompts.schemas import (
    DirectoryManager,
    ExecutionStatus,
    PromptSpec,
    RunSpec,
    SchemaUtils,
)
from cosmos_workflow.utils.smart_naming import generate_smart_name

from .base import CLIContext, handle_errors
from .completions import complete_prompt_specs, complete_video_dirs_smart, complete_video_files
from .helpers import (
    console,
    display_next_step,
    display_success,
    format_id,
    format_weights,
)


@click.group()
@click.pass_context
def create(ctx):
    """📝 Create prompts and run specifications.

    Use these commands to create the JSON specifications needed for
    Cosmos Transfer inference and upscaling workflows.
    """


@create.command("prompt")
@click.argument("prompt_text")
@click.argument(
    "video_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    shell_complete=complete_video_dirs_smart,
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

    Creates a PromptSpec JSON file for use with Cosmos Transfer inference.
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
        from pathlib import Path

        video_dir_path = Path(video_dir)
        video_path = str(video_dir_path / "color.mp4")

        # Build control inputs from same directory
        control_inputs_dict = {
            "depth": str(video_dir_path / "depth.mp4"),
            "seg": str(video_dir_path / "segmentation.mp4"),
        }

        # Generate unique ID
        prompt_id = SchemaUtils.generate_prompt_id(prompt_text, video_path, control_inputs_dict)

        # Create PromptSpec
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        prompt_spec = PromptSpec(
            id=prompt_id,
            name=name,
            prompt=prompt_text,
            negative_prompt=negative,
            input_video_path=video_path,
            control_inputs=control_inputs_dict,
            timestamp=timestamp,
            is_upsampled=False,
            parent_prompt_text=None,
        )

        # Save to file
        config_manager = ctx_obj.get_config_manager()
        local_config = config_manager.get_local_config()

        dir_manager = DirectoryManager(local_config.prompts_dir, local_config.runs_dir)
        dir_manager.ensure_directories_exist()

        file_path = dir_manager.get_prompt_file_path(name, timestamp, prompt_id)
        prompt_spec.save(file_path)

    # Display success with rich formatting
    results_data = {
        "ID": format_id(prompt_id),
        "Name": name,
        "File": str(file_path),
        "Video": video_path,
    }

    display_success("Prompt created successfully!", results_data)
    display_next_step(f"cosmos run {file_path}")


@create.command("run")
@click.argument(
    "prompt_spec_path",
    type=click.Path(exists=True, path_type=Path),
    shell_complete=complete_prompt_specs,
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
@click.option("--output", help="Custom output path")
@click.pass_context
@handle_errors
def create_run_spec(ctx, prompt_spec_path, weights, steps, guidance, seed, fps, output):
    r"""Create a run specification for a prompt.

    \b
    Examples:
      cosmos create run prompt_spec.json
      cosmos create run prompt_spec.json --weights 0.3 0.3 0.2 0.2
      cosmos create run prompt_spec.json --steps 50 --guidance 8.0
    """
    ctx_obj: CLIContext = ctx.obj

    with console.status("[bold green]Creating run specification..."):
        # Load the PromptSpec
        prompt_spec = PromptSpec.load(Path(prompt_spec_path))

        # Build control weights
        weights_dict = {
            "vis": weights[0],
            "edge": weights[1],
            "depth": weights[2],
            "seg": weights[3],
        }

        # Build parameters
        parameters = {
            "num_steps": steps,
            "guidance": guidance,
            "sigma_max": 70.0,
            "blur_strength": "medium",
            "canny_threshold": "medium",
            "fps": fps,
            "seed": seed,
        }

        # Generate unique run ID
        run_id = SchemaUtils.generate_run_id(prompt_spec.id, weights_dict, parameters)

        # Build output path
        output_path = output or f"outputs/{prompt_spec.name}_{run_id}"

        # Create RunSpec
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        run_spec = RunSpec(
            id=run_id,
            prompt_id=prompt_spec.id,
            name=f"{prompt_spec.name}_{run_id}",
            control_weights=weights_dict,
            parameters=parameters,
            timestamp=timestamp,
            execution_status=ExecutionStatus.PENDING,
            output_path=output_path,
        )

        # Save to file
        config_manager = ctx_obj.get_config_manager()
        local_config = config_manager.get_local_config()

        dir_manager = DirectoryManager(local_config.prompts_dir, local_config.runs_dir)
        dir_manager.ensure_directories_exist()

        file_path = dir_manager.get_run_file_path(prompt_spec.name, timestamp, run_id)
        run_spec.save(file_path)

    # Display success
    results_data = {
        "Run ID": format_id(run_id),
        "Prompt": prompt_spec.name,
        "File": str(file_path),
        "Weights": format_weights(weights_dict),
    }

    display_success("Run specification created!", results_data)
    display_next_step(f"cosmos run {file_path}")
