# Cosmos Workflow Refactoring Plan

## Overview
Refactoring the Cosmos Workflow CLI to simplify the user experience by hiding run management and providing a unified operations interface.

### Key Changes
1. **Hide run creation from users** - Runs are created automatically during inference
2. **Unify all operations through WorkflowOperations class** - Single interface for CLI and future Gradio
3. **Simplify from 3-step to 2-step workflow** - Remove the need to manually create runs

### Before vs After

**Before (3 steps):**
```bash
cosmos create prompt "A sunset" videos/scene1  # Returns ps_abc123
cosmos create run ps_abc123 --weights 0.3 0.3 0.2 0.2  # Returns rs_xyz789
cosmos inference rs_xyz789
```

**After (2 steps):**
```bash
cosmos create prompt "A sunset" videos/scene1  # Returns ps_abc123
cosmos inference ps_abc123 --weights 0.3 0.3 0.2 0.2  # Creates run internally
```

---

## Current Status

**Last Updated:** 2025-09-06

### What We've Achieved So Far:
1. **Core API refactored** - `quick_inference()` and `batch_inference()` now accept prompt IDs directly
2. **Better internal design** - Created semantic helper methods instead of procedural ones
3. **Cleaner code** - Methods now directly use service/orchestrator instead of calling deprecated methods
4. **Backward compatibility maintained** - Old methods still work but show deprecation warnings
5. **All tests passing** - Functionality preserved while improving design

### What's Different From Original Plan:
- **No private methods yet** - Keeping `create_run`/`execute_run` public with deprecation warnings
- **Direct service calls** - `quick_inference` now calls service/orchestrator directly instead of using create_run/execute_run
- **Simpler documentation** - Removed "primary" vs "low-level" language, just say "use quick_inference"

### Next Steps:
When we update the CLI commands (Step 2), we'll remove the deprecated methods entirely since:
- The CLI is the only user of these methods
- No external users to worry about
- Deprecation warnings are enough for the transition period

---

## Implementation Steps

### Step 1: Update WorkflowOperations Core Methods
**Status:** ✅ COMPLETED
**Files modified:** `cosmos_workflow/api/workflow_operations.py`, `tests/unit/api/test_workflow_operations_refactor.py`

**All changes completed:**
1. ✅ `quick_inference()` accepts prompt_id directly and creates run internally
2. ✅ `batch_inference()` accepts list of prompt_ids and creates runs internally
3. ✅ Full TDD workflow completed (Gates 1-6)
4. ✅ Documentation updated (README, CHANGELOG, API docs)
5. ✅ Phase 1A refinements completed:
   - Added deprecation warnings to `create_run()` and `execute_run()`
   - Created semantic helper methods (`_validate_prompt()`, `_build_execution_config()`)
   - Refactored methods to use service/orchestrator directly
   - Simplified docstring language
6. ✅ All 13 tests passing

**Success criteria achieved:**
- ✅ Can run inference without manually creating runs
- ✅ Batch inference works with multiple prompt IDs
- ✅ Returns run_id in results for tracking
- ✅ Maintains backward compatibility for CLI
- ✅ Clean internal architecture with semantic helpers

---

### Step 2: Remove Create Run Command
**Status:** ✅ COMPLETED
**Files to modify:** `cosmos_workflow/cli/create.py`

**Changes needed:**
1. Delete the entire `create_run` command function (lines 75-156 currently)
2. Remove related imports that are no longer needed
3. Update module docstring to remove mention of run creation
4. Keep only `create_prompt` command

**Testing:**
```bash
cosmos create run ps_abc123  # Should show "no such command"
cosmos create prompt "test" videos/test  # Should still work
```

**Success criteria:**
- `cosmos create --help` only shows `prompt` subcommand
- No references to run creation in help text

---

### Step 3: Update Inference Command for Single/Multiple Prompts
**Status:** ✅ COMPLETED
**Files to modify:** `cosmos_workflow/cli/inference.py`

**Changes needed:**
1. Change command signature:
   ```python
   @click.command()
   @click.argument("prompt_ids", nargs=-1, required=True)  # Accept multiple
   @click.option("--prompts-file", type=click.File('r'),
                 help="File containing prompt IDs, one per line")
   ```

2. Update function logic:
   ```python
   def inference(ctx, prompt_ids, prompts_file, weights, ...):
       ops = ctx.obj.get_operations()

       # Gather all prompt IDs
       all_prompts = list(prompt_ids)
       if prompts_file:
           all_prompts.extend([line.strip() for line in prompts_file
                              if line.strip()])

       if len(all_prompts) == 1:
           # Single inference
           result = ops.quick_inference(all_prompts[0], weights=weights, ...)
           display_success(...)
       else:
           # Batch inference
           results = ops.batch_inference(all_prompts, weights=weights, ...)
           display_batch_success(...)
   ```

3. Update help text and examples to show both single and multiple usage
4. Remove all references to run_id as input

**Testing:**
```bash
cosmos inference ps_abc123  # Single prompt
cosmos inference ps_abc123 ps_def456  # Multiple prompts
echo -e "ps_abc123\nps_def456" > prompts.txt
cosmos inference --prompts-file prompts.txt  # From file
```

**Success criteria:**
- Single prompt inference works
- Multiple prompt inference works
- File-based prompt list works
- Clear output showing which prompts were processed

---

### Step 4: Simplify Enhance Command
**Status:** ✅ COMPLETED
**Files to modify:** `cosmos_workflow/cli/enhance.py`

**Changes needed:**
1. Remove all run creation/management code (lines 93-108, 141-167)
2. Simplify to just call `ops.enhance_prompt()`:
   ```python
   def prompt_enhance(ctx, prompt_id, model, create_new, dry_run):
       ops = ctx.obj.get_operations()

       if dry_run:
           # Show what would happen
           ...
           return

       # Simple enhancement
       enhanced = ops.enhance_prompt(
           prompt_id=prompt_id,
           create_new=not overwrite,  # Add --overwrite flag
           enhancement_model=model
       )

       display_success(...)
   ```

3. Add `--overwrite` flag to control whether to create new or update existing
4. Remove complex run tracking logic

**Testing:**
```bash
cosmos enhance ps_abc123  # Creates new enhanced prompt
cosmos enhance ps_abc123 --overwrite  # Updates existing (if no runs)
cosmos enhance ps_abc123 --dry-run  # Preview only
```

**Success criteria:**
- Enhancement creates new prompt by default
- Can optionally overwrite if prompt has no runs
- Much simpler code (under 100 lines vs current 187)

---

### Step 5: Update Main CLI Registration
**Status:** ✅ COMPLETED
**Files to modify:** `cosmos_workflow/cli/__init__.py` or `cosmos_workflow/__main__.py`

**Changes needed:**
1. Remove registration of `generate` command (if it was added)
2. Ensure inference command is properly registered
3. Update main help text if needed
4. Remove any batch command registration (merged into inference)

**Testing:**
```bash
cosmos --help  # Should show: create, inference, enhance, list, status, etc.
cosmos generate  # Should show "no such command"
```

**Success criteria:**
- Only intended commands are available
- Help text is accurate and helpful

---

### Step 6: Update Create Prompt Next Step Hint
**Status:** ✅ COMPLETED (Done in Step 2)
**Files to modify:** `cosmos_workflow/cli/create.py`

**Changes needed:**
1. Change line that shows next step (currently line 72):
   ```python
   # Before:
   display_next_step(f"cosmos create run {prompt['id']}")

   # After:
   display_next_step(f"cosmos inference {prompt['id']}")
   ```

2. Update any other references to the old workflow

**Testing:**
```bash
cosmos create prompt "test" videos/test
# Should show: "Next step: cosmos inference ps_xxxxx"
```

**Success criteria:**
- Correct next step is displayed
- No references to "create run" anywhere

---

### Step 7: Clean Up Imports and Dependencies
**Status:** Pending
**Files to modify:** Multiple CLI files

**Changes needed:**
1. Remove unused imports from all CLI files:
   - `from cosmos_workflow.services.workflow_service import PromptNotFoundError`
   - Direct service/orchestrator imports
2. Remove any helper functions that are no longer needed
3. Check for and remove dead code

**Testing:**
```bash
python -m cosmos_workflow --help  # No import errors
ruff check cosmos_workflow/cli/  # No unused imports
```

**Success criteria:**
- No import errors
- No unused imports flagged by linter
- Code is cleaner and simpler

---

### Step 8: Integration Testing
**Status:** Pending

**Test scenarios:**

1. **Full single workflow:**
   ```bash
   cosmos create prompt "A beautiful sunset" inputs/videos/test1
   # Note prompt ID: ps_xxx
   cosmos inference ps_xxx --weights 0.3 0.3 0.2 0.2
   # Verify video generated
   ```

2. **Multiple runs on same prompt:**
   ```bash
   cosmos inference ps_xxx --weights 0.5 0.2 0.2 0.1
   cosmos inference ps_xxx --weights 0.1 0.6 0.2 0.1 --steps 50
   # Verify both runs completed
   ```

3. **Batch inference:**
   ```bash
   cosmos create prompt "Sunset" inputs/videos/test1  # ps_aaa
   cosmos create prompt "Sunrise" inputs/videos/test2  # ps_bbb
   cosmos create prompt "Night" inputs/videos/test3    # ps_ccc
   cosmos inference ps_aaa ps_bbb ps_ccc --weights 0.25 0.25 0.25 0.25
   # Verify all three generated
   ```

4. **Enhancement workflow:**
   ```bash
   cosmos enhance ps_xxx
   # Note new prompt ID: ps_yyy
   cosmos inference ps_yyy
   # Verify enhanced prompt works
   ```

5. **Error handling:**
   ```bash
   cosmos inference ps_nonexistent  # Should show clear error
   cosmos inference  # Should show help
   ```

**Success criteria:**
- All workflows complete successfully
- Error messages are clear and helpful
- Performance is acceptable for batch operations

---

## Migration Guide for Users

### What Changed
- **No more `create run` command** - Runs are created automatically when you run inference
- **`inference` now accepts prompt IDs** - Not run IDs
- **`inference` can handle multiple prompts** - Just list them all
- **Simpler workflow** - 2 steps instead of 3

### How to Update Your Scripts

**Old way:**
```bash
PROMPT_ID=$(cosmos create prompt "My prompt" videos/dir | grep "ID:" | cut -d' ' -f2)
RUN_ID=$(cosmos create run $PROMPT_ID | grep "ID:" | cut -d' ' -f2)
cosmos inference $RUN_ID
```

**New way:**
```bash
PROMPT_ID=$(cosmos create prompt "My prompt" videos/dir | grep "ID:" | cut -d' ' -f2)
cosmos inference $PROMPT_ID
```

### Batch Processing

**Old way:** Required complex scripting to create multiple runs

**New way:**
```bash
# Process multiple prompts at once
cosmos inference ps_001 ps_002 ps_003 ps_004 ps_005

# Or from a file
cosmos inference --prompts-file my_prompts.txt
```

---

## Notes for Implementation

### Session 1: Core Operations (Steps 1-2)
- Focus on WorkflowOperations changes
- Remove create run command
- Test basic functionality

### Session 2: CLI Commands (Steps 3-4)
- Update inference command
- Simplify enhance command
- Test command behavior

### Session 3: Cleanup (Steps 5-7)
- Update registration and hints
- Clean up imports
- Polish the interface

### Session 4: Testing & Documentation (Step 8)
- Run full integration tests
- Update documentation
- Create migration guide

### Architecture Decisions Made

1. **Why hide runs?** - Users think in terms of "run inference on a prompt", not "create a run then execute it"
2. **Why keep runs in database?** - Still need them for tracking, history, and debugging
3. **Why merge batch into inference?** - Follows Unix philosophy (like `rm file1 file2 file3`)
4. **Why remove generate command?** - With simplified inference, it's not needed
5. **Why use WorkflowOperations?** - Single source of truth for business logic, used by both CLI and future Gradio

### Refinement Decisions (Post-Implementation)

1. **Deprecation over removal** - Keep `create_run`/`execute_run` public with deprecation warnings for smooth transition
2. **Better internal abstractions** - Helper methods should be semantic (`_validate_prompt`) not procedural (`_create_run`)
3. **Simplify documentation** - Remove "primary" vs "low-level" distinction, just say "use quick_inference"
4. **Phase approach** - Phase 1: Deprecate, Phase 2: Remove (when updating CLI)

### Potential Issues to Watch

1. **Backward compatibility** - Existing scripts will break (document well)
2. **Run ID visibility** - Users can't see run IDs easily (add to verbose output?)
3. **Batch size limits** - Need to handle very large batches gracefully
4. **Error handling** - Batch needs clear reporting of which prompts failed

---

## Completion Checklist

### Phase 1 (Step 1 - Core API) ✅ COMPLETED
- [x] WorkflowOperations updated for simplified flow
- [x] `quick_inference()` accepts prompt_id directly
- [x] `batch_inference()` accepts list of prompt_ids
- [x] Full TDD workflow (Gates 1-6)
- [x] Documentation updated (README, CHANGELOG, API docs)
- [x] All tests passing

### Phase 1A (Refinements) - ✅ COMPLETED
- [x] Add deprecation warnings to create_run/execute_run
- [x] Create semantic helper methods (_validate_prompt, _build_execution_config)
- [x] Refactored quick_inference and batch_inference to use helpers directly
- [x] Simplified docstring language (removed "primary method" terminology)
- [x] All existing tests still passing (except one docstring test - fixed)
- [ ] ~~Test deprecation warnings~~ (Skipped - removing methods in Step 2 anyway)

### Phase 2 (Steps 2-7 - CLI Updates) - ✅ COMPLETED
- [x] Create run command removed
- [x] Inference command handles single and multiple prompts
- [x] Batch inference merged into main inference command
- [x] Enhance command simplified (186 lines -> 127 lines)
- [x] CLI registration updated
- [x] Next step hints updated (all point to 'cosmos inference')
- [x] Imports cleaned up
- [x] CLI help text verified
- [x] All linting and formatting passes