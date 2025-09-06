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

## Implementation Steps

### Step 1: Update WorkflowOperations Core Methods
**Status:** Pending  
**Files to modify:** `cosmos_workflow/api/workflow_operations.py`

**Changes needed:**
1. Ensure `quick_inference()` is the primary method that accepts prompt_id directly
2. Update method signature to emphasize it's the main path:
   ```python
   def quick_inference(self, prompt_id: str, weights: dict = None, **kwargs) -> dict:
       """Primary inference method - creates run internally and executes."""
   ```
3. Ensure `batch_inference()` accepts list of prompt_ids and creates runs internally
4. Keep `create_run()` and `execute_run()` as low-level methods (for advanced use)

**Testing:**
- Create a test prompt manually in DB
- Call `ops.quick_inference("ps_test")` - should create run and execute
- Call `ops.batch_inference(["ps_test1", "ps_test2"])` - should handle multiple

**Success criteria:**
- Can run inference without manually creating runs
- Batch inference works with multiple prompt IDs
- Returns run_id in results for tracking

---

### Step 2: Remove Create Run Command
**Status:** Pending  
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
**Status:** Pending  
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
**Status:** Pending  
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
**Status:** Pending  
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
**Status:** Pending  
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

### Potential Issues to Watch

1. **Backward compatibility** - Existing scripts will break (document well)
2. **Run ID visibility** - Users can't see run IDs easily (add to verbose output?)
3. **Batch size limits** - Need to handle very large batches gracefully
4. **Error handling** - Batch needs clear reporting of which prompts failed

---

## Completion Checklist

- [ ] WorkflowOperations updated for simplified flow
- [ ] Create run command removed
- [ ] Inference command handles single and multiple prompts
- [ ] Enhance command simplified
- [ ] CLI registration updated
- [ ] Next step hints updated
- [ ] Imports cleaned up
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] Migration guide written
- [ ] CHANGELOG.md updated
- [ ] README.md examples updated