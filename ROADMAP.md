# ROADMAP - Cosmos Workflow System

## 🔥 Priority 1: Critical Fixes

### Complete Abstraction Layer Migration
**Issue:** Multiple files bypass abstraction layers, calling SSH/Docker commands directly instead of using RemoteCommandExecutor/DockerCommandBuilder

**Export Missing Classes:**
- [ ] Add RemoteCommandExecutor to cosmos_workflow/execution/__init__.py exports

**Fix Direct SSH Usage - cosmos_workflow/api/cosmos_api.py:**
- [ ] Line 868: Replace ssh_manager.execute_command with RemoteCommandExecutor
- [ ] Line 894: Replace ssh_manager.execute_command for Docker logs streaming

**Fix Direct SSH Usage - cosmos_workflow/transfer/file_transfer.py:**
- [ ] Line 248: Replace direct mkdir -p with RemoteCommandExecutor.create_directory() loop

**Fix Direct SSH Usage - cosmos_workflow/execution/docker_executor.py:**
- [ ] Lines 277, 320, 347, 654: Background Docker runs (preserve timeout=5 pattern)
- [ ] Lines 372, 377: Docker info/images commands
- [ ] Lines 415, 477, 497, 522, 546, 564: Various Docker commands
- [ ] Lines 662, 703: File listing and log streaming

**Fix Direct SSH Usage - cosmos_workflow/execution/gpu_executor.py:**
- [ ] Line 87: Replace manual docker inspect with RemoteCommandExecutor.inspect_container()
- [ ] Lines 406, 752, 895, 1021: Replace rm -rf with RemoteCommandExecutor.cleanup_run_directories()
- [ ] Replace deprecated execute_command() calls with specialized methods

**Extend DockerCommandBuilder:**
- [ ] Add build_ps_command() for docker ps with filters/formatting
- [ ] Add build_exec_command() for docker exec operations
- [ ] Document which Docker commands need builder methods vs RemoteCommandExecutor

**Special Handling Required:**
- [ ] Document streaming pattern for Docker logs (preserve stream_output parameter)
- [ ] Document background execution pattern (timeout=5 for fire-and-forget)
- [ ] Ensure all timeout and stream_output parameters are preserved

### Log Recovery on Failure
- [ ] Add `_ensure_log_downloaded()` method to DockerExecutor
- [ ] Wrap Docker execution in try/finally blocks
- [ ] Test with intentional failures to verify log preservation

### Fix F-String Logging Violations
- [ ] Fix `cosmos_workflow/api/workflow_operations.py`
- [ ] Fix `cosmos_workflow/execution/docker_executor.py`
- [ ] Fix `cosmos_workflow/transfer/file_transfer.py`
- [ ] Fix `cosmos_workflow/workflows/workflow_orchestrator.py`
- [ ] Fix `cosmos_workflow/ui/app.py`
- [ ] Fix `cosmos_workflow/connection/ssh_manager.py`
- [ ] Fix `cosmos_workflow/services/workflow_service.py`

### Thread Management Improvements
- [ ] Create thread pool for log streaming
- [ ] Add proper cleanup on exit
- [ ] Implement thread tracking

## 🚀 Priority 2: Architecture Refactoring

### Operation-Centric Architecture Migration
**Issue:** Adding a single database field requires changes to 5-8 files due to excessive coupling between layers. God objects (GPUExecutor: 1437 lines, DataRepository: 1462 lines) handle too many responsibilities.

**Goal:** Reduce coupling so changes affect only 2 files: the operation and its test. Each operation owns its complete workflow.

**Implementation:** See [docs/ARCHITECTURE_REFACTOR.md](docs/ARCHITECTURE_REFACTOR.md) for detailed 8-phase migration plan.

**Phase 1 - Create Operation Framework:**
- [ ] Create cosmos_workflow/operations/ directory
- [ ] Implement BaseOperation class with enforced patterns
- [ ] Create InferenceOperation as proof of concept
- [ ] Update CosmosAPI.quick_inference() to use InferenceOperation
- [ ] Verify tests pass with new operation

**Phase 2 - Migrate Remaining Operations:**
- [ ] Create EnhanceOperation (prompt enhancement)
- [ ] Create UpscaleOperation (video upscaling)
- [ ] Create BatchOperation (handles N runs → 1 Docker)
- [ ] Update CosmosAPI to use all operations

**Phase 3 - Remove Pass-Through Layer:**
- [ ] Delete DataRepository (1462 lines of pass-through)
- [ ] Move database logic directly into operations
- [ ] Update all references

**Phase 4 - Simplify CosmosAPI:**
- [ ] Reduce to thin routing layer (~300 lines)
- [ ] Remove business logic (moved to operations)
- [ ] Keep only request routing and response formatting

**Phase 5 - Split GPUExecutor:**
- [ ] Move Docker operations to remote/ directory
- [ ] Move SSH operations to remote/ directory
- [ ] Delete GPUExecutor (functionality absorbed)

**Benefits:**
- Adding a field: Change operation + test only (2 files vs 5-8)
- Clear ownership: Each operation owns its workflow
- Testable: Mock at operation boundaries
- Maintainable: ~300-500 lines per operation vs 1400+ line god objects

## 🚀 Priority 3: Performance & Reliability

### Simplify Container Status Monitoring
**Consideration:** Running inference.sh/prompt-enhance.sh/etc. scripts from the local machine instead of inside Docker containers could simplify the status checking system

**Current Issues with Container-Based Execution:**
- Complex polling logic to check container status
- Difficult to determine if process inside container has actually started
- Need to parse docker inspect output for state information
- Hard to distinguish between container running and actual work being done

**Potential Benefits of Local Script Execution:**
- [ ] Direct process control and status monitoring
- [ ] Simpler error handling and recovery
- [ ] Easier to implement timeouts and cancellation
- [ ] Could use standard process monitoring tools
- [ ] Would eliminate need for container polling

**Investigation Tasks:**
- [ ] Analyze if scripts have dependencies that require container environment
- [ ] Determine if GPU access can be managed from local scripts
- [ ] Evaluate security implications of running scripts locally
- [ ] Consider hybrid approach: local orchestration with containerized GPU operations

### Smart Batching System ✅ COMPLETED (2025-09-26)
**Completed:** Advanced smart batching with run-level optimization and enhanced APIs
- [x] **Smart Batching Algorithms**: Complete TDD-implemented system providing 2-5x performance improvements
- [x] **Two Batching Modes**: Strict (identical controls) and Mixed (master batch) approaches
- [x] **Conservative Memory Management**: Batch sizing based on control count (8→4→2 jobs) prevents OOM
- [x] **Non-Invasive Integration**: Zero impact when not used, overlay on existing queue system
- [x] **Comprehensive Testing**: 48 passing tests with performance benchmarks and edge case validation
- [x] **Queue Service Integration**: analyze_queue_for_smart_batching(), execute_smart_batches(), get_smart_batch_preview()
- [x] **Enhanced batch_inference API**: Now accepts weights_list (different weights per prompt) instead of shared_weights
- [x] **Run-Level Optimization**: Extracts individual runs from jobs and reorganizes into optimal batches
- [x] **Comprehensive Documentation**: Created docs/SMART_BATCHING.md user guide

**Technical Achievements:**
- Core smart batching algorithms in `cosmos_workflow/utils/smart_batching.py`
- Enhanced SimplifiedQueueService with three new smart batching methods
- Intelligent job filtering to only batch compatible job types (inference, batch_inference)
- Efficiency calculations with estimated speedup metrics and control reduction analysis
- Memory safety through conservative batch sizing based on control complexity
- Analysis workflow with preview, validation, and atomic execution

### Batch Processing Implementation ✅ COMPLETED (Enhanced with Smart Batching)
- [x] **Smart Batch Commands**: Integrated into queue system with analysis and execution workflow
- [x] **Advanced Batch Job Management**: Database-backed queue with smart batching overlay
- [x] **Performance Optimization**: 2-5x speedup through intelligent job grouping and batching
- [x] **Comprehensive Progress Tracking**: Full batch lifecycle with efficiency metrics

### Container Lifecycle Management
- [ ] Add container ID to Run model in database
- [ ] Label containers with run_id during creation
- [ ] Implement `cosmos kill --run <run_id>` command
- [ ] Add "cancelled" status to database schema
- [ ] Create graceful shutdown option (SIGTERM vs SIGKILL)

### Remote Environment Setup Automation
- [ ] Create setup script for Docker image building
- [ ] Automate checkpoint download and verification
- [ ] Configure environment variables and secrets
- [ ] Add health check verification

## 🛠️ Priority 4: Code Quality

### Reduce Method Complexity
- [ ] Refactor `enhance_prompt` (136 lines) into smaller methods
- [ ] Refactor `quick_inference` (97 lines) into smaller methods
- [ ] Extract validation logic into separate methods
- [ ] Extract execution logic into separate methods
- [ ] Extract status update logic into separate methods

### Directory Structure Refactoring
**Goal:** Reorganize codebase directories to better couple related functionality and improve architectural clarity

**Current Issues:**
- data_repository.py located in services/ but contains database-specific logic
- Related functionality scattered across multiple directories
- Unclear separation of concerns in directory structure

**Refactoring Tasks:**
- [ ] Move data_repository.py from services/ to database/ directory
- [ ] Identify and merge other directories with overlapping responsibilities
- [ ] Update all import statements and references
- [ ] Ensure tests continue to work after directory changes
- [ ] Update documentation to reflect new structure

### Gradio UI Refactoring ✅ COMPLETED (2025-01-25)
**Goal:** Reduce monolithic app.py file (originally 3,200+ lines) to improve maintainability - **ACHIEVED**

**Completed Improvements:**
- [x] **Major UI Architecture Refactoring**: Reduced app.py from 3,255 to 152 lines (95.5% reduction)
- [x] **Cross-Tab Navigation System**: Complete navigation between all tabs with intelligent filtering
  - [x] Navigate from Inputs tab to Runs tab filtering by input directory
  - [x] Navigate from Inputs tab to Prompts tab with automatic search filtering
  - [x] Navigate from Prompts tab to Runs tab with selected prompts filtering
  - [x] Persistent filter state with clear visual indicators
- [x] **Enhanced Prompts Tab Management**: Advanced filtering, selection tracking, and batch operations
- [x] **Modular Architecture**: Created 25+ focused modules with clear separation of concerns
- [x] **Code Elimination**: Removed 2,852 lines of legacy backward compatibility functions
- [x] **Extract inline event handlers to separate modules**: Created specialized wiring modules
- [x] **Move event bindings closer to their respective tab definitions**: Organized by tab responsibility
- [x] **Unified filter system**: Consistent filtering patterns across all tabs
- [x] **State management**: Enhanced cross-tab communication and navigation state

**Technical Achievements:**
- **app.py**: 3,255 → 152 lines (95.5% reduction)
- **Total lines eliminated**: 4,100+ lines including legacy code removal
- **Code duplication**: 30% → <2%
- **Average file size**: 1,000+ → ~150 lines
- **Monolithic files eliminated**: All major monoliths broken down into focused modules

### Progress Indicators for GPU Jobs
- [ ] Add progress bars for GPU jobs to the Gradio app

### Standardize Error Handling
- [ ] Create base exception classes in `cosmos_workflow/exceptions.py`
- [ ] Define ValidationError, ExecutionError, NetworkError
- [ ] Update all modules to use consistent exceptions
- [ ] Add retry logic for transient errors

### Test Architecture Refactoring
**Issue:** Tests currently mock implementation details (exact SSH commands) instead of abstraction boundaries

**Problems with Current Approach:**
- Tests break when implementation changes (e.g., changing mkdir flags)
- Tests document HOW instead of WHAT (implementation vs behavior)
- Excessive mock setup for simple operations
- White-box testing when black-box would be more maintainable

**Refactoring Tasks:**
- [ ] Unit tests should mock at RemoteCommandExecutor/DockerExecutor level
- [ ] Integration tests should mock at SSHManager level or use real SSH
- [ ] Remove assertions on exact shell commands (e.g., "mkdir -p /path")
- [ ] Replace with behavior assertions (e.g., create_directory was called)
- [ ] Document testing strategy in developer guide

**Example Migration:**
```python
# Bad (current): Testing implementation
mock_ssh.execute_command_success.assert_called_with("mkdir -p /dir")

# Good (target): Testing behavior
mock_remote_executor.create_directory.assert_called_with("/dir")
```

### Architecture Validation Tests
- [ ] Create `tests/test_architecture.py`
- [ ] Check for direct library imports (paramiko, docker)
- [ ] Check for direct ssh_manager.execute_command usage
- [ ] Validate all remote commands use RemoteCommandExecutor
- [ ] Ensure DockerCommandBuilder is used for Docker commands
- [ ] Validate wrapper usage
- [ ] Add to CI pipeline

## 📚 Priority 5: Future Enhancements

#### Proper Cancellation Status Propagation
**Issue:** When killing containers with SIGKILL, the system shows a RuntimeError for exit code 137 in console logs (but functionality works correctly)

**Current Behavior:**
- Docker kill returns exit code 137 (SIGKILL) which is expected behavior
- System treats this as an error and logs RuntimeError, but continues functioning
- Jobs are correctly marked as cancelled in database

**Future Implementation Tasks:**
- [ ] Add "cancelled" as distinct status from "failed" throughout execution chain
- [ ] Handle SIGKILL (137) vs SIGTERM (143) exit codes differently
- [ ] Prevent race conditions between kill operations and job processing
- [ ] Update gpu_executor.py to handle cancelled status without raising exceptions
- [ ] Propagate cancellation status through CosmosAPI to UI layer

**Note:** Currently addressed with minimal fix that accepts exit code 137 as valid. Full implementation would require architectural changes across multiple layers.

## 📚 Priority 6: Documentation & Tooling

### User Documentation
- [ ] Create step-by-step setup guide
- [ ] Document all CLI commands with examples
- [ ] Add troubleshooting section for common issues
- [ ] Create workflow examples for common use cases

### Dead Code Analysis
- [ ] Configure Vulture or deadcode tool
- [ ] Create whitelist for CLI entry points
- [ ] Add to CI pipeline as warning
- [ ] Clean up identified dead code

### Model Checkpoint Management
- [ ] Create checkpoint manifest file with hashes
- [ ] Add validation on startup
- [ ] Document required checkpoints
- [ ] Implement automatic download option

---

## ✅ Completed Features

### Queue Service Simplification (2025-09-20)
**Completed:** Migrated from complex threaded QueueService to simplified database-backed queue

**Improvements:**
- Reduced code from 682 lines to 400 lines (40% reduction)
- Eliminated all race conditions by using database transactions
- Removed threading complexity - now uses Gradio timer for processing
- Implemented single warm container strategy to prevent accumulation
- Fixed logging format bugs (loguru compatibility)
- Maintained backward compatibility with existing UI

**Technical Details:**
- Used `with_for_update(skip_locked=True)` for atomic job claiming
- Replaced background thread with Gradio Timer component (2-second interval)
- Fresh database sessions prevent stale data issues
- See `docs/queue_simplification_migration.md` for full details

---

*Last Updated: 2025-09-20*