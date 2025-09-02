# Known Issues & Workarounds

This document tracks known issues, bugs, and their workarounds. Critical for AI assistants to avoid regenerating buggy code.

## 🔴 Critical Issues

### 1. Vocab Out of Range Error
**Problem**: High-resolution videos with prompt upsampling cause vocabulary errors
```python
# This will fail with high-res input
--upsample-prompt --input-video 4k_video.mp4
```

**Workaround**: Use manual upsampling
```python
# Instead, call upsampling functions directly
from cosmos_workflow.workflows.upsample_integration import upsample_manually
result = upsample_manually(prompt, video_path)
```

**Status**: Upstream bug in Cosmos Transfer model

---

### 2. SFTP Large File Timeout
**Problem**: Files >1GB timeout during SFTP transfer
```python
# Fails silently after 300 seconds
file_transfer.upload_for_inference(large_video)
```

**Workaround**: Increase timeout
```python
ssh_manager = SSHManager(ssh_options, timeout=1800)  # 30 minutes
```

**Fix Planned**: Implement chunked transfers

## 🟡 Medium Priority Issues

### 3. Docker Container Cleanup
**Problem**: Containers not cleaned after failed runs
```bash
# Leaves orphaned containers
docker ps -a  # Shows stopped containers accumulating
```

**Workaround**: Manual cleanup
```python
docker_executor.cleanup_containers()
# Or via SSH: sudo docker container prune -f
```

**Fix Planned**: Add cleanup in exception handlers

---

### 4. Circular Import Prevention
**Problem**: Some imports must stay inside functions
```python
# These MUST remain as function-level imports
def create_prompt():
    from cosmos_workflow.prompts.schemas import DirectoryManager  # Circular if top-level
```

**Permanent Design**: These 22 imports are intentional, not bugs

---

### 5. Windows Path Issues
**Problem**: Mixed path separators on Windows
```python
# Breaks on Windows
remote_path = f"{base_dir}/{filename}"  # Uses forward slash
```

**Current Fix**: Always use
```python
remote_path = remote_path.replace("\\", "/")  # Normalize for SFTP
local_path = Path(local_path)  # Use pathlib for local
```

## 🟢 Minor Issues

### 6. Logging Performance
**Problem**: F-strings in logging are slower
```python
# Slow (but still works)
logger.info(f"Processing {file}")
```

**Fixed**: Most converted to lazy formatting
```python
# Fast
logger.info("Processing %s", file)
```
**Remaining**: 11 instances in non-critical paths

---

### 7. Line Length Violations
**Problem**: 13 lines exceed 100 characters
**Impact**: Cosmetic only
**Fix**: Low priority formatting task

---

### 8. Missing Docstrings
**Problem**: Some internal functions lack docstrings
**Impact**: Documentation completeness
**Policy**: Only public functions require docstrings

## 🔧 Workaround Patterns

### Pattern 1: Timeout Handling
```python
# Always use configurable timeouts
def long_operation(timeout: int = 300):
    try:
        result = ssh.execute_command(cmd, timeout=timeout)
    except TimeoutError:
        logger.warning("Operation timed out, retrying with longer timeout")
        result = ssh.execute_command(cmd, timeout=timeout * 2)
```

### Pattern 2: Path Normalization
```python
# Always normalize paths for cross-platform
def safe_path(path: str) -> str:
    if sys.platform == "win32":
        return path.replace("/", "\\")
    return path.replace("\\", "/")
```

### Pattern 3: Import Guards
```python
# For optional dependencies
try:
    from transformers import BlipProcessor
    HAS_AI = True
except ImportError:
    HAS_AI = False

def ai_feature():
    if not HAS_AI:
        logger.warning("AI features not available")
        return None
```

## 🐛 Bugs by Module

### cosmos_workflow.connection
- SSH connection reuse sometimes fails (use context manager)
- SFTP mkdir doesn't handle nested paths (create parent first)

### cosmos_workflow.execution
- Docker --gpus flag needs sudo on some systems
- Container names can conflict (use unique IDs)

### cosmos_workflow.prompts
- Schema validation too strict for legacy prompts
- DirectoryManager creates duplicate date folders

### cosmos_workflow.local_ai
- AI models require 8GB+ RAM (document requirement)
- Video processor assumes cv2 available (add check)

### cosmos_workflow.workflows
- Orchestrator doesn't rollback on partial failure
- Status checks can miss Docker daemon issues

## 📝 When You Encounter a Bug

1. **Check this file first** - It might be known
2. **Try the workaround** - Usually faster than fixing
3. **Document here** if new:
   ```markdown
   ### N. Brief Description
   **Problem**: What breaks
   **Workaround**: How to avoid
   **Fix Planned**: If applicable
   ```
4. **Update PROJECT_STATE.md** if critical

## 🔄 Recently Fixed

### ✅ Windows SFTP Compatibility (2024-12-30)
- Replaced rsync with pure Python SFTP
- Fixed path separator issues

### ✅ Datetime Timezone Issues (2024-12-30)
- Added UTC timezone to all datetime.now() calls
- Fixed timezone-naive datetime warnings

### ✅ Import Organization (2024-12-30)
- Moved 15 unnecessary function imports to top-level
- Kept 22 intentional lazy imports

## 📊 Issue Statistics

- **Critical**: 2 (workarounds available)
- **Medium**: 3 (fixes planned)
- **Minor**: 3 (cosmetic/performance)
- **Fixed This Week**: 8
- **Total Closed**: 47

## 🎯 Priority Fix Order

1. SFTP chunked transfers for large files
2. Docker cleanup in exception handlers
3. Better error messages for vocab errors
4. Path normalization utilities
5. Schema validation flexibility

---

**Last Updated**: 2024-12-30
**Next Review**: 2025-01-06
