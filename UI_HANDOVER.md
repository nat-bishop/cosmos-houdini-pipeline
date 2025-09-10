# Cosmos Workflow UI - Handover Document
**Date**: 2025-09-10
**Current Status**: Phases 1-2 Complete, Phase 4 (Outputs) needs fixing

## Quick Start
```bash
# Launch the UI
cosmos ui

# UI will be available at http://localhost:7860
```

## What's Working ✅

### 1. Input Browser Tab
- Displays all input video directories from `inputs/` folder
- Gallery view with 4 columns, 16:9 aspect ratio thumbnails
- Left panel (gallery) is 2x size of right panel (details)
- Click thumbnail to see video details and previews
- Video previews show Color RGB, Depth Map, and Segmentation in tabs
- "Create Prompt for This Input" button auto-navigates to Prompts tab

### 2. Prompts Tab
- Lists all existing prompts in a table
- Create new prompts with:
  - Video Directory (auto-filled from Input Browser)
  - Prompt text
  - Negative prompt (pre-filled with default from config)
  - Model type selector
- Filters by model type and limit
- Automatic refresh after prompt creation

### 3. Log Monitor Tab
- Real-time log streaming from active containers
- Shows active container status
- Log statistics display

## What Needs Fixing 🔧

### Outputs Tab (Phase 4)
The Outputs tab structure is implemented but **not functioning properly**:

**Issues:**
1. Gallery not displaying any outputs even though runs exist in database
2. The `load_outputs()` function may not be correctly fetching/filtering runs
3. Gallery might be receiving empty data on app load

**Debug Steps Needed:**
1. Check if `ops.list_runs()` returns data correctly
2. Verify the output_path exists for completed runs
3. Test if gallery can display video files when given correct paths
4. Check if auto-load on app start is working

**Relevant Code Location:**
- File: `cosmos_workflow/ui/app.py`
- Function: `load_outputs()` (around line 741)
- Event handlers for Outputs tab (around line 809-819)

## Recent Changes (2025-09-10)

### UI Improvements
- Changed Input Browser from 5 to 4 columns for larger thumbnails
- Increased gallery height from 400px to 900px
- Made Input Browser 2x the size of right panel
- Added CSS for 16:9 aspect ratio with 200px minimum height
- Set galleries to `interactive=False` to prevent file uploads
- Fixed "Multimodal Control Inputs:" formatting
- Theme: Soft (respects system dark/light preference)

### File Structure
- Main UI: `cosmos_workflow/ui/app.py`
- Implementation plan: `cosmos_ui_implementation_plan.md`
- This handover: `UI_HANDOVER.md`

## Architecture Notes

### Important Principles
1. **ALWAYS use CosmosAPI** (`ops`) - never bypass to DataRepository
2. All operations should mirror CLI functionality
3. Use existing wrappers (SSHManager, DockerExecutor, etc.)
4. Follow the implementation plan phases

### Key Components
- `ops`: Instance of CosmosAPI for all operations
- `config`: ConfigManager instance for configuration
- `log_viewer`: LogViewer instance for log display

## Next Steps

### Priority 1: Fix Outputs Tab
1. Debug why `load_outputs()` isn't populating the gallery
2. Verify database has runs with valid output_path
3. Test gallery with hardcoded video paths first
4. Fix the data flow from database to gallery

### Priority 2: Phase 3 - Operations Tab
After fixing Outputs, implement the Operations tab:
- Add "Run Inference" button for selected prompts
- Implement `ops.quick_inference()` call
- Add progress monitoring
- Display container status

### Future Enhancements
- Phase 5: Prompt enhancement and upscaling
- Phase 6: Video comparison tools
- Phase 7: Search, filtering, and preferences
- Phase 8: Workflow templates (stretch goal)

## Testing
- Manual testing: Launch with `cosmos ui` and check each tab
- The UI should respect system dark/light mode preference
- Verify all galleries are read-only (no upload capability)
- Test Input-to-Prompt workflow by selecting input and creating prompt

## Known Issues
- Outputs tab not displaying runs (main issue to fix)
- Playwright navigation sometimes gets stuck (browser issue, not UI)

## Contact
Refer to `CLAUDE.md` for coding standards and `cosmos_ui_implementation_plan.md` for detailed phase descriptions.