# Batch Generation for Cosmos Transfer

## Overview

This document details the batch generation capabilities of NVIDIA Cosmos Transfer and provides implementation guidance for smart batching in our workflow system.

## Key Findings from NVIDIA Cosmos Transfer Analysis

### How Batch Generation Works

NVIDIA's batch generation system requires two files working together:
1. **Base controlnet spec** (`controlnet_specs.json`) - Defines default configuration for all videos
2. **Batch input file** (`batch_input.jsonl`) - Per-video overrides and customizations

The batch system processes multiple videos through the inference pipeline, but with important constraints based on GPU architecture.

### GPU Batching Fundamentals

#### Why Batching Improves Performance
- **Single model load**: Load model weights once, use for multiple inputs
- **Parallel compute**: Process N videos through identical operations simultaneously
- **Better GPU utilization**: Increases from ~20% (single) to 80%+ (batch)
- **Amortized overhead**: Setup/teardown costs spread across multiple videos

#### Critical Constraint: Architectural Uniformity
GPU batch inference requires all inputs in a batch to go through the **exact same computational graph**:
- Same model architecture
- Same active control branches
- Same tensor operations

### What Can and Cannot Be Batched

#### CAN change per video in a batch:
- ✅ Control weights (scalar multipliers)
- ✅ Input control paths (different data, same ops)
- ✅ Text prompts (different embeddings, same architecture)
- ✅ Setting `input_control: null` for auto-generation

#### CANNOT change per video in a batch:
- ❌ Which controls are enabled/disabled
- ❌ Different combinations of control types
- ❌ Model architecture or branches

Example: Cannot batch together:
- Video 1: edge control only
- Video 2: edge + depth controls
(These require different computational paths)

### Performance Implications

Multi-controlnet inference is significantly slower than single control:
- Single control (e.g., edge): ~X seconds
- Four controls (vis+edge+depth+seg): ~3-4X seconds
- Memory usage scales with number of controls

This means forcing all videos through all control branches (even unused ones) causes massive performance penalties.

## Smart Batching Implementation

### Design Principles

1. **Group by control configuration**: Only batch videos with identical control types
2. **Minimize control overhead**: Never force unnecessary controls
3. **Dynamic batch sizing**: Adjust based on control complexity and memory
4. **Priority processing**: Handle simpler configs first for faster results

### Implementation Strategy

#### Step 1: Control Signature Generation

```python
def get_control_signature(run_dict):
    """Generate hashable signature of active controls"""
    weights = run_dict.get("execution_config", {}).get("weights", {})
    active_controls = tuple(sorted(k for k, v in weights.items() if v > 0))
    return active_controls  # e.g., ('depth', 'edge', 'seg')
```

#### Step 2: Group Compatible Runs

```python
def group_runs_for_batching(runs):
    """Group runs by identical control configurations"""
    groups = {}
    for run in runs:
        signature = get_control_signature(run)
        if signature not in groups:
            groups[signature] = []
        groups[signature].append(run)
    return groups
```

#### Step 3: Create Minimal Base Specs

```python
def create_minimal_base_spec(runs_group):
    """Create base spec with ONLY controls this group uses"""
    # Find controls used by ANY run in group
    all_used_controls = set()
    for run in runs_group:
        weights = run.get("execution_config", {}).get("weights", {})
        all_used_controls.update(k for k, v in weights.items() if v > 0)

    base_spec = {
        "negative_prompt": "low quality, blurry",
        "num_steps": 35,
        "guidance": 7.0,
        "sigma_max": 70.0,
        "seed": 42,
        "fps": 8
    }

    # Only include actually used controls
    for control in all_used_controls:
        base_spec[control] = {"control_weight": 0}  # Overridden per video

    return base_spec
```

#### Step 4: Dynamic Batch Sizing

```python
def determine_batch_size(num_controls):
    """Adjust batch size based on control complexity"""
    if num_controls == 1:
        return 8  # Can handle more with single control
    elif num_controls == 2:
        return 4
    elif num_controls <= 4:
        return 2  # Memory limited with many controls
    else:
        return 1  # Upscaling or very complex configs
```

### Complete Smart Batching Algorithm

```python
def smart_batch_generation(all_runs):
    """
    Intelligently batch runs for optimal performance.

    Returns list of batch configurations, each containing:
    - runs: List of compatible runs
    - base_spec: Minimal controlnet spec for this batch
    - batch_jsonl: Per-video overrides
    """
    # Step 1: Group by control signature
    control_groups = group_runs_for_batching(all_runs)

    batches = []
    for signature, compatible_runs in control_groups.items():
        # Step 2: Determine optimal batch size
        num_controls = len(signature)
        max_batch_size = determine_batch_size(num_controls)

        # Step 3: Create batches respecting size limits
        for i in range(0, len(compatible_runs), max_batch_size):
            batch_runs = compatible_runs[i:i + max_batch_size]

            # Step 4: Generate minimal base spec
            base_spec = create_minimal_base_spec(batch_runs)

            # Step 5: Generate batch JSONL with overrides
            batch_jsonl = to_cosmos_batch_inference_jsonl(
                [(run, prompt) for run, prompt in batch_runs]
            )

            batches.append({
                'runs': batch_runs,
                'base_spec': base_spec,
                'batch_jsonl': batch_jsonl,
                'batch_size': len(batch_runs),
                'control_count': num_controls,
                'signature': signature
            })

    # Sort by control complexity (process simpler configs first)
    batches.sort(key=lambda x: x['control_count'])

    return batches
```

### File Generation

For each batch, generate two files:

1. **Base controlnet spec** (`batch_XXXX_spec.json`):
```json
{
  "negative_prompt": "low quality, blurry",
  "num_steps": 35,
  "guidance": 7.0,
  "edge": {"control_weight": 0},
  "depth": {"control_weight": 0}
}
```

2. **Batch input JSONL** (`batch_XXXX.jsonl`):
```jsonl
{"visual_input": "runs/rs_xxx/inputs/videos/color.mp4", "prompt": "...", "control_overrides": {"edge": {"control_weight": 0.5}}}
{"visual_input": "runs/rs_yyy/inputs/videos/color.mp4", "prompt": "...", "control_overrides": {"edge": {"control_weight": 0.7}, "depth": {"control_weight": 0.3}}}
```

## Performance Analysis

### Example Scenario
10 runs with varying control configurations:
- 6 runs: edge only
- 3 runs: edge + depth
- 1 run: all 4 controls

#### Without Smart Batching (force all controls):
- All 10 runs process through 4 controls
- Time: 10 × 4X = 40X time units
- Memory: Limited to batch_size=2

#### With Smart Batching:
- Batch 1: 6 edge-only runs (batch_size=6) = 1X time
- Batch 2: 3 edge+depth runs (batch_size=3) = 2X time
- Batch 3: 1 four-control run = 4X time
- Total: 7X time units (5.7x faster!)

## Integration with Queue System

### Hybrid Approach

Combine queue management with smart batching:

1. **Queue accumulation**: Collect jobs in queue
2. **Periodic batching**: Every N seconds or M jobs
3. **Smart grouping**: Group by control configuration
4. **Batch execution**: Process compatible groups
5. **Fallback**: Process incompatible jobs individually

### Special Cases

#### Upscaling
- Always process with `batch_size=1`
- Cannot be batched due to different model architecture

#### Priority Jobs
- Process immediately without waiting for batch
- User-marked urgent tasks skip batching

## Implementation Checklist

- [ ] Add `get_control_signature()` utility function
- [ ] Implement `group_runs_for_batching()`
- [ ] Create `create_minimal_base_spec()` generator
- [ ] Add dynamic batch sizing logic
- [ ] Update `to_cosmos_batch_inference_jsonl()` for control overrides
- [ ] Implement batch file generation
- [ ] Add batch validation before execution
- [ ] Create batch status tracking
- [ ] Add performance metrics/logging
- [ ] Handle batch failure recovery

## Future Optimizations

1. **Predictive batching**: Analyze historical patterns to predict compatible future jobs
2. **Adaptive sizing**: Adjust batch sizes based on current GPU memory usage
3. **Multi-GPU distribution**: Split large batches across available GPUs
4. **Control caching**: Cache preprocessed control inputs for reuse

## Conclusion

Smart batching can provide 2-8x performance improvements for compatible workloads. The key is grouping by exact control configuration and never forcing unnecessary control processing. This approach maintains flexibility while maximizing GPU utilization.