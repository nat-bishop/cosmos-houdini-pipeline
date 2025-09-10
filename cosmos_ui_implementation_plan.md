# Cosmos Workflow Gradio App - Phased Implementation Plan

## Overview
Build a comprehensive Gradio UI that provides all cosmos CLI functionality with superior UX, using the existing log viewer as a foundation. Each phase builds on the previous, with Playwright testing at every step.

## Core Principles
1. **Never bypass CosmosAPI** - Always use the same methods as CLI
2. **Test incrementally** - Playwright verification after each feature
3. **Build on existing** - Leverage the working log viewer component
4. **Progressive enhancement** - Start simple, add complexity gradually

---

## Phase 1: Foundation & Input Browser (Simplest)
**Goal**: Basic navigation and input visualization

### 1.1 Enhanced App Structure
- [x] Convert existing `app.py` to multi-tab interface
- [x] Keep existing log viewer as one tab
- [x] Add "Inputs" tab with basic file listing
- [x] Test: Verify tabs switch correctly with Playwright ✅

### 1.2 Input Directory Gallery
- [x] Display `inputs/videos/*` directories as cards
- [x] Show directory names and file count
- [x] Use `gr.Gallery` with video thumbnails
- [x] Test: Verify all input directories appear ✅

### 1.3 Input Preview
- [x] Load and display `color.mp4` as thumbnail for each directory
- [x] Add selection handler with SelectData
- [x] Display file sizes and video metadata (with enhanced info)
- [x] Show all modalities (color, depth, segmentation) in side-by-side display
- [x] Test: Verify video thumbnails load and display ✅

**Testing Checkpoint**: Full Playwright test of input browsing ✅ COMPLETED

### Progress Notes:
- Created `cosmos_workflow/ui/cosmos_app.py` with multi-tab interface
- Implemented input gallery using gr.Gallery with video thumbnails
- Added video preview for all modalities (color, depth, segmentation)
- Used gr.SelectData for handling gallery selection events
- Integrated existing log viewer into new tabbed interface
- Renamed cosmos_app.py to app.py (replaced old single-tab version)
- App can be launched using `cosmos ui` command or `python -m cosmos_workflow.ui.app`

---

## Phase 2: Prompt Management
**Goal**: View and create prompts for inputs

### 2.1 List Existing Prompts
- [x] Add "Prompts" tab
- [x] Call `ops.list_prompts()` (same as CLI)
- [x] Display in `gr.Dataframe` with search
- [x] Test: Verify prompt list matches CLI output

### 2.2 Prompt Creation Form
- [x] Add prompt creation interface in Inputs tab
- [x] Text input for prompt text
- [x] Negative prompt field (optional)
- [x] Model type selector (transfer/upscale)
- [x] Call `ops.create_prompt()` exactly like CLI
- [x] Test: Create prompt and verify it appears in list

### 2.3 Input-Prompt Association
- [x] When input selected, show associated prompts
- [x] Filter prompts by selected input
- [x] Add "Create Prompt for This Input" button
- [x] Test: Verify prompt-input relationships

**Testing Checkpoint**: Full prompt CRUD operations test - COMPLETED

### Phase 2 Completion Notes (Updated 2025-09-10):
- All prompt management features implemented ✅
- Using CosmosAPI exactly as CLI does (never bypassing to DataRepository) ✅
- Proper config path handling using ConfigManager ✅
- Input-prompt association with auto-navigation to Prompts tab ✅
- Added "Input Prompt ID" field for better tracking ✅
- Negative prompt pre-filled with default from config.toml ✅
- Ready for Phase 3 (Operations/Inference)

### Recent Improvements (2025-09-10):
- Fixed "Loading..." screen bug - app now loads properly
- Enhanced metadata display with proper line breaks
- Gallery configured for 5 columns with 400px height
- Video previews changed from tabs to side-by-side display
- Auto-navigation working when clicking "Create Prompt for This Input"
- Negative prompt shows full default value, editable by user

### Known Minor Issues:
- Gallery thumbnails appear square despite videos being 16:9 (Gradio limitation)
- "Multimodal Control Inputs:" label occasionally on same line as previous field

### Development Setup:
- Use `cosmos ui` to launch the app (or `python -m cosmos_workflow.ui.app`)
- App replaced old single-tab log viewer with multi-tab interface
- Located in cosmos_workflow/ui/app.py (renamed from cosmos_app.py)
- For CLI development: use `pip install -e .` then normal cosmos commands
- For multi-branch work: reinstall with `pip install -e .` when switching

---

## Phase 3: Basic Operations (Inference)
**Goal**: Run inference with real-time progress

### 3.1 Inference Execution
- [ ] Add "Run Inference" button for selected prompts
- [ ] Call `ops.quick_inference()` like CLI
- [ ] Show operation started confirmation
- [ ] Test: Verify inference starts on remote

### 3.2 Progress Monitoring
- [ ] Integrate existing log streaming for active runs
- [ ] Show container status using `ops.get_active_containers()`
- [ ] Add progress bar based on log parsing
- [ ] Test: Verify logs stream during inference

### 3.3 Run Status Display
- [ ] Add "Active Runs" section
- [ ] Poll for status updates
- [ ] Show estimated time remaining
- [ ] Test: Verify status updates in real-time

**Testing Checkpoint**: Complete inference workflow test

---

## Phase 4: Run History & Outputs
**Goal**: View historical runs and outputs

### 4.1 Run History Table
- [ ] Add "Runs" tab
- [ ] Call `ops.list_runs()` like CLI
- [ ] Sortable/filterable DataTable
- [ ] Include all run types (inference, enhance, upscale)
- [ ] Test: Verify run history matches database

### 4.2 Output Gallery
- [ ] Add "Outputs" tab for visual results
- [ ] Filter runs with video outputs only
- [ ] Display output videos in gallery
- [ ] Add download buttons
- [ ] Test: Verify output videos play correctly

### 4.3 Run Details View
- [ ] Click run to see full details
- [ ] Show inputs, parameters, timestamps
- [ ] Display logs from completed runs
- [ ] Link to output files
- [ ] Test: Verify all run metadata displays

**Testing Checkpoint**: Full history and output browsing test

---

## Phase 5: Advanced Operations
**Goal**: Prompt enhancement and upscaling

### 5.1 Prompt Enhancement
- [ ] Add "Enhance" button for prompts
- [ ] Call `ops.enhance_prompt()` like CLI
- [ ] Show enhancement in progress
- [ ] Display before/after comparison
- [ ] Test: Verify enhancement works

### 5.2 Upscaling Workflow
- [ ] Add "Upscale" button for completed runs
- [ ] Call `ops.upscale()` with proper parameters
- [ ] Show upscaling progress
- [ ] Display 4K output when complete
- [ ] Test: Verify upscaling produces 4K video

### 5.3 Batch Operations
- [ ] Multi-select for prompts
- [ ] Batch inference execution
- [ ] Queue management UI
- [ ] Test: Verify batch operations work

**Testing Checkpoint**: Advanced operations workflow test

---

## Phase 6: Comparison & Analysis
**Goal**: Side-by-side comparisons and quality analysis

### 6.1 Video Comparison Tool
- [ ] Add "Compare" tab
- [ ] Dual video player with sync controls
- [ ] Frame-by-frame stepping
- [ ] A/B slider overlay
- [ ] Test: Verify synchronized playback

### 6.2 Output Selection
- [ ] Select multiple outputs to compare
- [ ] Drag-and-drop into comparison slots
- [ ] Save comparison sessions
- [ ] Test: Verify comparison state persists

### 6.3 Metrics Display
- [ ] Show video properties side-by-side
- [ ] Resolution, bitrate, duration
- [ ] Generation parameters used
- [ ] Test: Verify metrics accuracy

**Testing Checkpoint**: Full comparison feature test

---

## Phase 7: Polish & UX Enhancements
**Goal**: Production-ready interface

### 7.1 Search & Filtering
- [ ] Global search across prompts/runs
- [ ] Advanced filters (date, status, type)
- [ ] Save filter presets
- [ ] Test: Verify search returns correct results

### 7.2 User Preferences
- [ ] Remember last selected tab
- [ ] Save view preferences
- [ ] Custom shortcuts
- [ ] Test: Verify preferences persist

### 7.3 Error Handling
- [ ] Graceful error messages
- [ ] Retry mechanisms
- [ ] Offline mode detection
- [ ] Test: Verify error states handled

### 7.4 Performance Optimization
- [ ] Lazy loading for large galleries
- [ ] Thumbnail caching
- [ ] Pagination for tables
- [ ] Test: Verify performance with many items

**Testing Checkpoint**: Full application stress test

---

## Phase 8: Advanced Features (Stretch Goals)
**Goal**: Power user features

### 8.1 Workflow Templates
- [ ] Save operation sequences
- [ ] One-click workflow execution
- [ ] Share workflows

### 8.2 Keyboard Navigation
- [ ] Tab navigation
- [ ] Hotkeys for common operations
- [ ] Vim-style navigation

### 8.3 Export/Import
- [ ] Export prompts/settings
- [ ] Import from JSON/CSV
- [ ] Backup/restore functionality

---

## Testing Strategy

### After Each Sub-Phase:
1. **Functionality Test**: Does the feature work as intended?
2. **API Consistency**: Does it use CosmosAPI like the CLI?
3. **UI Responsiveness**: Is the interface responsive?
4. **Error Handling**: Does it handle errors gracefully?

### Playwright Test Points:
- Navigation between tabs
- Form submissions
- Button clicks and responses
- Data loading and display
- Video playback
- Real-time updates
- Error states

### Review Checkpoints:
- After each major phase
- Before moving to next complexity level
- When encountering issues
- After significant refactoring

---

## Implementation Order Rationale

1. **Start with visualization** (Phase 1) - Easiest, no mutations
2. **Add read operations** (Phase 2) - Still safe, builds confidence
3. **Introduce mutations** (Phase 3) - Controlled, single operations
4. **Expand to history** (Phase 4) - More complex queries
5. **Advanced operations** (Phase 5) - Build on proven foundation
6. **Comparison tools** (Phase 6) - Enhanced UX features
7. **Polish** (Phase 7) - Production readiness
8. **Stretch goals** (Phase 8) - Nice-to-haves

---

## Success Metrics

- [ ] Feature parity with CLI
- [ ] Faster task completion than CLI
- [ ] Zero CosmosAPI bypasses
- [ ] All Playwright tests passing
- [ ] Responsive performance
- [ ] Intuitive navigation
- [ ] Comprehensive error handling

---

## Notes
- Each phase should take 1-2 hours to implement
- Testing should take 15-30 minutes per phase
- Regular commits after each working feature
- Document any API limitations discovered
- Keep existing log viewer functional throughout