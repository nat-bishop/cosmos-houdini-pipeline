# Smart Batching Implementation Plan (TDD Approach)

## Overview
Implement smart batching as an **overlay optimization** for the existing queue system. Smart batching analyzes already-queued jobs and reorganizes them into optimized batches for 2-5x performance improvements. This approach preserves existing workflows while adding optional batching capabilities.

## Key Design Decisions
- **TDD approach**: Write comprehensive tests first, implement to pass tests
- **Overlay optimization**: Works on top of existing queue, no workflow changes required
- **User-initiated only**: Smart batching requires explicit user action when queue is paused
- **Preserves existing UI**: Keep familiar multi-select interface initially
- **Two batching modes**: Strict (identical controls) or Mixed (master batch)
- **Conservative memory management**: Use proven batch sizes based on control count
- **Non-invasive**: Zero impact when not used - existing functionality unchanged

## Smart Batching Prerequisites
- **Queue must be paused**: Smart batching only available when queue toggle is set to "Don't proceed"
- **User-initiated**: Batching happens only when user clicks "Analyze for Smart Batching"
- **Preview required**: User sees optimization preview before execution
- **Optional feature**: System works normally if smart batching is never used

---

## Phase 1: TDD Foundation - Write Tests First
**Goal**: Define core behavior through pragmatic tests
**Estimated Time**: 1-2 hours

### Testing Philosophy (Solo Developer)
- Focus on happy path and main failure modes
- Don't test implementation details, test behavior
- Skip exhaustive edge case testing initially
- Add tests when bugs are found (test-driven debugging)

### Test Files to Create
- `tests/unit/utils/test_smart_batching.py` - Core batching algorithms
- `tests/unit/services/test_queue_smart_batching.py` - Queue service extensions
- `tests/integration/test_smart_batching_workflow.py` - End-to-end workflow

### Test Coverage Requirements
```python
# Control signature extraction
test_get_control_signature_single_control()
test_get_control_signature_multiple_controls()
test_get_control_signature_no_controls()
test_get_control_signature_zero_weights()

# Job grouping - strict mode
test_group_jobs_strict_identical_controls()
test_group_jobs_strict_mixed_controls() # should create separate groups
test_group_jobs_strict_respects_batch_limits()
test_group_jobs_strict_with_different_prompt_counts()

# Job grouping - mixed mode
test_group_jobs_mixed_optimizes_control_overhead()
test_group_jobs_mixed_creates_master_batch()
test_group_jobs_mixed_respects_batch_limits()
test_group_jobs_mixed_master_control_selection() # verify union algorithm

# Conservative batch sizing
test_safe_batch_size_single_control() # max 8
test_safe_batch_size_two_controls() # max 4
test_safe_batch_size_three_plus_controls() # max 2
test_safe_batch_size_respects_user_override()

# State management
test_analysis_invalidation_on_queue_change()

# Error handling
test_batch_with_job_failure() # basic failure handling

# Edge cases
test_empty_job_list()
test_single_job()
test_non_batchable_jobs_excluded()
test_all_jobs_different_controls()
test_mixed_batchable_and_non_batchable_jobs()
```

### Success Criteria
- All test scenarios defined with expected behavior
- Edge cases and error conditions covered
- Clear requirements for implementation
- Tests fail initially (red phase of TDD)

---

## Phase 2: Core Smart Batching Logic Implementation
**Goal**: Implement utilities to make all tests pass (green phase)
**Estimated Time**: 2-3 hours

### New File: `cosmos_workflow/utils/smart_batching.py`

### Functions to Implement (Following TDD)
```python
def get_control_signature(job_config: dict) -> tuple[str, ...]:
    """Extract sorted tuple of active controls from job config.
    Example: {'weights': {'edge': 0.5, 'depth': 0}} -> ('edge',)
    Only includes controls with weight > 0.
    """

def group_jobs_strict(jobs: list[JobQueue], max_batch_size: int) -> list[dict]:
    """Group jobs with identical control signatures only.
    Returns list of batch configurations with 'jobs' and 'signature'.
    Jobs with different signatures go in separate batches.
    """

def group_jobs_mixed(jobs: list[JobQueue], max_batch_size: int) -> list[dict]:
    """Group jobs allowing mixed controls using master batch approach.
    Creates batches that minimize total control overhead.
    Master controls = union of all controls in the batch.
    Returns list of batch configurations with 'jobs' and 'master_controls'.
    Algorithm: Group jobs to minimize total unique controls across all batches.
    """

def calculate_batch_efficiency(batches: list[dict], original_jobs: list) -> dict:
    """Calculate efficiency metrics for batch configuration.
    Returns: estimated_speedup, control_reduction, job_count_before/after.
    """

def get_safe_batch_size(num_controls: int, user_max: int = 16) -> int:
    """Conservative batch sizing based on control count.
    1 control: min(8, user_max)
    2 controls: min(4, user_max)
    3+ controls: min(2, user_max)
    Note: Consider making these configurable via config.toml in future.
    """

def filter_batchable_jobs(jobs: list[JobQueue]) -> list[JobQueue]:
    """Filter jobs that can be batched together.
    Excludes: enhance, upscale job types
    Includes: inference, batch_inference
    """
```

### Implementation Guidelines
- Make tests pass with minimal, clean code
- No over-engineering - implement exactly what tests require
- Focus on correctness, readability
- Conservative approach to memory/batch sizing

### Success Criteria
- All tests pass (green phase)
- Clean, readable implementation
- Conservative batch sizing verified
- No premature optimization

---

## Phase 3: Queue Service Smart Batching Extension
**Goal**: Add smart batching overlay to existing queue system
**Estimated Time**: 1-2 hours

### Extensions to `cosmos_workflow/services/simple_queue_service.py`

```python
def analyze_queue_for_smart_batching(self, mix_controls: bool = False) -> dict:
    """Analyze queued jobs for batching opportunities.
    Returns analysis with batch preview and efficiency metrics.
    Stores analysis for later execution.
    """

def execute_smart_batches(self) -> dict:
    """Execute the stored smart batch analysis.
    Validates queue hasn't changed (simple size check).
    Claims jobs, executes batches, returns results with speedup metric.
    """

def get_smart_batch_preview(self) -> str:
    """Get human-readable preview of stored analysis.
    Returns empty string if no analysis or if stale.
    """
```

### Key Design Principles
- **Overlay approach**: Works with existing queue, doesn't change core behavior
- **Atomic operations**: Use existing database transaction patterns
- **Graceful degradation**: If batching fails, jobs can still run individually
- **Preserve queue state**: Analysis doesn't modify queue until execution

### Success Criteria
- Integration tests pass
- Existing queue functionality unaffected
- Atomic job claiming works correctly
- Batch execution uses existing CosmosAPI patterns

---

## Phase 4: Smart Batching UI Controls
**Goal**: Add user interface for smart batching analysis and execution
**Estimated Time**: 1-2 hours

### UI Components to Add to `cosmos_workflow/ui/tabs/jobs_ui.py`

```python
# Smart batching section (only visible when queue is paused)
with gr.Group(visible=False) as components["smart_batch_group"]:
    gr.Markdown("#### ⚡ Smart Batching Optimization")
    gr.Markdown("Analyze queued jobs to create optimized batches for better performance.")

    with gr.Row():
        components["analyze_batching_btn"] = gr.Button(
            "Analyze for Smart Batching",
            variant="secondary"
        )
        components["mix_controls_checkbox"] = gr.Checkbox(
            label="Allow Mixed Controls",
            value=False,
            info="Group jobs with different control inputs using master batch approach"
        )

    components["batch_analysis"] = gr.Markdown("", visible=False)
    components["execute_smart_batch_btn"] = gr.Button(
        "Execute Smart Batches",
        variant="primary",
        visible=False
    )
```

### Event Handlers to Add

```python
def analyze_smart_batching(mix_controls: bool, queue_service):
    """Analyze queue and show preview."""
    analysis = queue_service.analyze_queue_for_smart_batching(mix_controls)
    preview = queue_service.get_smart_batch_preview()

    if not preview:
        return "No batchable jobs found.", gr.update(visible=False)

    return preview, gr.update(visible=True)

def execute_smart_batching(queue_service):
    """Execute the smart batches."""
    results = queue_service.execute_smart_batches()
    return f"Completed: {results['jobs_executed']} jobs → {results['batches_created']} batches (Speedup: {results['speedup']:.1f}x)"
```

### UI Behavior Requirements
- **Smart batch controls only visible when queue is paused**
- **Analysis is non-destructive** - just shows preview
- **Clear preview** shows what will be batched and expected benefits
- **Execution confirmation** required before actual batching
- **Progress feedback** during batch execution

### Success Criteria
- Smart batch controls show/hide correctly with pause state
- Analysis provides clear, informative preview
- Execution works smoothly with good feedback
- No impact on existing UI when not used

---

## Phase 5: Integration Testing & Validation
**Goal**: Validate complete workflow and performance improvements
**Estimated Time**: 1-2 hours

### End-to-End Test Scenarios

1. **Basic Smart Batching Workflow**
   - Add multiple jobs with similar controls to queue
   - Pause queue
   - Analyze for smart batching
   - Review preview
   - Execute smart batches
   - Verify results and performance

2. **Strict Mode Testing**
   - Queue jobs with identical control signatures
   - Queue jobs with different control signatures
   - Verify strict mode groups only identical signatures
   - Check batch size limits respected

3. **Mixed Mode Testing**
   - Enable "Allow Mixed Controls"
   - Queue jobs with varied control configurations
   - Verify master batch approach used
   - Check control overhead optimization

4. **Edge Cases & Error Handling**
   - Empty queue analysis
   - Single job in queue
   - Queue with only non-batchable jobs (enhance/upscale)
   - Queue exceeding batch size limits
   - Network errors during batch execution

### Performance Benchmarks
- **Strict mode**: Measure speedup for identical controls (target: 3-5x)
- **Mixed mode**: Measure efficiency for varied controls (target: 2-3x)
- **Memory usage**: Verify conservative batch sizes prevent OOM errors
- **Queue throughput**: Compare batched vs individual execution times

### Success Criteria
- All test scenarios pass without errors
- Performance improvements meet or exceed targets
- Existing functionality completely unaffected
- Smart batching provides clear user value

---

## Phase 6: Future UI Simplification (Optional Future Work)
**Goal**: Eventually simplify multi-select interface once smart batching is proven
**Status**: Future enhancement, not part of current implementation

### Potential Future Changes
- Replace multi-select checkboxes with single "Add to Queue" buttons
- Simplify inference workflow to individual job queuing
- Remove bulk operation complexity from UI
- Focus on smart batching as primary optimization method

### Migration Strategy
- Deploy smart batching overlay first and validate adoption
- Gather user feedback on batching effectiveness
- Consider UI simplification only after smart batching is proven valuable
- Maintain backward compatibility during any future UI changes

---

## Critical Implementation Considerations

### State Management (Keep It Simple)
- **Analysis Storage**: Store analyzed batch configurations in SimplifiedQueueService instance
- **Staleness Check**: Simple check - if queue size changed, analysis is stale
- **Invalidation**: Clear stored analysis when queue changes

### Error Handling Strategy
- **Partial Batch Failures**: If individual jobs fail within a batch:
  - Continue processing remaining jobs in batch
  - Mark failed jobs with error status individually
  - Return detailed failure report with successful and failed job IDs
- **Batch Execution Rollback**: If entire batch fails:
  - Revert all claimed jobs back to 'queued' status
  - Log detailed error for debugging
  - Allow user to retry with smaller batches or individually

### Mixed Mode Algorithm Details
- **Master Control Selection**: Union of all controls in the batch
  - Example: Job1 has [edge], Job2 has [depth], Job3 has [edge, depth]
  - Master controls = [edge, depth] for all three jobs
- **Optimization Goal**: Minimize total number of unique controls across all batches
- **Grouping Strategy**: Greedy algorithm that groups jobs with most control overlap first

### User Feedback (Simple)
- **Progress**: Simple "Executing smart batches..." message during execution
- **Results**: Show actual speedup achieved after completion (for validation)
- **Stale Warning**: Simple warning if queue changed since analysis

## Solo Developer Best Practices

### YAGNI (You Aren't Gonna Need It)
- Start with the simplest implementation that delivers value
- Don't add features "just in case" - add them when needed
- Focus on core 2-5x speedup benefit, not edge cases
- Perfect is the enemy of good - ship working code

### MVP Focus
- **Phase 1-2**: Core algorithms with basic tests
- **Phase 3-4**: Simple integration with existing queue
- **Phase 5**: Minimal UI - just enough to use the feature
- **Skip initially**: Metrics, telemetry, complex state management, fancy UI

## Implementation Notes

### What Smart Batching IS
- **Optional optimization overlay** that works with existing queue
- **User-controlled feature** that requires explicit activation
- **Conservative approach** using proven batch sizes and algorithms
- **Transparent system** showing users exactly what's being optimized
- **Performance enhancement** delivering 2-5x speedup for compatible jobs
- **Non-invasive feature** with zero impact when not used

### What Smart Batching IS NOT
- Automatic background optimization
- Complex machine learning system
- Memory prediction or dynamic scaling
- Replacement for existing queue functionality
- Required feature for normal operation

### Key Technical Constraints
- **Queue must be paused**: Smart batching only works when queue is stopped
- **User-initiated analysis**: No automatic batching decisions
- **Preview before execution**: Users see and approve optimizations
- **Conservative batch sizing**: Proven limits prevent memory issues
- **Atomic operations**: Uses existing database transaction patterns
- **Graceful fallback**: Individual job execution if batching fails

### Files Modified/Created
```
New Files:
├── cosmos_workflow/utils/smart_batching.py
├── tests/unit/utils/test_smart_batching.py
├── tests/unit/services/test_queue_smart_batching.py
└── tests/integration/test_smart_batching_workflow.py

Modified Files:
├── cosmos_workflow/services/simple_queue_service.py (add batching methods)
├── cosmos_workflow/ui/tabs/jobs_ui.py (add smart batch controls)
└── cosmos_workflow/ui/core/wiring/jobs.py (wire smart batch events)
```

### Rollback Strategy
Each phase can be independently rolled back:
- **Phase 1-2**: Remove test files and utility module (no user impact)
- **Phase 3**: Remove queue service extensions (no user impact)
- **Phase 4**: Hide smart batching UI controls
- **Existing functionality remains 100% intact** at all phases

### Success Metrics
- **Performance**: 2-5x demonstrated speedup for batched operations
- **Usability**: Clear, intuitive interface with helpful previews
- **Reliability**: No regressions in existing queue functionality
- **Adoption**: Users find smart batching valuable and use it regularly
- **Safety**: Conservative approach prevents memory or stability issues