# Jobs & Queue Tab Enhancement Implementation Plan

## Overview
Transform the Jobs & Queue tab from a basic monitoring panel into an effective queue management center without overengineering or duplicating features from other tabs.

## Implementation Steps

### Step 1: Add Queue Control Buttons ✅ CURRENT
**Priority: CRITICAL**
- Add "Kill Active Job" button with confirmation dialog
- Add "Clear Queue" button with confirmation dialog
- Wire up handlers to use existing CosmosAPI methods
- Test with Playwright

### Step 2: Improve Status Display
**Priority: HIGH**
- Replace text fields with formatted cards
- Active Job Card: Run ID, Prompt name, Status, Progress, Container ID
- Queue Summary Card: Pending count, Next in queue, GPU availability
- Use gr.Group and gr.Markdown for better formatting

### Step 3: Replace Recent Runs with Pending Queue
**Priority: HIGH**
- Change table to show pending runs instead of recent runs
- Columns: Position, Run ID, Prompt Name, Actions
- Add "Remove" button for each pending item
- Connect to `list_runs(status="pending")`

### Step 4: Enhance Log Viewer
**Priority: MEDIUM**
- Auto-start streaming when job is active
- Add color coding for log levels
- Implement auto-scroll toggle
- Add search within logs

### Step 5: Smart Timer Updates
**Priority: HIGH**
- Use existing queue_timer component
- Activate only when Jobs & Queue tab is selected
- Deactivate when switching to other tabs
- Update queue status, active jobs, and pending table every 2-3 seconds

## Design Principles
- **Focused Purpose**: Monitor active work and manage queue
- **No Duplication**: Don't replicate features from Runs tab
- **Simple & Maintainable**: Avoid overengineering
- **User-Centric**: Clear actions with confirmations

## Technical Notes
- Use CosmosAPI exclusively (no direct low-level access)
- Test with Playwright after each step
- Commit after each working implementation
- Follow existing UI patterns from other tabs

## Success Criteria
- Users can kill running jobs safely
- Users can clear the queue with confirmation
- Queue status updates automatically when viewing the tab
- Pending jobs are clearly visible with management options
- Log streaming works reliably

---
Last Updated: 2025-09-15