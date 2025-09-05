# Service Layer Refactoring Plan - SIMPLIFIED
**Version:** 2.1
**Date:** 2025-09-05
**Author:** NAT
**Status:** IN PROGRESS - Chunk 3 Fixed, GPU Execution Untested (2025-09-05)

## Executive Summary

This document outlines a **simplified** refactoring plan to migrate from JSON files to a service layer with SQLAlchemy database. The refactoring prioritizes **simplicity and extensibility** for future AI models while enabling analytics dashboard creation.

**Key Changes from v1:**
- ❌ No complex interface/protocol layer
- ✅ Direct service implementation
- ✅ Flexible schema for multiple AI models
- ✅ Focus on dashboard/analytics goals
- ✅ Fresh start, no complex migration

---

## Table of Contents
1. [Current State](#current-state)
2. [Architecture Design](#architecture-design)
3. [Extensibility for Future Models](#extensibility-for-future-models)
4. [Simplified Implementation Chunks](#simplified-implementation-chunks)
5. [Dashboard Goals](#dashboard-goals)
6. [Progress Tracking](#progress-tracking)

---

## Current State

### System Overview
- **Test Status:** 526 tests passing
- **Branch:** `refactor/service-architecture`
- **Existing Data:** ~15 prompt JSON files (can recreate manually)

### Current Commands That Work Well
- `cosmos create prompt` - Creates prompt spec
- `cosmos inference` - Runs inference (two-step process is good!)
- `cosmos status` - Checks GPU status
- `cosmos prompt-enhance` - AI enhancement

---

## Architecture Design

### Critical Architectural Insight (Added 2025-09-05)

The execution layer is **constrained by NVIDIA Cosmos requirements**:
- NVIDIA scripts (`inference.sh`, `upscale.sh`) expect JSON files on disk
- JSON must be in specific NVIDIA Cosmos format
- Scripts are hardcoded to read from `inputs/prompts/${PROMPT_NAME}.json`
- Cannot simply pass dictionaries to GPU execution

**Solution: Two-Layer Architecture**
1. **Data Layer** (Database → Service → CLI): Database-first, no JSON persistence
2. **Execution Layer** (Orchestrator → GPU): Creates temporary NVIDIA-format JSON for scripts

This requires simple format conversion utilities, not complex schema systems.

### Simplified Architecture (No Over-Engineering!)

```
┌────────────────────────────────────────┐
│              CLI Layer                 │
│  • Parses commands                     │
│  • Calls service methods               │
│  • Formats output                      │
└──────────────────┬─────────────────────┘
                   │ Direct calls
┌──────────────────▼─────────────────────┐
│          Service Layer                 │
│  • WorkflowService (business logic)    │
│  • Returns dicts for CLI display       │
│  • Handles database operations         │
└──────────┬────────────────┬────────────┘
           │                │
┌──────────▼────────┐  ┌───▼─────────────┐
│    Database       │  │  Infrastructure  │
│  • SQLAlchemy     │  │  • SSH/Docker    │
│  • Flexible JSON  │  │  • File Transfer │
└───────────────────┘  └──────────────────┘
```

### No Interface Layer Needed!
Just direct implementation:
```python
class WorkflowService:
    def __init__(self, db_session, config):
        self.db = db_session
        self.config = config

    def create_prompt(self, model_type: str, **kwargs) -> dict:
        # Direct implementation, no protocol
        pass
```

---

## Extensibility for Future Models

### The Key Question: How to Add Cosmos Reason, Cosmos Predict?

**Answer: Flexible Database Schema**

```python
class Prompt(Base):
    __tablename__ = 'prompts'

    # Common fields for ALL models
    id = Column(String, primary_key=True)
    model_type = Column(String)  # "transfer", "reason", "predict"
    prompt_text = Column(Text)
    created_at = Column(DateTime)

    # Flexible fields for model-specific data
    model_config = Column(JSON)  # Different for each model
    inputs = Column(JSON)         # Video paths, images, etc.
    parameters = Column(JSON)     # Model-specific params

class Run(Base):
    __tablename__ = 'runs'

    id = Column(String, primary_key=True)
    prompt_id = Column(String, ForeignKey('prompts.id'))
    model_type = Column(String)
    status = Column(String)

    # Flexible execution data
    execution_config = Column(JSON)  # Weights, params, etc.
    outputs = Column(JSON)           # Results, paths, metrics
    metadata = Column(JSON)          # Anything else
```

### Adding New Models Is Easy!

**Current: Cosmos Transfer**
```python
service.create_prompt(
    model_type="transfer",
    prompt_text="cyberpunk city",
    inputs={"video": "path/to/video", "depth": "path/to/depth"},
    parameters={"num_steps": 35}
)
```

**Future: Cosmos Reason**
```python
service.create_prompt(
    model_type="reason",
    prompt_text="What happens next?",
    inputs={"video": "path/to/result"},
    parameters={"reasoning_depth": 3}
)
```

**Future: Cosmos Predict**
```python
service.create_prompt(
    model_type="predict",
    prompt_text="Continue this scene",
    inputs={"frames": ["frame1.png", "frame2.png"]},
    parameters={"prediction_length": 60}
)
```

### Service Extensibility

```python
class WorkflowService:
    def execute_run(self, run_id: str) -> dict:
        run = self.db.query(Run).get(run_id)

        # Dispatch to appropriate executor
        if run.model_type == "transfer":
            return self._execute_transfer(run)
        elif run.model_type == "reason":
            return self._execute_reason(run)
        elif run.model_type == "predict":
            return self._execute_predict(run)
        else:
            raise ValueError(f"Unknown model: {run.model_type}")
```

---

## Simplified Implementation Chunks

### Chunk 1: Database Foundation ✅ COMPLETED (3 hours)
**Goal:** Create flexible database schema

**Completed Files:**
- ✅ `cosmos_workflow/database/models.py` - Flexible schema with JSON fields
- ✅ `cosmos_workflow/database/connection.py` - Secure connection management
- ✅ `cosmos_workflow/database/__init__.py` - Proper module exports
- ✅ `tests/unit/database/test_models.py` - 29 model tests
- ✅ `tests/unit/database/test_connection.py` - 20 connection tests
- ✅ `docs/DATABASE.md` - Comprehensive documentation

**Implemented Features:**
- Flexible JSON columns for model-specific data
- Security validation (path traversal protection)
- Input validation with SQLAlchemy validators
- Transaction safety with automatic rollback
- 49 passing tests following TDD principles

---

### Chunk 2: Service Core ✅ COMPLETED (3 hours)
**Goal:** Simple service implementation

**Completed Files:**
- ✅ `cosmos_workflow/services/workflow_service.py` - Full implementation
- ✅ `cosmos_workflow/services/__init__.py` - Module exports
- ✅ `tests/unit/services/test_workflow_service.py` - 27 passing tests

**Implemented Methods:**
- ✅ `create_prompt()` - With validation and sanitization
- ✅ `create_run()` - With UUID-based IDs
- ✅ `get_prompt()` - Returns dict or None
- ✅ `get_run()` - Returns dict or None

---

### Chunk 3: CLI Migration with Comprehensive Testing (10 hours) ✅ FIXED BUT UNTESTED
**Goal:** Add CLI tests, switch to WorkflowService, simplify system

**ISSUE DISCOVERED AND FIXED (2025-09-05):**
Found that NVIDIA scripts require specific JSON format on disk:
- Created `cosmos_workflow/utils/nvidia_format.py` for conversion
- Deleted overcomplicated `cosmos_workflow/prompts/` directory
- Orchestrator now converts dicts → NVIDIA JSON → GPU execution
- **STATUS:** Fixed but GPU execution not yet tested

**Core Simplifications:**
- WorkflowService: Data operations AND query logic (pragmatic approach)
- WorkflowOrchestrator: ONLY GPU execution coordination
- Clear separation of concerns - no mixed responsibilities
- ALL AI model operations treated as "runs" (inference, enhancement, etc.)

**Testing Strategy:**
1. **Service tests** - Already complete from Chunk 2 ✅
2. **CLI behavioral tests** - Tests for TARGET behavior (database/service) ✅
3. **Integration tests** - Test CLI→Service→Database flow ✅
4. **Manager tests** - DELETE with managers ⏳

**Commands to Migrate:**
- `cosmos create prompt` → Creates prompt in database ✅
- `cosmos create run` → Creates run from prompt ID ✅
- `cosmos inference` → Executes run (transfer model) ✅
- `cosmos prompt-enhance` → Executes enhancement run (Pixtral model) ✅

**Target CLI Behavior:**
- Commands work with database IDs as primary identifiers
- No JSON files created or used (except for dry-run preview)
- Smart naming continues for user-friendly names
- Comprehensive output for technical CLI users
- Clear error messages, no silent failures
- Trust prepare.py validation, light validation at CLI level
- ALL AI operations tracked as runs in database

**Implementation Phases:**

**Phase 1: Write Target Behavior Tests**
- Write tests for desired service-based behavior
- Tests define the future CLI contract
- Skip making them pass with current JSON implementation
- These tests will initially FAIL (that's expected!)

**Phase 2: Service Migration**
- Update CLI commands to use WorkflowService directly ✅
- Commands accept/return database IDs ✅
- Add enhancement run support to WorkflowService ✅
- Simplify orchestrator - remove data management responsibilities ✅ DONE (but broken)
- Fixed critical code issues (bare excepts, validation) ✅
- Track ALL AI operations (inference, enhancement) as runs ✅

**Phase 2.5: Fix Execution Layer (NEW - Required)**
- Create `cosmos_workflow/utils/nvidia_format.py` for format conversion
- Simplify FileTransferService to work with raw data, not schemas
- Fix orchestrator to properly convert and upload NVIDIA format JSON
- Delete overcomplicated `cosmos_workflow/prompts/` directory
- Test end-to-end execution actually works

**Phase 3: Complete Cleanup**
- ✅ Deleted PromptSpecManager, RunSpecManager (but had to restore schemas.py)
- ✅ Deleted test files
- ⚠️ Cannot fully remove JSON management - NVIDIA requires it
- Replace complex schemas with simple format conversion utils

**Important Distinctions:**
- **Logging**: Operational info → log files/stdout
- **Run Tracking**: AI model executions → database
- Database tracks ONLY concrete model runs, not CLI invocations

**NO dual-write, NO backward compatibility complexity**

---

**Run Types in the System:**
```python
# Transfer Run (video generation)
run = {
    "model_type": "transfer",
    "outputs": {"video_path": "/outputs/result.mp4"}
}

# Enhancement Run (prompt improvement)
run = {
    "model_type": "enhancement",
    "outputs": {"enhanced_prompt_id": "ps_enhanced_123"}
}
```

---

### Chunk 4: Query Methods (2 hours)
**Goal:** List and search functionality

**Service Query Methods to Add:**
```python
class WorkflowService:
    # Existing methods (create, get)
    def list_prompts(self, model_type=None, limit=50)
    def list_runs(self, status=None, prompt_id=None)
    def search_prompts(self, query: str)
    def get_prompt_with_runs(self, prompt_id)  # Joined query
```

**CLI Commands:**
- `cosmos list prompts [--model transfer]` - Filter by model
- `cosmos list runs [--status completed]` - Filter by status
- `cosmos search "cyberpunk"` - Search across everything

**Implementation:**
- Query methods in WorkflowService (pragmatic, no over-engineering)
- Support filtering and pagination
- Rich formatted output for CLI users

---

### Chunk 5: Progress Tracking (2 hours)
**Goal:** Real-time progress for dashboard

**What It Tracks:**
```python
Progress(
    run_id="rs_123",
    timestamp=datetime.now(),
    stage="uploading",     # uploading/inference/downloading
    percentage=45,
    message="Uploading depth video..."
)
```

**Why:** Dashboard shows real-time progress bars!

---

### ~~Chunk 6: Migration~~ SKIP!
**Just manually recreate the ~15 prompts you care about**

---

### ~~Chunk 7: Cleanup~~ MERGED INTO CHUNK 3!
**Cleanup happens immediately in Chunk 3, not deferred**

---

## Dashboard Goals

### Why This Refactor Enables Dashboard

**Current System:** JSON files = hard to query
**New System:** Database = easy analytics!

### Queries the Dashboard Needs

```sql
-- Prompts over time
SELECT DATE(created_at), COUNT(*)
FROM prompts
GROUP BY DATE(created_at)

-- Success rate by model
SELECT model_type,
       COUNT(CASE WHEN status='success' THEN 1 END) / COUNT(*) as success_rate
FROM runs
GROUP BY model_type

-- Average inference time
SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))
FROM runs
WHERE status = 'success'

-- Most used videos
SELECT inputs->>'video' as video, COUNT(*)
FROM prompts
GROUP BY inputs->>'video'
```

### Future Dashboard Implementation (After Refactor)

```
Chunk 9: FastAPI Backend
├── /api/prompts - List/create prompts
├── /api/runs - List/create runs
├── /api/progress/{run_id} - Real-time updates
└── /api/analytics - Charts data

Chunk 10: Web Dashboard
├── Simple HTML + Alpine.js
├── WebSocket for live progress
├── Chart.js for analytics
└── Gallery for outputs
```

---

## Progress Tracking

| Chunk | Description | Time | Status |
|-------|-------------|------|--------|
| 1 | Database with flexible schema | 3h | ✅ Completed |
| 2 | Service core with CRUD methods | 3h | ✅ Completed |
| 3 | CLI Migration with Testing (incl. enhance) | 6-7h | ⚠️ Blocked - Critical Issue |
| 4 | List/search commands | 2h | ⏳ |
| 5 | Progress tracking | 2h | ⏳ |

**Progress:** 9h / 17-18h (50% complete - but blocked on critical issue)
**Total:** ~14-15 hours (adjusted for prompt-enhance inclusion)

**Simplifications Made:**
- Removed duplicate work (old Chunk 5 was redundant)
- Merged cleanup into Chunk 3 (immediate, not deferred)
- No dual-write complexity
- Clear separation of concerns

---

## Key Decisions

### ✅ What We're Doing
1. **Simple service class** - No interface layer
2. **Flexible JSON columns** - Easy to add new models
3. **Fresh start** - No complex migration
4. **Focus on dashboard** - Design for analytics queries
5. **Behavioral CLI tests** - Test the contract, not implementation
6. **Immediate cleanup** - Remove old code as soon as replaced
7. **Clear separation** - Each component has one responsibility

### ❌ What We're NOT Doing
1. **No Protocol/Interface layer** - Unnecessary complexity
2. **No dual-write** - Direct switch to database (confirmed)
3. **No `cosmos run` command** - Two-step process is fine
4. **No migration script** - Just recreate ~15 prompts
5. **No deferred cleanup** - Delete old code immediately
6. **No mixed responsibilities** - WorkflowOrchestrator won't manage data

### 🎯 Success Criteria
1. **Extensible:** Adding Cosmos Reason = new else-if branch
2. **Queryable:** Database enables analytics
3. **Simple:** Less code than current system
4. **Tested:** All tests still pass

---

## Proposed Solution for Chunk 3 Issue

### Option 2: Simple Utils Approach (Recommended)

**File Structure:**
```
cosmos_workflow/
  utils/
    nvidia_format.py          # Simple conversion functions
  workflows/
    workflow_orchestrator.py  # Uses utils for conversion
  transfer/
    file_transfer.py         # Simplified, no schema knowledge
```

**Implementation:**
1. **Create `nvidia_format.py`** with simple functions:
```python
def to_cosmos_inference_json(prompt_dict, run_dict):
    """Convert database dicts to NVIDIA Cosmos format."""
    return {
        "prompt": prompt_dict["prompt_text"],
        "negative_prompt": "",
        "video_path": prompt_dict.get("inputs", {}).get("video", ""),
        "control_weights": run_dict.get("execution_config", {}).get("weights", {}),
        # ... other NVIDIA-required fields
    }
```

2. **Simplify FileTransferService:**
   - Remove schema dependencies
   - Just upload/download files
   - Takes paths and raw data

3. **Fix orchestrator's execute_run():**
   - Convert dicts to NVIDIA format
   - Write temporary JSON
   - Upload and execute

4. **Delete `cosmos_workflow/prompts/` directory:**
   - Overcomplicated and misnamed
   - Replace with simple utils

**Benefits:**
- Clear separation: Database format vs NVIDIA format
- Simple conversion at execution boundary
- No coupling between data and execution layers
- Easy to maintain and extend

## CLAUDE.md Updates Required

After completion, update CLAUDE.md:

```markdown
## New Service Layer
- WorkflowService: Central business logic
- Database models with flexible JSON fields
- Direct implementation, no complex interfaces

## Removed Components
- PromptSpecManager (use WorkflowService)
- RunSpecManager (use WorkflowService)
- DirectoryManager (use WorkflowService)
```

---

## Next Steps

**IMMEDIATE: Fix Chunk 3 Critical Issue**
1. Implement Option 2: Simple Utils approach
2. Create `nvidia_format.py` with conversion functions
3. Fix FileTransferService to handle raw data
4. Update orchestrator's execute_run to properly convert formats
5. Delete overcomplicated prompts directory
6. Test that execution actually works end-to-end

**Then Continue with Chunk 4**

**Remember:** This refactor makes ADDING FEATURES EASIER, not harder!

---

## Assessment: Do Remaining Chunks Still Make Sense?

**YES - The remaining chunks are still valid:**

### Chunk 4: Query Methods ✅
- Adding list/search functionality to WorkflowService
- Independent of execution layer issues
- Still needed for dashboard analytics

### Chunk 5: Progress Tracking ✅
- Real-time progress updates for runs
- Independent of format conversion issues
- Critical for dashboard UX

**However:** We MUST fix the Chunk 3 execution issue first, otherwise:
- The system won't actually execute runs
- We'd be building on a broken foundation
- Integration testing would be impossible

**Revised Timeline:**
- Fix Chunk 3 Issue: 2-3 hours
- Complete Chunk 4: 2 hours
- Complete Chunk 5: 2 hours
- **New Total:** 19-20 hours (was 14-15 hours)

The discovery of NVIDIA format constraints adds complexity but doesn't invalidate the overall architecture. The service layer refactoring is still the right approach - we just need a clean boundary between data management and execution.

---

*This simplified plan reduces complexity while maintaining extensibility for future AI models.*