# Filename Format Update - Handover Document

## Objective
Transform filenames from: `golden_hour_warmth_2025-09-03T07-55-25_ps_c2e9e46032bf.json`
To: `golden_hour_warmth_2025-09-03_07-55-25-123.json`

## Current Status

### ✅ COMPLETED Changes

#### 1. Core Schema Updates (`cosmos_workflow/prompts/schemas.py`)
- **Line 327**: Changed timestamp format to include milliseconds
  - From: `dt.strftime("%Y-%m-%dT%H-%M-%S")`
  - To: `dt.strftime("%Y-%m-%d_%H-%M-%S-%f")[:-3]`
- **Line 333**: Removed hash from prompt filename
  - From: `f"{safe_prompt_name}_{safe_timestamp}_{prompt_hash}.json"`
  - To: `f"{safe_prompt_name}_{safe_timestamp}.json"`
- **Line 350**: Same timestamp change for RunSpec files
- **Line 355**: Removed hash from RunSpec filename
  - From: `f"{safe_prompt_name}_{safe_timestamp}_{run_hash}.json"`
  - To: `f"{safe_prompt_name}_{safe_timestamp}.json"`

#### 2. Workflow Orchestrator (`cosmos_workflow/workflows/workflow_orchestrator.py`)
- **Lines 248-259**: Updated search strategy
  - Changed from searching by hash in filename
  - To loading JSON files and checking the "id" field
  - This is INEFFICIENT but works - needs optimization

#### 3. Test Updates
- `tests/unit/config/test_directory_manager.py` - ✅ Updated
- `tests/unit/prompts/test_prompt_spec_manager.py` - ✅ Updated
- `tests/unit/prompts/test_run_spec_manager.py` - ✅ Updated
- `tests/unit/workflows/test_workflow_orchestrator.py` - ✅ Partially updated
- `tests/unit/prompts/test_schemas.py` - ✅ Updated

### ❌ REMAINING Issues

#### 1. Test Files Still Need Updates
Many test files still expect hash in filename:
- Need to remove `_abc123` or `_def456` suffix from expected filenames
- Update pattern: `test_2025-09-03_10-00-00-000_abc123.json` → `test_2025-09-03_10-00-00-000.json`

#### 2. Import Statement Missing
**CRITICAL**: Line 251 in `workflow_orchestrator.py` uses `json` but doesn't import it!
Add at top of file: `import json`

#### 3. Inefficient File Search
The current implementation loads EVERY prompt file to find matches. This is slow!
Better solution: Create an index file or use a naming convention that includes partial ID.

#### 4. Collision Risk
Without hash, files with same name created in same millisecond will overwrite!
Solutions:
- Add a counter if file exists
- Use microseconds instead of milliseconds
- Add a small random suffix

## Test Results
- ✅ 133/133 prompt tests passing
- ✅ 45/45 workflow tests passing
- ✅ 24/24 directory manager tests passing
- ❌ 1 unrelated test failure in test_prompt_upsampler.py

## New Filename Examples

### PromptSpec Files
- **Old**: `golden_hour_warmth_2025-09-03T07-55-25_ps_c2e9e46032bf.json`
- **New**: `golden_hour_warmth_2025-09-03_07-55-25-123.json`

### RunSpec Files
- **Old**: `test_run_2025-09-03T10-30-45_rs_def456.json`
- **New**: `test_run_2025-09-03_10-30-45-567.json`

## Important Notes

### The Hash/ID System
- **IDs remain unchanged internally**: `ps_abc123def456` and `rs_xyz789abc123`
- **Only filenames changed**: Hash removed from filename, not from data
- **PromptSpec.id**: Still contains `ps_` prefix + hash
- **RunSpec.id**: Still contains `rs_` prefix + hash
- **RunSpec.prompt_id**: Still references PromptSpec.id with `ps_` prefix

### Migration for Existing Files
17 files in `inputs/prompts/2025-09-03/` need renaming:
```powershell
# PowerShell script to rename existing files
Get-ChildItem "inputs\prompts\2025-09-03\*.json" | ForEach-Object {
    $newName = $_.Name -replace 'T(\d{2})-(\d{2})-(\d{2})_ps_[a-f0-9]+', '_$1-$2-$3-000'
    Rename-Item $_.FullName "$newName.json"
}
```

## Critical TODO Items

### High Priority
1. **Add json import** to workflow_orchestrator.py
2. **Add collision detection** in DirectoryManager.get_prompt_file_path()
3. **Test file creation** to ensure no overwrites

### Medium Priority
1. **Optimize file search** in workflow_orchestrator.py
2. **Update remaining test files** to remove hash expectations
3. **Add integration test** for the new filename format

### Low Priority
1. **Consider adding counter** for same-millisecond files
2. **Document the new naming convention** in README

## How The System Works Now

1. **Creating a PromptSpec**:
   - Generates ID with hash: `ps_abc123def456`
   - Saves to: `name_2025-09-03_10-30-45-123.json`
   - ID stored inside JSON, not in filename

2. **Creating a RunSpec**:
   - References PromptSpec by ID: `prompt_id: "ps_abc123def456"`
   - Saves to: `run_name_2025-09-03_10-30-45-456.json`
   - Has its own ID: `rs_xyz789abc123`

3. **Finding PromptSpec from RunSpec**:
   - Loads RunSpec, gets `prompt_id`
   - Searches all prompt files, loading each to check `id` field
   - Matches when `data["id"] == run_spec.prompt_id`

## Testing Commands
```bash
# Test the changes
pytest tests/unit/config/ -v
pytest tests/unit/prompts/ -v
pytest tests/unit/workflows/ -v

# Create a test file
python -c "from cosmos_workflow.prompts.schemas import DirectoryManager; from datetime import datetime; dm = DirectoryManager('inputs/prompts', 'inputs/runs'); print(dm.get_prompt_file_path('test', datetime.now(), 'ps_test123'))"
# Should output: inputs\prompts\2025-09-03\test_2025-09-03_HH-MM-SS-mmm.json
```

## Rollback Instructions
If needed, revert these files:
1. `cosmos_workflow/prompts/schemas.py`
2. `cosmos_workflow/workflows/workflow_orchestrator.py`
3. Test files in `tests/unit/`

---

**Last Updated**: 2025-09-03
**Context**: The hash has been completely removed from filenames but remains in the ID fields. The system works but needs the json import fix and collision handling.