# Smart Batching User Guide

**Achieve 2-5x performance improvements through intelligent job optimization**

## Overview

Smart Batching is a powerful feature that analyzes your queued inference jobs and reorganizes them into optimal batches for maximum GPU efficiency. By grouping compatible jobs together, you can significantly reduce processing time and GPU overhead.

## Key Benefits

- **2-5x Performance Gains**: Dramatically faster processing through intelligent job grouping
- **Flexible Control**: Each prompt can have different control weights within the same batch
- **Two Optimization Modes**: Choose between speed (Strict) or efficiency (Mixed)
- **Safe Operation**: Conservative memory management prevents GPU out-of-memory errors
- **Queue Preservation**: Reorganizes without executing - you maintain full control

## How It Works

### 1. Run-Level Optimization

Smart Batching extracts individual runs from your queue jobs and reorganizes them into optimal batches:

```
Original Queue:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Job A: 2 runs   │    │ Job B: 1 run    │    │ Job C: 3 runs   │
│ - Visual focus  │    │ - Depth focus   │    │ - Mixed controls│
└─────────────────┘    └─────────────────┘    └─────────────────┘

After Smart Batching:
┌─────────────────────────────────────────────────────────────────────┐
│ Optimized Batch: 6 runs with individual weights per prompt         │
│ - weights_list: [visual_weights, depth_weights, mixed_weights, ...] │
└─────────────────────────────────────────────────────────────────────┘
```

### 2. Enhanced API

The new `batch_inference` API accepts `weights_list` instead of `shared_weights`:

```python
# Before: All prompts used same weights
batch_inference(prompt_ids=["ps_1", "ps_2"], shared_weights={"vis": 0.5})

# After: Each prompt can have different weights
batch_inference(
    prompt_ids=["ps_1", "ps_2"],
    weights_list=[
        {"vis": 0.5, "edge": 0.3, "depth": 0.2},  # ps_1 weights
        {"vis": 0.3, "edge": 0.5, "depth": 0.2}   # ps_2 weights
    ]
)
```

## Getting Started

### Prerequisites

1. **Gradio UI**: Smart Batching is integrated into the Gradio web interface
2. **Queued Jobs**: You need multiple inference jobs in the queue
3. **Paused Queue**: Queue must be paused before analysis for safety

### Step-by-Step Process

#### 1. Queue Your Jobs

Add multiple inference jobs to the queue using the Gradio UI:

```python
# Queue several jobs with different control configurations
queue_service.add_job(
    prompt_ids=["ps_001", "ps_002"],
    job_type="inference",
    config={"weights": {"vis": 0.5, "edge": 0.3, "depth": 0.2}}
)

queue_service.add_job(
    prompt_ids=["ps_003"],
    job_type="inference",
    config={"weights": {"vis": 0.3, "edge": 0.5, "depth": 0.2}}
)
```

#### 2. Pause the Queue

**Important**: Always pause the queue before analysis to prevent job state changes:

```python
queue_service.set_queue_paused(True)
```

#### 3. Analyze Batching Opportunities

Choose your optimization mode and analyze:

```python
# Strict Mode: Fastest execution, groups identical controls only
analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)

# Mixed Mode: Fewer batches, allows different controls together
analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=True)
```

#### 4. Review the Analysis

The analysis provides detailed insights:

```python
if analysis:
    print(analysis["preview"])
    # Output:
    # ⚡ Smart Batching Analysis (Strict Mode):
    # - 8 runs from 5 jobs → 3 batches
    # - Estimated speedup: 2.7x
    # - Mode: Strict (identical controls only, faster execution)
    # - Batch size: 4 runs/batch
    #
    # Batch breakdown:
    #   Batch 1: 4 runs from 2 jobs (vis, edge, depth)
    #   Batch 2: 3 runs from 2 jobs (vis, depth)
    #   Batch 3: 1 run from 1 job (edge, seg)
```

#### 5. Execute the Reorganization

If satisfied with the analysis, reorganize the queue:

```python
results = queue_service.execute_smart_batches()
print(results["message"])
# Output: Queue reorganized successfully. 5 jobs → 3 batches
```

#### 6. Resume Processing

Unpause the queue to process the optimized batches:

```python
queue_service.set_queue_paused(False)
```

## Optimization Modes

### Strict Mode (Recommended for Performance)

**Best for**: Queues with many similar jobs
**Characteristics**:
- Groups runs with identical control signatures AND execution parameters
- Fastest execution per batch
- Maximum GPU efficiency
- May create more batches

```python
# Strict mode example
analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)
```

**When to use**:
- You have many jobs with identical control configurations
- Maximum speed is priority
- GPU memory is limited

### Mixed Mode (Recommended for Efficiency)

**Best for**: Diverse job queues
**Characteristics**:
- Groups runs by execution parameters only
- Allows different control types in same batch
- Fewer total batches
- Slightly slower per batch due to control overhead

```python
# Mixed mode example
analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=True)
```

**When to use**:
- You have diverse control configurations
- Reducing total batch count is priority
- You want to minimize queue management overhead

## Performance Characteristics

### Expected Speedups

| Scenario | Strict Mode | Mixed Mode |
|----------|-------------|------------|
| Identical controls | 3-5x speedup | 2-4x speedup |
| Mixed controls | 2-3x speedup | 2-4x speedup |
| Single job types | Minimal gain | Minimal gain |

### Memory Considerations

Smart Batching uses conservative batch sizing to prevent GPU out-of-memory errors:

- **Automatic batch sizing**: Based on your configured batch size and control complexity
- **Memory safety**: Conservative approach prevents OOM crashes
- **User control**: You set the maximum batch size in queue service settings

## Best Practices

### 1. Optimal Queue Composition

For best results, queue jobs with:
- **Similar execution parameters**: Same num_steps, guidance, seed
- **Compatible control types**: Jobs that can benefit from grouping
- **Reasonable batch sizes**: 4-8 runs per batch typically optimal

### 2. Analysis Strategy

```python
# Always check analysis before executing
analysis = queue_service.analyze_queue_for_smart_batching()
if analysis and analysis["efficiency"]["speedup"] > 1.5:
    # Good speedup potential - execute
    queue_service.execute_smart_batches()
else:
    # Minimal benefit - continue with normal processing
    queue_service.set_queue_paused(False)
```

### 3. Mode Selection Guidelines

```python
# Choose mode based on queue composition
if queue_has_many_identical_jobs():
    # Use strict mode for maximum speed
    analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)
else:
    # Use mixed mode for better batch consolidation
    analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=True)
```

## Troubleshooting

### Common Issues

#### "No analysis available"
```
Error: No analysis available. Run analyze_queue_for_smart_batching first.
```
**Solution**: Always analyze before executing:
```python
analysis = queue_service.analyze_queue_for_smart_batching()
if analysis:
    queue_service.execute_smart_batches()
```

#### "Analysis is stale"
```
Error: Analysis is stale - queue has changed. Please re-analyze.
```
**Solution**: Queue was modified after analysis. Re-run analysis:
```python
# Queue changed - analyze again
analysis = queue_service.analyze_queue_for_smart_batching()
queue_service.execute_smart_batches()
```

#### "No batchable jobs found"
**Causes**:
- Queue contains only enhancement/upscale jobs (not batchable)
- All jobs have incompatible execution parameters
- Queue is empty

**Solution**: Add compatible inference jobs to the queue

### Debug Information

Enable detailed logging to understand batching decisions:

```python
import logging
logging.getLogger('cosmos_workflow.utils.smart_batching').setLevel(logging.DEBUG)
```

## API Reference

### SimplifiedQueueService Methods

#### `analyze_queue_for_smart_batching(mix_controls: bool = False) -> dict | None`

Analyzes queued jobs for batching opportunities.

**Parameters:**
- `mix_controls`: Use mixed mode if True, strict mode if False

**Returns:**
- Analysis dictionary with batches, efficiency metrics, and preview
- `None` if no batchable jobs found

#### `execute_smart_batches() -> dict`

Reorganizes queue based on stored analysis.

**Returns:**
```python
{
    "jobs_deleted": 5,           # Original jobs removed
    "batches_created": 3,        # New optimized batches created
    "mode": "strict",            # Batching mode used
    "message": "Queue reorganized successfully. 5 jobs → 3 batches"
}
```

#### `get_smart_batch_preview() -> str`

Returns human-readable preview of stored analysis.

**Returns:**
- Formatted preview string
- Empty string if no analysis available

### Core Smart Batching Functions

Located in `cosmos_workflow.utils.smart_batching`:

#### `group_runs_strict(jobs, max_batch_size) -> list`
Groups runs with identical control signatures for maximum efficiency.

#### `group_runs_mixed(jobs, max_batch_size) -> list`
Groups runs by execution parameters only, allowing mixed controls.

#### `calculate_batch_efficiency(batches, original_jobs, mode) -> dict`
Calculates efficiency metrics including estimated speedup.

#### `filter_batchable_jobs(jobs) -> list`
Filters jobs to include only inference and batch_inference types.

## Example Workflows

### Complete Batching Workflow

```python
# 1. Setup
from cosmos_workflow.services import SimplifiedQueueService
queue_service = SimplifiedQueueService()

# 2. Add jobs to queue (via UI or API)
# ... add multiple inference jobs ...

# 3. Pause and analyze
queue_service.set_queue_paused(True)
analysis = queue_service.analyze_queue_for_smart_batching(mix_controls=False)

if analysis:
    # 4. Review analysis
    print("Batching Analysis:")
    print(analysis["preview"])

    # 5. Execute if beneficial
    if analysis["efficiency"]["speedup"] > 2.0:
        results = queue_service.execute_smart_batches()
        print(f"Success: {results['message']}")
    else:
        print("Minimal speedup - skipping batching")

# 6. Resume processing
queue_service.set_queue_paused(False)
```

### Gradio UI Integration

The Gradio interface provides smart batching controls:

1. **Queue Management Panel**: Pause/resume queue
2. **Smart Batching Analysis Button**: Trigger analysis with mode selection
3. **Preview Display**: Shows batching preview and efficiency metrics
4. **Execute Batching Button**: Reorganize queue based on analysis
5. **Status Indicators**: Real-time feedback on batching operations

## Advanced Topics

### Custom Batch Sizing

Configure optimal batch sizes based on your GPU capacity:

```python
# Conservative: Suitable for most GPUs
queue_service.set_batch_size(4)

# Aggressive: For high-memory GPUs (H100, A100)
queue_service.set_batch_size(8)

# Memory-constrained: For smaller GPUs
queue_service.set_batch_size(2)
```

### Efficiency Monitoring

Track batching performance over time:

```python
def monitor_batching_efficiency():
    analysis = queue_service.analyze_queue_for_smart_batching()
    if analysis:
        metrics = analysis["efficiency"]
        print(f"Runs: {metrics['total_runs']}")
        print(f"Original jobs: {metrics['original_jobs']}")
        print(f"Optimized batches: {metrics['total_batches']}")
        print(f"Expected speedup: {metrics['speedup']:.1f}x")
```

### Integration with External Systems

Smart Batching can be integrated with external job scheduling systems:

```python
# Example: External job submission
def submit_batch_job(job_spec):
    # Add to queue
    queue_service.add_job(**job_spec)

    # Trigger automatic batching if queue reaches threshold
    queue_size = len(queue_service.get_queue_status()["queued_jobs"])
    if queue_size >= 10:  # Threshold for auto-batching
        queue_service.set_queue_paused(True)
        analysis = queue_service.analyze_queue_for_smart_batching()
        if analysis and analysis["efficiency"]["speedup"] > 1.5:
            queue_service.execute_smart_batches()
        queue_service.set_queue_paused(False)
```

## Conclusion

Smart Batching transforms your GPU utilization by intelligently grouping compatible inference jobs. With support for individual control weights per prompt and two optimization modes, you can achieve significant performance improvements while maintaining full control over your workflow.

Key takeaways:
- **Always analyze before executing** to understand potential benefits
- **Choose the right mode** based on your queue composition
- **Monitor efficiency metrics** to optimize your batching strategy
- **Use conservative batch sizes** to prevent memory issues

For questions or advanced configuration needs, refer to the API documentation or contact the development team.