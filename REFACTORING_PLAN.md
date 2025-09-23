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

## Phase 1: Fix Named Returns (Week 1, Days 1-2)

### Problem
`on_runs_table_select` returns 40+ positional values - impossible to maintain

### Solution: Use Python's NamedTuple

#### Tasks
- [ ] Create `cosmos_workflow/ui/models/` directory
- [ ] Create `responses.py` with NamedTuple definitions
- [ ] Define response classes:
  - [ ] `RunDetailsResponse` for `on_runs_table_select` (40+ fields)
  - [ ] `PromptDetailsResponse` for `on_prompt_row_select` (10 fields)
  - [ ] `InputSelectionResponse` for `on_input_select` (12 fields)
- [ ] Update `on_runs_table_select` to return `RunDetailsResponse`
- [ ] Update calling code to handle NamedTuple response
- [ ] Test all UI updates still work correctly

### Implementation Example
```python
# ui/models/responses.py
from typing import NamedTuple, Any

class RunDetailsResponse(NamedTuple):
    details_visible: Any  # gr.update()
    run_id: str
    status: str
    transfer_visible: Any
    enhance_visible: Any
    upscale_visible: Any
    # ... name all 40 fields explicitly
```

---

## Phase 2: Extract Common Utilities (Week 1, Days 3-4)

### Problem
DataFrame/list checking and formatting logic repeated 10+ times

### Tasks

#### 2.1 DataFrame Utilities
- [ ] Create `cosmos_workflow/ui/utils/dataframe.py`
- [ ] Implement utility functions:
  - [ ] `get_selected_ids(data) -> list[str]`
  - [ ] `count_selected(data) -> int`
  - [ ] `select_all(data)`
  - [ ] `clear_selection(data)`
  - [ ] `get_row_by_index(data, index) -> list`
- [ ] Replace all inline DataFrame checking with utility calls
- [ ] Test with both DataFrame and list formats

#### 2.2 Formatting Utilities
- [ ] Create `cosmos_workflow/ui/utils/formatting.py`
- [ ] Implement formatting functions:
  - [ ] `format_duration(start, end) -> str`
  - [ ] `truncate_text(text, max_length=50) -> str`
  - [ ] `format_file_size(bytes) -> str`
  - [ ] `format_timestamp(iso_string) -> str`
  - [ ] `format_run_status(status) -> str`
- [ ] Replace all inline formatting with utility calls

#### 2.3 Video Utilities
- [ ] Move video functions from helpers.py to `utils/video.py`:
  - [ ] `extract_video_metadata(path) -> dict`
  - [ ] `generate_thumbnail_fast(path) -> str`
  - [ ] `get_multimodal_inputs(directory) -> list`
  - [ ] `validate_video_directory(path) -> tuple[bool, str]`

---

## Phase 3: Simplify Event Handlers (Week 2, Days 1-2)

### Problem
Tab navigation handler is 200+ lines with deeply nested conditions

### Tasks

#### 3.1 Break Down Large Functions
- [ ] Split `on_runs_table_select` into smaller functions:
  - [ ] `extract_run_details(run_id) -> dict`
  - [ ] `prepare_video_inputs(run_details) -> list`
  - [ ] `build_transfer_response(run_details) -> NamedTuple`
  - [ ] `build_enhance_response(run_details) -> NamedTuple`
  - [ ] `build_upscale_response(run_details) -> NamedTuple`
- [ ] Each function must be < 50 lines
- [ ] Keep original function that dispatches to new ones

#### 3.2 Simplify Tab Navigation
- [ ] Create `ui/handlers/tab_navigation.py`
- [ ] Split `handle_tab_select` into separate handlers:
  - [ ] `handle_inputs_tab() -> tuple`
  - [ ] `handle_prompts_tab() -> tuple`
  - [ ] `handle_runs_tab(nav_state, pending_data) -> tuple`
  - [ ] `handle_jobs_tab() -> tuple`
- [ ] Create dispatcher dictionary pattern
- [ ] Remove deeply nested conditions

---

## Phase 4: Reorganize File Structure (Week 2, Days 3-4)

### Current Structure (Monolithic)
```
ui/
  app.py (3000+ lines!)
  tabs/
    runs_handlers.py (1700+ lines!)
    prompts_handlers.py (300+ lines)
```

### Target Structure (Modular)
```
ui/
  app.py (200 lines - just assembly)
  core/
    builder.py (builds the UI structure)
    events.py (wires up event handlers)
  tabs/
    inputs/
      ui.py (UI components)
      handlers.py (event handlers)
    prompts/
      ui.py
      handlers.py
    runs/
      ui.py
      handlers.py
      filters.py (filter logic)
    jobs/
      ui.py
      handlers.py
  utils/
    dataframe.py (DataFrame utilities)
    formatting.py (display formatting)
    video.py (video operations)
  models/
    responses.py (NamedTuple definitions)
    state.py (state definitions)
```

### Tasks
- [ ] Create new directory structure
- [ ] Move code gradually (keep imports working):
  - [ ] Move inputs tab code to `tabs/inputs/`
  - [ ] Move prompts tab code to `tabs/prompts/`
  - [ ] Move runs tab code to `tabs/runs/`
  - [ ] Move jobs tab code to `tabs/jobs/`
- [ ] Update imports incrementally
- [ ] Test after each move
- [ ] Only delete old files when confirmed working

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
- [ ] No function > 100 lines (currently 400+)
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

-

---

## Risk Mitigation

- **Keep old code working** - Don't delete until new code proven
- **Test after each step** - Catch issues early
- **Incremental changes** - Each step independently valuable
- **Commit frequently** - Can rollback if needed
- **Document patterns** - Future devs understand approach

---

## Post-Refactoring Checklist

- [ ] All tests passing
- [ ] Documentation updated
- [ ] Team walkthrough completed
- [ ] Performance benchmarked
- [ ] Deployment verified
