# Manual Testing Protocol - Post Checkpoint Installation

## Context
This document outlines the current status after completing a comprehensive investigation of the logging infrastructure implementation. We successfully implemented the auto-streaming UI but discovered critical infrastructure issues that require manual testing once AI model checkpoints are installed.

## ✅ COMPLETED: Auto-Streaming UI Implementation

### What Was Successfully Accomplished
✅ **Auto-streaming UI**: Fully implemented with automatic job detection on page load
✅ **Manual controls removed**: No more Run ID input or Start Streaming button
✅ **Architecture cleanup**: All database access uses WorkflowOperations facade exclusively
✅ **Infrastructure fixes**: Docker daemon running, SSH working, file transfer bugs resolved
✅ **Database consolidation**: Single fresh `outputs/cosmos.db` with proper schema including `log_path` column

### Files Modified During Implementation
- `cosmos_workflow/ui/app.py` - Complete auto-streaming implementation
  - Removed: `run_id_input`, `start_btn`, manual event handlers
  - Added: `check_and_auto_stream()` function for automatic job detection
  - Fixed: Database access patterns and run ID field mapping
- `cosmos_workflow/transfer/file_transfer.py:209,219` - Fixed logging format bugs
- `cosmos_workflow/cli/status.py:69-72` - Fixed Docker status detection bug

### Current UI Status
- **Location**: http://localhost:8001 (ready to start)
- **Database**: `outputs/cosmos.db` (fresh, consolidated)
- **Behavior**:
  - No jobs → Shows "No active jobs. Waiting..."
  - Jobs exist → Auto-detects, displays job info, starts streaming automatically
  - All controls work: Filters, search, refresh, clear logs

## 🔍 INVESTIGATION FINDINGS

### Infrastructure Status (RESOLVED)
✅ **SSH Connection**: Working properly
✅ **Docker Daemon**: Running and accessible
✅ **File Transfers**: Upload/download functioning correctly
✅ **Log Streaming System**: File-based logging and RemoteLogStreamer operational

### Critical Issue Discovered (BLOCKING)
❌ **Missing AI Model Checkpoints**:
- Error: `FileNotFoundError: './checkpoints/nvidia/Cosmos-Transfer1-7B/base_model.pt'`
- **Impact**: All inference jobs fail after ~9 seconds with checkpoint errors
- **Status**: User downloading checkpoints (in progress)

### Secondary Bugs Discovered (NON-BLOCKING)
🟡 **Status Reporting Bug**: Failed runs incorrectly marked as "completed success"
🟡 **Container Detection Bug**: `cosmos status --stream` can't find running containers due to image filtering issues

## 📋 MANUAL TESTING PROTOCOL

### Prerequisites (Before Testing)
- [ ] AI model checkpoints installed on remote GPU instance
- [ ] Docker daemon confirmed running on remote
- [ ] Fresh database at `outputs/cosmos.db` (already prepared)

### Test Environment
- **Test Prompts Available**:
  - `ps_4943750370622cfefc54` - "manual test - debugging CLI and Docker logs" (recommended)
  - `ps_84374dabad0fc2458261` - "test fresh database with fixed logging"
  - `ps_f12d1c219c2a3736f35c` - "fresh test for UI streaming"

### Step-by-Step Testing Sequence

#### Phase 1: Infrastructure Validation
```bash
# 1. Verify remote status
cosmos status
# Expected: SSH ✓, Docker ✓, GPU status varies

# 2. Check available test prompts
cosmos list prompts --limit 3
# Expected: Shows 3 test prompts listed above
```

#### Phase 2: CLI Testing
```bash
# 3. Test inference with latest prompt
cosmos inference ps_4943750370622cfefc54

# Expected Success Indicators:
# - Files upload successfully (✓ confirmed working)
# - Docker container starts (✓ confirmed working)
# - No checkpoint errors (depends on installation)
# - Process runs longer than 30 seconds (real AI work, not quick failure)
# - Logs show actual inference progress, not just setup steps
```

#### Phase 3: UI Testing (Real-time)
```bash
# 4. Start UI (in separate terminal/background)
cosmos ui --port 8001

# 5. Visit http://localhost:8001
# Expected Auto-streaming Behavior:
# - UI loads and shows "Checking for active jobs..."
# - If job running: Auto-detects, shows job details, starts streaming logs immediately
# - If no jobs: Shows "No active jobs. Waiting..."
# - Color-coded logs: ERROR=red, WARNING=yellow, INFO=blue
# - Real-time log updates as inference progresses
```

#### Phase 4: End-to-End Validation
```bash
# 6. Test simultaneous CLI + UI
# Terminal 1: Start a new job
cosmos inference ps_84374dabad0fc2458261

# Browser: Refresh UI or wait for auto-detection
# Expected: UI automatically switches to new job and streams its logs

# 7. Test manual refresh and controls
# Browser: Use refresh, search, filter controls
# Expected: All UI controls work properly during live streaming
```

### Success Criteria
✅ **CLI Success**: Job runs for several minutes (not seconds), shows real AI inference progress
✅ **UI Success**: Automatically detects running jobs and displays real-time logs
✅ **Integration Success**: UI streams logs from jobs started via CLI
✅ **Log Quality**: Colored, searchable, filterable logs with meaningful content

### Troubleshooting Guide
- **Job fails immediately**: Check checkpoint installation and error messages
- **UI shows "No active jobs"**: Check database connection, job may have finished quickly
- **No log streaming**: Check RemoteLogStreamer connectivity and file paths
- **Container detection issues**: Known bug with `cosmos status --stream`, use direct UI

## 🐛 KNOWN BUGS (For Future Fix)

### High Priority
1. **Status Reporting Bug**: Failed runs marked as "completed success" instead of "failed"
   - Location: Run status logic in workflow orchestrator
   - Impact: Misleading success messages for failed jobs

2. **Container Detection Bug**: `cosmos status --stream` can't find containers
   - Location: Image filtering in DockerExecutor
   - Impact: Manual log streaming via CLI doesn't work

### Lower Priority
3. **GPU Detection**: Status command shows "GPU Not detected"
4. **Auto-refresh**: UI doesn't auto-refresh job list (5-second intervals planned)

## 🚀 NEXT STEPS AFTER CHECKPOINTS

1. **Run Phase 2 CLI Testing** - Validate inference works end-to-end
2. **Run Phase 3 UI Testing** - Validate auto-streaming UI with real jobs
3. **Run Phase 4 Integration** - Test CLI + UI together
4. **Optional**: Fix discovered bugs if they impact usage
5. **Optional**: Add auto-refresh timer for UI job list

## Additional Context
- Full implementation details in `docs/logging-infrastructure-implementation-plan.md`
- Auto-streaming UI is feature-complete and ready for testing
- All infrastructure issues have been resolved except checkpoint installation
- The logging system architecture is solid and proven to work during our investigation