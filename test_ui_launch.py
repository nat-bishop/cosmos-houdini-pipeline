#!/usr/bin/env python
"""Test script to launch UI directly and verify changes."""

import sys

print(f"Python executable: {sys.executable}")
print(f"Python path: {sys.path[:3]}")

# Import and check module location
import cosmos_workflow

print(f"cosmos_workflow location: {cosmos_workflow.__file__}")

# Import the UI app module
from cosmos_workflow.ui import app

print(f"app module location: {app.__file__}")

# Check if our new function exists
if hasattr(app, "get_input_videos_for_run"):
    print("[SUCCESS] get_input_videos_for_run function found - changes are present!")
else:
    print("[FAIL] get_input_videos_for_run function NOT found - using old code!")

# Try to launch the UI
print("\nLaunching UI on port 7872...")
try:
    ui = app.create_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=7872,
        inbrowser=True,
        allowed_paths=["inputs/", "outputs/"],
    )
except Exception as e:
    print(f"Error launching UI: {e}")
    import traceback

    traceback.print_exc()
