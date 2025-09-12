"""Global controls component for the Cosmos Workflow Manager UI."""

import gradio as gr
from datetime import datetime

from cosmos_workflow.config import ConfigManager
from cosmos_workflow.utils.logging import logger


def create_global_controls(config: ConfigManager):
    """Create the global refresh control panel.

    Args:
        config: Configuration manager instance

    Returns:
        Tuple of (components_dict, event_handlers)
    """
    # Get refresh interval from config
    ui_config = config._config_data.get("ui", {})
    default_refresh_interval = ui_config.get("refresh_interval", 5)

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


def setup_global_refresh_handlers(
    components: dict,
    data_loading_functions: dict
) -> None:
    """Set up event handlers for global refresh controls.

    Args:
        components: Dictionary of UI components
        data_loading_functions: Dictionary of data loading functions for each tab
    """

    def global_refresh_all():
        """Refresh all data across all tabs."""
        try:
            # Get current status
            status = f"✅ Connected | Last refresh: {datetime.now().strftime('%H:%M:%S')}"

            # Load all data using provided functions
            results = {"status": status}

            for key, func in data_loading_functions.items():
                try:
                    results[key] = func()
                except Exception as e:
                    logger.error("Error refreshing %s: %s", key, str(e))
                    results[key] = None

            return results

        except Exception as e:
            logger.error("Error during global refresh: %s", str(e))
            return {"status": f"❌ Error: {str(e)}"}

    # Connect timer to refresh function
    if "global_refresh_timer" in components:
        components["global_refresh_timer"].tick(
            fn=global_refresh_all,
            inputs=[],
            outputs=list(components.values())
        )

    # Manual refresh button
    if "manual_refresh_btn" in components:
        components["manual_refresh_btn"].click(
            fn=global_refresh_all,
            inputs=[],
            outputs=list(components.values())
        )

    # Auto-refresh toggle
    if "auto_refresh_enabled" in components and "global_refresh_timer" in components:
        components["auto_refresh_enabled"].change(
            fn=lambda enabled: gr.Timer(active=enabled),
            inputs=[components["auto_refresh_enabled"]],
            outputs=[components["global_refresh_timer"]],
        )

    # Refresh interval change
    if "refresh_interval" in components and "global_refresh_timer" in components:
        components["refresh_interval"].change(
            fn=lambda interval: gr.Timer(value=interval, active=True),
            inputs=[components["refresh_interval"]],
            outputs=[components["global_refresh_timer"]],
        )