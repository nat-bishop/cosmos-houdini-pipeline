"""Prompt enhancement command using AI models."""

import sys
from pathlib import Path

import click

from cosmos_workflow.prompts.schemas import PromptSpec

from .base import CLIContext, handle_errors
from .completions import complete_prompt_specs
from .helpers import (
    console,
    create_info_table,
    create_progress_context,
    display_dry_run_footer,
    display_dry_run_header,
    display_success,
    format_prompt_text,
)


@click.command("prompt-enhance")
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
@handle_errors
def prompt_enhance(ctx, prompt_specs, resolution, dry_run):
    r"""✨ Enhance prompts using Pixtral AI model.

    Creates new enhanced PromptSpecs with improved prompt quality.
    Enhanced specs are saved with smart names based on the enhanced content.

    \b
    Examples:
      cosmos prompt-enhance prompt_spec.json
      cosmos prompt-enhance spec1.json spec2.json spec3.json
      cosmos prompt-enhance inputs/prompts/*.json --resolution 480
      cosmos prompt-enhance prompt_spec.json --dry-run
    """
    ctx_obj: CLIContext = ctx.obj

    if not prompt_specs:
        console.print("[bold red]❌ No prompt specs provided![/bold red]")
        console.print("Usage: cosmos prompt-enhance <spec1.json> [spec2.json ...]")
        sys.exit(1)

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
        display_dry_run_header()

        dry_run_data = {
            "📁 Would enhance": f"{len(specs_to_enhance)} prompt(s)",
            "🤖 AI Model": "Pixtral for prompt enhancement",
            "💾 Output": "Save with smart names based on content",
        }

        if preprocess:
            dry_run_data["🎬 Preprocessing"] = f"Resize videos to {max_resolution}p"

        table = create_info_table(dry_run_data)
        console.print(table)

        console.print("\n[bold]Prompts to enhance:[/bold]")
        for spec, _ in specs_to_enhance:
            formatted_prompt = format_prompt_text(spec.prompt)
            console.print(f'  • {spec.name}: "{formatted_prompt}"')

        console.print("\n[bold]Would create files:[/bold]")
        console.print("  • Files with smart names based on enhanced content")
        console.print("  • Example: 'foggy_morning' → 'misty_dawn_landscape'")
        console.print(f"  • Total: {len(specs_to_enhance)} enhanced prompt file(s)")

        display_dry_run_footer()
        return

    orchestrator = ctx_obj.get_orchestrator()

    with create_progress_context(
        f"[cyan]Enhancing {len(specs_to_enhance)} prompt(s)..."
    ) as progress:
        task = progress.add_task(
            f"[cyan]Enhancing {len(specs_to_enhance)} prompt(s)...", total=None
        )

        # Process all specs
        enhanced_count = 0
        for spec, _ in specs_to_enhance:
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

                    # The spec was already saved by PromptSpecManager with a smart name
                    # We just need to report success - no need to save again
                    enhanced_count += 1
                    console.print(f"  [green]✓[/green] Enhanced: {spec.name} → {updated_spec.name}")
                else:
                    console.print(f"  [yellow]⚠[/yellow] Failed: {spec.name}")

            except Exception as e:
                console.print(f"  [red]✗[/red] Error enhancing {spec.name}: {e}")

        progress.update(task, completed=True)

    count_msg = f"Enhanced {enhanced_count}/{len(specs_to_enhance)} prompts!"
    display_success(count_msg)
