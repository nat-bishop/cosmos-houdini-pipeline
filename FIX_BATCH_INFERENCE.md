# Batch Inference Fix Implementation Checklist

## Overview
Fix batch inference to properly handle multiple prompts efficiently while maintaining individual run tracking in the database and UI.

## Key Requirements
- Use JSONL format with `control_overrides` structure per NVIDIA spec
- Execute as single batch on GPU for efficiency
- Create individual database runs for each prompt
- Download outputs to individual run directories
- Maintain compatibility with Gradio UI (no UI changes needed)

## Implementation Steps

### ✅ Step 0: Initial Setup
- [x] Commit all current changes
- [x] Create this implementation checklist

### ✅ Step 1: Fix Batch File Format
**File:** `cosmos_workflow/execution/gpu_executor.py` (lines 572-583)
- [x] Replace `to_cosmos_inference_json()` with `to_cosmos_batch_inference_jsonl()`
- [x] Change file extension from `.json` to `.jsonl`
- [x] Use `write_batch_jsonl()` instead of `json_handler.write_json()`
- [x] Test JSONL format matches NVIDIA spec
- [x] Create unit tests in `tests/unit/execution/test_batch_format.py`
- [x] Commit changes

### ✅ Step 2: Fix Upload Path
**File:** `cosmos_workflow/execution/gpu_executor.py` (lines 587-597)
- [x] Changed batch upload path to `{remote_config.remote_dir}/inputs/batches`
- [x] Fixed video upload to `{remote_config.remote_dir}/runs/{run_id}/inputs/videos`
- [x] Both paths now match what batch_inference.sh and JSONL format expect
- [ ] Test file paths in JSONL match upload locations (integration test)
- [ ] Commit changes

### ✅ Step 3: Fix Batch Output Handling
**File:** `cosmos_workflow/execution/gpu_executor.py` (`_split_batch_outputs` method, lines 658-717)
- [x] Updated to handle NVIDIA naming: `video_000.mp4`, `video_001.mp4`, etc.
- [x] Map sequential output files to run IDs with proper index matching
- [x] Keep fallback for unexpected naming patterns (sequential and run_id based)
- [x] Added comprehensive logging for debugging
- [x] Created unit tests in `tests/unit/execution/test_batch_output_mapping.py`
- [x] All 5 test scenarios pass (sequential, fallback, missing, run_id, mixed)
- [ ] Commit changes

### ✅ Step 4: Download to Individual Run Directories
**File:** `cosmos_workflow/execution/gpu_executor.py` (lines 610-621, 723-780)
- [x] Created `_download_batch_output_for_run()` method to handle downloads
- [x] Download from batch output directory to individual `outputs/run_{run_id}/`
- [x] Rename batch outputs (`video_XXX.mp4`) to standard name (`output.mp4`)
- [x] Ensure proper directory structure for each run (outputs/, logs/)
- [x] Also copy shared batch log to each run's logs directory
- [x] Handle errors gracefully with error marker files
- [x] Created comprehensive unit tests in `tests/unit/execution/test_batch_download.py`
- [x] All 3 test scenarios pass (normal, missing log, download failure)
- [ ] Test Gradio can find outputs in expected locations (integration test)
- [ ] Commit changes

### ✅ Step 5: Handle Shared Batch Log
**File:** `cosmos_workflow/execution/gpu_executor.py` (lines 761-779)
- [x] Copy batch log (`batch_run.log`) to each individual run directory
- [x] Name as `logs/batch.log` in each run directory
- [x] Create `logs/run.log` file that references the batch for UI compatibility
- [x] Handle missing batch log gracefully (doesn't fail the download)
- [x] Updated tests to verify both batch.log and run.log creation
- [x] All tests pass
- [ ] Test log availability in UI (integration test)
- [ ] Commit changes

### ✅ Step 6: Add Minimal Batch Tracking (Optional)
**File:** `cosmos_workflow/api/cosmos_api.py` (lines 503-511, 684-687)
- [x] Add `batch_id` to execution_config for batch runs only
- [x] Use UUID4-based unique ID generation (same pattern as prompts/runs)
- [x] Single runs don't get batch_id (remains null/absent)
- [x] JSON column handles optional field automatically (no migration needed)
- [x] Created unit tests to verify batch_id format and uniqueness
- [x] All tests pass
- [ ] Commit changes

## Testing Checklist

### ⬜ Unit Tests
- [ ] Test JSONL format generation
- [ ] Test output file mapping logic
- [ ] Test batch tracking metadata

### ⬜ Integration Tests
- [ ] Test single prompt (ensure no regression)
- [ ] Test 2-prompt batch
- [ ] Test 5-prompt batch
- [ ] Test batch with mixed control inputs (depth, seg)

### ⬜ End-to-End Tests
- [ ] Run `cosmos inference ps_xxx ps_yyy` from CLI
- [ ] Verify both runs complete and have outputs
- [ ] Check Gradio UI displays runs correctly
- [ ] Verify individual run logs are accessible
- [ ] Confirm output videos play in UI

## Risk Mitigation

### Before Each Step
- [ ] Create git commit
- [ ] Test with single inference first
- [ ] Back up working code

### If Issues Occur
- [ ] Check batch_inference.sh expectations
- [ ] Verify NVIDIA format requirements
- [ ] Review container logs for errors
- [ ] Revert to last working commit if needed

## Success Criteria
- ✅ Batch inference executes on GPU without errors
- ✅ Individual runs created in database
- ✅ Outputs downloadable for each run
- ✅ Gradio UI shows runs as normal (no special batch handling)
- ✅ Performance improvement over sequential execution
- ✅ No regression in single prompt inference

## Notes
- Batch is an execution optimization, not a data model change
- Runs remain independent in database/UI
- JSONL format allows streaming/parallel processing
- Output naming pattern: `video_000.mp4`, `video_001.mp4`, etc.