"""Prompt enhancement command using AI models."""

import click

# These imports are for mocking in tests
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
    "--dry-run",
    is_flag=True,
    help="Preview what would happen without calling AI API",
)
@click.pass_context
@handle_errors
def prompt_enhance(ctx, prompt_id, model, dry_run):
    r"""Enhance prompts using AI models.

    Creates an enhancement run in the database, executes it to get an enhanced prompt,
    then creates a new prompt with the enhanced text. The enhancement is tracked as
    a run with model_type="enhancement".

    \b
    Examples:
      cosmos prompt-enhance ps_abc123
      cosmos prompt-enhance ps_abc123 --model gpt-4
      cosmos prompt-enhance ps_abc123 --dry-run
    """
    ctx_obj: CLIContext = ctx.obj

    # Get service and load prompt data
    try:
        # Use the get_workflow_service from context
        service = ctx_obj.get_workflow_service()

        # Get original prompt
        original_prompt = service.get_prompt(prompt_id)
        if not original_prompt:
            raise ValueError(f"Prompt not found: {prompt_id}")
    except Exception as e:
        if "not found" in str(e).lower():
            raise ValueError(str(e)) from e
        raise Exception(f"Database error: {e!s}") from e

    # Handle dry-run mode
    if dry_run:
        display_dry_run_header()

        dry_run_data = {
            "Original prompt ID": format_id(prompt_id),
            "Original text": format_prompt_text(original_prompt["prompt_text"]),
            "AI Model": model,
            "Would create": "Enhancement run in database",
            "Would execute": f"Prompt enhancement using {model}",
            "Would generate": "New enhanced prompt with improved text",
            "Would track": "Enhancement as run with outputs",
        }

        table = create_info_table(dry_run_data)
        console.print(table)

        console.print("\n[bold]Expected workflow:[/bold]")
        console.print(f"  1. Create enhancement run for prompt {prompt_id}")
        console.print(f"  2. Call {model} API to enhance prompt text")
        console.print("  3. Create new prompt with enhanced text")
        console.print("  4. Link enhanced prompt to original via run outputs")
        console.print("  5. Mark enhancement run as completed")

        display_dry_run_footer()
        return

    with create_progress_context("[cyan]Enhancing prompt...") as progress:
        task = progress.add_task("[cyan]Enhancing prompt...", total=None)

        try:
            # Create enhancement run
            enhancement_run = service.create_run(
                prompt_id=prompt_id,
                execution_config={
                    "model": model,
                    "type": "enhancement",
                    "temperature": 0.7,
                },
                metadata={"purpose": "prompt_enhancement"},
            )

            console.print(f"[dim]Created enhancement run: {enhancement_run['id']}[/dim]")

            # Update run status to running
            service.update_run_status(enhancement_run["id"], "running")

            # Get orchestrator and run enhancement
            orchestrator = ctx_obj.get_orchestrator()

            # Call the upsampling method (will be simplified in orchestrator refactor)
            enhanced_text = orchestrator.run_prompt_upsampling(
                prompt_text=original_prompt["prompt_text"],
                model=model,
            )

            # Create new enhanced prompt
            enhanced_prompt = service.create_prompt(
                model_type="transfer",  # Enhanced prompts are for transfer
                prompt_text=enhanced_text,
                inputs=original_prompt["inputs"],  # Keep same inputs
                parameters={
                    **original_prompt.get("parameters", {}),
                    "enhanced": True,
                    "parent_prompt_id": prompt_id,
                    "enhancement_model": model,
                },
            )

            console.print(f"[dim]Created enhanced prompt: {enhanced_prompt['id']}[/dim]")

            # Update run with outputs
            import time

            duration = (
                time.time() - enhancement_run["created_at"].timestamp()
                if hasattr(enhancement_run.get("created_at"), "timestamp")
                else 0
            )

            service.update_run(
                enhancement_run["id"],
                outputs={
                    "type": "text_enhancement",  # Mark as text enhancement
                    "enhanced_prompt_id": enhanced_prompt["id"],
                    "enhanced_text": enhanced_text[:500]
                    if len(enhanced_text) > 500
                    else enhanced_text,  # Store preview
                    "enhanced_text_full_length": len(enhanced_text),
                    "model_used": model,
                    "duration_seconds": duration,
                },
            )

            # Update run status to completed
            service.update_run_status(enhancement_run["id"], "completed")

        except Exception as e:
            # Update run status to failed if it exists
            if "enhancement_run" in locals():
                try:
                    service.update_run_status(enhancement_run["id"], "failed")
                    service.update_run(enhancement_run["id"], outputs={"error": str(e)})
                except Exception:  # noqa: S110
                    pass  # Status update is best-effort, don't fail the command
            raise

        progress.update(task, completed=True)

    # Display results
    results_data = {
        "Original prompt": format_id(prompt_id),
        "Enhancement run": format_id(enhancement_run["id"]),
        "Enhanced prompt": format_id(enhanced_prompt["id"]),
        "Model used": model,
    }

    display_success("Prompt enhanced successfully!", results_data)

    # Show the enhanced text
    console.print("\n[bold]Enhanced text:[/bold]")
    console.print(format_prompt_text(enhanced_text))

    # Suggest next step
    console.print(f"\n[dim]Next step: cosmos create run {enhanced_prompt['id']}[/dim]")
