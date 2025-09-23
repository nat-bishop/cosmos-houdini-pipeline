# Gradio UI Refactoring Plan: Simplified Approach

## Overview
Refactor the Gradio UI to be less monolithic and more maintainable using simple, incremental steps. Focus on solving real problems without over-engineering.

**Core Principles:**
- Keep It Flat - Gradio works best with simple function signatures
- Use Native Features - Don't fight Gradio's design patterns
- Separate Concerns - UI, business logic, and data access should be distinct
- Make It Testable - Pure functions are easier to test and debug
- No Over-Engineering - Avoid unnecessary abstractions

---

## Phase 1: Fix Named Returns (Week 1, Days 1-2) ✅ COMPLETED

### Problem
`on_runs_table_select` returns 40+ positional values - impossible to maintain

### Solution: Use Python's NamedTuple

#### Tasks
- [x] Create `cosmos_workflow/ui/models/` directory
- [x] Create `responses.py` with NamedTuple definitions
- [x] Define response classes:
  - [x] `RunDetailsResponse` for `on_runs_table_select` (43 fields)
  - [x] `PromptDetailsResponse` for `on_prompt_row_select` (10 fields)
  - [x] `InputSelectionResponse` for `on_input_select` (12 fields)
- [x] Update `on_runs_table_select` to return `RunDetailsResponse`
- [x] Update calling code to handle NamedTuple response
- [x] Test all UI updates still work correctly
- [x] Add performance optimization (response caching)

### Completion Summary
- **Successfully refactored** `on_runs_table_select` with NamedTuple
- **Maintained 100% backward compatibility** using `list(response)`
- **Added caching** to reduce error case overhead from ~1.5ms to ~0.001ms
- **Code review verdict**: READY TO COMMIT - no critical issues found

### Code Review Recommendations for Future Phases
1. **Add unit tests** for response classes (HIGH priority)
2. **Consider field naming consistency** (runs_details_group vs runs_detail_id)
3. **Apply pattern to other handlers** with multiple returns
4. **Consider nested structures** for grouping related fields in Phase 4

---

## Phase 2: Extract Common Utilities (Week 1, Days 3-4) ✅ FULLY COMPLETED

### Problem
DataFrame/list checking and formatting logic repeated 10+ times across multiple files

### Tasks

#### 2.1 DataFrame Utilities ✅
- [x] Create `cosmos_workflow/ui/utils/dataframe.py`
- [x] Implement utility functions:
  - [x] `get_selected_ids(data) -> list[str]`
  - [x] `count_selected(data) -> int`
  - [x] `select_all(data)`
  - [x] `clear_selection(data)`
  - [x] `get_row_by_index(data, index) -> list`
  - [x] Added bonus utilities: `get_cell_value()`, `get_selected_rows()`, `update_selection_status()`, `is_dataframe()`
- [x] Replace all inline DataFrame checking with utility calls
- [x] Test with both DataFrame and list formats

#### 2.2 Formatting Utilities ✅
- [x] Create `cosmos_workflow/ui/utils/formatting.py`
- [x] Implement formatting functions:
  - [x] `format_duration(start, end) -> str`
  - [x] `truncate_text(text, max_length=50) -> str`
  - [x] `format_file_size(bytes) -> str`
  - [x] `format_timestamp(iso_string) -> str`
  - [x] `format_run_status(status) -> str`
  - [x] Added bonus utilities: `format_percentage()`, `format_number()`, `format_time_ago()`
- [x] Updated helpers.py to delegate to new utilities

#### 2.3 Video Utilities ✅
- [x] Move video functions to `utils/video.py`:
  - [x] `extract_video_metadata(path) -> dict`
  - [x] `generate_thumbnail_fast(path) -> str` (moved from runs_handlers.py)
  - [x] `get_multimodal_inputs(directory) -> list`
  - [x] `validate_video_directory(path) -> tuple[bool, str]`
  - [x] Added bonus utilities: `get_video_files()`, `get_video_duration_seconds()`

#### 2.4 Refactored Files ✅
- [x] `prompts_handlers.py` - Replaced all DataFrame checks with utilities
- [x] `runs_handlers.py` - Replaced 2 DataFrame checks with utilities
- [x] `app.py` - Replaced 6 DataFrame checks with utilities
- [x] `tabs/inputs.py` - Updated to import video_utils directly

#### 2.5 Legacy Code Removal ✅
- [x] Removed all delegation functions from helpers.py
- [x] Updated all imports to use utilities directly
- [x] **Deleted helpers.py entirely** (no longer needed)
- [x] Verified no functionality was broken

### Final Statistics (2025-01-23)
- **3 utility modules created** with 23 utility functions
- **4 files refactored** to use utilities
- **8 DataFrame checks replaced** with utility calls
- **~300 lines of duplicate code eliminated**
- **211 lines removed** by deleting helpers.py entirely
- **100% test coverage** with all tests passing
- **Zero legacy code** - all delegations and unused functions removed

---

## Phase 3: Simplify Event Handlers (Week 2, Days 1-2) ✅ FULLY COMPLETED

### Problem
Multiple functions exceed reasonable complexity limits:
- `on_runs_table_select` is 418 lines with mixed responsibilities
- `load_runs_data` is 313 lines with complex filtering logic
- `load_runs_for_multiple_prompts` is 334 lines (duplicates load_runs_data)
- `handle_tab_select` has deeply nested conditions
- Duplicate `generate_thumbnail_fast` exists in runs_handlers.py

### Tasks

#### 3.0 Quick Cleanup ✅ COMPLETED
- [x] Remove duplicate `generate_thumbnail_fast` from runs_handlers.py
- [x] Update all calls to use `video_utils.generate_thumbnail_fast`

#### 3.1 Break Down on_runs_table_select (418 → ~330 lines) ✅ COMPLETED
Extract helper functions (keep in runs_handlers.py):
- [x] `_extract_run_metadata(run_details) -> dict` (28 lines)
- [x] `_resolve_video_paths(outputs, run_id) -> tuple` (43 lines)
- [x] `_load_spec_and_weights(run_id) -> dict` (21 lines)
- [x] `_build_input_gallery(spec_data, prompt_inputs, run_id) -> tuple` (71 lines)
- [x] `_prepare_transfer_ui_data(run_details, prepared_data) -> dict` (16 lines)
- [x] `_prepare_enhance_ui_data(run_details, prepared_data) -> dict` (34 lines)
- [x] `_prepare_upscale_ui_data(run_details, prepared_data) -> dict` (32 lines)
- [x] `_read_log_content(log_path, lines) -> str` (19 lines)
- [x] Refactor main function to use all helpers (reduced from 418 to ~330 lines)

#### 3.2 Break Down load_runs_data (313 → ~60 lines) ✅ COMPLETED
Extract helper functions (keep in runs_handlers.py):
- [x] `_apply_date_filter(runs, date_filter) -> list` (26 lines)
- [x] `_apply_run_filters(runs, type_filter, search, rating) -> list` (38 lines)
- [x] `_build_gallery_data(runs, limit) -> list` (75 lines)
- [x] `_build_runs_table_data(runs) -> list` (29 lines)
- [x] `_calculate_runs_statistics(runs, total) -> str` (11 lines)
- [x] Refactored main function to ~60 lines (from 313)

#### 3.3 Deduplicate load_runs_for_multiple_prompts ✅ COMPLETED
- [x] Refactored to use helper functions from load_runs_data
- [x] Removed all duplicate filtering logic
- [x] Reduced from 334 lines to ~85 lines
- [x] Now uses: `_apply_date_filter`, `_apply_run_filters`, `_build_gallery_data`, `_build_runs_table_data`
- [x] Tested with UI - filtering by multiple prompts works perfectly

#### 3.4 Simplify Tab Navigation (188 → ~30 lines) ✅ COMPLETED
Extract handlers (keep in app.py, use underscore prefix):
- [x] `_handle_jobs_tab_refresh() -> tuple` (18 lines)
- [x] `_format_filter_display(prompt_names) -> str` (13 lines)
- [x] `_handle_runs_tab_with_pending_data(pending_data) -> tuple` (21 lines)
- [x] `_handle_runs_tab_with_filter(nav_state) -> tuple` (34 lines)
- [x] `_handle_runs_tab_default() -> tuple` (23 lines)
- [x] Refactored main navigation handler to ~30 lines (from 188)

### Guidelines
- **Target function size**: Primary functions ~50 lines, helpers ~40 lines
- **Acceptable exceptions**: Data processing functions up to ~80-100 lines if logic is linear
- **Stay in existing files**: No new directories until Phase 4
- **Use underscore prefix**: Mark internal functions with `_` prefix
- **Keep it functional**: No classes, follow Gradio patterns
- **Test incrementally**: Verify UI works after each extraction

---

## Phase 4: Reorganize File Structure (Week 2, Days 3-4) 🚧 IN PROGRESS

### Problem
- **app.py is 3255 lines** - contains handler logic that belongs in tab-specific files
- **Inconsistent structure** - inputs has both inputs.py and inputs_ui.py (duplicate)
- **runs_handlers.py is 1607 lines** - still too large after Phase 3

### Current Structure Analysis
```
ui/
  app.py (3255 lines - monolithic!)
  tabs/
    inputs.py (405 lines - duplicate of inputs_ui.py)
    inputs_ui.py (225 lines)
    jobs_ui.py (167 lines)
    jobs_handlers.py (53 lines - underutilized)
    prompts_ui.py (355 lines)
    prompts_handlers.py (238 lines)
    runs_ui.py (569 lines)
    runs_handlers.py (1607 lines - still large)
  utils/ (✅ created in Phase 2)
  models/ (✅ created in Phase 1)
  components/ (exists but underutilized)
```

### Implementation Strategy: Incremental Migration
**Principle**: Move handlers from app.py to appropriate files WITHOUT breaking imports

### Execution Plan (Prioritized by Impact)

#### Step 4.1: Move Job Handlers (~200 lines) ✅ COMPLETED
- [x] Move from app.py to jobs_handlers.py:
  - [x] `check_running_jobs()` (135 lines)
  - [x] `refresh_jobs_on_tab_select()` (9 lines)
  - [x] `start_log_streaming()` (37 lines)
  - [x] `refresh_and_stream()` (13 lines)
- [x] Update imports in app.py
- [x] Test compilation - no errors
- **Result**: app.py reduced from 3255 → 3063 lines (-192 lines)

#### Step 4.2: Consolidate Inputs Tab (~400 lines) ✅ COMPLETED
- [x] Created new inputs_handlers.py with all handlers
- [x] Moved handler functions from app.py:
  - [x] `get_input_directories()`
  - [x] `filter_input_directories()`
  - [x] `load_input_gallery()`
  - [x] `on_input_select()`
  - [x] `create_prompt()`
- [x] Updated imports in app.py
- [x] Fixed function calls to pass inputs_dir parameter
- [x] Deleted duplicate inputs.py file (405 lines removed)
- **Result**: app.py reduced from 3063 → 2775 lines (-288 lines)

#### Step 4.3: Move Prompt Handlers from app.py (~500 lines)
- [ ] Move all prompt-related handlers to prompts_handlers.py
- [ ] Update imports and event bindings

#### Step 4.4: Move Run Handlers from app.py (~800 lines)
- [ ] Move all run-related handlers to runs_handlers.py
- [ ] Update imports and event bindings

#### Step 4.5: Extract Core Logic (~600 lines)
- [ ] Create core/ directory with:
  - [ ] navigation.py - tab navigation logic
  - [ ] state.py - global state management
  - [ ] builder.py - UI assembly logic

#### Step 4.6: Split runs_handlers.py (1607 → ~500x3)
- [ ] Create runs/ subdirectory:
  - [ ] handlers.py - main event handlers
  - [ ] filters.py - filtering logic
  - [ ] data_processing.py - gallery/table builders

### Target Structure (After Phase 4)
```
ui/
  app.py (~300 lines - just initialization)
  core/
    navigation.py (~200 lines)
    state.py (~150 lines)
    builder.py (~250 lines)
  tabs/
    inputs_ui.py
    inputs_handlers.py
    jobs_ui.py
    jobs_handlers.py (~250 lines)
    prompts_ui.py
    prompts_handlers.py (~700 lines)
    runs_ui.py
    runs/
      handlers.py (~500 lines)
      filters.py (~500 lines)
      data_processing.py (~500 lines)
```

### Why This Approach Works
1. **Immediate Impact** - Each step reduces app.py significantly
2. **No Breaking Changes** - Imports remain stable during migration
3. **Incremental Value** - Each step independently improves organization
4. **Easy Testing** - Can verify after each move
5. **Reversible** - Git history allows rollback if needed

---

## Phase 5: Apply Gradio Best Practices (Week 3)

### Tasks

#### 5.1 Component Creation Pattern
- [ ] Refactor each tab to follow pattern:
```python
def create_runs_tab():
    """Create runs tab UI components."""
    with gr.Tab("Runs"):
        # Create components
        gallery = gr.Gallery(...)
        table = gr.Dataframe(...)

        # Return component references
        return {
            'runs_gallery': gallery,
            'runs_table': table,
        }
```

#### 5.2 Event Wiring Pattern
- [ ] Create separate event setup functions:
```python
def setup_runs_events(components):
    """Wire up event handlers for runs tab."""
    components['runs_gallery'].select(
        fn=on_gallery_select,
        inputs=[components['runs_gallery']],
        outputs=[components['runs_details']]
    )
```

#### 5.3 State Management
- [ ] Use simple Gradio State (no complex classes)
- [ ] Replace complex navigation state with simple dict
- [ ] Document state structure clearly

#### 5.4 Documentation and Cleanup
- [ ] Add type hints to all functions
- [ ] Add docstrings to all modules
- [ ] Remove all `_legacy` functions
- [ ] Delete commented-out code

---

## What NOT to Do

❌ **Don't create abstract base classes** for handlers
❌ **Don't add dependency injection** - not needed
❌ **Don't create custom state management** - use gr.State
❌ **Don't wrap gr.update()** in abstractions
❌ **Don't create "services"** for simple functions
❌ **Don't add complex patterns** like Strategy or Observer
❌ **Don't over-abstract** - keep it simple and readable

---

## Testing Checklist

### After Each Phase
- [ ] All existing features still work
- [ ] No performance regression
- [ ] UI remains responsive
- [ ] No new errors in console

### Integration Tests
- [ ] Create prompt workflow
- [ ] Run inference workflow
- [ ] View runs with filtering
- [ ] Navigate between tabs
- [ ] Refresh data manually
- [ ] Kill running jobs

### Manual UI Testing
- [ ] Test with 0 prompts/runs
- [ ] Test with 100+ prompts/runs
- [ ] Test all filter combinations
- [ ] Test error scenarios
- [ ] Test on different screen sizes

---

## Success Metrics

### Code Quality
- [ ] Primary orchestrator functions < 100 lines
- [ ] Helper functions typically < 50 lines
- [ ] No file > 500 lines (currently 3000+)
- [ ] Clear separation: UI, handlers, utilities
- [ ] All functions have single responsibility

### Developer Experience
- [ ] Can find any code in < 10 seconds
- [ ] New developer understands structure in < 5 minutes
- [ ] Changes don't cascade to unrelated files
- [ ] Tests can run on individual components

### Maintainability
- [ ] Adding new tab requires < 100 lines
- [ ] Changing UI layout doesn't break handlers
- [ ] Can modify one feature without touching others
- [ ] Clear naming conventions throughout

---

## Implementation Notes

_Track discoveries, issues, and decisions here as you work:_

### Phase 1 (Completed 2024-01-23)
- Used NamedTuple instead of dataclass for lighter weight and tuple compatibility
- Added `create_empty_run_details_response()` helper to eliminate duplicate code
- Implemented caching optimization based on code review feedback
- Verified integration with app.py - all 43 fields properly mapped
- Tested with Playwright - UI works correctly with refactored code

### Phase 2 (Completed 2025-01-23)
- Created 3 utility modules in cosmos_workflow/ui/utils/
- Fixed critical bug: Can't use `if not data` with pandas DataFrames (use `data is None`)
- Added bonus utilities beyond original plan for better coverage
- Comprehensive test suite created and passing
- **Deleted helpers.py entirely** after removing all delegations
- **Zero backward compatibility kept** - direct imports only

### Phase 3 Progress (2025-01-23)
- **Phase 3.1**: Successfully extracted 8 helper functions from `on_runs_table_select`
  - Removed duplicate `generate_thumbnail_fast` function
  - Refactored main function to use helpers - reduced from 418 to ~330 lines
  - Fixed critical bug: `input_videos` undefined error by properly calling `_build_input_gallery`
- **Phase 3.2**: Refactored `load_runs_data` function
  - Extracted 5 helper functions for filtering, gallery, table, and statistics
  - Reduced from 313 lines to ~60 lines
  - All filters tested and working correctly
- **Phase 3.3**: Consolidated `load_runs_for_multiple_prompts`
  - Removed all duplicate filtering logic
  - Now reuses helpers from `load_runs_data`
  - Reduced from 334 lines to ~85 lines
  - Tested with multiple prompt selection - working perfectly
- **Phase 3.4**: Simplified tab navigation handler in app.py
  - Extracted 5 helper functions for different tab handling scenarios
  - Reduced main `handle_tab_select` from 188 lines to ~30 lines
  - Cleaner separation of concerns for each tab's logic
- **Key achievements**:
  - Eliminated ~800 lines of code across 4 major functions
  - Created 18 reusable helper functions total
  - All helper functions are pure and testable
  - Tested with Playwright: All UI interactions work correctly

### Lessons Learned
- NamedTuples are perfect for refactoring functions with many returns
- Caching empty responses improves performance in error scenarios
- Code review agent provided valuable performance optimization suggestions
- DataFrame truthiness requires special handling in Python
- Always test with both DataFrame and list formats for Gradio compatibility
- **Don't keep backward compatibility unnecessarily** - clean breaks are better
- **Delete dead code immediately** - unused functions just create confusion
- **Extract helpers incrementally** - don't break working code
- **Complex UI functions** may benefit from helper extraction without full rewrite

---

## Risk Mitigation

- **Keep old code working** - Don't delete until new code proven
- **Test after each step** - Catch issues early
- **Incremental changes** - Each step independently valuable
- **Commit frequently** - Can rollback if needed
- **Document patterns** - Future devs understand approach

---

## Phase 3 Implementation Strategy

### Day 1: Core Functions
1. **Morning: Quick Cleanup**
   - Remove duplicate `generate_thumbnail_fast`
   - Verify all thumbnails still generate

2. **Afternoon: Refactor `on_runs_table_select`**
   - Extract helper functions one by one
   - Test UI after each extraction
   - Keep original working throughout
   - Only delete old code when new version proven

### Day 2: Data Loading & Navigation
1. **Morning: Refactor `load_runs_data`**
   - Extract filtering and display helpers
   - Consolidate with `load_runs_for_multiple_prompts`
   - Test all filter combinations

2. **Afternoon: Simplify Tab Navigation**
   - Extract tab-specific handlers
   - Implement dispatcher pattern
   - Test all navigation paths

---

## Post-Refactoring Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Team walkthrough completed
- [ ] Performance benchmarked
- [ ] Deployment verified
