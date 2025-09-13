# Gradio App Improvement Plan & Progress

## Overview
This document tracks the implementation of improvements to the Cosmos Workflow Gradio application, addressing both critical bugs and feature enhancements.

## Implementation Phases

### Phase 1: Critical Bug Fix - Runs Tab Video Display ⚠️
**Status**: PARTIALLY COMPLETED
**Priority**: CRITICAL
**Issue**: Videos not displaying when clicking on runs - run details and generated videos sections are empty

#### Root Cause Analysis
- [x] Database structure stores videos in `outputs['output_path']`
- [x] UI code incorrectly looked for `output_path` at root level
- [x] Event handler had incorrect signature with default value

#### Implementation Steps
1. [x] Fix `runs_handlers.py::on_runs_table_select()` - fixed event signature
2. [x] Fix `runs_handlers.py::load_runs_data()` - fixed path extraction
3. [x] Test with completed runs - details section appears
4. [x] Test with failed runs (empty outputs) - handled gracefully
5. [x] Verify gallery and detail views work - details section appears but videos not showing

#### Files Modified
- `cosmos_workflow/ui/tabs/runs_handlers.py`
  - Lines 74-77: Fixed gallery video path extraction
  - Lines 170-172: Fixed detail view video path extraction
  - Lines 25-30: Added prompt text enrichment
  - Line 131: Fixed event handler signature
  - Updated logging format from %s to {}

#### Remaining Issues (Found in Testing)
1. **Generated Videos Gallery Tab** - Still empty, videos not displaying
2. **Run Details - Output Video** - Video component shows but no video loads
3. **Run Details - Input Videos Gallery** - Shows empty placeholder
4. **Run Details - Info Tab** - Missing Prompt Name field (shows empty)
5. **Run Details - Parameters Tab** - Shows empty JSON object `{}` instead of actual parameters

---

### Phase 1.5: Complete Runs Tab Video Display Fix ✅
**Status**: FULLY COMPLETED (2025-09-13)
**Priority**: CRITICAL
**Issue**: Videos still not displaying despite path extraction fixes

#### Root Cause Analysis
- [x] Video file paths stored in `outputs['files']` array, not `output_path`
- [x] Circular import issue when loading CosmosAPI from app.py
- [x] Input videos needed to be fetched from prompt data
- [x] Parameters stored in `execution_config`, not root level

#### Implementation Steps
1. [x] Fixed output video extraction from files array
2. [x] Fixed gallery video extraction to use files array
3. [x] Created new CosmosAPI instance to avoid circular import
4. [x] Fixed input videos extraction from prompt data
5. [x] Removed non-existent prompt_name field
6. [x] Fixed parameters JSON extraction from execution_config
7. [x] Tested with actual video files - all working!

#### Specific Fixes Needed
- **Gallery Videos**: Check if `output_path` needs path normalization
- **Output Video**: Ensure Path.exists() check works correctly
- **Input Videos**: Investigate actual data structure, may need different extraction
- **Prompt Name**: Currently getting from `params.get("prompt_name")` - may be in different location
- **Parameters JSON**: Currently passing just `params` - may need full `execution_config`

---

### Phase 2: Core Feature Parity - Prompts Delete ❌
**Status**: Not Started
**Priority**: HIGH

#### Implementation Steps
1. [ ] Add selection checkboxes to prompts table
2. [ ] Add batch operation buttons (Select All, Clear, Delete)
3. [ ] Implement delete handler with confirmation
4. [ ] Show preview of items to delete
5. [ ] Update table after deletion

#### Files to Modify
- `cosmos_workflow/ui/tabs/prompts_ui.py`
- `cosmos_workflow/ui/tabs/prompts_handlers.py`
- `cosmos_workflow/ui/app.py`

---

### Phase 3: UI Polish ❌
**Status**: Not Started
**Priority**: MEDIUM

#### 3.1 Video Aspect Ratio Fix
- [ ] Remove conflicting CSS in `styles.py`
- [ ] Update gallery configuration in `inputs_ui.py`
- [ ] Test with various video aspect ratios

#### 3.2 Smart Filtering & Navigation
- [ ] Add status/text filters to Prompts tab
- [ ] Implement cross-tab data passing
- [ ] Add click handlers for input videos → filter prompts
- [ ] Implement programmatic tab switching

---

### Phase 4: Dashboard Enhancement - Jobs & Queue ❌
**Status**: Not Started
**Priority**: LOW

#### Implementation Steps
1. [ ] Redesign layout with better hierarchy
2. [ ] Create sub-tabs for Queue/Jobs/Logs
3. [ ] Remove redundant information
4. [ ] Add queue control buttons
5. [ ] Improve visual design with cards/metrics

---

### Phase 5: UI Reorganization ❌
**Status**: Not Started
**Priority**: FUTURE

#### Considerations
- [ ] Design unified input management tab
- [ ] Plan nested tab structure
- [ ] Avoid screen bloat
- [ ] Maintain intuitive workflow

---

## Testing Checklist

### Phase 1 Tests
- [ ] Completed run shows video in gallery - **FAILED: Gallery empty**
- [x] Clicking run shows video in detail view - **PARTIAL: Section appears but no video**
- [x] Failed runs handle gracefully
- [x] Runs with missing outputs don't crash
- [ ] Multiple video files handled correctly - **NOT TESTED**

### Phase 1.5 Tests
- [x] Generated Videos gallery shows videos - **PASS**
- [x] Output video plays in Run Details - **PASS**
- [x] Input videos display in gallery (all 3: Color/Visual, Depth, Segmentation) - **PASS**
- [x] Prompt Name shows in Info tab (earthquake_camera_derelict) - **PASS**
- [x] Parameters JSON displays correctly - **PASS**
- [x] Gallery videos are clickable and open run details - **PASS**

### Phase 2 Tests
- [ ] Can select individual prompts
- [ ] Select All/Clear work correctly
- [ ] Delete preview shows correct items
- [ ] Deletion updates table immediately
- [ ] Cannot delete prompts with active runs

---

## Notes & Discoveries

### Data Structure Findings
- Runs store outputs as: `{"outputs": {"files": [...]}}`
- Video path typically ends with `output.mp4`
- Some runs may have multiple MP4 files
- Path separators vary (Windows backslash vs forward slash)

### Component Count Verification
- Runs detail view expects 21 components
- Must maintain exact count when modifying returns

---

## Rollback Instructions
Each phase is independent. If issues arise:
1. Revert the specific phase's changes
2. Document the issue in this file
3. Adjust approach before retry

---

### Phase 1.6: Run Details Visibility Enhancement ✅
**Status**: COMPLETED (2025-09-13)
**Priority**: HIGH
**Issue**: Run details only visible in Run Records tab, not in Generated Videos tab

#### Implementation
- Moved Run Details section outside of both tabs structure
- Now appears below both Generated Videos and Run Records tabs
- Details persist when switching between tabs

#### Files Modified
- `cosmos_workflow/ui/tabs/runs_ui.py`
  - Line 126: Moved Run Details group outside tab panels
  - Lines 130-293: Fixed indentation for all run details components

---

Last Updated: 2025-09-13 (Phase 1.6 Completed - All Runs Tab issues resolved)