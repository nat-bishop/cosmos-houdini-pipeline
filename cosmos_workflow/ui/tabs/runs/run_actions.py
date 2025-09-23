"""Run action handlers for delete, upscale, transfer, and logging.

This module handles user-initiated actions on runs like deletion,
upscaling, transferring, and viewing logs.
"""

from pathlib import Path

import gradio as gr

from cosmos_workflow.api.cosmos_api import CosmosAPI
from cosmos_workflow.utils.logging import logger


def load_run_logs(log_path):
    """Load and display run logs.

    Args:
        log_path: Path to the log file

    Returns:
        Log content or error message
    """
    if not log_path:
        return "No log file available"

    log_file = Path(log_path)
    if not log_file.exists():
        return f"Log file not found: {log_path}"

    try:
        # Read last 100 lines
        with open(log_file, encoding="utf-8") as f:
            lines = f.readlines()
            return "".join(lines[-100:])
    except Exception as e:
        logger.error("Error reading log file: {}", e)
        return f"Error reading log file: {e}"


def preview_delete_run(selected_run_id):
    """Preview run deletion - show what will be deleted.

    Args:
        selected_run_id: The ID of the run to delete

    Returns:
        Tuple of updates for delete dialog components
    """
    if not selected_run_id:
        return (
            gr.update(visible=False),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
        )

    try:
        ops = CosmosAPI()
        run = ops.get_run(selected_run_id)

        if not run:
            return (
                gr.update(visible=False),
                gr.update(),
                gr.update(),
                gr.update(),
                gr.update(),
            )

        # Build preview text
        preview = f"""### Delete Run: {selected_run_id[:16]}...

**Status**: {run.get("status", "unknown")}
**Model Type**: {run.get("model_type", "unknown")}
**Created**: {run.get("created_at", "")[:19]}

This will permanently delete the run from the database.
"""

        # Check for output files
        outputs = run.get("outputs", {})
        if isinstance(outputs, dict):
            if "output_path" in outputs:
                output_path = Path(outputs["output_path"])
                if output_path.exists():
                    preview += f"\n**Output Video**: {output_path.name}"
            elif "files" in outputs:
                files = outputs["files"]
                if files:
                    preview += f"\n**Output Files**: {len(files)} files"

        return (
            gr.update(visible=True),  # Show dialog
            gr.update(value=preview),  # Preview text
            gr.update(value="", placeholder="Type 'DELETE' to confirm"),  # Clear confirmation
            gr.update(interactive=False),  # Disable confirm button initially
            gr.update(interactive=True),  # Enable cancel button
        )

    except Exception as e:
        logger.error("Error preparing delete preview: {}", e)
        return (
            gr.update(visible=False),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
        )


def confirm_delete_run(run_id, delete_outputs):
    """Execute run deletion after confirmation.

    Args:
        run_id: The ID of the run to delete
        delete_outputs: Whether to also delete output files

    Returns:
        Tuple of updates for UI components
    """
    if not run_id:
        return (
            gr.update(visible=False),
            gr.update(),
            "❌ No run selected",
        )

    try:
        ops = CosmosAPI()
        result = ops.delete_run(run_id, delete_outputs=delete_outputs)

        if result.get("success"):
            return (
                gr.update(visible=False),  # Hide dialog
                gr.update(value=""),  # Clear selected ID
                f"✅ Successfully deleted run {run_id[:16]}...",
            )
        else:
            return (
                gr.update(visible=False),
                gr.update(),
                f"❌ Failed to delete run: {result.get('error', 'Unknown error')}",
            )

    except Exception as e:
        logger.error("Error deleting run: {}", e)
        return (
            gr.update(visible=False),
            gr.update(),
            f"❌ Error deleting run: {e}",
        )


def cancel_delete_run():
    """Cancel run deletion - hide dialog.

    Returns:
        Update to hide the delete dialog
    """
    return gr.update(visible=False)


def show_upscale_dialog(run_id):
    """Show upscale dialog with preview.

    Args:
        run_id: The ID of the run to upscale

    Returns:
        Tuple of updates for upscale dialog components
    """
    if not run_id:
        return (
            gr.update(visible=False),  # Hide dialog
            gr.update(),  # Preview text
            gr.update(),  # Hidden ID
        )

    try:
        ops = CosmosAPI()
        run = ops.get_run(run_id)

        if not run:
            return (
                gr.update(visible=False),
                gr.update(),
                gr.update(),
            )

        # Check if already upscaled
        upscaled_run = ops.get_upscaled_run(run_id)
        if upscaled_run:
            status_text = f"""⚠️ **This run has already been upscaled!**

Upscaled Run ID: {upscaled_run.get("id", "unknown")[:16]}...
Status: {upscaled_run.get("status", "unknown")}

Proceeding will create a new upscale job."""
        else:
            status_text = "✅ Ready to upscale to 4K (2048x1152)"

        # Build preview
        preview = f"""### Upscale Run: {run_id[:16]}...

**Model Type**: {run.get("model_type", "unknown")}
**Status**: {run.get("status", "unknown")}
**Created**: {run.get("created_at", "")[:19]}

{status_text}

This will create a new 4K upscaled version of the output video.
"""

        # Return only the expected 3 values
        return (
            gr.update(visible=True),  # Show dialog
            gr.update(value=preview),  # Preview text
            run_id,  # Hidden run ID for the confirmation handler
        )

    except Exception as e:
        logger.error("Error preparing upscale dialog: {}", e)
        return (
            gr.update(visible=False),
            gr.update(),
            gr.update(),
        )


def execute_upscale(run_id, control_weight, prompt_text):
    """Execute upscaling for a run.

    Args:
        run_id: The ID of the run to upscale
        control_weight: Control weight for upscaling
        prompt_text: Prompt text for the upscale

    Returns:
        Tuple of updates for UI components
    """
    if not run_id:
        return (
            gr.update(visible=False),
            gr.update(),
            "❌ No run selected",
        )

    try:
        ops = CosmosAPI()

        # Start upscaling
        result = ops.upscale_run(run_id, control_weight=control_weight, prompt_text=prompt_text)

        if result.get("success"):
            new_run_id = result.get("run_id", "unknown")
            return (
                gr.update(visible=False),  # Hide dialog
                gr.update(),  # Don't clear selected ID
                f"✅ Upscaling started! New run: {new_run_id[:16]}...",
            )
        else:
            return (
                gr.update(visible=False),
                gr.update(),
                f"❌ Failed to start upscaling: {result.get('error', 'Unknown error')}",
            )

    except Exception as e:
        logger.error("Error starting upscale: {}", e)
        return (
            gr.update(visible=False),
            gr.update(),
            f"❌ Error starting upscale: {e}",
        )


def cancel_upscale():
    """Cancel upscaling - hide dialog.

    Returns:
        Update to hide the upscale dialog
    """
    return gr.update(visible=False)
