# Job Queue System - Implementation Status

**Purpose**: This is a working document for implementing a job queue system for the Gradio UI only. The CLI remains unchanged.

**Status**: ✅ **Phase 1 COMPLETED** (2025-01-17)
- JobQueue model implemented
- QueueService fully functional
- 28/31 tests passing (3 skipped due to SQLite concurrency)
- Ready for UI integration

## Quick Context
- **What**: Add a visible job queue to the Gradio web UI for inference/enhancement operations
- **Why**: Users can't see queue position, can't cancel jobs, and we're missing batching opportunities
- **How**: Layer a queue service on top of existing CosmosAPI - no changes to core architecture

## Goals
- **Primary**: Add queue visibility and control to inference operations
- **Secondary**: Enable smart batching to improve GPU utilization by 40-60%
- **Tertiary**: Provide queue management capabilities (reorder, cancel, priority)

## Non-Goals
- Replacing Gradio's request queue (we complement it)
- Making the system fully async (staying synchronous)
- Real-time streaming updates (polling is sufficient)
- Distributed queue processing (single GPU constraint)

---

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Gradio UI  │────▶│ QueueService │────▶│  Database   │
└─────────────┘     └──────────────┘     └─────────────┘
                            │                     ▲
                            ▼                     │
                    ┌──────────────┐             │
                    │ CosmosAPI    │─────────────┘
                    └──────────────┘
                            │
                            ▼
                    ┌──────────────┐
                    │ GPUExecutor  │
                    └──────────────┘
```

### Key Components

1. **JobQueue Table**: SQLite table tracking all queued/running jobs
2. **QueueService**: Service layer managing queue operations
3. **Queue Processor**: Background thread executing queued jobs
4. **UI Components**: Queue display and management controls
5. **Batch Optimizer**: Logic for grouping compatible jobs

---

## Implementation Phases

### Phase 1: Minimal Viable Queue (2 days)

#### 1.1 Database Schema
**File**: `cosmos_workflow/database/models.py`

```python
class JobQueue(Base):
    __tablename__ = "job_queue"

    id = Column(String, primary_key=True)
    prompt_ids = Column(JSON, nullable=False)
    status = Column(String, nullable=False)
    job_type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    result = Column(JSON, nullable=True)
```

**Migration**: `alembic revision -m "Add job queue table"`

#### 1.2 Queue Service
**File**: `cosmos_workflow/services/queue_service.py`

Core methods:
- `add_job()` - Add job to queue
- `get_next_job()` - Retrieve next queued job
- `process_job()` - Execute a single job
- `get_queue_status()` - Get current queue state
- `get_position()` - Get job's position in queue

#### 1.3 Integration Points
**Modified Files**:
- `cosmos_workflow/ui/app.py` - Update `run_inference_on_selected()`
- `cosmos_workflow/ui/tabs/jobs_ui.py` - Add queue display
- `cosmos_workflow/api/cosmos_api.py` - Add queue methods

#### 1.4 Testing Checklist
- [ ] Single job queues and executes
- [ ] Multiple jobs queue in order
- [ ] Failed jobs marked appropriately
- [ ] Queue survives app restart
- [ ] UI shows queue position

---

### Phase 2: Smart Batching (1 day)

#### 2.1 Batch Detection Logic
**File**: `cosmos_workflow/services/batch_optimizer.py`

```python
class BatchOptimizer:
    def find_batchable_jobs(self, jobs: List[JobQueue]) -> List[List[JobQueue]]:
        """Group compatible jobs for batch execution."""

    def calculate_batch_savings(self, batch_size: int) -> float:
        """Estimate time savings from batching."""
```

#### 2.2 Compatibility Rules
Jobs can be batched if:
- Same `num_steps`, `guidance_scale`, `fps`
- Weights within 0.1 tolerance
- Created within 30-second window
- Combined priority allows waiting

#### 2.3 Testing Checklist
- [ ] Compatible jobs are batched
- [ ] Incompatible jobs run separately
- [ ] Batch results distributed correctly
- [ ] Partial batch failure handled
- [ ] Performance improvement measured

---

### Phase 3: UI Enhancement (1 day)

#### 3.1 Queue Display Component
**Location**: Jobs Tab

```
┌─────────────────────────────────────┐
│ 📋 Job Queue (3 pending, 1 running) │
├─────────────────────────────────────┤
│ #  | Job ID | Type | Status | Time  │
│ 🏃 | job_a1 | inf  | run    | 0:45  │
│ 1  | job_b2 | inf  | queue  | ~2:00 │
│ 2  | job_c3 | enh  | queue  | ~2:30 │
│ 3  | job_d4 | inf  | queue  | ~4:30 │
└─────────────────────────────────────┘
[Refresh] [Clear Completed] [Cancel]
```

#### 3.2 Features
- Auto-refresh every 2 seconds
- Position in queue displayed
- Estimated wait time (Phase 4)
- Cancel queued jobs
- Clear completed jobs

#### 3.3 Testing Checklist
- [ ] Queue updates live
- [ ] Position numbers correct
- [ ] Cancel works for queued jobs
- [ ] Cannot cancel running jobs
- [ ] Completed jobs can be cleared

---

## Technical Decisions

### Why SQLite over Redis/RabbitMQ?
- **Simplicity**: No additional infrastructure
- **Persistence**: Survives crashes automatically
- **Queries**: Complex filtering via SQL
- **Consistency**: ACID transactions
- **Existing**: Already using SQLAlchemy

### Why Background Thread over Celery?
- **Simplicity**: No broker required
- **Single GPU**: Can't parallelize anyway
- **Control**: Direct process management
- **Integration**: Same process as Gradio

### Why JSON Fields over Relations?
- **Flexibility**: Schema can evolve
- **Performance**: Fewer joins
- **Simplicity**: Easier migrations
- **Batching**: Variable prompt counts

---

## Risk Mitigation

### Risk 1: Queue Processor Crash
**Mitigation**:
- Wrap in try/catch with logging
- Auto-restart on exception
- Watchdog timer for hung jobs
- Status reconciliation on startup

### Risk 2: Batch Failure
**Mitigation**:
- Conservative compatibility checks
- Retry failed batches as individual jobs
- Track failure patterns
- Gradual batch size increase

### Risk 3: User Confusion
**Mitigation**:
- Clear queue position display
- Accurate time estimates (Phase 4)
- Status notifications
- Detailed error messages

### Risk 4: Database Growth
**Mitigation**:
- Auto-cleanup completed jobs after 24h
- Archive old jobs to separate table
- Indexes on status and created_at
- VACUUM on cleanup

---

## Success Metrics

### Performance
- [ ] Queue processing latency < 2 seconds
- [ ] Batch detection time < 100ms
- [ ] UI refresh smooth at 0.5 fps
- [ ] Database queries < 50ms

### Functionality
- [ ] 100% of jobs complete successfully
- [ ] Batching achieves 40%+ time savings
- [ ] Queue position always accurate
- [ ] No zombie jobs after 24 hours

### User Experience
- [ ] Users understand queue concept
- [ ] Wait time estimates within 20%
- [ ] No complaints about queue order
- [ ] Positive feedback on visibility

---

## Future Enhancements (Phase 4+)

### Priority System
```python
class JobQueue(Base):
    priority = Column(Integer, default=50)
    user_tier = Column(String, default="standard")
```

### Time Estimation
```python
def estimate_wait_time(position: int) -> timedelta:
    avg_duration = get_average_job_duration()
    return avg_duration * position
```

### Queue Reordering
- Drag-and-drop in UI
- API endpoint for position change
- Respect priority constraints

### Notifications
- Email when job completes
- Discord/Slack webhooks
- Browser notifications

### Analytics Dashboard
- Jobs per hour/day
- Average wait times
- Batch efficiency
- Failure rates

---

## Start Here - Quick Implementation Path

### Step 1: Add Database Table (30 min)
1. Add `JobQueue` model to `cosmos_workflow/database/models.py`
2. Run `alembic revision -m "Add job queue table"`
3. Run migration

### Step 2: Create Queue Service (2 hours)
1. Create `cosmos_workflow/services/queue_service.py`
2. Implement basic `add_job()` and `process_job()` methods
3. Add background thread to `app.py`

### Step 3: Modify UI Handlers (1 hour)
1. Change `run_inference_on_selected()` to use QueueService
2. Change `run_enhance_on_selected()` to use QueueService
3. Return queue position instead of blocking

### Step 4: Add Queue Display (2 hours)
1. Add queue table to Jobs tab
2. Add 2-second timer for auto-refresh
3. Test queue visibility

---

## Rollback Plan

If the queue system causes issues:

1. **Immediate**: Set `DISABLE_QUEUE=true` environment variable
2. **Quick Fix**: Revert to direct execution in `run_inference_on_selected()`
3. **Data Preservation**: Keep job_queue table for analysis
4. **Full Rollback**: Run migration down, restore original code

---

## Documentation Updates

### User Documentation
- How the queue works
- Understanding queue position
- Why jobs are batched
- Canceling jobs
- Priority system (Phase 4)

### Developer Documentation
- Queue architecture
- Adding new job types
- Batch compatibility rules
- Database schema
- API endpoints

### Operations Guide
- Monitoring queue health
- Clearing stuck jobs
- Performance tuning
- Backup procedures
- Troubleshooting

---

## Sign-off Checklist

- [ ] Database migrations tested
- [ ] Queue service unit tests pass
- [ ] Integration tests pass
- [ ] UI components reviewed
- [ ] Performance benchmarks met
- [ ] Documentation complete
- [ ] Rollback plan tested
- [ ] Team training complete

---

## Appendix: Code Examples

### Example: Adding a Job
```python
job_id = queue_service.add_job(
    prompt_ids=["ps_12345"],
    job_type="inference",
    config={
        "weights": {"vis": 1.0, "edge": 0.5},
        "num_steps": 25,
        "guidance_scale": 4.0
    }
)
```

### Example: Batch Detection
```python
def are_compatible(job1, job2):
    c1, c2 = job1.config, job2.config

    # Must match exactly
    if c1["num_steps"] != c2["num_steps"]:
        return False

    # Weights can vary slightly
    for key in ["vis", "edge", "depth", "seg"]:
        if abs(c1["weights"][key] - c2["weights"][key]) > 0.1:
            return False

    return True
```

### Example: Queue Display Query
```sql
SELECT
    ROW_NUMBER() OVER (ORDER BY created_at) as position,
    id,
    job_type,
    status,
    created_at
FROM job_queue
WHERE status IN ('queued', 'running')
ORDER BY created_at;
```

---

## Implementation Notes

### Current System Analysis
- Gradio already provides request-level queuing that prevents UI blocking
- System uses synchronous execution (blocks until Docker container completes)
- Batch inference already implemented in `CosmosAPI.batch_inference()`
- All operations go through `CosmosAPI` facade pattern

### Critical Design Constraint
**THE CLI MUST NOT BE AFFECTED** - The queue is ONLY for Gradio UI. All existing CosmosAPI methods remain unchanged. The QueueService wraps CosmosAPI for UI use only.

### Key Integration Points
1. **app.py line 782-894**: `run_inference_on_selected()` - replace direct CosmosAPI call with QueueService
2. **app.py line 896-977**: `run_enhance_on_selected()` - replace direct CosmosAPI call with QueueService
3. **jobs_ui.py**: Add queue display components to existing Jobs tab
4. **NEW FILE**: `cosmos_workflow/services/queue_service.py` - wraps CosmosAPI for queue operations

### Database Considerations
- Using SQLAlchemy ORM (already in place)
- SQLite database at `cosmos_workflow.db`
- Existing migrations via Alembic
- JSON columns for flexibility (SQLite 3.9+ required)

---

## Implementation Status Report

### ✅ Phase 1 Completed (2025-01-17)
### 🆕 Upscaling Support Added (2025-01-17)

#### Upscaling Feature Details
- **Job Type**: Added "upscale" as a fourth supported job type
- **Video Sources**: Supports both run IDs (rs_xxx) and direct video file paths
- **Control Weight**: Configurable upscaling strength (0.0-1.0)
- **Optional Prompt**: Text prompt to guide AI enhancement direction
- **Empty Prompt IDs**: Upscale jobs use empty prompt_ids list (not required)
- **Full Integration**: Works with all queue features (position tracking, cancellation, etc.)

#### What Was Built
1. **JobQueue Database Model** (`cosmos_workflow/database/models.py`)
   - Tracks job ID, type, status, configuration
   - JSON columns for flexible parameters
   - Timestamps for queue management
   - Priority field for future use

2. **QueueService** (`cosmos_workflow/services/queue_service.py`)
   - Complete queue management system
   - Wraps CosmosAPI without modifying it
   - Background processor thread for automatic execution
   - FIFO processing order
   - Job cancellation support
   - Queue position tracking

3. **Test Coverage**
   - 34 total tests written (including 3 new upscale tests)
   - 31 tests passing
   - 3 tests skipped (SQLite concurrency limitations)
   - Comprehensive coverage of all queue operations including upscaling

#### Current Capabilities
- **Add Jobs**: Queue inference, batch_inference, enhancement, and upscale jobs
- **Track Position**: Get queue position for any job
- **View Status**: Complete queue status including running/queued jobs
- **Process Jobs**: Background thread automatically processes queue
- **Cancel Jobs**: Cancel queued (not running) jobs
- **Error Handling**: Graceful failure with error tracking
- **Job Persistence**: All job data persisted to database
- **Upscaling Support**: Process 4K upscaling jobs from run IDs or video files

#### Known Limitations
1. **SQLite Concurrency**: Limited concurrent write access (acceptable for UI-only use)
2. **No Priority Processing**: Jobs processed strictly FIFO (priority field exists but unused)
3. **Fixed Time Estimates**: Uses hardcoded 120s/job estimate
4. **No UI Integration**: Queue service built but not connected to UI yet

### 🔄 Next Steps (Phase 1.5 - UI Integration)
1. Integrate QueueService into `cosmos_workflow/ui/app.py`
2. Replace direct CosmosAPI calls with QueueService wrapper
3. Add queue display components to Jobs tab
4. Implement queue position notifications

### 📋 Phase 2 (Future - Batch Optimization)
- Batch detection logic
- Compatible job grouping
- Automatic batch formation
- Performance metrics tracking

### Performance Targets
- Single inference: ~2-5 minutes
- Batch of 8: ~8-12 minutes (40-60% savings)
- Queue poll interval: 2 seconds
- UI refresh rate: 0.5 Hz