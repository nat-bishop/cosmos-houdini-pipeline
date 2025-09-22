# Smart Batching Implementation Plan

## Overview
Refactor the job queue system to support intelligent batching of similar jobs for 2-5x performance improvements. This plan simplifies the current multi-selection interface and adds smart grouping based on control configurations.

## Key Design Decisions
- **Single job queue model**: Remove multi-selection, add jobs individually
- **Queue reordering allowed**: Batching can optimize job order
- **Two batching modes**: Strict (identical controls) or Mixed (master batch)
- **Conservative memory management**: Use proven batch sizes based on control count
- **Transparency over complexity**: Show users exactly what's being batched and why

---

## Phase 1: Simplify Prompts Tab UI
**Goal**: Remove multi-selection complexity, use single row selection
**Estimated Time**: 1-2 hours

### Tasks
- [ ] Remove checkbox column from prompts table (`prompts_ui.py`)
- [ ] Set table to `interactive=False`
- [ ] Remove "Select All" and "Clear Selection" buttons
- [ ] Update "Delete Selected" to work with selected row
- [ ] Update "View Runs" to use selected row instead of checkboxes
- [ ] Update event handlers in `app.py` to use row selection
- [ ] Remove all checkbox-related state management

### Testing Checklist
- [ ] Row selection highlights correctly
- [ ] Delete works with selected row
- [ ] View runs works with selected row
- [ ] Prompt details display for selected row
- [ ] No checkbox artifacts remain

### Success Criteria
- Simpler, cleaner UI
- All operations work with single selection
- Code is less complex

---

## Phase 2: Convert to Single-Job Queue Model
**Goal**: Replace multi-inference with "Add to Queue" for individual jobs
**Estimated Time**: 1 hour

### Tasks
- [ ] Replace "Run Inference" section with "Add to Queue"
- [ ] Remove prompt count displays
- [ ] Add single "Add to Queue" button for selected prompt
- [ ] Update handlers to add individual jobs (batch_size=1)
- [ ] Remove batch inference UI elements
- [ ] Update queue service to handle single job additions

### Testing Checklist
- [ ] "Add to Queue" adds single job
- [ ] Queue displays individual jobs
- [ ] Jobs execute correctly
- [ ] No multi-selection artifacts remain

### Success Criteria
- Simplified inference workflow
- Clear one-click queue addition
- Maintains existing functionality

---

## Phase 3: Create Smart Batching Utilities
**Goal**: Build core batching algorithms
**Estimated Time**: 2-3 hours

### New File: `cosmos_workflow/utils/smart_batching.py`

### Functions to Implement
```python
def get_control_signature(job_config: dict) -> tuple[str, ...]:
    """Extract sorted tuple of active controls from job config.
    Example: {'weights': {'edge': 0.5, 'depth': 0}} -> ('edge',)
    """

def count_active_controls(job_config: dict) -> int:
    """Count number of active controls (weight > 0)."""

def group_jobs_strict(jobs: list[JobQueue], max_batch_size: int) -> list[dict]:
    """Group jobs with identical control signatures only.
    Returns list of batch configurations with 'jobs' and 'signature'.
    """

def group_jobs_mixed(jobs: list[JobQueue], max_batch_size: int) -> list[dict]:
    """Group jobs allowing mixed controls using master batch approach.
    Optimizes to minimize total control overhead.
    Returns list of batch configurations with 'jobs' and 'master_controls'.
    """

def calculate_batch_metrics(batches: list[dict]) -> dict:
    """Calculate efficiency metrics for batch configuration.
    Returns: time_estimate, speedup_factor, control_overhead, etc.
    """

def get_safe_batch_size(num_controls: int, user_max: int) -> int:
    """Conservative batch sizing based on control count.
    1 control: min(8, user_max)
    2 controls: min(4, user_max)
    3+ controls: min(2, user_max)
    """
```

### Testing Checklist
- [ ] Control signature extraction works correctly
- [ ] Strict grouping creates correct groups
- [ ] Mixed grouping optimizes control overhead
- [ ] Batch metrics are accurate
- [ ] Safe batch sizes are conservative

### Success Criteria
- Clean, readable algorithms
- Comprehensive test coverage
- No over-engineering

---

## Phase 4: Extend Queue Service for Batching
**Goal**: Add batching capabilities to SimplifiedQueueService
**Estimated Time**: 1-2 hours

### Methods to Add to `simple_queue_service.py`

```python
def get_batchable_jobs(self, limit: int = 100) -> list[JobQueue]:
    """Get all queued inference/batch_inference jobs.
    Excludes enhance and upscale jobs.
    """

def create_smart_batches(self, mix_controls: bool = False) -> list[dict]:
    """Create optimized batches from queued jobs.
    Uses strict or mixed mode based on mix_controls flag.
    Returns list of batch configurations.
    """

def claim_batch_jobs(self, job_ids: list[str]) -> bool:
    """Atomically claim multiple jobs for batch processing.
    Uses database transaction to prevent race conditions.
    """

def execute_smart_batches(self, batches: list[dict]) -> dict:
    """Execute all smart batches.
    Returns results with performance metrics.
    """
```

### Testing Checklist
- [ ] Correctly identifies batchable jobs
- [ ] Creates valid batch configurations
- [ ] Atomic job claiming works
- [ ] Batch execution completes successfully
- [ ] Non-batchable jobs are excluded

### Success Criteria
- Clean integration with existing service
- Maintains atomicity guarantees
- Preserves error handling

---

## Phase 5: Add Smart Batching UI Controls
**Goal**: Add batching interface to Active Jobs tab
**Estimated Time**: 1-2 hours

### UI Components to Add (`jobs_ui.py`)

```python
# After pause_queue_checkbox:
components["mix_controls_checkbox"] = gr.Checkbox(
    label="Mix Control Inputs",
    value=False,
    info="Allow batching jobs with different controls"
)

# Smart batch group (visible when paused)
with gr.Group(visible=False) as components["smart_batch_group"]:
    gr.Markdown("#### ⚡ Smart Batching")
    components["batch_preview"] = gr.Markdown("")
    components["execute_batch_btn"] = gr.Button(
        "Execute Smart Batch",
        variant="primary"
    )
```

### Event Handlers to Add (`app.py`)

```python
def analyze_batches(paused: bool, mix_controls: bool):
    """Analyze queue for batching opportunities."""

def execute_smart_batches():
    """Execute the analyzed batches."""
```

### Testing Checklist
- [ ] Controls show/hide with pause state
- [ ] Batch preview displays correctly
- [ ] Mix controls toggle changes analysis
- [ ] Execute button processes batches
- [ ] Progress feedback during execution

### Success Criteria
- Clear, intuitive UI
- Transparent batch preview
- Smooth execution flow

---

## Phase 6: Integration Testing
**Goal**: Ensure all components work together
**Estimated Time**: 1-2 hours

### Test Scenarios

1. **Basic Flow**
   - [ ] Add individual jobs to queue
   - [ ] Pause queue
   - [ ] View batch analysis
   - [ ] Execute smart batch
   - [ ] Verify results

2. **Strict Mode Testing**
   - [ ] Add jobs with identical controls
   - [ ] Add jobs with different controls
   - [ ] Verify correct grouping
   - [ ] Check execution efficiency

3. **Mixed Mode Testing**
   - [ ] Enable mix controls
   - [ ] Add varied jobs
   - [ ] Verify master batch creation
   - [ ] Check overhead optimization

4. **Edge Cases**
   - [ ] Empty queue
   - [ ] Single job
   - [ ] Non-batchable jobs (enhance/upscale)
   - [ ] Maximum batch size limits

### Performance Benchmarks
- [ ] Measure speedup for identical controls (target: 3-5x)
- [ ] Measure mixed mode efficiency (target: 2-3x)
- [ ] Document actual vs theoretical speedup

### Success Criteria
- All test scenarios pass
- Performance improvements demonstrated
- No regressions in existing functionality

---

## Implementation Notes

### What We're Building
- Simple, transparent batching system
- Two clear modes: strict and mixed
- Conservative memory management
- User-visible efficiency metrics

### What We're NOT Building
- Complex memory prediction
- Dynamic retry mechanisms
- Automatic reordering beyond grouping
- Machine learning optimization
- Priority queues

### Key Files Modified
- `cosmos_workflow/ui/tabs/prompts_ui.py` - Remove multi-selection
- `cosmos_workflow/ui/tabs/prompts_handlers.py` - Update to single selection
- `cosmos_workflow/utils/smart_batching.py` - NEW: Batching algorithms
- `cosmos_workflow/services/simple_queue_service.py` - Add batching methods
- `cosmos_workflow/ui/tabs/jobs_ui.py` - Add batching controls
- `cosmos_workflow/ui/app.py` - Wire up events

### Migration Path
1. Phase 1-2 can be deployed immediately (UI simplification)
2. Phase 3-4 can be developed in parallel (backend)
3. Phase 5 connects frontend to backend
4. Phase 6 validates the complete system

---

## Rollback Plan
Each phase is independently valuable and can be rolled back:
- Phase 1-2: Revert to checkbox-based selection
- Phase 3-4: Remove batching utilities (no user impact)
- Phase 5: Hide batching UI controls
- System remains functional at each stage

---

## Future Enhancements (Post-MVP)
- Batch size learning from successful runs
- Memory usage profiling
- Automatic retry with smaller batches on OOM
- Batch scheduling optimization
- Historical performance analytics