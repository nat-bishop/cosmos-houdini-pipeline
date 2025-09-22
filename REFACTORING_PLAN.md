# Refactoring Plan: Named Component Response Pattern

## Overview
Refactor the Gradio UI to use named component responses instead of positional lists, fixing upscaling issues and improving maintainability.

**Total Estimated Time:** ~8 hours
**Approach:** Gradual refactoring with immediate bug fixes

---

## Current Issues to Fix

- [ ] **UI doesn't refresh after upscaling** - Runs display doesn't update after queuing job
- [ ] **Inefficient version filtering** - Makes O(n) API calls per filter operation
- [ ] **Upscale button doesn't hide** - Remains visible after upscaling completes
- [ ] **Fragile label parsing** - Extracts run_ids from display strings
- [ ] **No table indicators** - Table doesn't show which runs have upscaled versions

---

## Phase 1: Create Reusable Response Builder (2 hours)

### Tasks
- [ ] Create `cosmos_workflow/ui/components/` directory
- [ ] Create `response_builder.py` with `GradioResponse` class
- [ ] Implement core methods:
  - [ ] `__init__(component_names)`
  - [ ] `set(component_name, **kwargs)`
  - [ ] `set_many(updates)`
  - [ ] `to_list()`
  - [ ] `empty(component_names)` class method
- [ ] Write unit tests for GradioResponse
- [ ] Verify it handles all gr.update() parameters correctly

### Implementation Details
```python
class GradioResponse:
    """Manages complex Gradio update returns with named components."""

    def __init__(self, component_names: list[str]):
        self.component_names = component_names
        self.updates = {name: gr.update() for name in component_names}

    def set(self, component_name: str, **kwargs):
        """Set update parameters for a component."""
        if component_name not in self.component_names:
            raise ValueError(f"Unknown component: {component_name}")
        self.updates[component_name] = gr.update(**kwargs)
        return self  # For chaining

    def to_list(self) -> list:
        """Convert to ordered list for Gradio."""
        return [self.updates[name] for name in self.component_names]
```

---

## Phase 2: Quick Fix - UI Refresh After Upscaling (30 min)

### Tasks
- [ ] Update `execute_upscale` function signature to include filter parameters
- [ ] Add gallery, table, stats refresh after job queuing
- [ ] Update event handler in `app.py` to pass filter inputs
- [ ] Test that UI updates immediately after upscaling

### Files to Modify
- [ ] `cosmos_workflow/ui/tabs/runs_handlers.py::execute_upscale`
- [ ] `cosmos_workflow/ui/app.py` (upscale button click handler)

---

## Phase 3: Refactor `on_runs_table_select` (3 hours)

### Tasks

#### 3.1 Define Component Structure (30 min)
- [ ] Create `RUN_DETAILS_COMPONENTS` constant list with all 40+ components in order
- [ ] Document each component's purpose with comments
- [ ] Verify order matches current return statement

#### 3.2 Extract Video Processing (1 hour)
- [ ] Create `VideoProcessor` class
- [ ] Implement methods:
  - [ ] `__init__(run_details, ops)`
  - [ ] `get_input_videos()` -> list[tuple[str, str]]
  - [ ] `_load_spec_data()`
  - [ ] `_load_prompt_inputs()`
  - [ ] `_process_with_spec()`
  - [ ] `_process_with_defaults()`
  - [ ] `_find_control_video(control_type)`
- [ ] Move all nested video logic into VideoProcessor
- [ ] Test video extraction independently

#### 3.3 Split Model-Specific Builders (1.5 hours)
- [ ] Refactor main `on_runs_table_select` to dispatcher pattern
- [ ] Create `build_transfer_response(run_details, ops)`
- [ ] Create `build_enhance_response(run_details, ops)`
- [ ] Create `build_upscale_response(run_details, ops)`
- [ ] Extract common setup into `build_common_response()`
- [ ] Test each builder independently

### Files to Create/Modify
- [ ] `cosmos_workflow/ui/tabs/runs_handlers.py` (major refactor)
- [ ] Consider creating `cosmos_workflow/ui/processors/video_processor.py`

---

## Phase 4: Fix Version Filter Efficiency (1.5 hours)

### Tasks

#### 4.1 Add Batch Lookup Method (45 min)
- [ ] Add `find_upscaled_runs_batch()` to DataRepository
- [ ] Use single SQL query with IN clause
- [ ] Return dict mapping source_run_id -> upscaled_run
- [ ] Add to CosmosAPI as public method

#### 4.2 Refactor Version Filter (45 min)
- [ ] Create `apply_version_filter()` helper function
- [ ] Extract all run_ids first (single pass)
- [ ] Batch lookup upscaled versions
- [ ] Apply filter with map lookup (O(1) per item)
- [ ] Remove inefficient label parsing

### Files to Modify
- [ ] `cosmos_workflow/services/data_repository.py`
- [ ] `cosmos_workflow/api/cosmos_api.py`
- [ ] `cosmos_workflow/ui/tabs/runs_handlers.py::load_runs_data_with_version_filter`

---

## Phase 5: Add Visual Indicators (1 hour)

### Tasks

#### 5.1 Table Indicators (30 min)
- [ ] Modify `build_runs_table()` to batch check upscaled versions
- [ ] Add "⬆️" emoji to runs that have upscaled versions
- [ ] Consider adding separate column for upscale status

#### 5.2 Gallery Badges (30 min)
- [ ] Add "[4K ⬆️]" badge to upscaled videos in gallery
- [ ] Add small indicator to original videos that have upscaled versions
- [ ] Ensure badges are consistent across filters

### Files to Modify
- [ ] `cosmos_workflow/ui/tabs/runs_handlers.py::load_runs_data`

---

## Phase 6: Create Reusable Patterns (1 hour)

### Tasks

#### 6.1 Apply Pattern to Other Handlers (30 min)
- [ ] Create response builders for prompts tab
- [ ] Create response builders for jobs tab
- [ ] Identify other functions returning multiple gr.update()

#### 6.2 Create Validation Service (30 min)
- [ ] Create `RunValidationService` class
- [ ] Implement `can_upscale(run) -> (bool, str)`
- [ ] Implement `can_delete(run) -> (bool, str)`
- [ ] Implement `can_rerun(run) -> (bool, str)`
- [ ] Use throughout codebase for consistent validation

### Files to Create
- [ ] `cosmos_workflow/ui/services/validation_service.py`

---

## Testing Checklist

### Unit Tests
- [ ] GradioResponse class methods
- [ ] VideoProcessor extraction logic
- [ ] Validation service rules
- [ ] Batch lookup SQL queries

### Integration Tests
- [ ] Upscale workflow end-to-end
- [ ] Version filter with 100+ runs
- [ ] Table selection with all model types
- [ ] UI refresh after operations

### Manual Testing
- [ ] Create new upscale job and verify UI updates
- [ ] Test version filter dropdown (all options)
- [ ] Verify upscale button visibility logic
- [ ] Check table indicators display correctly
- [ ] Confirm no regression in existing features

---

## Rollback Plan

If issues arise during refactoring:

1. **Phase 2 is independent** - Can be deployed immediately
2. **Phase 3 can be done gradually** - One model type at a time
3. **Keep old functions** - Rename to `_legacy` during transition
4. **Feature flag option** - Use environment variable to toggle new/old code

---

## Success Metrics

- [ ] No more positional list returns (use named components)
- [ ] Version filter completes in <100ms for 500 runs
- [ ] All UI updates happen immediately after operations
- [ ] Code coverage increases by 20%
- [ ] Function length reduced to <100 lines
- [ ] Zero regressions in existing functionality

---

## Notes During Implementation

_Add discoveries, issues, and decisions here as you work:_

-

---

## Post-Refactoring Cleanup

- [ ] Remove all `_legacy` functions
- [ ] Update documentation with new patterns
- [ ] Write developer guide for GradioResponse usage
- [ ] Create template for new UI handlers
- [ ] Schedule team code review