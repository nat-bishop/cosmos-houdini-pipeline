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
    # Get refresh interval from config
    ui_config = config._config_data.get("ui", {})
    default_refresh_interval = ui_config.get("refresh_interval", 5)
    
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
            # Auto-refresh controls
            with gr.Row():
                components["auto_refresh_enabled"] = gr.Checkbox(
                    label="Auto-refresh",
                    value=True,
                    container=False,
                    elem_classes=["auto-refresh-toggle"],
                )
                components["refresh_interval"] = gr.Slider(
                    minimum=2,
                    maximum=30,
                    value=default_refresh_interval,
                    step=1,
                    label="Interval (s)",
                    container=False,
                    visible=True,
                )
                components["manual_refresh_btn"] = gr.Button(
                    "🔄 Refresh Now",
                    variant="secondary",
                    size="sm",
                )
    
    # Global timer for auto-refresh
    components["global_refresh_timer"] = gr.Timer(
        value=float(default_refresh_interval), 
        active=True
    )
    
    return components