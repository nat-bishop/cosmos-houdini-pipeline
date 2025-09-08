# ROADMAP - Cosmos Workflow System

## 🔥 Priority 1: Critical Fixes

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

## 🛠️ Priority 3: Code Quality

### Reduce Method Complexity
- [ ] Refactor `enhance_prompt` (136 lines) into smaller methods
- [ ] Refactor `quick_inference` (97 lines) into smaller methods
- [ ] Extract validation logic into separate methods
- [ ] Extract execution logic into separate methods
- [ ] Extract status update logic into separate methods

### Standardize Error Handling
- [ ] Create base exception classes in `cosmos_workflow/exceptions.py`
- [ ] Define ValidationError, ExecutionError, NetworkError
- [ ] Update all modules to use consistent exceptions
- [ ] Add retry logic for transient errors

### Architecture Validation Tests
- [ ] Create `tests/test_architecture.py`
- [ ] Check for direct library imports (paramiko, docker)
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