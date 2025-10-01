"""Named tuple response definitions for Gradio UI handlers.

This module provides structured response types to replace positional returns
in Gradio event handlers, improving maintainability and type safety.
"""

from typing import Any, NamedTuple

# Cache for empty response to avoid recreating on every error
_EMPTY_RESPONSE_CACHE = None


def create_empty_run_details_response():
    """Create an empty/hidden RunDetailsResponse for error cases.

    Uses caching to avoid recreating 43 gr.update() objects on every call.
    """
    global _EMPTY_RESPONSE_CACHE
    if _EMPTY_RESPONSE_CACHE is None:
        import gradio as gr

        # Create all fields as empty gr.update() calls (only once)
        _EMPTY_RESPONSE_CACHE = RunDetailsResponse(
            runs_details_group=gr.update(visible=False),
            runs_detail_id=gr.update(),
            runs_detail_status=gr.update(),
            runs_main_content_transfer=gr.update(),
            runs_main_content_enhance=gr.update(),
            runs_main_content_upscale=gr.update(),
            runs_input_video_1=gr.update(),
            runs_input_video_2=gr.update(),
            runs_input_video_3=gr.update(),
            runs_input_video_4=gr.update(),
            runs_output_video=gr.update(),
            runs_prompt_text=gr.update(),
            runs_original_prompt_enhance=gr.update(),
            runs_enhanced_prompt_enhance=gr.update(),
            runs_enhance_stats=gr.update(),
            runs_output_video_upscale=gr.update(),
            runs_original_video_upscale=gr.update(),
            runs_upscale_stats=gr.update(),
            runs_upscale_prompt=gr.update(),
            runs_info_id=gr.update(),
            runs_info_prompt_id=gr.update(),
            runs_info_status=gr.update(),
            runs_info_duration=gr.update(),
            runs_info_type=gr.update(),
            runs_info_prompt_name=gr.update(),
            star_1=gr.update(),
            star_2=gr.update(),
            star_3=gr.update(),
            star_4=gr.update(),
            star_5=gr.update(),
            runs_info_rating=gr.update(),
            runs_info_created=gr.update(),
            runs_info_completed=gr.update(),
            runs_info_output_path=gr.update(),
            runs_info_input_paths=gr.update(),
            runs_params_json=gr.update(),
            runs_log_path=gr.update(),
            runs_log_output=gr.update(),
            runs_upscale_selected_btn=gr.update(),
            runs_selected_id=gr.update(),
            runs_selected_info=gr.update(),
            runs_output_video_upscaled=gr.update(),
            runs_upscaled_tab=gr.update(),
        )
    return _EMPTY_RESPONSE_CACHE


class RunDetailsResponse(NamedTuple):
    """Response for run details selection in runs tab.

    This response contains all UI updates needed when selecting a run
    from either the gallery or table view.
    """

    # Main visibility controls
    runs_details_group: Any  # gr.update(visible=True/False)
    runs_detail_id: Any  # Hidden field with run ID
    runs_detail_status: Any  # Hidden field with status

    # Content block visibility (model-specific views)
    runs_main_content_transfer: Any  # Transfer model content visibility
    runs_main_content_enhance: Any  # Enhance model content visibility
    runs_main_content_upscale: Any  # Upscale model content visibility

    # Transfer content components (input videos)
    runs_input_video_1: Any  # First input video (usually color/visual)
    runs_input_video_2: Any  # Second input video (edge/canny)
    runs_input_video_3: Any  # Third input video (depth)
    runs_input_video_4: Any  # Fourth input video (segmentation)
    runs_output_video: Any  # Main output video
    runs_prompt_text: Any  # Prompt text display

    # Enhancement content components
    runs_original_prompt_enhance: Any  # Original prompt before enhancement
    runs_enhanced_prompt_enhance: Any  # Enhanced prompt after processing
    runs_enhance_stats: Any  # Enhancement statistics

    # Upscale content components
    runs_output_video_upscale: Any  # Upscaled output video
    runs_original_video_upscale: Any  # Original video before upscaling
    runs_upscale_stats: Any  # Upscale statistics
    runs_upscale_prompt: Any  # Upscale guiding prompt

    # Info tab components
    runs_info_id: Any  # Run ID display
    runs_info_prompt_id: Any  # Prompt ID display
    runs_info_status: Any  # Status display
    runs_info_duration: Any  # Duration display
    runs_info_type: Any  # Model type display
    runs_info_prompt_name: Any  # Prompt name display

    # Star rating buttons (5 separate buttons)
    star_1: Any  # First star button
    star_2: Any  # Second star button
    star_3: Any  # Third star button
    star_4: Any  # Fourth star button
    star_5: Any  # Fifth star button

    # Additional info fields
    runs_info_rating: Any  # Rating value (hidden)
    runs_info_created: Any  # Creation timestamp
    runs_info_completed: Any  # Completion timestamp
    runs_info_output_path: Any  # Output file path
    runs_info_input_paths: Any  # Input file paths

    # Parameters and Logs tabs
    runs_params_json: Any  # Parameters JSON display
    runs_log_path: Any  # Log file path
    runs_log_output: Any  # Log content display

    # Action buttons
    runs_upscale_selected_btn: Any  # Upscale button visibility

    # Selected run tracking
    runs_selected_id: Any  # Currently selected run ID
    runs_selected_info: Any  # Selection info display

    # Upscaled output components
    runs_output_video_upscaled: Any  # Upscaled video display
    runs_upscaled_tab: Any  # Upscaled tab visibility


class InputSelectionResponse(NamedTuple):
    """Response for input directory selection in inputs tab."""

    selected_dir_path: str  # Path to selected directory
    preview_group: Any  # Preview group visibility (compatibility)
    input_tabs_group: Any  # Input tabs visibility
    input_name: Any  # Directory name
    input_path: Any  # Directory path
    input_created: Any  # Creation time
    input_resolution: Any  # Video resolution
    input_duration: Any  # Video duration
    input_fps: Any  # Video FPS
    input_codec: Any  # Video codec
    input_files: Any  # Files list
    video_preview_gallery: Any  # Video preview gallery
    create_video_dir: Any  # Video directory for prompt creation


class PromptDetailsResponse(NamedTuple):
    """Response for prompt row selection in prompts tab."""

    prompt_id: Any  # Prompt ID
    name: Any  # Prompt name
    prompt_text: Any  # Prompt text
    negative_prompt: Any  # Negative prompt
    created: Any  # Creation date
    video_dir: Any  # Video directory
    enhanced: Any  # Enhancement status
    runs_stats: Any  # Run statistics
    rating: Any  # Average rating
    thumbnail: Any  # Video thumbnail
