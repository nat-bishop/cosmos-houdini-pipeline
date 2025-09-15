"""Global controls component for the Cosmos Workflow Manager UI."""

import gradio as gr

from cosmos_workflow.config import ConfigManager


def create_global_controls(config: ConfigManager):
    """Create the global refresh control panel.

    Args:
        config: Configuration manager instance

    Returns:
        Tuple of (components_dict, event_handlers)
    """
    components = {}

    with gr.Row():
        with gr.Column(scale=3):
            # Status indicators
            components["refresh_status"] = gr.Textbox(
                label="System Status",
                value="✅ Connected | Last refresh: Never",
                interactive=False,
                container=False,
                elem_classes=["status-indicator"],
            )

        with gr.Column(scale=1):
            # Manual refresh control
            components["manual_refresh_btn"] = gr.Button(
                "🔄 Refresh Now",
                variant="secondary",
                size="sm",
            )

    return components
