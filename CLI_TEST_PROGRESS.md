# CLI Migration Plan - CRITICAL DISCOVERY

## 🚨 Critical Issue Discovered
**We've been working on the WRONG CLI implementation!**

### What Happened:
1. A modular CLI structure already exists in `cli_new/` (created Sep 1, 2025)
2. The application still uses the old monolithic `cli.py` (800+ lines)
3. Our --dry-run changes were added to the OLD `cli.py`
4. All tests are testing the OLD `cli.py`
5. The refactoring we planned to do is ALREADY DONE in `cli_new/`

### Current State:
- **OLD CLI** (`cosmos_workflow/cli.py`):
  - 800+ lines, monolithic
  - Has our new --dry-run features
  - Currently being used by the application
  - All tests point here

- **NEW CLI** (`cosmos_workflow/cli_new/`):
  - Already refactored into modules
  - Does NOT have --dry-run features
  - NOT being used
  - NOT tested

---

## 📋 Migration Plan for Next Session

### Phase 1: Migrate --dry-run Features (2 hours)
1. **Port --dry-run to cli_new modules**:
   - `inference.py`: Add --dry-run flag and logic
   - `prepare.py`: Add --dry-run flag and logic
   - `enhance.py`: Add --dry-run flag and logic
   - Copy the implementation from old `cli.py`

2. **Verify feature parity**:
   - Compare old vs new command outputs
   - Ensure all flags work the same way

### Phase 2: Switch Over (1 hour)
1. **Update entry point**:
   ```python
   # cosmos_workflow/__main__.py
   from .cli_new import main  # Instead of from .cli import main
   ```

2. **Update imports**:
   - Check all files that import from `cli.py`
   - Update to import from `cli_new`

3. **Rename directories**:
   - Move `cli.py` → `cli_old.py` (backup)
   - Move `cli_new/` → `cli/`
   - Update all imports accordingly

### Phase 3: Update Tests (2 hours)
1. **Update test imports**:
   ```python
   # tests/test_cli.py
   from cosmos_workflow.cli import cli  # Should now point to new modular CLI
   ```

2. **Fix any broken tests**:
   - Module structure is different
   - May need to patch different locations
   - Verify all 23 tests still pass

3. **Add missing tests**:
   - Test for `create run` command
   - More tests for `prepare` (non dry-run)
   - More tests for `prompt-enhance` (non dry-run)

### Phase 4: Cleanup (30 mins)
1. **Remove old code**:
   - Delete `cli_old.py` once confirmed working
   - Clean up any duplicate code

2. **Update documentation**:
   - Update README with new structure
   - Document the modular architecture

---

## 🔍 Architecture Questions to Investigate

### 1. Context Manager vs Config Manager
- **CLIContext**: Click's context for passing data between commands
- **ConfigManager**: Manages config.toml settings
- **Assessment**: Both needed - they serve different purposes
  - CLIContext: Runtime command state
  - ConfigManager: Persistent configuration

### 2. Resolution Tester
- **Purpose**: Tests video resolutions for token limits
- **Location**: `cosmos_workflow/workflows/resolution_tester.py`
- **Assessment**: Still useful for debugging resolution issues
- **Recommendation**: Keep but move to utilities/debugging

### 3. Upsample Integration
- **Purpose**: Adds upsampling methods to WorkflowOrchestrator via mixin
- **Concern**: Is WorkflowOrchestrator becoming monolithic?
- **Current State**: WorkflowOrchestrator inherits from UpsampleWorkflowMixin
- **Assessment**: Mixin pattern is OK but WorkflowOrchestrator is getting large
- **Recommendation**: Consider composition over inheritance in future

### 4. WorkflowOrchestrator Architecture
- **Current Responsibilities**:
  - SSH connection management
  - File transfers
  - Docker execution
  - Inference workflows
  - Upsampling workflows (via mixin)
  - Status checking
- **Assessment**: Becoming a "God Object" - doing too much
- **Recommendation**: Future refactor into smaller services:
  - InferenceService
  - UpsampleService
  - TransferService
  - StatusService

---

## 📝 Documentation Structure Issues

### Current Problems:
1. **Too many .md files** scattered everywhere
2. **Duplicate information** in multiple places
3. **No clear update strategy** - unclear what to update when
4. **Temporary vs permanent** docs mixed together
5. **CLAUDE.md requirements** not consistently followed

### Proposed Structure:
```
docs/
├── README.md              # Main project documentation
├── CHANGELOG.md           # Version history (keep here)
├── architecture/          # Technical documentation
│   ├── README.md         # Architecture overview
│   ├── cli.md            # CLI structure
│   └── workflows.md      # Workflow design
├── guides/               # How-to guides
│   ├── setup.md
│   └── usage.md
├── development/          # Developer docs
│   ├── testing.md
│   └── contributing.md
└── _temp/                # Temporary reports (gitignored)
    └── *.md              # Session reports, test results

project root:
├── CLAUDE.md             # AI assistant instructions
├── TODO.md               # Project-wide todos
├── README.md             # User-facing docs
└── [each directory]/README.md  # Directory-specific technical details
```

### Guidelines:
1. **One source of truth** per topic
2. **README per directory** for technical details
3. **Temp folder** for ephemeral reports (gitignored)
4. **CLAUDE.md** for AI instructions only
5. **TODO.md** for project todos (not Claude's working notes)

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
