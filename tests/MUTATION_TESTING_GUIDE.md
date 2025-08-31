# Mutation Testing Setup Guide

## 🎯 Purpose
Mutation testing verifies that your tests actually catch bugs by introducing small changes (mutations) to the code and checking if tests fail.

## 📋 Prerequisites
```bash
# Install mutation testing tool
pip install mutmut

# Verify installation
mutmut --version
```

## 🚀 Quick Start

### 1. Run Mutation Testing on Refactored Tests

#### Test the Workflow Orchestrator
```bash
# Run mutations on workflow orchestrator with specific test file
mutmut run \
    --paths-to-mutate cosmos_workflow/workflows/workflow_orchestrator.py \
    --tests-dir tests/integration/ \
    --runner "python -m pytest tests/integration/test_workflow_orchestration.py -x -q"

# View results
mutmut results
```

#### Test the Docker Executor
```bash
# Run mutations on docker executor
mutmut run \
    --paths-to-mutate cosmos_workflow/execution/docker_executor.py \
    --tests-dir tests/unit/execution/ \
    --runner "python -m pytest tests/unit/execution/test_docker_executor.py -x -q"

# Show surviving mutations
mutmut show
```

#### Test File Transfer Service
```bash
# Run mutations on file transfer
mutmut run \
    --paths-to-mutate cosmos_workflow/transfer/file_transfer.py \
    --tests-dir tests/integration/ \
    --runner "python -m pytest tests/integration/test_sftp_workflow.py -x -q"
```

### 2. Interpret Results

```bash
# Check summary
mutmut results

# Example output:
# Killed 45 out of 52 mutants
# 7 mutants survived
# Mutation score: 86.5%
```

**Score Interpretation:**
- **>90%**: Excellent - tests catch most bugs
- **75-90%**: Good - some gaps but acceptable
- **<75%**: Needs improvement - tests miss many bugs

### 3. Investigate Surviving Mutants

```bash
# List all surviving mutants
mutmut results --show-surviving

# Show specific mutant details
mutmut show 1  # Shows mutant #1

# Apply a mutant to see why it survives
mutmut apply 1
pytest tests/integration/test_workflow_orchestration.py -xvs
git checkout .  # Revert the mutation
```

## 📊 Batch Testing All Refactored Components

```bash
#!/bin/bash
# mutation_test_all.sh

echo "=== Mutation Testing for Refactored Tests ==="
echo ""

# Clean previous results
rm -f .mutmut-cache

# Test each component
components=(
    "cosmos_workflow/workflows/workflow_orchestrator.py:tests/integration/test_workflow_orchestration.py"
    "cosmos_workflow/execution/docker_executor.py:tests/unit/execution/test_docker_executor.py"
    "cosmos_workflow/transfer/file_transfer.py:tests/integration/test_sftp_workflow.py"
)

for component in "${components[@]}"; do
    IFS=':' read -r source_file test_file <<< "$component"
    echo "Testing: $source_file"

    mutmut run \
        --paths-to-mutate "$source_file" \
        --runner "python -m pytest $test_file -x -q" \
        --no-progress \
        > /dev/null 2>&1

    echo "Results for $source_file:"
    mutmut results | head -3
    echo ""
done

echo "=== Overall Results ==="
mutmut results
```

## 🔍 Common Mutations and What They Test

### 1. **Operator Mutations**
```python
# Original
if x > 5:
# Mutation
if x >= 5:  # Tests boundary conditions
```

### 2. **Return Value Mutations**
```python
# Original
return True
# Mutation
return False  # Tests that return values matter
```

### 3. **Constant Mutations**
```python
# Original
timeout = 30
# Mutation
timeout = 31  # Tests that constants are used correctly
```

## 🎯 Focus Areas for Our Refactored Tests

### High Priority Mutations to Check:

1. **Workflow Orchestrator**
   - Connection state checks
   - Return values (True/False)
   - GPU count boundaries
   - File existence checks

2. **Docker Executor**
   - Container run tracking
   - Status dictionary keys
   - Path construction
   - Error conditions

3. **File Transfer**
   - Upload/download success indicators
   - File existence validation
   - Path manipulation
   - Error handling

## 📈 Improving Mutation Score

If mutations survive, add tests for:

### Example: Surviving Boundary Mutation
```python
# If this mutation survives:
# Original: if len(files) > 0:
# Mutation: if len(files) >= 0:

# Add this test:
def test_empty_files_list_handling():
    """Test behavior with exactly zero files."""
    result = transfer.upload_files([])  # Empty list
    assert result is False  # Should fail or skip
```

### Example: Surviving Return Value
```python
# If this mutation survives:
# Original: return workflow_succeeded
# Mutation: return True

# Add this test:
def test_workflow_failure_returns_false():
    """Test that failed workflows return False."""
    orchestrator.ssh_manager.disconnect()  # Force failure
    result = orchestrator.run_inference("spec.json")
    assert result is False  # Must detect failure
```

## 🚨 Important Notes

### Performance Considerations
- Mutation testing is SLOW (can take hours for large codebases)
- Start with single files, not entire packages
- Use `--no-progress` for CI/CD environments
- Consider using `--simple-output` for scripts

### Best Practices
1. **Run on critical code first** - Start with most important modules
2. **Fix high-value mutations** - Don't aim for 100%, aim for meaningful coverage
3. **Use in CI sparingly** - Run weekly, not on every commit
4. **Cache results** - `.mutmut-cache` speeds up subsequent runs

### Excluding Code from Mutation
```python
# Add pragma comment to exclude line from mutation
result = True  # pragma: no mutate

# Or exclude entire functions
def debug_function():  # pragma: no mutate
    pass
```

## 🔄 Continuous Integration Setup

```yaml
# .github/workflows/mutation-test.yml
name: Mutation Testing

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly on Sunday

jobs:
  mutmut:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install mutmut

      - name: Run mutation testing
        run: |
          mutmut run \
            --paths-to-mutate cosmos_workflow/ \
            --tests-dir tests/ \
            --runner "python -m pytest -x -q" \
            --no-progress

      - name: Generate report
        run: |
          mutmut results
          mutmut html

      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: mutation-report
          path: html/
```

## 📝 Session Recovery

If mutation testing is interrupted:

```bash
# Resume from where it stopped
mutmut run --rerun

# Or check current status
mutmut results

# Clean and start fresh
rm .mutmut-cache
mutmut run
```

## 🎯 Target Metrics

For the refactored tests, aim for:
- **Mutation Score**: >85%
- **Runtime**: <10 minutes per module
- **False Positives**: <5% (mutations that don't represent real bugs)

## 💡 Quick Commands Reference

```bash
# Run mutations on specific file
mutmut run --paths-to-mutate <file.py>

# Show results summary
mutmut results

# Show surviving mutants
mutmut show

# Apply specific mutant for debugging
mutmut apply <id>

# Generate HTML report
mutmut html

# Clean cache and start fresh
rm .mutmut-cache
```

## 🔗 Resources
- [Mutmut Documentation](https://mutmut.readthedocs.io/)
- [Mutation Testing Concepts](https://en.wikipedia.org/wiki/Mutation_testing)
- [Improving Test Quality with Mutations](https://testdriven.io/blog/mutation-testing-python/)
