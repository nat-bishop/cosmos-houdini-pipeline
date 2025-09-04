# Implementation Plan: Testing Improvements & Code Quality

## Executive Summary
This document outlines the comprehensive plan for improving test coverage and fixing known issues following the PromptManager removal refactoring. The plan emphasizes minimal mocking, maximum use of real code, and follows testing best practices.

## Current State (Post-Refactoring)

### ✅ Completed
- **PromptManager removed**: 2,091 lines of redundant code deleted
- **Smart naming implemented**: Enhanced prompts get descriptive names from content
- **Architecture simplified**: Separated into PromptSpecManager, RunSpecManager, SchemaValidator
- **Dangerous tests removed**: Tests attempting real SSH connections deleted
- **Manual testing verified**: CLI and enhancement workflows working correctly

### 🔴 Known Issues
1. **test_completions.py**: 5 test failures due to Windows Path.exists mocking issue
2. **SSH connection tests**: 4 failures (expected - no SSH in test environment)
3. **Missing test coverage**: No proper mocked tests for upsampling smart naming

## Testing Philosophy & Principles

### Core Principles
1. **Mock only external boundaries** (SSH, Docker, remote file I/O)
2. **Use real objects for business logic** (PromptSpecManager, smart naming)
3. **Separate I/O from logic** where possible
4. **Use dependency injection** for testability
5. **Follow the test pyramid**: More unit tests, fewer integration tests

### What to Mock vs What to Keep Real
| Mock | Keep Real |
|------|-----------|
| SSH connections | PromptSpecManager |
| SFTP file transfers | DirectoryManager |
| Docker execution | Smart naming logic |
| Remote API calls | Path generation |
| Network I/O | Business validation |

## Phase 1: Smart Naming Tests (HIGH PRIORITY)

### 1.1 Unit Tests for Pure Logic
**File**: `tests/unit/workflows/test_upsample_smart_naming.py`

```python
# Example test structure
def test_smart_name_generation():
    """Test smart name generation with REAL logic."""
    # NO MOCKS - pure function test
    from cosmos_workflow.utils.smart_naming import generate_smart_name

    # Test various prompt types
    assert "foggy" in generate_smart_name("A foggy morning in mountains")
    assert "sunset" in generate_smart_name("Beautiful sunset over ocean")
    assert generate_smart_name("") == "sequence"  # fallback
```

### 1.2 Integration Tests with Minimal Mocking
```python
def test_upsampling_workflow_with_smart_names(tmp_path, monkeypatch):
    """Test the full upsampling workflow with only external mocks."""

    # Only mock external service initialization
    def mock_initialize_services(self):
        self.ssh_manager = Mock()  # Mock SSH
        self.file_transfer = Mock()  # Mock SFTP
        self.docker_executor = Mock()  # Mock Docker
        self.config_manager = ConfigManager()  # REAL config

    monkeypatch.setattr(
        UpsampleWorkflowMixin, "_initialize_services",
        mock_initialize_services
    )

    # Use REAL WorkflowOrchestrator
    orchestrator = WorkflowOrchestrator()

    # Setup mock returns for external calls ONLY
    orchestrator.file_transfer.download_file = Mock(return_value=True)
    orchestrator.docker_executor.run_command = Mock(
        return_value=(0, "Success", "")
    )

    # Create test data
    test_results = [{
        "spec_id": "test_id",
        "upsampled_prompt": "A serene misty morning with fog rolling through ancient forest paths",
        "name": "test_prompt"
    }]

    # Mock the download to return our test data
    with patch('builtins.open', mock_open(read_data=json.dumps(test_results))):
        result = orchestrator.run_prompt_upsampling([test_prompt])

    # Verify smart naming worked
    assert result["success"]
    updated_spec = result["updated_specs"][0]
    assert "misty" in updated_spec.name or "fog" in updated_spec.name
    assert updated_spec.name != "test_prompt_enhanced"  # Not old pattern
```

### 1.3 Test Coverage Goals
- [ ] Smart name generation from various prompt types
- [ ] Fallback behavior when smart naming fails
- [ ] Name uniqueness when processing multiple prompts
- [ ] Metadata preservation during upsampling
- [ ] Edge cases (empty prompts, special characters, very long prompts)

## Phase 2: Fix test_completions.py (MEDIUM PRIORITY)

### Problem Analysis
The tests create real temporary directories but then try to mock `Path.exists` which is read-only on Windows Path objects.

### Solution A: Use Real Paths (Recommended)
```python
def test_complete_all_specs(monkeypatch):
    """Test with real paths, no Path mocking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create real directory structure
        prompts_dir = Path(tmpdir) / "inputs" / "prompts"
        prompts_dir.mkdir(parents=True)

        # Create test files
        (prompts_dir / "test1.json").touch()
        (prompts_dir / "test2.json").touch()

        # Monkeypatch the function to use our temp directory
        def mock_get_prompts_dir():
            return prompts_dir

        monkeypatch.setattr(
            "cosmos_workflow.cli.completions.get_prompts_dir",
            mock_get_prompts_dir
        )

        # Test with REAL paths
        result = complete_prompt_specs(None, None, "")
        assert len(result) == 2
```

### Solution B: Refactor for Testability
Make the code more testable by accepting base paths as parameters:
```python
def complete_prompt_specs(ctx, param, incomplete, base_dir=None):
    """Enhanced with dependency injection for testability."""
    prompts_dir = Path(base_dir or "inputs/prompts")
    if not prompts_dir.exists():
        return []
    # ... rest of function
```

## Phase 3: Systematic Verification (HIGH PRIORITY)

### 3.1 Create Verification Script
**File**: `scripts/verify_refactoring.py`

```python
#!/usr/bin/env python3
"""Verification script for PromptManager removal refactoring."""

def verify_no_prompt_manager_references():
    """Ensure PromptManager is completely removed."""
    import subprocess
    result = subprocess.run(
        ["grep", "-r", "PromptManager", "cosmos_workflow/", "--include=*.py"],
        capture_output=True
    )
    assert result.returncode == 1, "Found PromptManager references!"
    print("✓ No PromptManager references found")

def verify_smart_naming_works():
    """Test smart naming end-to-end."""
    from cosmos_workflow.prompts.prompt_spec_manager import PromptSpecManager
    from cosmos_workflow.prompts.schemas import DirectoryManager
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        dir_manager = DirectoryManager(tmpdir, tmpdir)
        spec_manager = PromptSpecManager(dir_manager)

        # Create enhanced prompt
        spec = spec_manager.create_prompt_spec(
            prompt_text="A foggy morning in the mountains",
            is_upsampled=True,
            parent_prompt_text="morning"
        )

        assert "foggy" in spec.name or "morning" in spec.name
        assert spec.name != "morning_enhanced"
        print(f"✓ Smart naming works: {spec.name}")

def verify_no_duplicate_saves():
    """Ensure single file creation per enhancement."""
    # Implementation here
    print("✓ No duplicate saves detected")

if __name__ == "__main__":
    verify_no_prompt_manager_references()
    verify_smart_naming_works()
    verify_no_duplicate_saves()
    print("\n✅ All verifications passed!")
```

### 3.2 Manual Test Checklist
- [ ] `cosmos create prompt "Test" inputs/videos/test` - creates with smart name
- [ ] `cosmos prompt-enhance <file>` - enhances with smart name, no duplicates
- [ ] `cosmos status` - works without PromptManager
- [ ] All integration tests pass (except known SSH failures)

## Phase 4: Code Organization Improvements (LOW PRIORITY)

### 4.1 Extract Smart Naming Service
```python
# cosmos_workflow/services/smart_naming_service.py
class SmartNamingService:
    """Centralized smart naming logic with fallback strategies."""

    def __init__(self, max_length: int = 30):
        self.max_length = max_length
        self._name_cache = {}  # Cache for performance

    def generate_name_for_enhanced_prompt(
        self,
        enhanced_text: str,
        original_name: str = None
    ) -> str:
        """Generate smart name with intelligent fallback."""
        # Check cache
        if enhanced_text in self._name_cache:
            return self._name_cache[enhanced_text]

        # Try smart naming
        name = generate_smart_name(enhanced_text, self.max_length)

        # Fallback if needed
        if name == "sequence" and original_name:
            name = f"{original_name}_enhanced"

        # Handle duplicates
        name = self._ensure_unique_name(name)

        # Cache and return
        self._name_cache[enhanced_text] = name
        return name

    def _ensure_unique_name(self, name: str) -> str:
        """Ensure name is unique by adding suffix if needed."""
        # Implementation here
        return name
```

### 4.2 Separate I/O from Logic
```python
# cosmos_workflow/processors/upsample_processor.py
class UpsampleResultProcessor:
    """Pure logic for processing upsampling results - easily testable."""

    def process_results(
        self,
        results: list[dict],
        original_specs: list[PromptSpec],
        spec_manager: PromptSpecManager
    ) -> list[PromptSpec]:
        """Process results without any I/O operations."""
        updated_specs = []

        for result in results:
            matching_spec = self._find_matching_spec(
                result, original_specs
            )
            if matching_spec:
                updated_spec = self._create_enhanced_spec(
                    result, matching_spec, spec_manager
                )
                updated_specs.append(updated_spec)

        return updated_specs

    def _find_matching_spec(
        self,
        result: dict,
        specs: list[PromptSpec]
    ) -> PromptSpec | None:
        """Pure logic for spec matching."""
        spec_id = result.get("spec_id")
        name = result.get("name")
        return next(
            (s for s in specs if s.id == spec_id or s.name == name),
            None
        )
```

## Implementation Order & Timeline

### Week 1: Foundation
1. **Day 1-2**: Phase 3 - Systematic Verification
   - Create and run verification script
   - Manual testing checklist
   - Document any issues found

2. **Day 3-5**: Phase 1 - Smart Naming Tests
   - Write unit tests for pure logic
   - Add integration tests with minimal mocking
   - Achieve 80% coverage on new code

### Week 2: Refinement
3. **Day 6-7**: Phase 2 - Fix test_completions.py
   - Implement Solution A (real paths)
   - Fix all 5 failing tests
   - Ensure Windows compatibility

4. **Day 8-10**: Phase 4 - Code Organization (if time permits)
   - Extract SmartNamingService
   - Separate I/O from logic
   - Update documentation

## Success Metrics

### Quantitative
- ✅ 0 PromptManager references in production code
- ✅ 100% of smart naming tests passing
- ✅ 5 test_completions.py tests fixed
- ✅ <5% of code uses mocks (only external boundaries)
- ✅ Test execution time <30 seconds for unit tests

### Qualitative
- Tests clearly document behavior
- New developers can understand system from tests
- Refactoring can be done with confidence
- CI/CD pipeline is reliable and fast

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking production | Run verification script before any changes |
| Over-mocking | Review each mock - ask "is this external?" |
| Test complexity | Keep tests simple, one assertion per test |
| Windows compatibility | Test on both Linux and Windows |
| Performance regression | Add timing benchmarks to critical paths |

## Next Steps After Implementation

1. **Documentation Update**
   - Update README with new architecture
   - Add testing guide for contributors
   - Document smart naming behavior

2. **Performance Monitoring**
   - Add metrics for smart name generation time
   - Monitor file I/O patterns
   - Track test execution times

3. **Future Enhancements**
   - Consider async I/O for file operations
   - Add caching for frequently used prompts
   - Implement prompt versioning system

## Appendix: Testing Best Practices Reference

### The Test Pyramid
```
         /\
        /UI\       <- Few (slow, flaky)
       /----\
      / Intg \     <- Some (slower)
     /--------\
    /   Unit   \   <- Many (fast, reliable)
   /____________\
```

### AAA Pattern
```python
def test_example():
    # Arrange - setup test data
    data = create_test_data()

    # Act - perform the action
    result = function_under_test(data)

    # Assert - verify the outcome
    assert result == expected
```

### Mock vs Stub vs Fake
- **Mock**: Verifies interactions (was method called?)
- **Stub**: Returns canned responses (always returns X)
- **Fake**: Simplified working implementation (in-memory database)

## Document Version
- **Created**: 2025-09-03
- **Author**: Claude (with human guidance)
- **Status**: Ready for Implementation
- **Review**: Pending human approval