## Gradio UI for Cosmos Workflow

This is a Gradio web interface for managing AI inference workflows. Gradio is a Python framework that creates web UIs using pre-built components.

## UI Structure
- **app.py** — Main entry point, assembles all tabs
- **tabs/** — Each major UI section
  - prompts_ui.py — Prompt management interface
  - runs_ui.py — Run monitoring interface
  - runs_handlers.py — Event handlers for runs
  - inputs_ui.py — Input file management
  - jobs_ui.py — Active jobs monitoring interface
- **components/** — Reusable UI components
  - header.py — App header
  - global_controls.py — Shared controls
- **styles.py** — Theme and styling
- **helpers.py** — UI utility functions

## Design Philosophy

Go all out within Gradio's component system. Create the most fully-featured, thoughtful implementation possible. Include as many relevant features and interactions as the framework allows. Don't hold back - give it your all.

## Technical Context

Uses CosmosAPI for all backend operations - never bypass to use low-level wrappers directly. Check if a method is already implemented before you duplicate code.

## Testing

Use Playwright to test the UI regularly during development. Test interactions, data updates, and user workflows frequently to ensure everything works as expected.