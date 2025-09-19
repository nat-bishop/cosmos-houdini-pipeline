#!/usr/bin/env python3
"""Event handlers for Prompts tab functionality."""

import gradio as gr

from cosmos_workflow.utils.logging import logger


def select_all_prompts(table_data):
    """Select all prompts in the table."""
    try:
        import pandas as pd

        # Handle empty data
        if table_data is None:
            return [], "**0** prompts selected"

        # Handle DataFrame format (what Gradio returns)
        if isinstance(table_data, pd.DataFrame):
            if table_data.empty:
                return table_data, "**0** prompts selected"
            # Set first column to True for all rows
            table_data = table_data.copy()
            table_data.iloc[:, 0] = True
            count = len(table_data)
            return table_data, f"**{count}** prompts selected"

        # Handle list format (legacy)
        elif isinstance(table_data, list):
            if len(table_data) == 0:
                return table_data, "**0** prompts selected"
            # Set all checkboxes to True (first column)
            updated_data = []
            for row in table_data:
                updated_row = list(row)
                updated_row[0] = True  # Check the checkbox
                updated_data.append(updated_row)
            count = len(updated_data)
            return updated_data, f"**{count}** prompts selected"

        else:
            # Unknown format
            return table_data, "**0** prompts selected"

    except Exception as e:
        logger.error("Error selecting all prompts: {}", str(e))
        return table_data, "Error selecting prompts"


def clear_selection(table_data):
    """Clear all selections in the prompts table."""
    try:
        import pandas as pd

        # Handle empty data
        if table_data is None:
            return [], "**0** prompts selected"

        # Handle DataFrame format (what Gradio returns)
        if isinstance(table_data, pd.DataFrame):
            if table_data.empty:
                return table_data, "**0** prompts selected"
            # Set first column to False for all rows
            table_data = table_data.copy()
            table_data.iloc[:, 0] = False
            return table_data, "**0** prompts selected"

        # Handle list format (legacy)
        elif isinstance(table_data, list):
            if len(table_data) == 0:
                return table_data, "**0** prompts selected"
            # Set all checkboxes to False (first column)
            updated_data = []
            for row in table_data:
                updated_row = list(row)
                updated_row[0] = False  # Uncheck the checkbox
                updated_data.append(updated_row)
            return updated_data, "**0** prompts selected"

        else:
            # Unknown format
            return table_data, "**0** prompts selected"

    except Exception as e:
        logger.error("Error clearing selection: {}", str(e))
        return table_data, "Error clearing selection"


def update_selection_count(table_data):
    """Update the count of selected prompts."""
    try:
        import pandas as pd

        if table_data is None:
            logger.debug("update_selection_count: table_data is None")
            return "**0** prompts selected"

        # Handle DataFrame format
        if isinstance(table_data, pd.DataFrame):
            if table_data.empty:
                logger.debug("update_selection_count: DataFrame is empty")
                return "**0** prompts selected"
            # Count True values in first column
            count = table_data.iloc[:, 0].sum()
            logger.info("update_selection_count: DataFrame count={}", count)
            if count == 1:
                return f"**{count}** prompt selected"
            else:
                return f"**{count}** prompts selected"

        # Handle list format
        elif isinstance(table_data, list):
            if len(table_data) == 0:
                logger.debug("update_selection_count: List is empty")
                return "**0** prompts selected"
            # Count checked rows (first column is checkbox)
            count = sum(1 for row in table_data if row[0])
            logger.info("update_selection_count: List count={}", count)
            if count == 1:
                return f"**{count}** prompt selected"
            else:
                return f"**{count}** prompts selected"

        else:
            logger.debug("update_selection_count: Unknown data type: {}", type(table_data))
            return "**0** prompts selected"

    except Exception as e:
        logger.error("Error updating selection count: {}", str(e))
        return "Error counting selection"


def get_selected_prompt_ids(table_data):
    """Extract IDs of selected prompts from table data."""
    import pandas as pd

    selected_ids = []

    if table_data is None:
        return selected_ids

    # Handle DataFrame format
    if isinstance(table_data, pd.DataFrame):
        if not table_data.empty:
            # Get rows where first column is True
            selected_rows = table_data[table_data.iloc[:, 0]]
            # Get IDs from second column
            selected_ids = selected_rows.iloc[:, 1].tolist()

    # Handle list format
    elif isinstance(table_data, list) and len(table_data) > 0:
        for row in table_data:
            if row[0]:  # If checkbox is checked
                selected_ids.append(row[1])  # ID is in second column

    logger.debug("Selected %d prompts from table", len(selected_ids))
    return selected_ids


def preview_delete_prompts(table_data):
    """Preview what will be deleted for selected prompts."""
    try:
        selected_ids = get_selected_prompt_ids(table_data)

        if not selected_ids:
            return (
                gr.update(visible=False),  # Hide dialog
                "",  # No preview text
                False,  # Reset checkbox
                "",  # No IDs to store
            )

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        if not ops:
            return (
                gr.update(visible=False),
                "Error: Cannot connect to API",
                False,
                "",
            )

        # Build preview for each prompt
        preview_lines = []
        total_runs = 0
        total_size = 0
        has_active_runs = False

        for prompt_id in selected_ids:
            preview = ops.preview_prompt_deletion(prompt_id, keep_outputs=False)
            if preview and preview.get("prompt"):
                prompt_info = preview["prompt"]
                runs = preview.get("runs", [])
                size_mb = preview.get("total_size_mb", 0)

                # Check for active runs
                active_runs = [r for r in runs if r.get("status") in ["running", "pending"]]
                if active_runs:
                    has_active_runs = True
                    preview_lines.append(
                        f"⚠️ **{prompt_info.get('id', '')[:8]}...** - {prompt_info.get('prompt_text', '')[:50]}... "
                        f"({len(active_runs)} ACTIVE RUNS!)"
                    )
                else:
                    preview_lines.append(
                        f"• **{prompt_info.get('id', '')[:8]}...** - {prompt_info.get('prompt_text', '')[:50]}... "
                        f"({len(runs)} runs, {size_mb:.1f} MB)"
                    )

                total_runs += len(runs)
                total_size += size_mb

        # Build preview text
        preview_text = f"""### ⚠️ Delete Prompts Confirmation

**Selected Prompts:** {len(selected_ids)}
**Total Runs:** {total_runs}
**Total Size:** {total_size:.2f} MB

**Prompts to delete:**
"""
        preview_text += "\n".join(preview_lines)

        if has_active_runs:
            preview_text += (
                "\n\n🚨 **WARNING:** Some prompts have active runs! These cannot be deleted."
            )

        preview_text += "\n\n⚠️ **Warning:** This action cannot be undone!"

        # Store selected IDs as comma-separated string
        ids_string = ",".join(selected_ids)

        return (
            gr.update(visible=True),  # Show dialog
            preview_text,  # Preview text
            False,  # Default to keep outputs
            ids_string,  # Store IDs for confirmation
        )

    except Exception as e:
        logger.error("Error previewing prompt deletion: {}", str(e))
        return (
            gr.update(visible=False),
            f"Error: {e}",
            False,
            "",
        )


def confirm_delete_prompts(prompt_ids_string, delete_outputs):
    """Actually delete the prompts after confirmation."""
    try:
        if not prompt_ids_string:
            return "No prompts selected", gr.update(visible=False)

        prompt_ids = prompt_ids_string.split(",")
        if not prompt_ids:
            return "No prompts selected", gr.update(visible=False)

        # Create CosmosAPI instance
        from cosmos_workflow.api.cosmos_api import CosmosAPI

        ops = CosmosAPI()
        if not ops:
            return "Error: Cannot connect to API", gr.update(visible=False)

        # Delete each prompt
        keep_outputs = not delete_outputs
        deleted_count = 0
        failed_prompts = []

        for prompt_id in prompt_ids:
            try:
                # Check for active runs first
                preview = ops.preview_prompt_deletion(prompt_id, keep_outputs)
                if preview and preview.get("runs"):
                    active_runs = [
                        r for r in preview["runs"] if r.get("status") in ["running", "pending"]
                    ]
                    if active_runs:
                        failed_prompts.append(f"{prompt_id[:8]} (has active runs)")
                        continue

                # Delete the prompt
                result = ops.delete_prompt(prompt_id, keep_outputs=keep_outputs)
                if result.get("success"):
                    deleted_count += 1
                else:
                    failed_prompts.append(
                        f"{prompt_id[:8]} ({result.get('error', 'unknown error')})"
                    )

            except Exception as e:
                logger.error("Error deleting prompt {}: {}", prompt_id, str(e))
                failed_prompts.append(f"{prompt_id[:8]} ({e!s})")

        # Build result message
        if deleted_count > 0:
            msg = f"✅ Successfully deleted {deleted_count} prompt(s)"
            if delete_outputs:
                msg += " (output files deleted)"
            else:
                msg += " (output files preserved)"
        else:
            msg = "❌ No prompts were deleted"

        if failed_prompts:
            msg += f"\n\n⚠️ Failed to delete: {', '.join(failed_prompts)}"

        return msg, gr.update(visible=False)

    except Exception as e:
        logger.error("Error deleting prompts: {}", str(e))
        return f"❌ Error deleting prompts: {e}", gr.update(visible=False)


def cancel_delete_prompts():
    """Cancel prompt deletion."""
    return "Deletion cancelled", gr.update(visible=False)
