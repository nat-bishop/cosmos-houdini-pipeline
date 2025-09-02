# CLI Migration Checklist
*Ready to execute - Estimated time: 1 hour*

## Pre-Migration Verification
- [ ] Confirm all tests pass with old CLI: `pytest tests/test_cli.py -q`
- [ ] Note the test count (should be 23)
- [ ] Create a git branch: `git checkout -b migrate-to-modular-cli`

## Phase 1: Switch to New CLI (5 minutes)

### Step 1: Update entry point
- [ ] Edit `cosmos_workflow/__main__.py`
- [ ] Change line 6 from:
  ```python
  from .cli import main
  ```
  To:
  ```python
  from .cli_new import main
  ```
- [ ] Save the file

### Step 2: Test the switch
- [ ] Run: `python -m cosmos_workflow --help`
- [ ] Should see help output (may have slight formatting differences)
- [ ] If error, check import path

## Phase 2: Update Tests (20 minutes)

### Step 1: Update test imports
- [ ] Edit `tests/test_cli.py`
- [ ] Change line 16 from:
  ```python
  from cosmos_workflow.cli import cli
  ```
  To:
  ```python
  from cosmos_workflow.cli_new import cli
  ```

### Step 2: Run tests and fix issues
- [ ] Run: `pytest tests/test_cli.py -v`
- [ ] Note any failures
- [ ] Common fixes:
  - [ ] Update mock paths if needed
  - [ ] Adjust for any output format differences
  - [ ] Check if module structure affects patching

### Step 3: Verify all tests pass
- [ ] Run: `pytest tests/test_cli.py -q`
- [ ] Should see 23 passed
- [ ] If not all pass, debug and fix

## Phase 3: Manual Testing (20 minutes)

### Test each command with --dry-run first:
- [ ] `python -m cosmos_workflow create prompt "test" --dry-run`
- [ ] `python -m cosmos_workflow inference dummy.json --dry-run`
- [ ] `python -m cosmos_workflow prepare ./test/ --dry-run`
- [ ] `python -m cosmos_workflow prompt-enhance test.json --dry-run`
- [ ] `python -m cosmos_workflow status`

### Verify help works:
- [ ] `python -m cosmos_workflow --help`
- [ ] `python -m cosmos_workflow create --help`
- [ ] `python -m cosmos_workflow inference --help`

## Phase 4: Reorganize Files (10 minutes)

### Step 1: Backup old CLI
- [ ] Run: `git mv cosmos_workflow/cli.py cosmos_workflow/cli_old.py`

### Step 2: Rename new CLI directory
- [ ] Run: `git mv cosmos_workflow/cli_new cosmos_workflow/cli`

### Step 3: Update imports
- [ ] Edit `cosmos_workflow/__main__.py`
- [ ] Change from `.cli_new` to `.cli`
- [ ] Edit `tests/test_cli.py`
- [ ] Change from `.cli_new` to `.cli`

### Step 4: Test again
- [ ] Run: `pytest tests/test_cli.py -q`
- [ ] Run: `python -m cosmos_workflow --help`

## Phase 5: Cleanup (5 minutes)

### Remove old code (only after confirming everything works)
- [ ] Run: `git rm cosmos_workflow/cli_old.py`
- [ ] Commit: `git add -A && git commit -m "refactor: migrate to modular CLI structure"`

## Post-Migration Verification

### Final checks:
- [ ] All 23 tests pass
- [ ] Help command works
- [ ] Each command works with --dry-run
- [ ] No import errors

### Documentation updates:
- [ ] Update CHANGELOG.md with migration details
- [ ] Update README.md if CLI usage changed
- [ ] Delete temporary migration documents

## Rollback Plan (if needed)

If something goes wrong:
1. Git reset: `git reset --hard HEAD`
2. Or checkout main: `git checkout main`
3. Review what went wrong
4. Try again with fixes

## Success Criteria

✅ All tests pass (23/23)
✅ All commands work
✅ --dry-run prevents execution
✅ Help displays correctly
✅ No regression in functionality

## Notes

- The new CLI has better display formatting (Rich tables)
- --dry-run output may look different but should show same info
- Error messages might be slightly different
- The modular structure makes debugging easier

---

## Quick Test Commands (for copy-paste)

```bash
# Test suite
pytest tests/test_cli.py -q

# Quick smoke test
python -m cosmos_workflow --version
python -m cosmos_workflow --help
python -m cosmos_workflow status

# Dry run tests
echo '{"prompt": "test", "name": "test"}' > test_spec.json
python -m cosmos_workflow inference test_spec.json --dry-run
rm test_spec.json
```
