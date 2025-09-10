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

## 🚀 Priority 2: Performance & Reliability

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

### Batch Processing Implementation
- [ ] Create `cosmos batch` command
- [ ] Implement queue management in DataRepository
- [ ] Add progress tracking for batch jobs
- [ ] Support resuming interrupted batches

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

### Video Metadata Extraction for Gradio UI
**Issue:** Gradio UI displays hardcoded placeholder values for video resolution and duration instead of actual metadata

**Current Problems:**
- UI shows static "1920x1080" resolution for all videos (line 114 in app.py)
- Duration shows placeholder "120 frames (5.0 seconds @ 24fps)" (line 116 in app.py)
- No validation that multimodal videos (color, depth, segmentation) have matching properties
- CosmosSequenceValidator only works with PNG sequences, not video files

**Implementation Tasks:**
- [ ] Create `cosmos_workflow/utils/video_metadata.py` for video analysis
  - Implement `extract_video_resolution(video_path)` using cv2.VideoCapture
  - Implement `extract_video_duration(video_path)` for duration in seconds
  - Implement `extract_video_frame_count(video_path)` for total frames
  - Implement `extract_video_fps(video_path)` for frame rate
  - Implement `get_video_metadata(video_path)` combining all metadata
- [ ] Create `cosmos_workflow/utils/multimodal_validator.py` for consistency checks
  - Implement `validate_video_consistency(video_dir)` to check all videos have same length
  - Implement `validate_matching_properties(video_paths)` for resolution/fps matching
  - Report mismatches between color, depth, and segmentation videos
- [ ] Update Gradio UI to use real metadata
  - Replace TODO comments in `on_input_select()` function
  - Handle edge cases (missing files, corrupted videos)
- [ ] Add comprehensive tests
  - Unit tests for metadata extraction
  - Integration tests for multimodal validation
  - Test error handling for invalid videos

**Technical Approach:**
- Leverage existing OpenCV (cv2) dependency already in project
- Place in utils/ as these are general-purpose utilities for remote GPU workflows
- Follow project patterns: parameterized logging, type hints, Google docstrings

## 🛠️ Priority 3: Code Quality

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

## 📚 Priority 4: Documentation & Tooling

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

*Last Updated: 2025-01-08*