# Test Improvement Tasks & Validation Strategies

## 🔍 Areas for Improvement & Validation

### 1. **Mutation Testing** - Verify Test Effectiveness
Run mutation testing to ensure tests actually catch bugs:

```bash
# Install mutmut for Python mutation testing
pip install mutmut

# Run mutation testing on refactored tests
mutmut run --paths-to-mutate cosmos_workflow/workflows/workflow_orchestrator.py \
           --tests-dir tests/integration/test_workflow_orchestration.py

# Check which mutations survived (tests didn't catch)
mutmut results

# HTML report showing what tests missed
mutmut html
```

**What to look for:**
- If many mutations survive, tests might be checking the wrong things
- Good tests should kill 80%+ of mutations
- Surviving mutations show gaps in test coverage

### 2. **Contract Testing** - Ensure Fakes Match Reality
Create contract tests that verify fakes behave like real implementations:

```python
# tests/contracts/test_fake_contracts.py
"""Verify that fakes maintain the same contracts as real implementations."""

import pytest
from tests.fixtures.fakes import FakeSSHManager, FakeDockerExecutor
from cosmos_workflow.connection.ssh_manager import SSHManager
from cosmos_workflow.execution.docker_executor import DockerExecutor

class TestFakeContracts:
    """Ensure fakes have same interface as real implementations."""

    def test_fake_ssh_manager_has_all_methods(self):
        """FakeSSHManager should have all public methods of SSHManager."""
        real_methods = {m for m in dir(SSHManager) if not m.startswith('_')}
        fake_methods = {m for m in dir(FakeSSHManager) if not m.startswith('_')}

        missing = real_methods - fake_methods
        assert not missing, f"FakeSSHManager missing methods: {missing}"

    def test_fake_docker_executor_signatures_match(self):
        """Method signatures should match between fake and real."""
        import inspect

        real_sig = inspect.signature(DockerExecutor.run_inference)
        fake_sig = inspect.signature(FakeDockerExecutor.run_inference)

        # Compare parameters (excluding self)
        real_params = list(real_sig.parameters.keys())[1:]
        fake_params = list(fake_sig.parameters.keys())[1:]

        assert real_params == fake_params, "Signature mismatch"
```

### 3. **Property-Based Testing** - Test Invariants
Add property tests to verify system invariants:

```python
# tests/properties/test_workflow_properties.py
from hypothesis import given, strategies as st
import pytest
from tests.fixtures.fakes import FakeWorkflowOrchestrator

class TestWorkflowProperties:
    @given(
        num_gpus=st.integers(min_value=1, max_value=8),
        num_runs=st.integers(min_value=1, max_value=10)
    )
    def test_workflow_history_preserves_order(self, num_gpus, num_runs):
        """Workflow history should preserve chronological order."""
        orchestrator = FakeWorkflowOrchestrator()

        for i in range(num_runs):
            orchestrator.run_inference(f"spec_{i}.json", num_gpus=num_gpus)

        # Property: timestamps should be monotonically increasing
        timestamps = [w["timestamp"] for w in orchestrator.workflows_run]
        assert timestamps == sorted(timestamps)

    @given(st.lists(st.text(min_size=1), min_size=1))
    def test_file_upload_idempotency(self, filenames):
        """Uploading same file multiple times should be safe."""
        from tests.fixtures.fakes import FakeFileTransferService
        transfer = FakeFileTransferService()

        for name in filenames:
            # Property: multiple uploads don't corrupt state
            for _ in range(3):
                try:
                    transfer.upload_file(Path(name), "/remote")
                except FileNotFoundError:
                    pass  # Expected for non-existent files

        # State should be consistent
        assert len(transfer.uploaded_files) >= 0
```

### 4. **Fault Injection Testing** - Test Error Handling
Enhance fakes to simulate failures:

```python
# tests/fixtures/enhanced_fakes.py
class FakeSSHManagerWithFailures(FakeSSHManager):
    """Enhanced fake that can simulate failures."""

    def __init__(self):
        super().__init__()
        self.failure_mode = None
        self.failure_count = 0

    def set_failure_mode(self, mode: str, count: int = 1):
        """Configure failure simulation."""
        self.failure_mode = mode
        self.failure_count = count

    def execute_command(self, command: str):
        if self.failure_mode == "timeout" and self.failure_count > 0:
            self.failure_count -= 1
            raise TimeoutError("SSH command timed out")
        elif self.failure_mode == "connection" and self.failure_count > 0:
            self.failure_count -= 1
            raise ConnectionError("SSH connection lost")

        return super().execute_command(command)

# Use in tests:
def test_workflow_handles_transient_ssh_failures():
    ssh = FakeSSHManagerWithFailures()
    ssh.set_failure_mode("timeout", count=2)  # Fail first 2 attempts

    orchestrator = FakeWorkflowOrchestrator(ssh_manager=ssh)
    # Should retry and eventually succeed
    result = orchestrator.run_inference("spec.json", retry=True)
    assert result is True
```

### 5. **Performance Regression Testing**
Track that tests remain fast:

```python
# tests/test_performance.py
import time
import pytest

@pytest.mark.performance
class TestPerformance:
    def test_fake_operations_are_fast(self):
        """Fakes should be much faster than real operations."""
        from tests.fixtures.fakes import FakeWorkflowOrchestrator

        orchestrator = FakeWorkflowOrchestrator()

        start = time.time()
        for _ in range(100):
            orchestrator.run_inference("spec.json")
        duration = time.time() - start

        # 100 fake operations should complete in < 1 second
        assert duration < 1.0, f"Fakes too slow: {duration}s for 100 ops"
```

### 6. **Test Coverage Gaps Analysis**
Find untested code paths:

```bash
# Generate detailed coverage report
pytest tests/ --cov=cosmos_workflow \
              --cov-report=html \
              --cov-report=term-missing \
              --cov-branch

# Look for:
# - Uncovered error handling paths
# - Untested edge cases
# - Missing boundary conditions

# Generate coverage diff between old and new tests
pytest tests/integration/test_workflow_orchestration.py \
       --cov=cosmos_workflow.workflows \
       --cov-report=json:new_coverage.json

# Compare coverage metrics
```

### 7. **Behavior Verification Completeness**
Audit what behaviors aren't being tested:

```python
# tests/audit/test_behavior_coverage.py
"""Audit which behaviors are tested."""

class BehaviorCoverageAudit:
    """Track which behaviors are covered by tests."""

    EXPECTED_BEHAVIORS = {
        "WorkflowOrchestrator": [
            "handles_missing_input_files",
            "validates_prompt_spec_format",
            "respects_gpu_limits",
            "cleans_up_on_failure",
            "preserves_partial_results",
            "handles_network_interruption",
            "supports_resume_from_checkpoint",
            "validates_output_permissions",
        ],
        "DockerExecutor": [
            "enforces_memory_limits",
            "handles_container_crash",
            "cleans_up_orphaned_containers",
            "validates_docker_daemon_running",
            "handles_image_pull_failure",
        ],
        "FileTransferService": [
            "handles_partial_uploads",
            "validates_checksums",
            "handles_disk_full",
            "supports_resume_transfer",
            "handles_permission_denied",
        ]
    }

    def test_behavior_coverage_audit(self):
        """Generate report of untested behaviors."""
        import ast
        import inspect

        # Parse test files to find what's tested
        tested_behaviors = set()

        # ... parse test files and extract tested behaviors ...

        # Report gaps
        for component, behaviors in self.EXPECTED_BEHAVIORS.items():
            untested = set(behaviors) - tested_behaviors
            if untested:
                print(f"\n{component} - Untested behaviors:")
                for behavior in untested:
                    print(f"  - {behavior}")
```

### 8. **Integration Test Scenarios**
Create end-to-end scenarios with fakes:

```python
# tests/scenarios/test_realistic_workflows.py
class TestRealisticScenarios:
    """Test complete user journeys with fakes."""

    def test_typical_user_workflow(self):
        """Simulate typical user's complete workflow."""
        # 1. User uploads prompt
        # 2. System validates
        # 3. Transfers files
        # 4. Runs inference
        # 5. Handles partial failure
        # 6. Retries
        # 7. Downloads results

    def test_stress_scenario_many_parallel_jobs(self):
        """Simulate many parallel jobs."""
        orchestrators = [FakeWorkflowOrchestrator() for _ in range(10)]
        # Run parallel workflows and verify isolation

    def test_failure_recovery_scenario(self):
        """Test complete failure and recovery."""
        # Simulate failures at each stage
        # Verify system recovers gracefully
```

### 9. **Test Maintenance Metrics**
Track if tests are actually easier to maintain:

```bash
# Create metrics tracking script
cat > tests/track_metrics.sh << 'EOF'
#!/bin/bash
echo "Test Maintenance Metrics"
echo "========================"
echo ""
echo "Lines of test code:"
wc -l tests/**/*.py | tail -1

echo ""
echo "Mock usage:"
grep -r "mock\|Mock\|patch" tests/ --include="*.py" | wc -l

echo ""
echo "Behavior assertions:"
grep -r "assert\|Verify\|Check" tests/ --include="*.py" | wc -l

echo ""
echo "Test execution time:"
time pytest tests/ -q

echo ""
echo "Test changes in last month:"
git log --since="1 month ago" --oneline -- tests/ | wc -l
EOF

chmod +x tests/track_metrics.sh
```

### 10. **Documentation Testing**
Ensure test documentation matches reality:

```python
# tests/test_documentation.py
def test_readme_examples_work():
    """Verify that examples in documentation actually work."""
    import subprocess
    import re

    # Extract code examples from README
    with open("tests/BEHAVIOR_TESTING_GUIDE.md") as f:
        content = f.read()

    # Find code blocks
    code_blocks = re.findall(r'```python\n(.*?)\n```', content, re.DOTALL)

    for code in code_blocks:
        # Try to execute the code
        try:
            exec(code)
        except NameError:
            pass  # Expected for incomplete examples
        except SyntaxError as e:
            pytest.fail(f"Documentation has invalid Python: {e}")
```

## 🎯 Priority Tasks

### Immediate (Do First)
1. **Run mutation testing** on the 3 refactored files - reveals if tests actually catch bugs
2. **Create contract tests** - ensure fakes match real implementations
3. **Add fault injection** to fakes - test error handling paths

### Short Term (This Week)
4. **Property-based tests** - verify invariants hold
5. **Coverage gap analysis** - find untested behaviors
6. **Performance benchmarks** - ensure tests stay fast

### Ongoing
7. **Track metrics** - monitor if maintenance improves
8. **Scenario tests** - realistic user journeys
9. **Documentation tests** - keep examples working

## 📊 Success Metrics

Track these metrics over time:

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Mutation Score | >80% | `mutmut run` |
| Behavior Coverage | >90% | Custom audit script |
| Test Speed | <10s for unit | `pytest -m unit --durations=10` |
| Maintenance Time | <30min/bug | Track time to fix test failures |
| False Positives | <5% | Track tests that fail without code bugs |

## 🔧 Tooling Setup

```bash
# Install testing tools
pip install mutmut hypothesis pytest-timeout pytest-benchmark

# Run continuous validation
watch -n 60 'pytest tests/ -x --lf'  # Re-run failed tests

# Monitor test performance
pytest tests/ --durations=10  # Show 10 slowest tests
```

## 💡 Key Validation: The Refactoring Test

The ultimate test of your test suite:

1. **Make a significant refactoring** to the production code
2. **Run the tests** - they should still pass if behavior unchanged
3. **Introduce a behavior change** - tests should fail
4. **Fix the behavior** - tests should pass again

If this cycle works smoothly, your tests are effective!
