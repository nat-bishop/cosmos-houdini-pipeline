# Data Architecture Analysis & Next Steps
**Date**: 2025-09-05
**Author**: Claude Code Assistant
**Purpose**: Document current data architecture issues and provide actionable next steps

---

## Executive Summary

The Cosmos Workflow system has a functional but fragile data architecture. While the UI works due to defensive programming (fallback checks), the underlying data model has integrity issues that could cause problems for API consumers, debugging, and future development.

---

## Current System Analysis

### What's Working Well ✅

1. **Directory Structure**: Already uses `outputs/run_rs_xxxxx/` format consistently
2. **File Downloads**: Correctly downloads entire directories from GPU server
3. **Gallery Display**: Works due to defensive fallback checks for multiple filenames
4. **Database-First Design**: Good separation between data (WorkflowService) and execution (WorkflowOrchestrator)

### Critical Issues 🔴

1. **Database-Filesystem Mismatch**
   - Database stores: `outputs/run_rs_xxx/result.mp4`
   - Actual file: `outputs/run_rs_xxx/output.mp4`
   - Impact: Database contains paths to non-existent files

2. **Scattered Logging**
   - `/logs/runs/` - Contains only 1 file (mostly unused)
   - `/notes/` - Contains only run_history.log (unclear purpose)
   - Actual logs in `outputs/run_rs_xxx/run.log` - Not tracked in database
   - Impact: Confusing, hard to debug, logs not findable

3. **Type Confusion in Run Model**
   - Video generation and text enhancement both use same Run model
   - Enhancement runs get stuck in "running" state (as we saw earlier)
   - No way to distinguish operation types in database
   - Impact: Gallery has to filter out non-video runs, queries are difficult

4. **No Data Integrity Mechanisms**
   - No manifest of files in each directory
   - No verification that outputs match database
   - No cleanup for orphaned files or failed runs
   - Impact: Data corruption accumulates over time

---

## Architecture Discoveries

### Run Output Structure
Each run creates a directory with multiple outputs:
```
outputs/run_rs_xxxxx/
├── output.mp4           # Primary generated video
├── edge_input_control.mp4  # Generated control video
├── spec_used.json       # Actual spec sent to model
├── run.log             # Docker execution logs
└── output.txt          # Text output from process
```

### Database Storage Pattern
The `Run` model stores outputs as flexible JSON:
```json
{
  "outputs": {
    "status": "success",
    "output_path": "outputs/run_rs_xxx/result.mp4",  // WRONG filename
    "upscaled": false,
    "duration_seconds": 720.664128,
    "started_at": "2025-09-05T22:34:45",
    "completed_at": "2025-09-05T22:46:45"
  }
}
```

### Gallery Resilience
The Gallery works despite the bug because it checks multiple paths:
```python
possible_paths = [
    Path(f"outputs/{run_name}/output.mp4"),    # Actual file ✓
    Path(f"outputs/{run_name}/result.mp4"),    # Database path ✗
    # ... more fallbacks
]
```

---

## Recommended Fixes

### Priority 1: Critical Path Fixes (Do First)

#### 1.1 Fix Output Path in Database
**File**: `cosmos_workflow/workflows/workflow_orchestrator.py`
**Line**: 157
**Change**:
```python
# From:
output_path = f"outputs/{prompt_name}/result.mp4"
# To:
output_path = f"outputs/{prompt_name}/output.mp4"
```
**Impact**: Database will contain correct paths to actual files

#### 1.2 Update Outputs JSON Structure
**File**: `cosmos_workflow/workflows/workflow_orchestrator.py`
**Lines**: 161-169
**Add fields**:
```python
return {
    "status": "success",
    "type": "video_generation",              # NEW: Operation type
    "output_dir": f"outputs/{prompt_name}/", # NEW: Directory reference
    "primary_output": "output.mp4",          # NEW: Just filename
    "output_path": output_path,              # KEEP: For compatibility
    # ... rest unchanged
}
```

### Priority 2: Cleanup & Consolidation

#### 2.1 Remove Confusing Directories
```bash
rm -rf logs/   # Only has 1 file, logs should be in run directories
rm -rf notes/  # Unclear purpose, only has run_history.log
```

#### 2.2 Fix Log Location
**File**: `cosmos_workflow/cli/inference.py` (or wherever log_path is set)
**Change**:
```python
# From:
log_path = Path(f"logs/runs/{run_id}.log")
# To:
log_path = Path(f"outputs/run_{run_id}/run.log")
```

### Priority 3: Type Separation

#### 3.1 Fix Text Enhancement
**File**: `cosmos_workflow/cli/enhance.py`
**Store meaningful outputs**:
```python
outputs = {
    "type": "text_enhancement",  # Mark as different type
    "enhanced_prompt_id": enhanced_prompt["id"],
    "enhanced_text": enhanced_text[:500],  # Store preview
    "model_used": model,
    "duration_seconds": duration
}
service.update_run(enhancement_run["id"], outputs=outputs)
```

#### 3.2 Update Gallery to Filter Types
**File**: `cosmos_workflow/ui/app.py`
**Line**: ~320
**Add filter**:
```python
for run in runs:
    outputs = run.get("outputs", {})
    # Skip non-video runs
    if outputs.get("type") == "text_enhancement":
        continue
```

### Priority 4: Data Integrity

#### 4.1 Add Manifest Generation
**File**: `cosmos_workflow/transfer/file_transfer.py`
**After line 141** (after download):
```python
# Create manifest of downloaded files
manifest_path = local_out / "manifest.txt"
with open(manifest_path, "w") as f:
    for file in local_out.iterdir():
        if file.name != "manifest.txt":
            stat = file.stat()
            f.write(f"{file.name}\t{stat.st_size}\t{stat.st_mtime}\n")
```

#### 4.2 Create Integrity Check Command
**New file**: `cosmos_workflow/cli/verify.py`
```python
@cli.command()
def verify():
    """Verify database-filesystem integrity."""
    issues = []

    for run in service.list_runs():
        output_path = run["outputs"].get("output_path")
        if output_path and not Path(output_path).exists():
            issues.append(f"Missing file: {output_path} for run {run['id']}")

    # Check for orphaned directories
    for dir_path in Path("outputs").glob("run_*"):
        run_id = dir_path.name.replace("run_", "")
        if not service.get_run(run_id):
            issues.append(f"Orphaned directory: {dir_path}")

    if issues:
        for issue in issues:
            click.echo(f"❌ {issue}")
    else:
        click.echo("✅ No integrity issues found")
```

---

## Implementation Plan

### Phase 1: Fix Critical Issues (1 hour)
1. Fix output.mp4 filename (1 line change)
2. Add type field to outputs JSON
3. Test that Gallery still works

### Phase 2: Consolidate Logging (30 minutes)
1. Update log path to use run directory
2. Delete /logs and /notes directories
3. Verify logs appear in correct location

### Phase 3: Handle Different Types (1 hour)
1. Fix text enhancement outputs
2. Update Gallery to filter by type
3. Test both video and text operations

### Phase 4: Add Integrity (2 hours)
1. Implement manifest generation
2. Create verify command
3. Create backup script
4. Document backup/restore process

---

## Future Considerations

### Option A: Separate Models for Different Operations
Instead of forcing everything into Run model:
```python
class VideoGeneration(Base):
    # Video-specific fields

class TextEnhancement(Base):
    # Text-specific fields

class Job(Base):  # Generic parent
    job_type = Column(String)
    # Polymorphic relationship
```

### Option B: Content-Addressable Storage
Store files by hash instead of run ID:
```
storage/
  videos/abc123.mp4  # SHA-256 hash
  manifests/run_rs_xxx.json  # Points to content
```

### Option C: Event Sourcing
Track all changes as events for perfect audit trail:
```python
class Event(Base):
    event_type = Column(String)  # "run_started", "file_created", etc.
    entity_id = Column(String)   # run_id
    payload = Column(JSON)
    timestamp = Column(DateTime)
```

---

## Testing Checklist

After implementing changes:

- [ ] Run normal inference - verify output.mp4 path correct in database
- [ ] Check Gallery - ensure videos still display
- [ ] Run text enhancement - verify it completes properly
- [ ] Check logs appear in run directory, not /logs
- [ ] Run verify command - should find no issues
- [ ] Create backup - verify it captures all data
- [ ] Restore from backup - verify system still works

---

## Backup Strategy

### Simple Backup Script
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backups/$DATE"

mkdir -p $BACKUP_DIR

# Backup database
cp outputs/cosmos.db $BACKUP_DIR/

# Backup all run directories
cp -r outputs/run_* $BACKUP_DIR/

# Create manifest
ls -la outputs/ > $BACKUP_DIR/manifest.txt

# Compress
tar -czf "backup_$DATE.tar.gz" $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "Backup created: backup_$DATE.tar.gz"
```

---

## Conclusion

The system is more robust than initially apparent due to defensive programming, but has underlying data integrity issues that should be addressed. The fixes are relatively simple and can be implemented incrementally without breaking existing functionality.

**Key Insight**: The directory-based approach (`outputs/run_rs_xxx/`) is actually good - it's self-contained, easy to backup, and simple to understand. The main issues are just mismatched filenames and scattered logging.

**Recommendation**: Implement Phase 1 and 2 immediately (low risk, high value), then evaluate whether Phase 3 and 4 are needed based on actual usage patterns.