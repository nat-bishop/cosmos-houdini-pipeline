# Remaining Refactoring Tasks

## Missing Event Wiring (14 components)

### Inputs Tab
1. **input_gallery** - Gallery selection for input videos
2. **inputs_date_filter** - Date filtering for input directories
3. **inputs_search** - Search functionality for inputs
4. **inputs_sort** - Sort order for input directories
5. **view_prompts_for_input_btn** - Navigate to prompts for selected input

### Prompts Tab
6. **select_all_btn** - Select all prompts in table
7. **clear_selection_btn** - Clear prompt selection
8. **delete_selected_btn** - Delete selected prompts
9. **prompts_confirm_delete_btn** - Confirm prompt deletion
10. **prompts_cancel_delete_btn** - Cancel prompt deletion
11. **ops_prompts_table** - Operations prompts table selection

### Runs Tab
12. **view_runs_btn** - Navigate to runs (cross-tab navigation)
13. **clear_nav_filter_btn** - Clear navigation filter

### Jobs Tab
14. **auto_advance_toggle** - Auto-advance for job logs
15. **batch_size** - Batch size configuration
16. **cancel_job_btn** - Cancel job operation
17. **clear_logs_btn** - Clear log display
18. **queue_pause_checkbox** - Pause queue checkbox

## Import/Component Issues to Fix

### 1. None Component Handling
- **Problem**: `components.get()` returns None for missing components
- **Solution**: Add None filtering before passing to Gradio events
- **Status**: Partially fixed for manual_refresh

### 2. Missing Component Safety Checks
Need to add safety checks for:
- All event wirings should check component existence
- All outputs should filter None values
- All inputs should verify components exist

### 3. Cross-Tab Navigation Events
Missing implementations for:
- `prepare_runs_navigation()` - Navigate from prompts to runs
- `prepare_prompts_navigation_from_input()` - Navigate from inputs to prompts
- These are in `wire_cross_tab_navigation()` but incomplete

### 4. Prompts Deletion Dialog
Missing the complete deletion flow:
- Preview dialog
- Confirmation
- Cancellation
- Currently only basic handlers exist

### 5. Input Gallery Events
The input gallery selection and preview functionality needs:
- `on_input_gallery_select()`
- Update preview components
- Load metadata

## Code Quality Issues

### 1. Inconsistent Error Handling
- Some events have try/catch, others don't
- Need consistent error handling pattern

### 2. Duplicate Code
- Star rating handlers repeat similar logic
- Filter event wiring has repetition
- Could be further simplified

### 3. Long Functions
- `wire_runs_selection_events()` - 100+ lines
- `wire_runs_action_events()` - 150+ lines
- Could be broken down further

## Testing Requirements

### 1. Component Existence Tests
- Verify all expected components are created
- Check component IDs match between UI creation and event wiring

### 2. Event Wiring Tests
- Confirm all events are properly wired
- Test None filtering works correctly
- Verify cross-tab navigation

### 3. Integration Tests
- Full UI load without errors
- All tabs functional
- Event handlers execute without errors

## Priority Order for Completion

1. **HIGH**: Fix None component handling throughout builder.py
2. **HIGH**: Add missing cross-tab navigation events
3. **MEDIUM**: Wire missing input gallery events
4. **MEDIUM**: Complete prompts deletion flow
5. **LOW**: Add remaining filter/sort events
6. **LOW**: Implement auto-advance and batch size controls

## Estimated Effort

- **Immediate fixes** (None handling): 1 hour
- **Missing events**: 2-3 hours
- **Testing & validation**: 1-2 hours
- **Total**: 4-6 hours to fully complete

## Files to Modify

1. `cosmos_workflow/ui/core/builder.py` - Main event wiring
2. `cosmos_workflow/ui/core/navigation.py` - Cross-tab navigation
3. `cosmos_workflow/ui/tabs/inputs_handlers.py` - Input gallery handlers
4. `cosmos_workflow/ui/tabs/prompts_handlers.py` - Deletion flow