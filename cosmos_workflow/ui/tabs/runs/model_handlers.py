"""Model-specific UI data preparation for runs display.

This module contains functions for preparing display data specific to
different model types (transfer, enhance, upscale).
"""


def prepare_transfer_ui_data(run_details: dict, exec_config: dict, outputs: dict) -> dict:
    """Prepare UI data for transfer model runs.

    Args:
        run_details: Full run details
        exec_config: Execution configuration
        outputs: Run outputs

    Returns:
        Dictionary with transfer-specific UI data
    """
    return {
        "show_transfer_content": True,
        "show_enhance_content": False,
        "show_upscale_content": False,
    }


def prepare_enhance_ui_data(run_details: dict, exec_config: dict, outputs: dict) -> dict:
    """Prepare UI data for enhance model runs.

    Args:
        run_details: Full run details
        exec_config: Execution configuration
        outputs: Run outputs

    Returns:
        Dictionary with enhance-specific UI data
    """
    original_prompt = exec_config.get("original_prompt_text", "")
    enhanced_prompt = outputs.get("enhanced_text", "")
    enhancement_model = exec_config.get("model", "Unknown")
    create_new = exec_config.get("create_new", True)
    enhanced_at = outputs.get("enhanced_at", "")

    enhance_stats_text = f"""
    **Model Used:** {enhancement_model}
    **Mode:** {"Created new prompt" if create_new else "Overwrote original"}
    **Enhanced At:** {enhanced_at[:19] if enhanced_at else "Unknown"}
    **Original Length:** {len(original_prompt)} characters
    **Enhanced Length:** {len(enhanced_prompt)} characters
    **Status:** {run_details.get("status", "unknown").title()}
    """

    return {
        "show_transfer_content": False,
        "show_enhance_content": True,
        "show_upscale_content": False,
        "original_prompt": original_prompt,
        "enhanced_prompt": enhanced_prompt,
        "enhance_stats_text": enhance_stats_text,
    }


def prepare_upscale_ui_data(
    run_details: dict, exec_config: dict, outputs: dict, duration: str = "N/A"
) -> dict:
    """Prepare UI data for upscale model runs.

    Args:
        run_details: Full run details
        exec_config: Execution configuration
        outputs: Run outputs
        duration: Formatted duration string

    Returns:
        Dictionary with upscale-specific UI data
    """
    source_run_id = exec_config.get("source_run_id", "")
    input_video_source = exec_config.get("input_video_source", "")
    # Ensure control_weight is a float or use default
    control_weight = exec_config.get("control_weight", 0.5)
    if isinstance(control_weight, str):
        try:
            control_weight = float(control_weight)
        except (ValueError, TypeError):
            control_weight = 0.5
    upscale_prompt = exec_config.get("prompt", "")

    upscale_stats_text = f"""
    **Control Weight:** {control_weight}
    **Source:** {"Run " + source_run_id[:8] if source_run_id else "Direct video"}
    **Duration:** {duration}
    **Status:** {run_details.get("status", "unknown").title()}
    """

    return {
        "show_transfer_content": False,
        "show_enhance_content": False,
        "show_upscale_content": True,
        "input_video_source": input_video_source,
        "upscale_prompt": upscale_prompt,
        "upscale_stats_text": upscale_stats_text,
    }


# Maintain backward compatibility with underscore-prefixed names
_prepare_transfer_ui_data = prepare_transfer_ui_data
_prepare_enhance_ui_data = prepare_enhance_ui_data
_prepare_upscale_ui_data = prepare_upscale_ui_data

__all__ = [
    "prepare_enhance_ui_data",
    "prepare_transfer_ui_data",
    "prepare_upscale_ui_data",
]
