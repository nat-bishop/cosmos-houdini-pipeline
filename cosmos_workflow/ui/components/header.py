#!/usr/bin/env python3
"""Header component for Cosmos Workflow UI.

Contains the system status display and refresh controls.
"""

import gradio as gr


def create_header_ui(config):
    """Create the header UI with status and refresh controls.

    Args:
        config: ConfigManager instance for getting UI config

    Returns:
        dict: Dictionary of UI components
    """
    components = {}

    # Title and description
    gr.Markdown("# 🌌 Cosmos Workflow Manager v1.2")
    gr.Markdown("Comprehensive UI for managing Cosmos Transfer workflows")

    # Global Refresh Control Panel
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
