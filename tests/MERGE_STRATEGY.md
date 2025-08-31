# Merge Strategy for Parallel Development
## Test Refactoring Branch + Prompt Upsampler Branch

## 🎯 Goal
Ensure seamless merge of test refactoring changes with prompt upsampler development

## 📋 Current Situation
- **This Branch**: Test refactoring (minimal production code changes)
- **Other Branch**: Prompt upsampler feature (production code changes)
- **Overlap Risk**: Low to Medium (tests may call upsampler code)

## 🛡️ Strategies for Seamless Merging

### 1. **Keep Production Code Changes Minimal Here**
```bash
# Before making any production code changes, ask:
# "Is this change ONLY to make tests pass?"
# If yes -> Make the change
# If no -> Document it for later

# Track any production changes you make:
git diff --name-only cosmos_workflow/ | grep -v test > production_changes.txt
```

### 2. **Document Interface Assumptions**
Create a file to track what interfaces your tests expect:

```python
# tests/INTERFACE_ASSUMPTIONS.md
## Interfaces Our Tests Assume:

### PromptUpsampler
- Method: `upsample_prompt(prompt: str, config: dict) -> str`
- Returns: Enhanced prompt string
- Raises: ValueError if prompt is empty

### WorkflowOrchestrator
- Method: `run_prompt_upsampling(spec_file: str) -> bool`
- Returns: Success boolean
- Side effect: Creates upsampled_prompt.json
```

### 3. **Use Feature Flags in Tests**
Make tests adaptable to both branches:

```python
# tests/fixtures/fakes.py
class FakeWorkflowOrchestrator:
    def __init__(self, config=None):
        self.config = config
        # Feature flag for prompt upsampling
        self.prompt_upsampling_enabled = getattr(
            config, 'prompt_upsampling_enabled', False
        )

    def run_prompt_upsampling(self, spec_file: str) -> bool:
        """Stub for prompt upsampling - will work regardless of implementation."""
        if not self.prompt_upsampling_enabled:
            # Return success but do nothing (for test branch)
            return True

        # When merged, this will do actual upsampling simulation
        self.workflows_run.append({
            "type": "prompt_upsampling",
            "spec": spec_file,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        return True
```

### 4. **Create Adapter Pattern for New Features**
Instead of directly calling prompt upsampler methods in tests:

```python
# tests/fixtures/adapters.py
class PromptUpsamplerAdapter:
    """Adapter to handle differences between branches."""

    @staticmethod
    def get_upsampler():
        try:
            # Try to import the real upsampler (other branch)
            from cosmos_workflow.prompts.prompt_upsampler import PromptUpsampler
            return PromptUpsampler()
        except ImportError:
            # Fall back to fake (this branch)
            return FakePromptUpsampler()

    @staticmethod
    def upsample_prompt(prompt: str, **kwargs):
        upsampler = PromptUpsamplerAdapter.get_upsampler()
        if hasattr(upsampler, 'upsample_prompt'):
            return upsampler.upsample_prompt(prompt, **kwargs)
        else:
            # Fallback behavior
            return f"[UPSAMPLED] {prompt}"
```

### 5. **Keep Test Data Independent**
Don't use test data that depends on upsampler implementation:

```python
# BAD - Depends on specific upsampler output
def test_workflow_with_upsampling():
    result = orchestrator.run_upsampling("prompt.json")
    assert "detailed cosmic scene with stars" in result  # Too specific!

# GOOD - Tests behavior, not specific output
def test_workflow_with_upsampling():
    result = orchestrator.run_upsampling("prompt.json")
    assert result is not None  # Output exists
    assert len(result) > len(original_prompt)  # Output is enhanced
    assert isinstance(result, str)  # Output is correct type
```

### 6. **Add Merge Preparation Tests**
Create tests that will help detect merge conflicts early:

```python
# tests/integration/test_merge_compatibility.py
"""Tests to ensure branches can merge safely."""

import pytest
import importlib
import inspect

class TestMergeCompatibility:

    def test_critical_interfaces_exist(self):
        """Verify critical interfaces exist (won't break on merge)."""
        critical_modules = [
            "cosmos_workflow.workflows.workflow_orchestrator",
            "cosmos_workflow.connection.ssh_manager",
            "cosmos_workflow.execution.docker_executor",
        ]

        for module_name in critical_modules:
            try:
                module = importlib.import_module(module_name)
                assert module is not None
            except ImportError:
                pytest.skip(f"Module {module_name} not yet implemented")

    def test_no_conflicting_test_names(self):
        """Ensure no duplicate test names that would conflict."""
        import os
        test_names = set()

        for root, dirs, files in os.walk("tests/"):
            for file in files:
                if file.startswith("test_") and file.endswith(".py"):
                    if file in test_names:
                        pytest.fail(f"Duplicate test file: {file}")
                    test_names.add(file)
```

### 7. **Version Your Fakes**
Add version info to track compatibility:

```python
# tests/fixtures/fakes.py
FAKE_VERSION = "2.0.0"  # Bump when interface changes
COMPATIBLE_WITH = ["cosmos_workflow>=1.0.0"]

class FakeSSHManager:
    """Fake SSH Manager v2.0.0 - Compatible with cosmos_workflow 1.0.0+"""

    @classmethod
    def version_info(cls):
        return {
            "fake_version": FAKE_VERSION,
            "compatible_with": COMPATIBLE_WITH,
            "has_upsampling_support": False  # Will be True after merge
        }
```

## 🔄 Pre-Merge Checklist

Before merging, run this checklist:

```bash
#!/bin/bash
# pre_merge_check.sh

echo "=== Pre-Merge Compatibility Check ==="

# 1. Check for production code changes
echo "1. Production changes in test branch:"
git diff main --name-only -- cosmos_workflow/ | grep -v test

# 2. Check for conflicting test files
echo "2. Modified test files:"
git diff main --name-only -- tests/

# 3. Run tests with mock upsampler
echo "3. Testing with mock upsampler:"
MOCK_UPSAMPLER=true pytest tests/ -q

# 4. Check interface assumptions
echo "4. Checking interface contracts:"
pytest tests/contracts/ -q

# 5. Look for hardcoded paths/assumptions
echo "5. Hardcoded assumptions:"
grep -r "prompt_upsampl" tests/ --include="*.py" | grep -v "^#"

echo "=== Check Complete ==="
```

## 🎯 Specific Tips for Prompt Upsampler Integration

### 1. **Keep Upsampler Tests Isolated**
```python
# tests/unit/prompts/test_prompt_upsampler.py
@pytest.mark.upsampler  # Tag for easy identification
class TestPromptUpsampler:
    """Tests specific to prompt upsampler - separate from workflow tests."""
```

### 2. **Make Fakes Upsampler-Aware but Not Dependent**
```python
class FakeWorkflowOrchestrator:
    def run_inference(self, spec_file: str, **kwargs):
        # Check if upsampling requested but don't require it
        if kwargs.get('upsample_prompt', False):
            if hasattr(self, 'upsample_prompt'):
                # Use upsampler if available
                self.upsample_prompt(spec_file)
            else:
                # Continue without upsampling
                pass

        # Rest of inference logic
        return True
```

### 3. **Use Environment Variables for Feature Detection**
```python
# tests/conftest.py
import os

@pytest.fixture
def upsampler_available():
    """Check if prompt upsampler is available."""
    if os.getenv("FORCE_MOCK_UPSAMPLER"):
        return False

    try:
        from cosmos_workflow.prompts import PromptUpsampler
        return True
    except ImportError:
        return False

# Use in tests:
def test_workflow_with_optional_upsampling(upsampler_available):
    if not upsampler_available:
        pytest.skip("Prompt upsampler not available")
```

## 🚦 Git Strategy

### Branch Management
```bash
# Keep branches updated without merging
# In test branch:
git fetch origin
git rebase origin/main  # Stay current with main

# In upsampler branch:
git fetch origin
git rebase origin/main  # Stay current with main

# Don't merge branches into each other yet!
```

### Commit Strategy
```bash
# Make atomic commits that are easy to cherry-pick
git add tests/fixtures/fakes.py
git commit -m "test: Add ensure_connected to FakeSSHManager"

git add tests/contracts/
git commit -m "test: Add contract tests for fakes"

# Use conventional commits:
# test: Changes to tests only
# fix: Bug fixes
# feat: New features
# refactor: Code restructuring
```

## 📝 Communication Protocol

### Document Changes That Affect the Other Branch
```markdown
# CROSS_BRANCH_NOTES.md

## Changes in Test Branch that Affect Upsampler:
1. FakeWorkflowOrchestrator now has run_prompt_upsampling stub
2. Tests expect upsample_prompt to return string (not dict)

## Changes Upsampler Branch Should Know:
1. New contract tests will verify interface compatibility
2. Fakes need updating when new methods added
```

## 🎁 Benefits of This Approach

1. **No Merge Conflicts**: Minimal overlapping changes
2. **Tests Stay Green**: Tests work in both branches
3. **Easy Integration**: Fakes adapt to presence/absence of features
4. **Clear Boundaries**: Each branch owns its domain
5. **Traceable Changes**: Easy to see what each branch modified

## 🔮 Post-Merge Plan

After merging:
1. Run full test suite
2. Update fakes to use real upsampler interfaces
3. Remove feature flags and adapters
4. Update contract tests with new interfaces
5. Document the integrated behavior

## Quick Reference Card

```bash
# Daily checks to maintain merge compatibility:

# 1. Check you haven't modified production code unnecessarily
git status cosmos_workflow/

# 2. Run contract tests to ensure interfaces match
pytest tests/contracts/ -q

# 3. Check your tests work with minimal mocking
MOCK_UPSAMPLER=true pytest tests/ -q --tb=no

# 4. Keep your branch updated with main (not the other feature branch)
git fetch && git rebase origin/main
```
