# 🧹 Codebase Cleanup Action Plan

## Quick Command Summary
```bash
# Step 1: Delete test scripts and temporary files (SAFE - not used by tests)
rm -f test_resolution_*.py quick_resolution_test.py simple_boundary_test.py
rm -f lint.py fix_all_linting.py
rm -f *.log *.json resolution_test_log.txt

# Step 2: Delete unused test directories (SAFE - only mock refs in tests)
rm -rf resolution_tests/ resolution_test_results/ upsampling_tests/ test_notes/
rm -rf test_videos/ test_images/  # Only referenced as mock strings in unit tests
rm -rf testing/  # Contains duplicate scripts

# Step 3: Clean cache and build artifacts
rm -rf htmlcov/ .coverage .mypy_cache/ .ruff_cache/ .pytest_cache/
rm -rf notes/ art/  # Empty directories

# Step 4: Migrate scripts to CLI (then delete scripts/)
# See detailed instructions below
```

## Detailed Actions

### 1️⃣ **DELETE NOW** - Temporary Files (100% Safe)
These files are not referenced anywhere in the codebase:

```bash
# Test scripts in root (move functionality to CLI or delete)
rm test_resolution_boundary.py
rm test_resolution_limits.py
rm quick_resolution_test.py
rm simple_boundary_test.py

# Linting helpers (use ruff directly)
rm lint.py
rm fix_all_linting.py

# Log files and test outputs
rm deploy_test.log
rm upsampling_fixed.log
rm upsampling_run.log
rm resolution_test_log.txt

# Test JSON files
rm test_batch_prompts.json
rm test_batch_safe.json
rm resolution_boundary_results.json

# Build artifacts
rm -rf htmlcov/
rm .coverage
```

### 2️⃣ **DELETE NOW** - Unused Directories (Safe)
These are only referenced as mock strings in unit tests, not actual file dependencies:

```bash
# Test directories (not used by actual tests)
rm -rf resolution_tests/
rm -rf resolution_test_results/
rm -rf upsampling_tests/
rm -rf test_notes/
rm -rf test_videos/    # Only mocked in tests
rm -rf test_images/    # Only mocked in tests

# Duplicate test utilities
rm -rf testing/        # Contains create_test_*.py scripts

# Empty directories
rm -rf notes/
rm -rf art/

# Cache directories (auto-regenerated)
rm -rf .mypy_cache/
rm -rf .ruff_cache/
rm -rf .pytest_cache/
```

### 3️⃣ **MIGRATE TO CLI** - Scripts Directory
Before deleting `scripts/`, integrate these into the CLI:

| Script | New CLI Command | Priority |
|--------|----------------|----------|
| `check_remote_results.py` | `cosmos remote check-results` | Low |
| `deploy_and_test_upsampler.py` | `cosmos test upsampler` | Low |
| `test_actual_resolution_limits.py` | `cosmos test resolution` | Medium |
| `working_prompt_upsampler.py` | Already done: `cosmos prompt-enhance` | ✅ |

**Shell scripts to delete** (not cross-platform):
```bash
rm scripts/*.sh  # All functionality should be in Python CLI
```

### 4️⃣ **REORGANIZE** - Documentation
Keep it simple:

```bash
# Move technical docs
mkdir -p docs/technical
mv REFERENCE.md docs/technical/cli-reference.md
mv docs/RESOLUTION_LIMITS_FINAL.md docs/technical/

# Root should only have:
# - README.md (user-facing)
# - CHANGELOG.md (changes)
# - CLAUDE.md (AI context)
# - TODO.md → Delete (use GitHub issues)
rm TODO.md
```

### 5️⃣ **VERIFY** - Before Deleting
Run these checks to ensure nothing breaks:

```bash
# 1. Run all tests to verify they don't need deleted files
pytest tests/ -v

# 2. Check for any remaining references
grep -r "test_resolution_" --include="*.py" .
grep -r "resolution_tests" --include="*.py" .

# 3. Ensure CLI still works
cosmos --help
```

## Summary Checklist

- [ ] Delete all `.py` test scripts in root
- [ ] Delete all `.log` and test `.json` files
- [ ] Remove `lint.py` and `fix_all_linting.py`
- [ ] Delete unused test directories
- [ ] Clean cache/build directories
- [ ] Migrate useful scripts to CLI commands
- [ ] Delete all `.sh` scripts
- [ ] Reorganize docs (move `REFERENCE.md`, delete `TODO.md`)
- [ ] Run tests to verify

## After Cleanup

Your clean structure:
```
cosmos-houdini-experiments/
├── cosmos_workflow/       # Source code only
├── tests/                 # Test suite only
├── docs/                  # All documentation
├── inputs/                # User inputs
├── outputs/               # Generated outputs
├── scripts/               # DELETE after migration
├── .gitignore
├── CHANGELOG.md
├── CLAUDE.md
├── README.md
├── pyproject.toml
└── requirements*.txt
```

**Total files to delete: ~30+**
**Directories to remove: 10**
**Expected cleanup: ~50% less clutter**
