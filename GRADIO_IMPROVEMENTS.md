# Gradio App Improvement Plan - Remaining Tasks

## Overview
This document tracks the remaining improvements to be implemented for the Cosmos Workflow Gradio application.

## Completed Work Summary
✅ **Phase 1**: Critical Runs Tab fixes - all video display issues resolved
✅ **Phase 1.5**: Complete video display implementation
✅ **Phase 1.6**: Run Details visibility in both tabs

---

## Remaining Implementation Phases

### Phase 2: Core Feature Parity - Prompts Delete
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

#### Testing Checklist
- [ ] Can select individual prompts
- [ ] Select All/Clear work correctly
- [ ] Delete preview shows correct items
- [ ] Deletion updates table immediately
- [ ] Cannot delete prompts with active runs

---

### Phase 3: UI Polish
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

### Phase 4: Dashboard Enhancement - Jobs & Queue
**Status**: Not Started
**Priority**: LOW

#### Implementation Steps
1. [ ] Redesign layout with better hierarchy
2. [ ] Create sub-tabs for Queue/Jobs/Logs
3. [ ] Remove redundant information
4. [ ] Add queue control buttons
5. [ ] Improve visual design with cards/metrics

---

### Phase 5: UI Reorganization
**Status**: Not Started
**Priority**: FUTURE

#### Considerations
- [ ] Design unified input management tab
- [ ] Plan nested tab structure
- [ ] Avoid screen bloat
- [ ] Maintain intuitive workflow

---

## Technical Notes

### Key Patterns to Follow
- Always use CosmosAPI for backend operations
- Create new CosmosAPI instances in handlers to avoid circular imports
- Maintain exact component count when modifying event handlers
- Test with Playwright regularly during development

### Data Structure Reference
- Runs store outputs as: `{"outputs": {"files": [...]}}`
- Video paths typically end with `output.mp4`
- Input videos use keys: "video", "depth", "seg"
- Prompt name stored in `prompt.parameters.name`
- Execution config contains weights and parameters

---

Last Updated: 2025-09-13