# Decision: Fix or Revert?

## What We Changed
In commit `e579914`, we refactored 3 test files:
1. `tests/integration/test_workflow_orchestration.py` 
2. `tests/integration/test_sftp_workflow.py`
3. `tests/unit/execution/test_docker_executor.py`

These now use `FakeWorkflowOrchestrator`, `FakeFileTransferService`, etc. instead of testing real code.

## The Problem
**These tests no longer verify your actual code works!** They only test that the fakes work.

## Option 1: REVERT (Recommended) ⭐
**Time: 2 minutes**

```bash
# Revert just the test changes from that commit
git checkout e579914~1 -- tests/integration/test_workflow_orchestration.py
git checkout e579914~1 -- tests/integration/test_sftp_workflow.py  
git checkout e579914~1 -- tests/unit/execution/test_docker_executor.py

# The old tests weren't perfect but they tested real code
```

**Pros:**
- Instant fix
- Tests will catch real bugs again
- Original tests had 97.7% pass rate (547/560)

**Cons:**
- Loses some improvements (better naming, documentation)
- Goes back to more mock usage (but testing real code)

## Option 2: FIX (More Work)
**Time: 1-2 hours**

Fix the tests to use real implementations:

```python
# Change from:
def test_workflow(fake_orchestrator):
    fake_orchestrator.run_inference("spec.json")  # Tests nothing

# To:
def test_workflow():
    orchestrator = WorkflowOrchestrator()  # Real code
    orchestrator.ssh_client = FakeSSHClient()  # Fake only externals
    orchestrator.run_inference("spec.json")  # Tests real logic
```

**Pros:**
- Keep the good parts (better structure, names)
- Learn from the experience

**Cons:**
- Takes time to fix properly
- Risk of introducing new issues
- Only 3 files were changed, not worth huge effort

## Option 3: HYBRID (Best Balance) ⭐⭐
**Time: 10 minutes**

1. Revert the 3 test files to get working tests back
2. Keep the good additions:
   - Keep `test_fake_contracts.py` (useful for validating fakes)
   - Keep the documentation files
   - Keep `FakeSSHClient`, `FakeDockerClient` for external dependencies

```bash
# Revert the test files
git checkout e579914~1 -- tests/integration/test_workflow_orchestration.py
git checkout e579914~1 -- tests/integration/test_sftp_workflow.py
git checkout e579914~1 -- tests/unit/execution/test_docker_executor.py

# Keep the fakes for external services (they're useful)
# Keep the contract tests
# Keep the documentation
```

Then gradually improve tests over time by:
- Using real implementations
- Using fakes only for SSH, Docker, filesystem

## My Recommendation: HYBRID

1. **Revert the 3 test files** - Get back to tests that work
2. **Keep the fakes** - They're useful for external dependencies  
3. **Keep contract tests** - They ensure fakes stay accurate
4. **Fix gradually** - Improve tests as you work on features

This gives you:
- Working tests immediately (catch bugs)
- Good fakes for external services
- Path to improvement without blocking progress

## Quick Test to Verify

After reverting, verify tests catch bugs:

```python
# Introduce intentional bug in WorkflowOrchestrator
# Run tests
# They should FAIL (proving they catch bugs)
# Fix bug
# Tests should PASS
```

## The Lesson

- **Fakes are good for external dependencies** (SSH, Docker, APIs)
- **Never fake your own business logic** (WorkflowOrchestrator, validators)
- **Tests must fail when code is broken** (otherwise they're useless)

## Bottom Line

**Just revert the 3 files.** The original tests weren't perfect but they actually tested your code. You can improve them gradually later, but right now you need tests that catch bugs when using AI to code fast.