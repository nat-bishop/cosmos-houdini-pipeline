# CLI Migration - READY TO EXECUTE

## ✅ Investigation Complete - Good News!
**The modular CLI in `cli_new/` is ALREADY COMPLETE with --dry-run!**

### Updated Discovery:
1. Modular CLI structure exists in `cli_new/` (created Sep 1, 2025)
2. **IT ALREADY HAS --dry-run implementation!** Better than the old one!
3. Only needs 2 import changes to switch over
4. Migration can be done in ~1 hour (not 5-6 hours)

### Current State:
- **OLD CLI** (`cosmos_workflow/cli.py`):
  - 800+ lines, monolithic
  - Has --dry-run features
  - Currently being used by the application
  - All tests point here

- **NEW CLI** (`cosmos_workflow/cli_new/`):
  - Already refactored into modules
  - **HAS COMPLETE --dry-run features with Rich formatting**
  - NOT being used (easy to switch)
  - NOT tested (just needs import updates)

---

## 📋 Migration Plan - SIMPLIFIED (1 hour total)

### Phase 1: Switch to New CLI (10 minutes)
1. **Update entry point**:
   ```python
   # cosmos_workflow/__main__.py
   from .cli_new import main  # Instead of from .cli import main
   ```

2. **Quick test**: `python -m cosmos_workflow --help`

### Phase 2: Update Tests (20 minutes)
1. **Update test import**:
   ```python
   # tests/test_cli.py
   from cosmos_workflow.cli_new import cli  # Update import
   ```

2. **Run tests and fix any issues**:
   - All 23 tests should pass with minor adjustments
   - May need to update mock paths

### Phase 3: Reorganize (10 minutes)
1. **Rename for clarity**:
   - `cli.py` → `cli_old.py` (backup)
   - `cli_new/` → `cli/`
   - Update imports in 2 files

### Phase 4: Verify & Cleanup (20 minutes)
1. **Test all commands with --dry-run**
2. **Delete old CLI once verified**
3. **Update CHANGELOG.md**

**Total Time: ~1 hour** (not 5-6 hours as originally estimated)

---

## ✅ Architecture Questions - INVESTIGATED & MOVED TO TODO.md

All architecture questions have been investigated and answers documented in TODO.md:

1. **CLIContext vs ConfigManager**: Both needed - different purposes
2. **Resolution Tester**: Keep for debugging, move to utilities
3. **Upsample Integration**: Mixin OK, but consider composition
4. **WorkflowOrchestrator**: Needs refactoring into services

See TODO.md section "Code Architecture Investigation" for detailed findings.

---

## ✅ Documentation Structure - MOVED TO TODO.md

Documentation reorganization plan has been moved to TODO.md.
See TODO.md section "Documentation Structure" for the complete plan.

---

## ✅ Completed in This Session

1. **Built CLI test infrastructure** (23 tests)
2. **Added --dry-run to all dangerous commands**
3. **Discovered the cli_new situation**
4. **Analyzed architecture issues**

## 🎯 Next Session Priority

**CRITICAL**: Migrate to cli_new first!
1. Port --dry-run features
2. Switch application to use cli_new
3. Update tests
4. Then continue with other improvements

---

## Implementation Checklist

### Pre-Migration Checklist:
- [ ] Backup current working state
- [ ] Document all --dry-run implementations in old CLI
- [ ] List all test scenarios that must pass

### Migration Steps:
- [ ] Copy --dry-run logic to cli_new modules
- [ ] Test each command manually
- [ ] Update __main__.py to use cli_new
- [ ] Run all tests
- [ ] Fix any failures
- [ ] Clean up old code

### Post-Migration:
- [ ] Verify all 23 tests pass
- [ ] Add missing test coverage
- [ ] Update documentation
- [ ] Commit with detailed message

### Success Criteria:
- All existing tests pass
- --dry-run works on all commands
- Code is modular and maintainable
- No functionality lost
