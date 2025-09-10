"""Prompt enhancement command using AI models."""

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


@click.command("prompt-enhance")
@click.argument("prompt_id")
@click.option(
    "--model",
    default="pixtral",
    help="AI model to use for enhancement (default: pixtral)",
)
@click.option(
    "--create-new/--overwrite",
    default=True,
    help="Create new prompt vs overwrite existing (default: --create-new)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without calling AI API",
)
@click.pass_context
@handle_errors
def prompt_enhance(ctx, prompt_id, model, create_new, dry_run):
    r"""Enhance prompts using AI models.

    Uses AI to improve prompt text quality and create better descriptions
    for video generation. Creates a new enhanced prompt by default.

    \b
    Examples:
      cosmos prompt-enhance ps_abc123
      cosmos prompt-enhance ps_abc123 --model gpt-4
      cosmos prompt-enhance ps_abc123 --overwrite
      cosmos prompt-enhance ps_abc123 --dry-run
    """
    ctx_obj: CLIContext = ctx.obj
    ops = ctx_obj.get_operations()

    # Get original prompt
    original_prompt = ops.get_prompt(prompt_id)
    if not original_prompt:
        raise ValueError(f"Prompt not found: {prompt_id}")

    # Handle dry-run mode
    if dry_run:
        display_dry_run_header()

        dry_run_data = {
            "Original prompt ID": format_id(prompt_id),
            "Original text": format_prompt_text(original_prompt["prompt_text"]),
            "AI Model": model,
            "Would execute": f"Prompt enhancement using {model}",
        }

        if create_new:
            dry_run_data["Would create"] = "New enhanced prompt with improved text"
            dry_run_data["Original prompt"] = "Remains unchanged"
        else:
            dry_run_data["Would update"] = "Existing prompt with enhanced text"
            dry_run_data["Warning"] = "Only if prompt has no runs"

        table = create_info_table(dry_run_data)
        console.print(table)

        console.print("\n[bold]Expected workflow:[/bold]")
        console.print(f"  1. Call {model} API to enhance prompt text")
        if create_new:
            console.print("  2. Create new prompt with enhanced text")
            console.print("  3. Return new prompt ID for inference")
        else:
            console.print("  2. Update existing prompt (if no runs exist)")

        display_dry_run_footer()
        return

    # Handle overwrite mode - check what will be deleted and get confirmation
    force_overwrite = False
    if not create_new:
        # Preview what will be affected
        preview = ops.preview_prompt_deletion(prompt_id, keep_outputs=True)
        all_runs = preview.get("runs", [])

        # Check for blocking runs (non-enhancement runs)
        blocking_runs = [r for r in all_runs if r.get("model_type") != "enhance"]

        if blocking_runs:
            console.print(
                "\n[yellow]⚠️  Warning: Overwrite mode will delete existing runs![/yellow]"
            )
            console.print(
                f"\nPrompt [cyan]{format_id(prompt_id)}[/cyan] has {len(blocking_runs)} run(s) that will be deleted:"
            )

            # Show run details
            for run in blocking_runs[:5]:  # Show first 5 runs
                run_type = run.get("model_type", "unknown")
                status = run.get("status", "unknown")
                console.print(f"  • Run {format_id(run['id'])} ({run_type}, status: {status})")

            if len(blocking_runs) > 5:
                console.print(f"  ... and {len(blocking_runs) - 5} more")

            # Show storage impact
            storage = preview.get("storage", {})
            if storage.get("total_size_mb", 0) > 0:
                console.print(
                    f"\n[yellow]Storage impact:[/yellow] {storage['total_size_mb']:.1f} MB in {storage.get('directory_count', 0)} directories"
                )
                console.print(
                    "[dim]Note: Output files will be kept (only database entries deleted)[/dim]"
                )

            # Get confirmation
            if not click.confirm("\nDo you want to proceed with deleting these runs?"):
                console.print("[red]Enhancement cancelled.[/red]")
                return

            force_overwrite = True
            console.print("\n[green]Proceeding with overwrite...[/green]")
        else:
            console.print("\n[dim]No existing runs found. Safe to overwrite.[/dim]")

    with create_progress_context("[cyan]Enhancing prompt...") as progress:
        task = progress.add_task("[cyan]Enhancing prompt...", total=None)

        # Use enhance_prompt operation with force_overwrite if needed
        result = ops.enhance_prompt(
            prompt_id=prompt_id,
            create_new=create_new,
            enhancement_model=model,
            force_overwrite=force_overwrite,
        )

        progress.update(task, completed=True)

    # Enhancement always runs in background now
    if result.get("status") == "started":
        # Display background execution info
        results_data = {
            "Run ID": format_id(result["run_id"]),
            "Original prompt": format_id(prompt_id),
            "Model": model,
            "Status": "Running in background",
        }

        display_success("Enhancement started in background!", results_data)

        console.print("\n[yellow]The enhancement is now running on the GPU.[/yellow]")
        console.print("\nTo monitor progress:")
        console.print("  [cyan]cosmos status --stream[/cyan]")
        console.print("\nThe enhanced prompt will be created automatically when complete.")

        if create_new:
            console.print(
                "\n[dim]Once complete, the new enhanced prompt ID will be available via:[/dim]"
            )
            console.print(f"  [cyan]cosmos show run {result['run_id']}[/cyan]")
    else:
        # Legacy synchronous path (shouldn't happen with current implementation)
        if create_new:
            results_data = {
                "Original prompt": format_id(prompt_id),
                "Enhanced prompt": format_id(result.get("enhanced_prompt_id", "pending")),
                "Model used": model,
            }
            success_message = "Prompt enhanced successfully!"
        else:
            results_data = {
                "Updated prompt": format_id(prompt_id),
                "Model used": model,
            }
            success_message = "Prompt updated successfully!"

        display_success(success_message, results_data)

        # Only show enhanced text if it exists
        if result.get("enhanced_text"):
            console.print("\n[bold]Enhanced text:[/bold]")
            console.print(format_prompt_text(result["enhanced_text"]))

        # Suggest next step if we have the enhanced prompt ID
        if create_new and result.get("enhanced_prompt_id"):
            console.print(
                f"\n[dim]Next step: cosmos inference {result['enhanced_prompt_id']}[/dim]"
            )
        elif not create_new:
            console.print(f"\n[dim]Next step: cosmos inference {prompt_id}[/dim]")
