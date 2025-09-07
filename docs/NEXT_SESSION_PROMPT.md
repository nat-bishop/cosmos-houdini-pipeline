# Prompt for Next Session

## Context
I've been implementing a logging infrastructure for the Cosmos Houdini Experiments project. We've completed Phases 1-4, which include centralized logging, database storage, remote log streaming, and a Gradio UI for log viewing. The system uses file-based logs that are written by scripts during Docker container execution and streamed back using RemoteLogStreamer.

## Current Implementation Status
- ✅ **LogViewer class** (`cosmos_workflow/ui/log_viewer.py`) - 95 lines, displays colored logs with search/filter
- ✅ **Gradio app** (`cosmos_workflow/ui/app.py`) - 250 lines, accessible via `cosmos ui` command
- ✅ **Unified operations** in `WorkflowOperations` for both CLI and UI
- ✅ **File-based log streaming** using RemoteLogStreamer (superior to Docker logs for our use case)

## What Works Now
1. Scripts write logs to `/workspace/outputs/{prompt_name}/run.log` on remote GPU
2. RemoteLogStreamer reads these files with position tracking
3. LogViewer displays logs with color coding (ERROR=red, WARNING=yellow, INFO=blue)
4. App shows active jobs and allows manual Run ID entry to stream logs

## Task for This Session
The Gradio UI currently requires manual interaction - users must:
1. Enter a Run ID manually
2. Click "Start Streaming" button
3. Click "Refresh" to update logs

**Please simplify the UI to automatically stream logs:**

### Requirements
1. **Remove manual Run ID input** - Auto-detect active jobs
2. **Remove Start Streaming button** - Start automatically
3. **Add job selector dropdown** - If multiple jobs, let user pick
4. **Auto-stream on load** - If one job running, stream it immediately
5. **Auto-refresh** - Update job list every 5 seconds

### Key Files to Modify
- `cosmos_workflow/ui/app.py` - The Gradio interface
- Current problematic code around lines 167-185 (Run ID input and Start button)

### Implementation Hints
- `get_running_jobs()` already fetches active runs from database
- Should return Gradio dropdown choices format: `[(display_name, run_id), ...]`
- Use `gr.Dropdown()` with `interactive=True`
- Hook into dropdown's `change` event to auto-stream
- Consider using `gr.Timer()` or periodic callback for auto-refresh

### Expected Outcome
When user runs `cosmos ui`:
- If NO jobs: Shows "No active jobs"
- If ONE job: Immediately starts streaming its logs
- If MULTIPLE jobs: Shows dropdown, streams first one, can switch

The interface should feel automatic and require minimal user interaction.

## Additional Context
The full implementation plan is in `docs/logging-infrastructure-implementation-plan.md`. The "Next Session TODO" section (line 313) has more details about this task.