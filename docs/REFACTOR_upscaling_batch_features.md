# Upscaling and Batch Features Refactor Document

## Executive Summary
This document outlines three phases of refactoring for upscaling and batch features. Each phase is self-contained and can be implemented independently:

- **Phase 1**: Upscaling Fixes & Refactor - Make upscaling video-agnostic with optional prompt support
- **Phase 2**: Batch Inference Implementation - Add parent-child run relationships for batch operations
- **Phase 3**: Batch Prompt Enhancement Integration - Integrate the existing prompt_upsampler.py into CLI

---

# PHASE 1: UPSCALING FIXES & REFACTOR

## Overview
Make upscaling work with any video source, not just inference runs. Add optional prompt support and fix current implementation issues.

### Current Issues
- Upscaling is tightly coupled to "parent runs" assuming they're inference runs
- Cannot upscale arbitrary video files
- Cannot upscale enhance runs (they don't produce videos)
- Import error: `convert_video_path` not imported in DockerExecutor

### Proposed Design

#### CLI Interface
```bash
# Option 1: From existing run (validates video output exists)
cosmos upscale --from-run rs_12345 --weight 0.5 [--prompt "custom prompt"]

# Option 2: From video file
cosmos upscale --video path/to/video.mp4 --weight 0.5 [--prompt "custom prompt"]

# Default: no prompt in JSON unless specified
```

#### Database Structure
```python
# Upscale run execution_config
{
    "input_video_source": "path/to/video.mp4",  # Actual video path
    "source_run_id": "rs_12345",                 # Optional - only if from run
    "control_weight": 0.5,
    "prompt": "custom prompt"                    # Optional - only if provided
}
```

#### JSON Specification
```python
# Without prompt (default)
{
    "input_video_path": "outputs/run_rs_12345/output.mp4",
    "upscale": {
        "control_weight": 0.5
    }
}

# With prompt
{
    "input_video_path": "outputs/run_rs_12345/output.mp4",
    "prompt": "cinematic 8K quality scene",
    "upscale": {
        "control_weight": 0.5
    }
}
```

### Implementation Steps
1. Update `to_cosmos_upscale_json()` to accept optional prompt parameter
2. Modify CLI to support both `--from-run` and `--video` options
3. Update `execute_upscaling_run()` to handle arbitrary video sources
4. Fix import issues in DockerExecutor
5. Ensure video is uploaded to remote before upscaling

### GUI Integration
- Query upscale runs by `source_run_id` in execution_config
- Show toggle between "Original" and "4K Upscaled" versions
- Display quality badges on upscaled content

### Testing Strategy for Phase 1
1. Fix import errors and path issues
2. Test basic upscaling with existing runs
3. Test upscaling from arbitrary video files
4. Test optional prompt parameter
5. Verify StatusChecker handles upscale containers
6. Update upscaling tests for lazy sync

### Key Principles for Upscaling
- **Video-agnostic**: Works with any video source, not just runs
- **Optional relationships**: source_run_id only when from a run
- **Flexible prompts**: Only include prompt in JSON when specified
- **Container naming**: Always `cosmos_upscale_{run_id[:8]}`
- **Lazy sync**: StatusChecker handles monitoring

### Files to Modify
- `cosmos_workflow/execution/docker_executor.py` - Fix import error
- `cosmos_workflow/cli/upscale.py` - Add --from-run and --video options
- `cosmos_workflow/utils/nvidia_format.py` - Update to_cosmos_upscale_json()
- `cosmos_workflow/execution/gpu_executor.py` - Handle video sources
- `tests/unit/execution/test_gpu_executor_upscaling.py` - Update tests

---

# PHASE 2: BATCH INFERENCE IMPLEMENTATION

## Overview
Fix batch inference to properly track parent-child relationships and enable StatusChecker monitoring of batch containers.

### Current Issues
- Creates individual runs but no parent batch run
- No way to track which runs belong to which batch
- StatusChecker doesn't know how to monitor batch containers
- Output distribution is fragile

### Proposed Design

#### Parent-Child Run Pattern
```python
# Parent batch run
{
    "id": "rs_batch_12345",
    "model_type": "batch",
    "prompt_id": prompt_ids[0],  # Use first prompt
    "execution_config": {
        "batch_size": 3,
        "container_name": "cosmos_batch_abc123",
        "child_run_ids": ["rs_001", "rs_002", "rs_003"]
    }
}

# Child runs
{
    "id": "rs_001",
    "model_type": "transfer",
    "prompt_id": "ps_xyz",
    "execution_config": {
        "batch_run_id": "rs_batch_12345",
        "batch_container": "cosmos_batch_abc123",
        "batch_index": 0,
        ...weights and params...
    }
}
```

### Implementation Steps
1. Create parent run with `model_type="batch"`
2. Link children via `batch_run_id` in execution_config
3. Update StatusChecker to recognize `cosmos_batch_` containers
4. When batch completes, update all child runs
5. Parse batch output manifest to map outputs correctly

### Container Naming
- Batch: `cosmos_batch_{batch_id[:8]}`
- Transfer: `cosmos_transfer_{run_id[:8]}`
- Individual runs still use their own container names

### StatusChecker Updates for Batch
```python
# Add to StatusChecker.sync_run_status()
elif model_type == "batch":
    container_name = execution_config.get("container_name", f"cosmos_batch_{run_id[:8]}")
```

### Testing Strategy for Phase 2
1. Create parent batch run
2. Verify child runs link correctly
3. Test StatusChecker monitors batch containers
4. Verify output distribution to child runs
5. Test batch failure handling

### Key Principles for Batch Inference
- **Parent-child pattern**: Every batch has a parent run
- **Explicit relationships**: Use batch_run_id in child execution_config
- **Atomic updates**: Update all children when batch completes
- **Container tracking**: Parent tracks container name for all children

### Files to Modify
- `cosmos_workflow/api/cosmos_api.py` - Update batch_inference() method
- `cosmos_workflow/execution/status_checker.py` - Add batch container support
- `cosmos_workflow/services/data_repository.py` - Add "batch" to SUPPORTED_MODEL_TYPES
- `tests/unit/api/test_batch_inference.py` - Add parent run tests

---

# PHASE 3: BATCH PROMPT ENHANCEMENT INTEGRATION

## Overview
Integrate the existing prompt_upsampler.py script into the CLI with proper database tracking and monitoring.

### Current State
- `scripts/prompt_upsampler.py` works but not integrated
- Supports batch processing with model kept in memory
- No CLI command or database integration

### Proposed Design

#### CLI Command
```bash
cosmos enhance-batch ps_001 ps_002 ps_003 [--model pixtral] [--create-new]
```

#### Implementation
```python
# CosmosAPI.enhance_batch()
def enhance_batch(self, prompt_ids, model="pixtral", create_new=False):
    # Create parent batch run
    batch_run = service.create_run(
        prompt_id=prompt_ids[0],
        model_type="enhance_batch",
        execution_config={
            "model": model,
            "prompt_count": len(prompt_ids),
            "container_name": f"cosmos_enhance_batch_{uuid[:8]}"
        }
    )

    # Create child runs for tracking
    for prompt_id in prompt_ids:
        child_run = service.create_run(
            prompt_id=prompt_id,
            model_type="enhance",
            execution_config={
                "batch_run_id": batch_run.id,
                "model": model
            }
        )
```

### Benefits
- Keeps model loaded in memory for efficiency
- Tracks each enhancement as a run
- Can create new prompts if requested
- Follows same parent-child pattern as batch inference

### StatusChecker Updates for Batch Enhancement
```python
# Add to StatusChecker.sync_run_status()
elif model_type == "enhance_batch":
    container_name = execution_config.get("container_name", f"cosmos_enhance_batch_{run_id[:8]}")
```

### Testing Strategy for Phase 3
1. Test CLI command with multiple prompts
2. Verify model stays loaded between prompts
3. Test new prompt creation option
4. Verify StatusChecker monitors enhance_batch containers
5. Test batch results parsing

### Key Principles for Batch Enhancement
- **Memory efficiency**: Keep model loaded for batch
- **Flexibility**: Support both update and create-new modes
- **Tracking**: Each enhancement gets a run entry
- **Parent-child**: Same pattern as batch inference

### Files to Modify
- `cosmos_workflow/cli/enhance_batch.py` - New CLI command file
- `cosmos_workflow/api/cosmos_api.py` - Add enhance_batch() method
- `cosmos_workflow/execution/gpu_executor.py` - Add batch enhancement support
- `cosmos_workflow/execution/status_checker.py` - Add enhance_batch container support
- `cosmos_workflow/services/data_repository.py` - Add "enhance_batch" to SUPPORTED_MODEL_TYPES

---

## Quick Reference

### Model Types to Add
```python
SUPPORTED_MODEL_TYPES = {
    "transfer",      # Standard inference (existing)
    "enhance",       # Prompt enhancement (existing)
    "upscale",       # 4K upscaling (existing)
    "batch",         # Batch inference parent (new)
    "enhance_batch", # Batch enhancement parent (new)
}
```

### Container Naming Convention
- Always: `cosmos_{model_type}_{identifier[:8]}`
- Examples:
  - `cosmos_transfer_rs_12345`
  - `cosmos_upscale_rs_67890`
  - `cosmos_batch_batch_abc`
  - `cosmos_enhance_batch_eb_xyz`

### Core Design Principles (All Phases)
1. **One GPU Operation = One Database Run**
2. **Lazy Sync via StatusChecker** - No active monitoring
3. **CosmosAPI as Entry Point** - Never bypass to services
4. **Parent-Child Relationships** - Use execution_config
5. **Flexible JSON** - Only include optional fields when specified

---

## Migration Notes

### Database Compatibility
- All changes use existing columns (execution_config JSON)
- No schema changes required
- Backward compatible with existing runs

### Breaking Changes
- `DockerExecutor.run_upscaling()` signature changes
- Remove `prompt_file` parameter, add `parent_run_id` or `video_path`

### Non-Breaking Additions
- New CLI options for upscaling
- New `enhance-batch` command
- Parent batch runs for better tracking

---

## Session Context Summary

### What We Accomplished
- Identified upscaling limitations
- Designed flexible video-agnostic approach
- Fixed path issues in upscale.sh
- Created to_cosmos_upscale_json()
- Updated StatusChecker for upscale containers

### What Needs Doing
- Fix import error in DockerExecutor
- Implement flexible upscaling CLI
- Add batch parent runs
- Create enhance-batch command
- Update tests for lazy sync

### Current Blockers
- Import error prevents upscaling test
- Parent video needs upload before upscaling
- Batch inference lacks parent run tracking

### Design Decisions Made
- Upscaling should work with any video source
- Optional prompt parameter (not included if not specified)
- source_run_id for GUI relationship tracking
- Parent-child pattern for all batch operations
- Lazy sync via StatusChecker for all operations

### Implementation Priority
1. **Phase 1** - Most critical, fixes broken upscaling
2. **Phase 2** - Important for proper batch tracking
3. **Phase 3** - Nice to have, enhances productivity