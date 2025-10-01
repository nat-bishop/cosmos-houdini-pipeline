# Architecture Refactoring Plan

## Executive Summary

This document outlines a refactoring plan to reduce coupling and minimize the number of files that need modification when making changes to the Cosmos workflow system.

## Current Problems

### Primary Issue: Excessive File Coupling
Adding a single database field currently requires changes across 5-8 files:
- `database/models.py` - Define the field
- `services/data_repository.py` - Add to CRUD methods
- `api/cosmos_api.py` - Thread parameter through
- `execution/gpu_executor.py` - Use the field
- `ui/app.py` - Display changes
- CLI files - Pass parameters
- Tests - Update tests

### Root Causes
1. **Scattered Business Logic**: Workflow logic spread across multiple abstraction layers
2. **Pass-Through Methods**: Many methods just forward calls without adding value
3. **Unclear Boundaries**: Files like `GPUExecutor` handle remote ops, database updates, and orchestration
4. **Over-Abstraction**: Too many wrapper classes that don't provide clear value

## Proposed Architecture

### Core Principle: Operation-Centric Design
Each operation (inference, enhance, upscale, batch) owns its complete workflow in a single file.

### New Structure
```
cosmos_workflow/
  # KEEP - Well-designed infrastructure services
  connection/
    ssh_manager.py     # Keep - SSH connection management
  execution/
    docker_executor.py # Keep - Docker command execution
  transfer/
    file_transfer.py   # Keep - File upload/download
  database/
    models.py          # Keep - Database schema (critical)
  services/
    queue_service.py   # Keep - UI queue management
  ui/                  # Keep - Gradio UI (unchanged)

  # NEW - Operations own workflows
  operations/
    base.py            # Base class enforcing consistency
    inference.py       # Complete inference workflow (400 lines)
    enhance.py         # Complete enhance workflow (300 lines)
    upscale.py         # Complete upscale workflow (300 lines)
    batch.py           # Complete batch workflow (400 lines)

  # SIMPLIFY - Remove pass-through
  api.py               # Thin routing layer (300 lines)
  cli.py               # All CLI commands (300 lines)
```

### Operation Base Class
```python
# operations/base.py
class BaseOperation:
    """Enforces consistency across all operations"""

    def __init__(self, db_session, ssh_manager, docker_executor, file_transfer):
        # Reuse existing infrastructure
        self.db = db_session
        self.ssh = ssh_manager
        self.docker = docker_executor
        self.files = file_transfer

    def create_run(self, prompt_id: str, model_type: str) -> Run:
        """Enforced method - ensures runs are created consistently"""
        run = Run(
            id=f"rs_{uuid.uuid4().hex[:8]}",
            prompt_id=prompt_id,
            model_type=model_type,
            status="pending",
            created_at=datetime.now(timezone.utc)
        )
        self.db.add(run)
        self.db.commit()
        return run

    def complete_run(self, run: Run, outputs: dict):
        """Enforced method - ensures completion is consistent"""
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.outputs = outputs
        self.db.commit()
```

### Operation Implementation Example
```python
# operations/inference.py
class InferenceOperation(BaseOperation):
    """Owns the complete inference workflow"""

    def execute(self, prompt_id: str, **params):
        # Uses base class for consistency
        prompt = self.db.query(Prompt).get(prompt_id)
        run = self.create_run(prompt_id, "transfer")

        try:
            # Uses existing infrastructure services
            with self.ssh:
                self.files.upload_file(video, remote_dir)
                result = self.docker.run_inference(run.id)
                output = self.files.download_file(remote_out, local_out)

            # Uses base class for consistency
            self.complete_run(run, {"output_path": output})
            return {"run_id": run.id, "output": output}

        except Exception as e:
            self.fail_run(run, e)
            raise
```

## Benefits

### Before vs After

| Change Type | Current Files | New Files |
|------------|---------------|-----------|
| Add database field | 5-8 files | 2 files (model + operation) |
| Add new AI model | 8+ files | 2 files (operation + api route) |
| Change execution flow | 4-6 files | 1 file (operation) |
| Add CLI parameter | 3-4 files | 2 files (cli + operation) |

### Concrete Example: Adding Priority Field

**Current Approach:**
1. models.py - Add field
2. data_repository.py - Update create_run()
3. cosmos_api.py - Pass priority through
4. gpu_executor.py - Handle priority
5. cli/inference.py - Add parameter

**New Approach:**
1. models.py - Add field
2. operations/inference.py - Use priority where needed

## Files to Modify/Delete

### Delete (logic moves to operations/)
- `services/data_repository.py` (1462 lines)
- `execution/gpu_executor.py` (1437 lines)
- `execution/gpu_orchestrator.py` (if exists)
- `cli/inference.py`, `cli/enhance.py`, etc. (7 files)
- `connection/` directory (merge into remote/)
- `transfer/` directory (merge into remote/)

### Modify
- `api/cosmos_api.py` - Reduce to thin routing (1179 → 300 lines)
- `execution/docker_executor.py` - Move to remote/docker.py

### Keep Unchanged
- `ui/app.py` - Gradio interface
- `services/queue_service.py` - UI queue management
- `database/models.py` - Database schema

## Migration Plan - Incremental Phases

Each phase is designed to be independently valuable and testable. You can stop after any phase and still have improvements.

### Phase 1: Inference Operation (2 days)
**Goal:** Prove the pattern with one complete workflow

**Changes:**
1. Create `operations/inference.py`
   - Extract inference logic from GPUExecutor.execute_run()
   - Include database operations from DataRepository
   - Own the complete inference workflow

2. Update `api/cosmos_api.py`
   ```python
   def quick_inference(self, prompt_id, **params):
       from operations.inference import InferenceOperation
       op = InferenceOperation(self.service, self.orchestrator)
       return op.execute(prompt_id, **params)
   ```

3. Update CLI to use new API method

**Testing:** Run `cosmos inference ps_xxx` - should work identically

**Immediate Benefit:**
- Adding fields to inference now touches 2 files (models.py + inference.py)
- All inference logic in one place
- Can still use old code for other operations

---

### Phase 2: Database Simplification (1 day)
**Goal:** Remove pass-through methods for operations we've converted

**Changes:**
1. Create `core/database.py`
   ```python
   class Database:
       def __init__(self):
           self.session = create_session()
       # Direct SQLAlchemy, no pass-through
   ```

2. Update `InferenceOperation` to use Database directly
3. Mark deprecated methods in DataRepository

**Testing:** Inference should still work with simpler database access

**Immediate Benefit:**
- No more pass-through for inference
- Direct database access where needed
- Old operations still work with DataRepository

---

### Phase 3: Enhance Operation (2 days)
**Goal:** Validate pattern with second workflow

**Changes:**
1. Create `operations/enhance.py`
   - Extract from GPUExecutor.execute_enhancement_run()
   - Include all enhance-specific logic

2. Update `api/cosmos_api.py` enhance_prompt()
3. Update CLI enhance command

**Testing:** Run `cosmos enhance ps_xxx` - should work identically

**Immediate Benefit:**
- Two operations now have clean separation
- Pattern is validated
- Can assess if continuing is worthwhile

---

### Phase 4: Remote Layer Consolidation (2 days)
**Goal:** Simplify remote operations interface

**Changes:**
1. Create `remote/gpu_client.py`
   - Combine SSHManager + FileTransferService + RemoteCommandExecutor
   - Provide simpler interface

2. Update InferenceOperation and EnhanceOperation to use gpu_client
3. Keep old classes for unconverted operations

**Testing:** Both operations should still work

**Immediate Benefit:**
- Simpler remote operations
- Less coupling between remote services
- Old operations still work with old classes

---

### Phase 5: Batch Operation (2 days)
**Goal:** Handle the complex batch case

**Changes:**
1. Create `operations/batch.py`
   - Extract from GPUExecutor.execute_batch_runs()
   - Handle the N-runs-to-1-execution complexity

2. Update batch inference in API and CLI

**Testing:** Batch inference should work

**Immediate Benefit:**
- Batch complexity isolated in one file
- Batch-specific logic no longer scattered

---

### Phase 6: Upscale Operation (1 day)
**Goal:** Complete the operation migrations

**Changes:**
1. Create `operations/upscale.py`
2. Update API and CLI

**Testing:** All operations should work

**Immediate Benefit:**
- All operations now follow same pattern
- Ready for cleanup

---

### Phase 7: CLI Consolidation (1 day)
**Goal:** Reduce CLI file sprawl

**Changes:**
1. Create unified `cli.py` with all commands
2. Delete individual CLI files
3. Update package entry points

**Testing:** All CLI commands should work

**Immediate Benefit:**
- Single file for all CLI logic
- Reduced duplication

---

### Phase 8: Final Cleanup (1 day)
**Goal:** Remove dead code

**Changes:**
1. Delete GPUExecutor (now empty)
2. Delete DataRepository (if all operations converted)
3. Delete old connection/transfer modules
4. Update all imports

**Testing:** Full system test

**Immediate Benefit:**
- Reduced codebase size
- Clear architecture

## Exit Points - Value at Each Phase

You can stop after any phase and still have improvements:

- **After Phase 1:** Inference changes only touch 2 files instead of 5-8
- **After Phase 2:** No more pass-through for inference operations
- **After Phase 3:** Two operations with clean boundaries, pattern proven
- **After Phase 4:** Simpler remote operations interface
- **After Phase 5:** Batch complexity properly isolated
- **After Phase 6:** All operations follow consistent pattern
- **After Phase 7:** Cleaner CLI structure
- **After Phase 8:** Minimal, clean codebase

## Success Metrics

- **File Coupling:** Changes touch maximum 2-3 files (down from 5-8)
- **Code Size:** ~30% reduction in total lines
- **File Count:** ~40 files (down from 73+)
- **Max File Size:** No file over 1000 lines
- **Test Coverage:** Maintain or improve current coverage

## Risk Mitigation

1. **Create operations incrementally** - Each operation can be migrated independently
2. **Keep old code during migration** - Delete only after new code is tested
3. **Test after each phase** - Ensure system works before proceeding
4. **Document changes** - Update imports and API docs as we go

## Timeline

Total estimated time: **2 weeks** (part-time)
- Week 1: Phases 1-2 (Create operations, consolidate remote)
- Week 2: Phases 3-5 (Simplify API, consolidate CLI, cleanup)

## Next Steps

1. Review and approve this plan
2. Create operations/ directory structure
3. Begin with InferenceOperation as proof of concept
4. Proceed with remaining operations once pattern is validated

## Implementation Rationale

### Why a Base Class?

The base class (`operations/base.py`) isn't about abstract design patterns - it's about enforcing the specific contracts your system needs to function correctly:

1. **Database Consistency**: All runs must be created with certain fields for the UI to display them
2. **Status Management**: Status transitions must follow patterns for the queue to work
3. **Output Structure**: Outputs must have certain keys for downstream processing
4. **Logging Patterns**: Consistent logging for debugging and monitoring

### What Problems This Solves

#### Problem 1: "Where do I add this field?"
**Current:** Adding a "priority" field requires changes to 5-8 files
**New:** Add to models.py and BaseOperation.create_run() - 2 files total

#### Problem 2: "Batch is different from everything else"
**Current:** Batch logic scattered across GPUExecutor, CosmosAPI, batch_inference.py
**New:** All batch complexity isolated in operations/batch.py

#### Problem 3: "How do I ensure consistency?"
**Current:** Different code paths create runs with different patterns
**New:** Everyone uses BaseOperation methods - guaranteed consistency

### Infrastructure Reuse vs Duplication

Operations DON'T duplicate infrastructure - they orchestrate it:

- **SSHManager**: Kept and reused by all operations
- **DockerExecutor**: Kept and reused by all operations
- **FileTransferService**: Kept and reused by all operations
- **Database Models**: Kept unchanged for compatibility

Operations only own the workflow logic (when to upload, what to execute, how to parse results).

## Adding New Models - Developer Guide

### Example: Adding "Cosmos Reason" Model

With the new architecture, adding a model requires:

1. **Create the operation** (`operations/reason.py`):
```python
class ReasonOperation(BaseOperation):
    def execute(self, prompt_id: str, question: str):
        # Guaranteed to work with UI (base class ensures it)
        run = self.create_run(prompt_id, "reason")

        # Your specific logic
        with self.ssh:
            self.files.upload_file(video, f"/workspace/{run.id}")
            answer = self.docker.run_container(
                "nvidia/cosmos-reason",
                f"--video {video} --question '{question}'"
            )
            result = self.files.download_file(f"/workspace/{run.id}/answer.json")

        # Guaranteed to display correctly (base ensures it)
        self.complete_run(run, {
            "output_path": result,
            "answer": answer["text"],
            "confidence": answer["confidence"]
        })
        return {"run_id": run.id, "answer": answer["text"]}
```

2. **Add API route** (`api.py`):
```python
def reason_video(self, prompt_id: str, question: str):
    op = ReasonOperation(self.db, self.ssh, self.docker, self.files)
    return op.execute(prompt_id, question)
```

3. **Add CLI command** (`cli.py`):
```python
@cli.command()
def reason(prompt_id, question):
    result = api.reason_video(prompt_id, question)
    print(f"Answer: {result['answer']}")
```

That's it. The model will:
- Show up in Gradio UI (runs table works automatically)
- Be queryable by CLI (list commands work automatically)
- Follow all system patterns (enforced by base class)

### Why This Works

The base class enforces that every operation:
1. Creates runs with required fields (UI compatibility)
2. Updates status correctly (queue compatibility)
3. Provides expected outputs (downstream compatibility)
4. Logs consistently (debugging compatibility)

You can't accidentally break these contracts because the base class methods enforce them.

## Migration Philosophy

Each phase provides immediate value:
- **Phase 1 alone** reduces inference changes from 5-8 files to 2
- **Phases 1-3** prove the pattern with real operations
- **Any phase** can be the stopping point with retained benefits

The key insight: Operations don't replace infrastructure, they orchestrate it. This gives you clean separation without code duplication.