#!/usr/bin/env python
"""Test script to launch UI directly and verify changes."""


# Import and check module location

# Import the UI app module
from cosmos_workflow.ui import app

# Check if our new function exists
if hasattr(app, "get_input_videos_for_run"):
    pass
else:
    pass

# Try to launch the UI
try:
    ui = app.create_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=7872,
        inbrowser=True,
        allowed_paths=["inputs/", "outputs/"],
    )
except Exception:
    import traceback

    traceback.print_exc()
