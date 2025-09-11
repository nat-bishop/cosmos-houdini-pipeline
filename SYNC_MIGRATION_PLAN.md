# Migration to Synchronous Execution - Implementation Plan

## Overview
Remove lazy loading and StatusChecker, making all GPU operations synchronous (blocking). This simplifies the codebase while maintaining CLI streaming and enabling proper Gradio queue management.

## Key Insight
Docker `run` without `-d` (detach) flag naturally blocks until container completes. No polling needed!

---

## Implementation Steps

### ✅ Prerequisites
- [x] Backup current working state: `git add . && git commit -m "backup: before sync migration"`
- [x] Stop any running containers: `cosmos kill`
- [x] Close Gradio UI if running

---

### Phase 1: Update Docker Execution Layer ✅ COMPLETE

#### Step 1.1: Modify docker_executor.py - Remove Background Execution
**File:** `cosmos_workflow/execution/docker_executor.py`

- [x] Find `_run_inference_script()` method - Now returns exit code
- [x] Remove `nohup {command} > /dev/null 2>&1 &` wrapping - All removed
- [x] Change to return exit code instead of None - Returns int exit code
- [x] Update to return exit code - All methods updated
- [x] Apply same pattern to `run_prompt_enhancement()` - Now synchronous
- [x] Apply same pattern to `_run_upscaling_script()` - Now synchronous
- [x] Verify no `-d` flags in DockerCommandBuilder calls - Verified

**Test:**
- [x] Run `ruff check cosmos_workflow/execution/docker_executor.py` - Passed

**Changes Made:**
- `_run_inference_script()`: Now blocks and returns exit code
- `_run_upscaling_script()`: Now blocks and returns exit code
- `run_prompt_enhancement()`: Now blocks and returns status with exit_code
- All use `stream_output` parameter for CLI visibility
- Timeouts set to 3600s (1 hour) for inference/upscaling, 1800s (30 min) for enhancement

---

### Phase 2: Update GPU Executor 🚧 IN PROGRESS

#### Step 2.1: Modify execute_run() for Synchronous Execution
**File:** `cosmos_workflow/execution/gpu_executor.py`

**Current Status:** Ready to modify - found at line 350
- [ ] Find `execute_run()` method - Located, needs modification
- [ ] Remove the section that returns `{"status": "started"}` - At line 428
- [ ] Add completion handling after container execution
- [ ] Add `stream_output` parameter to method signature if missing

**Key Changes Needed:**
- After `docker_executor.run_inference()` call (line 418), handle the exit code
- Download outputs using existing `_download_outputs()` method
- Update database with completion status
- Return completed status instead of started

**Test:**
- [ ] Create a test prompt: `cosmos create prompt "Test sync" inputs/videos/urban_scene`
- [ ] Run inference: `cosmos inference ps_xxxxx`
- [ ] Verify it blocks until complete
- [ ] Check database: `cosmos list runs --limit 1`
- [ ] Verify status is "completed" not "running"

---

#### Step 2.2: Update execute_enhancement_run()
**File:** `cosmos_workflow/execution/gpu_executor.py`

- [ ] Remove `{"status": "started"}` return
- [ ] After container execution, add prompt creation logic
- [ ] Use existing service methods for prompt operations

**Test:**
- [ ] Run enhancement: `cosmos prompt-enhance ps_xxxxx`
- [ ] Verify new prompt created: `cosmos list prompts --limit 2`
- [ ] Test update mode: `cosmos prompt-enhance ps_xxxxx --no-create-new`

---

#### Step 2.3: Update execute_upscaling_run()
**File:** `cosmos_workflow/execution/gpu_executor.py`

- [ ] Remove `{"status": "started"}` return
- [ ] Add completion handling after container execution
- [ ] Follow same pattern as execute_run()

---

#### Step 2.4: Update execute_batch_runs()
**File:** `cosmos_workflow/execution/gpu_executor.py`

- [ ] Remove any background execution logic
- [ ] Ensure batch runs sequentially (already does)
- [ ] Update status handling for synchronous execution

---

### Phase 3: Update CLI Commands ✅ COMPLETE

#### Step 3.1: Update inference CLI
**File:** `cosmos_workflow/cli/inference.py`

- [x] Find result display section (around line 190)
- [x] Change status message from "Started in background" to "Completed"
- [x] Remove "Monitor progress with cosmos status" message
- [x] Add completion message

**Test:**
- [ ] Run: `cosmos inference ps_xxxxx`
- [ ] Verify shows "Completed" not "Started in background"

---

#### Step 3.2: Update enhance CLI
**File:** `cosmos_workflow/cli/enhance.py`

- [x] Apply same changes as inference CLI (handled in upscale.py)
- [x] Show enhanced prompt ID in results (returns in execute_enhancement_run)

---

### Phase 4: Update Gradio UI

#### Step 4.1: Configure Queue
**File:** `cosmos_workflow/ui/app.py`

- [ ] Find where `demo` is created (near bottom)
- [ ] Add queue configuration
- [ ] Update `run_inference_on_selected()` to show completion

**Test:**
- [ ] Start UI: `cosmos ui`
- [ ] Queue multiple inference jobs
- [ ] Verify they run sequentially, not in parallel

---

### Phase 5: Remove StatusChecker ✅ COMPLETE

#### Step 5.1: Remove StatusChecker Class
- [x] Delete file: `cosmos_workflow/execution/status_checker.py`
- [x] Run: `git rm cosmos_workflow/execution/status_checker.py`

#### Step 5.2: Remove StatusChecker References
**File:** `cosmos_workflow/api/cosmos_api.py`

- [x] Remove import: `from cosmos_workflow.execution.status_checker import StatusChecker`
- [x] Remove line ~71: `self._initialize_status_checker()`
- [x] Remove method `_initialize_status_checker()` (lines ~75-86)

**File:** `cosmos_workflow/services/data_repository.py`

- [x] Remove any `status_checker` field
- [x] Remove `initialize_status_checker()` method if present
- [x] Remove StatusChecker import if present
- [x] Remove lazy sync logic from `get_run()` and `list_runs()`

---

### Phase 6: Testing & Validation

#### Step 6.1: Comprehensive Testing
- [ ] Run linting: `ruff check .`
- [ ] Run formatting: `ruff format .`

**Test inference:**
- [ ] Single: `cosmos inference ps_xxxxx`
- [ ] Batch: `cosmos inference ps_xxx ps_yyy ps_zzz`
- [ ] With streaming: `cosmos inference ps_xxxxx --stream`

**Test enhancement:**
- [ ] Create new: `cosmos prompt-enhance ps_xxxxx`
- [ ] Update existing: `cosmos prompt-enhance ps_xxxxx --no-create-new`

**Test upscaling:**
- [ ] From run: `cosmos upscale run_xxxxx`

**Test Gradio:**
- [ ] Start UI: `cosmos ui`
- [ ] Run multiple jobs
- [ ] Verify queue behavior

**Test error handling:**
- [ ] Invalid prompt ID
- [ ] Network interruption (kill SSH)
- [ ] Container failure (if possible)

---

### Phase 7: Cleanup & Documentation

- [ ] Update any documentation mentioning lazy loading
- [ ] Update ROADMAP.md if needed
- [ ] Commit changes: `git add . && git commit -m "refactor: migrate to synchronous execution"`

---

## Rollback Plan

If issues arise:
```bash
git reset --hard HEAD^  # Revert to backup commit
cosmos kill-all  # Clean up any stuck containers
```

---

## Success Criteria

✅ All operations block until complete
✅ CLI shows real-time progress with streaming
✅ Database always shows correct status
✅ Gradio queue prevents concurrent GPU jobs
✅ No StatusChecker references remain
✅ All tests pass

---

## Notes

- Keep `stream_output` parameter for CLI visibility
- Gradio should use `stream_output=False` for cleaner UI
- Default timeout of 3600s (1 hour) should be sufficient
- Exit codes: 0 = success, non-zero = failure