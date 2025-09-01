#!/usr/bin/env python3
"""Modern CLI interface for Cosmos-Transfer1 workflow orchestration."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from cosmos_workflow.config.config_manager import ConfigManager
from cosmos_workflow.prompts.schemas import (
    DirectoryManager,
    ExecutionStatus,
    PromptSpec,
    RunSpec,
    SchemaUtils,
)
from cosmos_workflow.utils.smart_naming import generate_smart_name
from cosmos_workflow.workflows.workflow_orchestrator import WorkflowOrchestrator

console = Console()


# ============================================================================
# AUTOCOMPLETE FUNCTIONS
# ============================================================================


def complete_prompt_specs(_ctx, _param, incomplete):
    """Autocomplete for PromptSpec JSON files."""
    prompts_dir = Path("inputs/prompts")
    if not prompts_dir.exists():
        return []

    # Match files starting with incomplete text
    results = []
    for json_file in prompts_dir.rglob("*.json"):
        if json_file.is_file():
            relative_path = str(json_file)
            if not incomplete or relative_path.startswith(incomplete):
                results.append(relative_path)
    return sorted(results)


def complete_video_files(_ctx, _param, incomplete):
    """Autocomplete for video files in inputs/videos."""
    videos_dir = Path("inputs/videos")
    if not videos_dir.exists():
        return []

    results = []
    for video in videos_dir.rglob("color.mp4"):
        relative_path = str(video)
        if not incomplete or relative_path.startswith(incomplete):
            results.append(relative_path)
    return sorted(results)


def complete_video_dirs(_ctx, _param, incomplete):
    """Autocomplete for video directories."""
    videos_dir = Path("inputs/videos")
    if not videos_dir.exists():
        return []

    results = []
    for subdir in videos_dir.iterdir():
        if subdir.is_dir():
            dir_path = str(subdir)
            if not incomplete or dir_path.startswith(incomplete):
                results.append(dir_path)
    return sorted(results)


def complete_directories(_ctx, _param, incomplete):
    """Autocomplete for any directory."""
    if incomplete:
        base_path = Path(incomplete)
        parent = base_path.parent if base_path.parent != base_path else Path(".")
        prefix = base_path.name
    else:
        parent = Path(".")
        prefix = ""

    if not parent.exists():
        return []

    results = []
    for item in parent.iterdir():
        if item.is_dir():
            dir_path = str(item)
            if not prefix or item.name.startswith(prefix):
                results.append(dir_path + "/")
    return sorted(results)


class CLIContext:
    """Context object to pass around CLI state."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.orchestrator: WorkflowOrchestrator | None = None
        self.config_manager: ConfigManager | None = None

    def setup_logging(self):
        """Setup logging configuration."""
        level = logging.DEBUG if self.verbose else logging.INFO
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stdout)],
        )

    def get_orchestrator(self) -> WorkflowOrchestrator:
        """Get or create workflow orchestrator."""
        if self.orchestrator is None:
            self.orchestrator = WorkflowOrchestrator()
        return self.orchestrator

    def get_config_manager(self) -> ConfigManager:
        """Get or create config manager."""
        if self.config_manager is None:
            self.config_manager = ConfigManager()
        return self.config_manager


@click.group(
    context_settings={
        "help_option_names": ["-h", "--help"],
        "auto_envvar_prefix": "COSMOS",
    }
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output for debugging")
@click.version_option(version="0.1.0", prog_name="Cosmos Workflow Orchestrator")
@click.pass_context
def cli(ctx, verbose):
    r"""Cosmos-Transfer1 Workflow Orchestrator.

    A powerful CLI for orchestrating NVIDIA Cosmos video generation workflows.
    Manage prompts, run inference, and control remote GPU execution with ease.

    \b
    Quick Start:
      1. Create a prompt:  cosmos create prompt "A cyberpunk city"
      2. Run inference:    cosmos inference <prompt_file>
      3. Check status:     cosmos status

    Use 'cosmos <command> --help' for detailed command information.
    """
    ctx.obj = CLIContext(verbose=verbose)
    ctx.obj.setup_logging()


# ============================================================================
# CREATE COMMAND GROUP
# ============================================================================


@cli.group()
@click.pass_context
def create(ctx):
    """📝 Create prompts and run specifications.

    Use these commands to create the JSON specifications needed for
    Cosmos Transfer inference and upscaling workflows.
    """


@create.command("prompt")
@click.argument("prompt_text")
@click.option("--name", "-n", help="Name for the prompt (auto-generated if not provided)")
@click.option(
    "--negative",
    default="bad quality, blurry, low resolution, cartoonish",
    help="Negative prompt for quality improvement",
)
@click.option(
    "--video",
    help="Path to input video file",
    shell_complete=complete_video_files,
)
@click.option("--enhanced", is_flag=True, help="Mark this as an enhanced (upsampled) prompt")
@click.option("--parent-prompt", help="Original prompt text (if this is enhanced)")
@click.pass_context
def create_prompt(ctx, prompt_text, name, negative, video, enhanced, parent_prompt):
    r"""Create a new prompt specification.

    \b
    Examples:
      cosmos create prompt "A futuristic city at night"
      cosmos create prompt "Transform to anime style" --video input.mp4
      cosmos create prompt "Enhanced prompt" --enhanced --parent-prompt "Original"
    """
    ctx_obj = ctx.obj

    try:
        with console.status("[bold green]Creating prompt specification..."):
            # Auto-generate name if not provided
            if name is None:
                name = generate_smart_name(prompt_text, max_length=30)
                console.print(f"[cyan]Generated name:[/cyan] {name}")

            # Build video path
            video_path = video or f"inputs/videos/{name}/color.mp4"

            # Default control inputs
            control_inputs_dict = {
                "depth": f"inputs/videos/{name}/depth.mp4",
                "seg": f"inputs/videos/{name}/segmentation.mp4",
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
                is_upsampled=enhanced,
                parent_prompt_text=parent_prompt,
            )

            # Save to file
            config_manager = ctx_obj.get_config_manager()
            local_config = config_manager.get_local_config()

            dir_manager = DirectoryManager(local_config.prompts_dir, local_config.runs_dir)
            dir_manager.ensure_directories_exist()

            file_path = dir_manager.get_prompt_file_path(name, timestamp, prompt_id)
            prompt_spec.save(file_path)

        # Display success with rich formatting
        console.print("\n[bold green]✅ Prompt created successfully![/bold green]")

        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value")

        table.add_row("ID", prompt_id[:16] + "...")
        table.add_row("Name", name)
        table.add_row("File", str(file_path))
        table.add_row("Video", video_path)

        console.print(table)

        console.print("\n[dim]Next step:[/dim]")
        console.print(f"  cosmos run {file_path}")

    except Exception as e:
        console.print(f"[bold red]❌ Failed to create prompt:[/bold red] {e}")
        if ctx_obj.verbose:
            console.print_exception()
        sys.exit(1)


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
    help="Control weights: VIS EDGE DEPTH SEG",
)
@click.option("--steps", default=35, help="Number of inference steps")
@click.option("--guidance", default=7.0, help="Guidance scale (CFG)")
@click.option("--seed", default=1, help="Random seed for reproducibility")
@click.option("--fps", default=24, help="Output video FPS")
@click.option("--output", help="Custom output path")
@click.pass_context
def create_run_spec(ctx, prompt_spec_path, weights, steps, guidance, seed, fps, output):
    r"""Create a run specification for a prompt.

    \b
    Examples:
      cosmos create run prompt_spec.json
      cosmos create run prompt_spec.json --weights 0.3 0.3 0.2 0.2
      cosmos create run prompt_spec.json --steps 50 --guidance 8.0
    """
    ctx_obj = ctx.obj

    try:
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
        console.print("\n[bold green]✅ Run specification created![/bold green]")

        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value")

        table.add_row("Run ID", run_id[:16] + "...")
        table.add_row("Prompt", prompt_spec.name)
        table.add_row("File", str(file_path))
        weights_str = f"vis={weights[0]:.2f} edge={weights[1]:.2f} "
        weights_str += f"depth={weights[2]:.2f} seg={weights[3]:.2f}"
        table.add_row("Weights", weights_str)

        console.print(table)

        console.print("\n[dim]Next step:[/dim]")
        console.print(f"  cosmos run {file_path}")

    except Exception as e:
        console.print(f"[bold red]❌ Failed to create run spec:[/bold red] {e}")
        if ctx_obj.verbose:
            console.print_exception()
        sys.exit(1)


# ============================================================================
# RUN COMMANDS
# ============================================================================


@cli.command()
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
    help="Enable/disable 4K upscaling after inference (default: enabled)",
)
@click.option("--upscale-weight", default=0.5, help="Control weight for upscaling (0.0-1.0)")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without executing",
)
@click.pass_context
def inference(ctx, spec_file, videos_dir, upscale, upscale_weight, dry_run):
    r"""🔮 Run Cosmos Transfer inference with optional upscaling.

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
    ctx_obj = ctx.obj

    # Handle dry-run mode
    if dry_run:
        console.print("\n[bold yellow]🔍 DRY RUN MODE[/bold yellow]")
        console.print("This is a preview of what would happen:\n")

        # Load and display prompt spec info
        from cosmos_workflow.prompts.schemas import PromptSpec

        prompt_spec = PromptSpec.load(Path(spec_file))

        # Show what would happen
        table = Table(show_header=False, box=None)
        table.add_column("Action", style="cyan")
        table.add_column("Details")

        table.add_row("📁 Would load", f"Prompt: {prompt_spec.name}")
        table.add_row(
            "📝 Prompt text",
            prompt_spec.prompt[:50] + "..." if len(prompt_spec.prompt) > 50 else prompt_spec.prompt,
        )
        table.add_row("🎬 Input video", prompt_spec.input_video_path)

        if videos_dir:
            table.add_row("📂 Videos from", videos_dir)

        table.add_row("⬆️ Would upload", "Prompt spec and video files to remote GPU")

        if upscale:
            table.add_row("🚀 Would execute", "Inference + 4K upscaling")
            table.add_row("⚖️ Upscale weight", str(upscale_weight))
        else:
            table.add_row("🚀 Would execute", "Inference only (no upscaling)")

        table.add_row("⬇️ Would download", "Generated video results")

        console.print(table)

        console.print("\n[dim]To execute for real, run without --dry-run[/dim]")
        return

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
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

        console.print(f"\n[bold green]✅ {workflow_desc.capitalize()} completed![/bold green]")

        if ctx_obj.verbose:
            console.print("\n[cyan]Results:[/cyan]")
            console.print_json(json.dumps(result, indent=2))

    except Exception as e:
        console.print(f"[bold red]❌ {workflow_desc.capitalize()} failed:[/bold red] {e}")
        if ctx_obj.verbose:
            console.print_exception()
        sys.exit(1)


# ============================================================================
# PROMPT ENHANCEMENT
# ============================================================================


@cli.command("prompt-enhance")
@click.argument(
    "prompt_specs",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, path_type=Path),
    shell_complete=complete_prompt_specs,
)
@click.option(
    "--resolution",
    default=None,
    type=int,
    help="Max resolution for preprocessing (implies preprocessing, e.g. 480)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without calling AI API",
)
@click.pass_context
def prompt_enhance(ctx, prompt_specs, resolution, dry_run):
    r"""✨ Enhance prompts using Pixtral AI model.

    Creates new enhanced PromptSpecs with improved prompt quality.
    Enhanced specs are saved with '_enhanced' suffix in the same directory structure.

    \b
    Examples:
      cosmos prompt-enhance prompt_spec.json
      cosmos prompt-enhance spec1.json spec2.json spec3.json
      cosmos prompt-enhance inputs/prompts/*.json --resolution 480
    """
    ctx_obj = ctx.obj

    if not prompt_specs:
        console.print("[bold red]❌ No prompt specs provided![/bold red]")
        console.print("Usage: cosmos prompt-enhance <spec1.json> [spec2.json ...]")
        sys.exit(1)

    try:
        # Determine preprocessing based on resolution
        preprocess = resolution is not None
        max_resolution = resolution if resolution else 480

        # Load all prompt specs
        specs_to_enhance = []
        for spec_path in prompt_specs:
            try:
                spec = PromptSpec.load(Path(spec_path))
                specs_to_enhance.append((spec, Path(spec_path)))
            except Exception as e:
                console.print(f"[yellow]Warning: Failed to load {spec_path}: {e}[/yellow]")

        if not specs_to_enhance:
            console.print("[bold red]❌ No valid prompt specs to enhance![/bold red]")
            sys.exit(1)

        # Handle dry-run mode
        if dry_run:
            console.print("\n[bold yellow]🔍 DRY RUN MODE[/bold yellow]")
            console.print("This is a preview of what would happen:\n")

            table = Table(show_header=False, box=None)
            table.add_column("Action", style="cyan")
            table.add_column("Details")

            table.add_row("📁 Would enhance", f"{len(specs_to_enhance)} prompt(s)")

            if preprocess:
                table.add_row("🎬 Preprocessing", f"Resize videos to {max_resolution}p")

            table.add_row("🤖 AI Model", "Pixtral for prompt enhancement")
            table.add_row("💾 Output", "Save as *_enhanced.json files")

            console.print(table)

            console.print("\n[bold]Prompts to enhance:[/bold]")
            for spec, spec_path in specs_to_enhance:
                console.print(
                    f'  • {spec.name}: "{spec.prompt[:50]}..."'
                    if len(spec.prompt) > 50
                    else f'  • {spec.name}: "{spec.prompt}"'
                )

            console.print("\n[bold]Would create files:[/bold]")
            for spec, spec_path in specs_to_enhance:
                enhanced_name = spec_path.stem.replace("_ps_", "_enhanced_ps_")
                if "_enhanced" not in enhanced_name:
                    enhanced_name = f"{spec_path.stem}_enhanced"
                console.print(f"  • {enhanced_name}.json")

            console.print("\n[dim]To execute for real, run without --dry-run[/dim]")
            return

        orchestrator = ctx_obj.get_orchestrator()
        config_manager = ctx_obj.get_config_manager()
        local_config = config_manager.get_local_config()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Enhancing {len(specs_to_enhance)} prompt(s)...", total=None
            )

            # Process all specs
            enhanced_count = 0
            for spec, original_path in specs_to_enhance:
                try:
                    result = orchestrator.run_single_prompt_upsampling(
                        prompt_spec=spec,
                        preprocess_videos=preprocess,
                        max_resolution=max_resolution,
                        num_frames=2,  # Fixed value
                        num_gpu=1,
                        cuda_devices="0",
                    )

                    if result["success"] and result.get("updated_spec"):
                        updated_spec = result["updated_spec"]

                        # Save enhanced spec in the same directory structure
                        # Get the relative path from prompts_dir
                        rel_path = original_path.relative_to(local_config.prompts_dir)

                        # Create enhanced filename
                        enhanced_name = rel_path.stem.replace("_ps_", "_enhanced_ps_")
                        if "_enhanced" not in enhanced_name:
                            enhanced_name = f"{rel_path.stem}_enhanced"

                        # Build the save path
                        save_path = (
                            local_config.prompts_dir / rel_path.parent / f"{enhanced_name}.json"
                        )
                        save_path.parent.mkdir(parents=True, exist_ok=True)

                        updated_spec.save(save_path)
                        enhanced_count += 1
                        console.print(
                            f"  [green]✓[/green] Enhanced: {spec.name} → {save_path.name}"
                        )
                    else:
                        console.print(f"  [yellow]⚠[/yellow] Failed: {spec.name}")

                except Exception as e:
                    console.print(f"  [red]✗[/red] Error enhancing {spec.name}: {e}")

            progress.update(task, completed=True)

        count_msg = f"Enhanced {enhanced_count}/{len(specs_to_enhance)} prompts!"
        console.print(f"\n[bold green]✅ {count_msg}[/bold green]")

    except Exception as e:
        console.print(f"[bold red]❌ Enhancement failed:[/bold red] {e}")
        if ctx_obj.verbose:
            console.print_exception()
        sys.exit(1)


# ============================================================================
# PREPARE COMMAND
# ============================================================================


@cli.command()
@click.argument(
    "input_dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False, path_type=Path),
)
@click.option("--name", help="Name for output (AI-generated if not provided)")
@click.option("--fps", default=24, help="Frame rate for output videos")
@click.option("--description", help="Description for metadata")
@click.option("--no-ai", is_flag=True, help="Skip AI analysis")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without creating files",
)
@click.pass_context
def prepare(ctx, input_dir, name, fps, description, no_ai, dry_run):
    r"""🎥 Prepare renders for Cosmos inference.

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
    """
    ctx_obj = ctx.obj

    try:
        from cosmos_workflow.local_ai.cosmos_sequence import (
            CosmosSequenceValidator,
            CosmosVideoConverter,
        )

        input_path = Path(input_dir)

        # Validate sequences first (needed for both dry-run and actual execution)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Validating sequences...", total=None)
            validator = CosmosSequenceValidator()
            sequence_info = validator.validate(input_path)

            if not sequence_info.valid:
                console.print("[bold red]❌ Invalid sequence:[/bold red]")
                for issue in sequence_info.issues:
                    console.print(f"  • {issue}")
                sys.exit(1)

            progress.update(task, completed=True, description="[green]✓ Validation complete")

        # Handle dry-run mode
        if dry_run:
            console.print("\n[bold yellow]🔍 DRY RUN MODE[/bold yellow]")
            console.print("This is a preview of what would happen:\n")

            # Show sequence details
            table = Table(show_header=False, box=None)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            table.add_row("📂 Input", str(input_path))
            table.add_row("🎬 Sequences", ", ".join(sequence_info.sequences.keys()))
            table.add_row("🖼️ Frames", str(sequence_info.frame_count))
            table.add_row(
                "📐 Resolution", f"{sequence_info.resolution[0]}x{sequence_info.resolution[1]}"
            )
            table.add_row("⏱️ FPS", str(fps))

            if name:
                table.add_row("📝 Name", name)
            else:
                table.add_row("📝 Name", "[dim]Would be AI-generated[/dim]")

            console.print(table)

            console.print("\n[bold]Would create:[/bold]")
            for seq_name in sequence_info.sequences:
                console.print(f"  • {seq_name}.mp4 ({sequence_info.frame_count} frames @ {fps}fps)")

            if not no_ai:
                console.print("\n[bold]Would also:[/bold]")
                console.print("  • Generate AI description")
                console.print("  • Create metadata.json")

            console.print("\n[dim]To execute for real, run without --dry-run[/dim]")
            return

        # Continue with actual conversion if not dry-run
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
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

            progress.update(task, completed=True, description="[green]✓ Videos created")

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

            progress.update(task, completed=True, description="[green]✓ Metadata generated")

        # Display results
        console.print("\n[bold green]✅ Inference inputs prepared![/bold green]")

        table = Table(show_header=False, box=None)
        table.add_column("Field", style="cyan")
        table.add_column("Value")

        table.add_row("Name", metadata.name)
        table.add_row("Output", str(output_dir))
        table.add_row("Frames", str(metadata.frame_count))
        table.add_row("Resolution", f"{metadata.resolution[0]}x{metadata.resolution[1]}")
        table.add_row("FPS", str(metadata.fps))

        if metadata.control_inputs:
            table.add_row("Controls", ", ".join(metadata.control_inputs.keys()))

        console.print(table)

        if metadata.description:
            console.print(f"\n[dim]Description:[/dim] {metadata.description}")

        console.print("\n[dim]Next step:[/dim]")
        console.print(f'  cosmos create prompt "Your prompt here" --video {metadata.video_path}')

    except Exception as e:
        console.print(f"[bold red]❌ Preparation failed:[/bold red] {e}")
        if ctx_obj.verbose:
            console.print_exception()
        sys.exit(1)


# ============================================================================
# STATUS COMMAND
# ============================================================================


@cli.command()
@click.pass_context
def status(ctx):
    """📊 Check remote GPU instance status.

    Shows SSH connectivity, Docker status, and available resources
    on the configured remote GPU instance.
    """
    ctx_obj = ctx.obj

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Checking remote status...", total=None)

            orchestrator = ctx_obj.get_orchestrator()
            status = orchestrator.check_remote_status()

            progress.update(task, completed=True)

        # Display status
        console.print("\n[bold]🖥️  Remote Instance Status[/bold]")

        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        if status["ssh_status"] == "connected":
            table.add_row("SSH Status", "[green]Connected[/green]")
            table.add_row("Remote Directory", status.get("remote_directory", "N/A"))
            table.add_row(
                "Directory Exists",
                "[green]Yes[/green]" if status.get("remote_directory_exists") else "[red]No[/red]",
            )

            docker_status = status.get("docker_status", {})
            table.add_row(
                "Docker Running",
                "[green]Yes[/green]" if docker_status.get("docker_running") else "[red]No[/red]",
            )

            if ctx_obj.verbose and docker_status.get("docker_running"):
                table.add_row(
                    "Docker Images",
                    str(len(docker_status.get("available_images", []))) + " available",
                )
                table.add_row(
                    "Running Containers", str(docker_status.get("running_containers", "0"))
                )
        else:
            table.add_row("SSH Status", "[red]Disconnected[/red]")
            table.add_row("Error", status.get("error", "Unknown error"))

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]❌ Status check failed:[/bold red] {e}")
        if ctx_obj.verbose:
            console.print_exception()
        sys.exit(1)


def main():
    """Main entry point."""
    # Ensure UTF-8 encoding for Windows
    if sys.platform == "win32":
        if sys.stdout.encoding != "utf-8":
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        if sys.stderr.encoding != "utf-8":
            sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

    try:
        cli(obj=None)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Unexpected error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
