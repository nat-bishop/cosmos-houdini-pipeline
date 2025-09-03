"""Prepare command for converting renders to Cosmos inference inputs."""

import sys
from pathlib import Path

import click

from cosmos_workflow.local_ai.cosmos_sequence import (
    CosmosSequenceValidator,
    CosmosVideoConverter,
)

from .base import CLIContext, handle_errors
from .completions import complete_directories
from .helpers import (
    console,
    create_info_table,
    create_progress_context,
    display_dry_run_footer,
    display_dry_run_header,
    display_next_step,
    display_success,
)


@click.command()
@click.argument(
    "input_dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
    shell_complete=complete_directories,
)
@click.option("--name", help="Name for output (AI-generated if not provided)")
@click.option("--fps", default=24, help="Frame rate for output videos (default: 24)")
@click.option("--description", help="Description for metadata")
@click.option("--no-ai", is_flag=True, help="Skip AI analysis")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without creating files",
)
@click.pass_context
@handle_errors
def prepare(ctx, input_dir, name, fps, description, no_ai, dry_run):
    r"""Prepare renders for Cosmos inference.

    Validates Houdini/Blender renders and converts control modality
    PNG sequences to videos ready for Cosmos Transfer.

    \b
    Expected structure:
      input_dir/
        ├── color.0001.png, color.0002.png, ...
        ├── depth.0001.png, depth.0002.png, ...
        └── segmentation.0001.png, segmentation.0002.png, ...

    \b
    Examples:
      cosmos prepare ./houdini_renders/
      cosmos prepare ./renders/ --name "city_scene" --fps 30
      cosmos prepare ./renders/ --no-ai
      cosmos prepare ./renders/ --dry-run
    """
    ctx_obj: CLIContext = ctx.obj
    input_path = Path(input_dir)

    # Validate sequences first (needed for both dry-run and actual execution)
    with create_progress_context("[cyan]Validating sequences...") as progress:
        task = progress.add_task("[cyan]Validating sequences...", total=None)
        validator = CosmosSequenceValidator()
        sequence_info = validator.validate(input_path)

        if not sequence_info.valid:
            console.print("[bold red][ERROR] Invalid sequence:[/bold red]")
            for issue in sequence_info.issues:
                console.print(f"  • {issue}")
            sys.exit(1)

        progress.update(task, completed=True, description="[green][OK] Validation complete")

    # Handle dry-run mode
    if dry_run:
        display_dry_run_header()

        # Show sequence details
        dry_run_data = {
            "Input": str(input_path),
            "Sequences": ", ".join(sequence_info.sequences.keys()),
            "Frames": str(sequence_info.frame_count),
            "Resolution": f"{sequence_info.resolution[0]}x{sequence_info.resolution[1]}",
            "FPS": str(fps),
        }

        if name:
            dry_run_data["Name"] = name
        else:
            dry_run_data["Name"] = "[dim]Would be AI-generated[/dim]"

        table = create_info_table(dry_run_data)
        console.print(table)

        console.print("\n[bold]Would create:[/bold]")
        for seq_name in sequence_info.sequences:
            console.print(f"  • {seq_name}.mp4 ({sequence_info.frame_count} frames @ {fps}fps)")

        if not no_ai:
            console.print("\n[bold]Would also:[/bold]")
            console.print("  • Generate AI description")
            console.print("  • Create metadata.json")

        display_dry_run_footer()
        return

    # Continue with actual conversion if not dry-run
    with create_progress_context("[cyan]Converting to videos...") as progress:
        # Convert
        task = progress.add_task("[cyan]Converting to videos...", total=None)
        converter = CosmosVideoConverter(fps=fps)

        config_manager = ctx_obj.get_config_manager()
        local_config = config_manager.get_local_config()
        videos_dir = Path(local_config.videos_dir)

        result = converter.convert_sequence(
            sequence_info=sequence_info, output_dir=videos_dir, name=name
        )

        if not result["success"]:
            raise Exception("Conversion failed")

        progress.update(task, completed=True, description="[green][OK] Videos created")

        # Generate metadata
        task = progress.add_task("[cyan]Generating metadata...", total=None)
        output_dir = Path(result["output_dir"])

        metadata = converter.generate_metadata(
            sequence_info=sequence_info,
            output_dir=output_dir,
            name=name,
            description=description,
            use_ai=not no_ai,
        )

        progress.update(task, completed=True, description="[green][OK] Metadata generated")

    # Display results
    results_data = {
        "Name": metadata.name,
        "Output": str(output_dir),
        "Frames": str(metadata.frame_count),
        "Resolution": f"{metadata.resolution[0]}x{metadata.resolution[1]}",
        "FPS": str(metadata.fps),
    }

    if metadata.control_inputs:
        results_data["Controls"] = ", ".join(metadata.control_inputs.keys())

    display_success("Inference inputs prepared!", results_data)

    if metadata.description:
        console.print(f"\n[dim]Description:[/dim] {metadata.description}")

    display_next_step(f'cosmos create prompt "Your prompt here" {Path(metadata.video_path).parent}')
