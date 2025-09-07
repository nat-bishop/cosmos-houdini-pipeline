# Wrapper Pattern Fixes - Implementation Handover

## Executive Summary
The codebase has established wrapper patterns to encapsulate external dependencies (SSH, Docker, file transfers). While mostly followed, there are 7 violations where Docker commands are built as raw strings instead of using the `DockerCommandBuilder` wrapper. This document outlines the fixes needed.

## Background
The project mandates using wrappers for all external operations to ensure:
- Consistent error handling
- Proper connection management
- Testability
- Security (no raw shell command injection)

## Current Issues

### 1. Docker Command String Violations
**Problem:** Direct Docker command strings violate the wrapper pattern documented in `CLAUDE.md`

**Affected Files:**
- `cosmos_workflow/api/workflow_operations.py` (lines 693, 723)
- `cosmos_workflow/execution/docker_executor.py` (lines 339, 344, 506, 526, 666)

**Pattern Violation Example:**
```python
# WRONG (current implementation):
cmd = f"sudo docker logs -f {container_id}"
self.ssh_manager.execute_command(cmd)

# RIGHT (should use wrapper):
# Should use DockerCommandBuilder or a specialized method
```

### 2. Missing Integration Tests
**Problem:** `WorkflowOperations.kill_containers()` has unit tests but no integration tests

**Current Test:** `tests/unit/api/test_workflow_operations_kill_containers.py` (mocked only)
**Needed:** Integration test that verifies actual SSH/Docker interaction

## Implementation Tasks

### Task 1: Fix Docker Command Violations
**Priority:** High
**Estimated Time:** 2-3 hours

#### Option A: Extend DockerCommandBuilder
Add specialized methods to `cosmos_workflow/execution/command_builder.py`:

```python
class DockerCommandBuilder:
    # Existing methods...

    @staticmethod
    def build_logs_command(container_id: str, follow: bool = False) -> str:
        """Build docker logs command."""
        cmd = f"sudo docker logs"
        if follow:
            cmd += " -f"
        cmd += f" {container_id}"
        return cmd

    @staticmethod
    def build_info_command() -> str:
        """Build docker info command."""
        return "sudo docker info"

    @staticmethod
    def build_kill_command(container_ids: list[str]) -> str:
        """Build docker kill command."""
        return f"sudo docker kill {' '.join(container_ids)}"
```

#### Option B: Create DockerCommandHelper
Create a new class for simple Docker commands that don't need the full builder pattern.

**Files to Modify:**
1. `cosmos_workflow/execution/command_builder.py` - Add new methods
2. `cosmos_workflow/api/workflow_operations.py` - Update lines 693, 723
3. `cosmos_workflow/execution/docker_executor.py` - Update lines 339, 344, 506, 526, 666

### Task 2: Add Integration Tests
**Priority:** Medium
**Estimated Time:** 1-2 hours

Create `tests/integration/test_workflow_operations_integration.py`:
- Test actual SSH connection (using test environment)
- Test kill_containers with real Docker
- Use environment variables for test server credentials
- Skip if test environment not available

### Task 3: Documentation Updates
**Priority:** Low
**Estimated Time:** 30 minutes

Update `CLAUDE.md` to add practical examples:
- How to use DockerCommandBuilder
- When to use static methods vs full builder
- Examples of each wrapper pattern

## Files to Review Before Starting

### Core Files to Understand:
1. **`CLAUDE.md`** - Project conventions and wrapper requirements (lines 117-137)
2. **`cosmos_workflow/execution/command_builder.py`** - Current DockerCommandBuilder implementation
3. **`cosmos_workflow/execution/docker_executor.py`** - Where most violations occur

### Test Files to Review:
1. **`tests/unit/api/test_workflow_operations_kill_containers.py`** - Existing unit tests
2. **`tests/unit/execution/test_docker_executor.py`** - Docker executor tests

### Architecture Files:
1. **`cosmos_workflow/api/workflow_operations.py`** - Main facade pattern
2. **`cosmos_workflow/connection/ssh_manager.py`** - SSH wrapper implementation (good example)

## Testing Strategy

### Unit Tests
- Ensure all new DockerCommandBuilder methods have unit tests
- Verify command string format is correct
- Test edge cases (empty container lists, special characters)

### Integration Tests
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("TEST_GPU_HOST"), reason="No test environment")
def test_kill_containers_integration():
    # Use real SSH connection
    # Create test container
    # Kill it
    # Verify it's gone
```

## Success Criteria
1. ✅ No raw Docker command strings in codebase
2. ✅ All Docker commands use DockerCommandBuilder or helper methods
3. ✅ Integration tests pass in test environment
4. ✅ Documentation updated with examples
5. ✅ All existing tests still pass

## Gotchas and Warnings
1. **Don't break existing tests** - The refactoring should be transparent
2. **Maintain backward compatibility** - Don't change public API signatures
3. **Follow TDD** - Write tests first for new methods
4. **Use parameterized logging** - `logger.info("%s", var)` not f-strings
5. **Context managers** - Always use `with ssh_manager:` pattern

## Implementation Order
1. Create new DockerCommandBuilder methods with tests
2. Update docker_executor.py to use new methods
3. Update workflow_operations.py to use new methods
4. Run all existing tests to ensure nothing broke
5. Add integration tests
6. Update documentation

## Questions to Consider
- Should simple commands like "docker info" warrant full builder pattern?
- Should we create a separate DockerCommandHelper for simple commands?
- Do we need integration tests for all wrapper methods or just critical ones?

## Contact
- Review the git history for `cosmos_workflow/execution/docker_executor.py` to understand evolution
- Check `ROADMAP.md` for any planned changes to Docker execution
- The pattern for SSHManager (context manager) is the gold standard - follow it