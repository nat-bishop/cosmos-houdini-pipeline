# CLI Migration Plan - Complete Action Plan
*Ready to Execute - Total Time: ~1 hour*

## 🎯 Migration Objective
Switch from monolithic `cli.py` (800+ lines) to modular `cli_new/` structure that's already built and feature-complete.

## ✅ Pre-Migration Status Check

### Good News - No Work Needed!
After investigation, the new CLI (`cli_new/`) already has:
- ✅ Full --dry-run implementation on all commands
- ✅ Better display formatting with Rich tables
- ✅ Consistent error handling
- ✅ All commands implemented (create, inference, prepare, enhance, status)
- ✅ Clean modular structure

### What Actually Needs Doing
1. Switch application to use new CLI (change 2 imports)
2. Update tests to import from new location
3. Rename directories for clarity
4. Delete old code

---

## 📋 Phase-by-Phase Migration Plan

### Phase 0: Backup Current State (5 minutes)
```bash
# Create a new branch for safety
git checkout -b migrate-to-modular-cli

# Verify current tests pass
pytest tests/test_cli.py -q --tb=no
# Should show: 23 passed

# Make a note of current functionality
python -m cosmos_workflow --help > old_cli_help.txt
```

### Phase 1: Switch to New CLI (10 minutes)

#### Step 1.1: Update Main Entry Point
```python
# Edit cosmos_workflow/__main__.py
# Change line 6:
from .cli import main
# To:
from .cli_new import main
```

#### Step 1.2: Quick Smoke Test
```bash
# Test that it runs
python -m cosmos_workflow --help
python -m cosmos_workflow --version

# If any errors, check import paths
```

### Phase 2: Update Tests (20 minutes)

#### Step 2.1: Update Test Imports
```python
# Edit tests/test_cli.py
# Change line 16:
from cosmos_workflow.cli import cli
# To:
from cosmos_workflow.cli_new import cli
```

#### Step 2.2: Run Tests and Fix Issues
```bash
# Run tests
pytest tests/test_cli.py -v --tb=short

# Expected issues and fixes:
# - Mock paths may need updating
# - Output format might differ slightly (Rich vs plain text)
```

#### Step 2.3: Ensure All Tests Pass
```bash
pytest tests/test_cli.py -q --tb=no
# Must show: 23 passed
```

### Phase 3: Manual Verification (15 minutes)

#### Test Each Command with --dry-run
```bash
# Create test prompt
echo '{"prompt": "test", "name": "test", "input_video_path": "test.mp4"}' > test_spec.json

# Test inference --dry-run
python -m cosmos_workflow inference test_spec.json --dry-run

# Test prepare --dry-run
python -m cosmos_workflow prepare ./some_dir --dry-run

# Test enhance --dry-run
python -m cosmos_workflow prompt-enhance test_spec.json --dry-run

# Test create prompt
python -m cosmos_workflow create prompt "A beautiful scene" --dry-run

# Test status (no --dry-run needed)
python -m cosmos_workflow status

# Cleanup
rm test_spec.json
```

### Phase 4: Reorganize Directory Structure (10 minutes)

#### Step 4.1: Rename Old CLI (Backup)
```bash
git mv cosmos_workflow/cli.py cosmos_workflow/cli_old.py
```

#### Step 4.2: Rename New CLI to Standard Name
```bash
git mv cosmos_workflow/cli_new cosmos_workflow/cli
```

#### Step 4.3: Update Imports Again
```python
# Edit cosmos_workflow/__main__.py
# Change:
from .cli_new import main
# To:
from .cli import main

# Edit tests/test_cli.py
# Change:
from cosmos_workflow.cli_new import cli
# To:
from cosmos_workflow.cli import cli
```

#### Step 4.4: Final Test
```bash
pytest tests/test_cli.py -q --tb=no
python -m cosmos_workflow --help
```

### Phase 5: Cleanup & Commit (5 minutes)

#### Step 5.1: Remove Old Code
```bash
# Only after everything works!
git rm cosmos_workflow/cli_old.py
```

#### Step 5.2: Update Documentation
```bash
# Update CHANGELOG.md with entry about migration
# Delete temporary migration docs (optional, or move to docs/_archive/)
```

#### Step 5.3: Commit Changes
```bash
git add -A
git commit -m "refactor: migrate to modular CLI structure

- Switch from 800+ line monolithic cli.py to modular cli/ directory
- Maintain 100% backward compatibility
- All 23 tests passing
- Improved display with Rich formatting
- Better code organization (max 217 lines per file vs 800+)"

git push origin migrate-to-modular-cli
```

---

## 🔍 Verification Checklist

### Functionality Tests
- [ ] `--help` works for main command
- [ ] `--help` works for each subcommand
- [ ] `--version` displays version
- [ ] `--verbose` flag works
- [ ] All --dry-run flags prevent execution
- [ ] All --dry-run flags show preview info

### Command Tests
- [ ] `create prompt` works
- [ ] `create run` works (if implemented)
- [ ] `inference` works with --dry-run
- [ ] `prepare` works with --dry-run
- [ ] `prompt-enhance` works with --dry-run
- [ ] `status` connects and shows info

### Test Suite
- [ ] All 23 tests pass
- [ ] No deprecation warnings
- [ ] No import errors

---

## 🚨 Rollback Plan

If anything goes wrong:

### Quick Rollback
```bash
# Reset all changes
git reset --hard HEAD
git checkout main
```

### Selective Rollback
```bash
# Just revert the imports
# Edit cosmos_workflow/__main__.py back to:
from .cli import main

# Edit tests/test_cli.py back to:
from cosmos_workflow.cli import cli
```

---

## 📊 Success Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Max file size | 800+ lines | 217 lines | ✅ |
| Test coverage | 100% | 100% | ✅ |
| Test count | 23 | 23 | ✅ |
| Commands | 6 | 6 | ✅ |
| --dry-run | All commands | All commands | ✅ |

---

## 🎉 Post-Migration Benefits

### Immediate
- 76% reduction in max file size
- Better display formatting (Rich tables)
- Cleaner code organization
- Easier debugging

### Future
- Easier to add new commands
- Simpler to test individual modules
- Better for new contributors
- Ready for further enhancements

---

## ⏱️ Timeline

| Phase | Task | Duration |
|-------|------|----------|
| 0 | Backup | 5 min |
| 1 | Switch to new CLI | 10 min |
| 2 | Update tests | 20 min |
| 3 | Manual verification | 15 min |
| 4 | Reorganize | 10 min |
| 5 | Cleanup & commit | 5 min |
| **Total** | **Complete Migration** | **~65 minutes** |

---

## 📝 Important Notes

1. **The new CLI is already feature-complete** - no need to port --dry-run
2. **Only 2 files need import changes** - very low risk
3. **Keep old CLI as backup** until fully verified
4. **Tests might need minor adjustments** for output format differences
5. **Document the change** in CHANGELOG.md

---

## 🚀 Ready to Execute!

This migration is simpler than originally thought because the work is already done. We're just switching which implementation the application uses.

**Let's proceed!**
