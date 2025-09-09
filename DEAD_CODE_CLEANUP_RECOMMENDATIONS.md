# Dead Code Cleanup Recommendations

**Analysis Date**: 2025-01-09
**Codebase**: Cosmos Workflow
**Analysis Scope**: Complete codebase review for unused code, duplicates, and safe improvements

---

## Risk Assessment Legend

- **0% Risk**: Can be deleted with zero chance of breaking anything
- **5% Risk**: Extremely low risk, might affect development tools only
- **10% Risk**: Very low risk, minimal chance of affecting functionality
- **15% Risk**: Low risk, may require minor import updates
- **25% Risk**: Medium-low risk, requires testing after changes
- **50% Risk**: Medium risk, significant refactoring involved
- **75% Risk**: High risk, major architectural changes
- **90%+ Risk**: Severe refactor required, could break system

---

## High Priority Recommendations

### 1. Remove Disabled Upscaling Function
**File**: `cosmos_workflow/utils/nvidia_format.py:137`
**Change**: Remove `to_cosmos_upscale_json()` function
**Reason**: Function deliberately raises `NotImplementedError("Upscaling is temporarily disabled")`
**Risk Level**: **0% Risk** - Function is intentionally broken and unused
**Impact**: Code reduction, removes misleading dead code

### 2. Remove Development Test Script
**File**: `verify_json_format.py` (root directory)
**Change**: Delete entire file
**Reason**: Development/testing script not part of production codebase
**Risk Level**: **0% Risk** - Pure development utility
**Impact**: Cleaner repository, no production dependencies

### 3. Remove One-Time Import Script
**File**: `scripts/import_json_prompts.py`
**Change**: Delete if data migration complete
**Reason**: Appears to be one-time historical data migration utility
**Risk Level**: **5% Risk** - Verify migration is complete first
**Impact**: Remove historical maintenance burden

### 4. Remove Unused Shell Completion Functions
**File**: `cosmos_workflow/cli/completions.py`
**Functions to Remove**:
- `complete_prompt_specs()`
- `complete_video_files()`
- `complete_video_dirs()`
- `complete_directories()`
**Reason**: Defined but never called in CLI implementation
**Risk Level**: **10% Risk** - May affect shell completion if configured
**Impact**: Reduced CLI module size, cleaner interface

### 5. Remove Unused Workflow Utilities
**File**: `cosmos_workflow/utils/workflow_utils.py`
**Functions to Remove**:
- `log_workflow_event()` - Exported but never imported
- `validate_gpu_configuration()` - Exported but never used
- `convert_local_path_to_remote_video()` - Defined but no usage found
**Reason**: Functions are exported in `__init__.py` but never imported or called
**Risk Level**: **10% Risk** - Verify no dynamic/string-based imports
**Impact**: Cleaner utility module, reduced API surface

### 6. Remove Unused Smart Naming Function
**File**: `cosmos_workflow/utils/smart_naming.py`
**Function**: `sanitize_name()`
**Reason**: Only used in tests, not in actual production code
**Risk Level**: **15% Risk** - May break tests that use this function
**Impact**: Cleaner utility module, tests may need updates

---

## Medium Priority Recommendations

### 7. Consolidate Duplicate Duration Formatting
**Files**:
- `cosmos_workflow/utils/workflow_utils.py` (keep this one)
- `cosmos_workflow/cli/helpers.py` (remove from here)
**Change**: Remove duplicate `format_duration()` function, update imports
**Reason**: Two different implementations of same functionality
**Risk Level**: **25% Risk** - Need to update imports and verify behavior compatibility
**Impact**: DRY principle compliance, single source of truth

### 8. Remove Redundant Wrapper Function
**File**: `cosmos_workflow/local_ai/cosmos_sequence.py`
**Function**: `_generate_smart_name()`
**Change**: Replace calls with direct `generate_smart_name()` calls
**Reason**: Wrapper only adds logging, provides no other value
**Risk Level**: **15% Risk** - Need to update all call sites
**Impact**: Simpler call chain, reduced indirection

### 9. Fix Missing Module Exports
**File**: `cosmos_workflow/utils/__init__.py`
**Change**: Add `nvidia_format` to exports
**Reason**: Module is used throughout codebase but not properly exposed
**Risk Level**: **10% Risk** - Improves import consistency
**Impact**: Better module organization, clearer API

### 10. Clean Up Empty UI Export
**File**: `cosmos_workflow/ui/__init__.py`
**Change**: Remove unused `app` export
**Reason**: Export is not used anywhere in codebase
**Risk Level**: **10% Risk** - Verify no dynamic imports
**Impact**: Cleaner module interface

### 11. Consolidate Path Conversion Logic
**Files**: Multiple files contain `path.replace("\\", "/")`
**Change**: Extract to utility function in `cosmos_workflow/utils/`
**Locations**:
- `nvidia_format.py`
- `import_json_prompts.py`
- `completions.py`
**Risk Level**: **25% Risk** - Need to update multiple files and test path handling
**Impact**: DRY compliance, centralized path logic

---

## Low Priority Recommendations

### 12. Review Optional Dependencies
**Dependencies**:
- `sentence-transformers` (only used in local AI functionality)
- `keybert` (only used for smart naming)
- `pyyaml` (not found to be actively used)
**Change**: Make truly optional or remove unused ones
**Risk Level**: **50% Risk** - Requires careful dependency analysis and testing
**Impact**: Smaller installation footprint, faster installs

### 13. Consolidate Container Management Logic
**Files**:
- `cosmos_workflow/execution/gpu_executor.py`
- `cosmos_workflow/execution/docker_executor.py`
**Change**: Extract common container naming/management patterns
**Risk Level**: **50% Risk** - Significant refactoring of core execution logic
**Impact**: Better code organization, reduced duplication

### 14. Clean Up Empty Package Files
**File**: `cosmos_workflow/transfer/__init__.py`
**Change**: Add proper exports or keep minimal
**Current State**: Only contains comment "# File transfer service package"
**Risk Level**: **0% Risk** - Pure documentation improvement
**Impact**: Cleaner package structure

---

## Maintenance Recommendations

### 15. Address TODO/FIXME Comments
**Files**:
- `cosmos_workflow/execution/docker_executor.py`
- `cosmos_workflow/local_ai/cosmos_sequence.py`
**Change**: Implement, remove, or convert to issues
**Risk Level**: **Variable** - Depends on specific TODOs
**Impact**: Cleaner code, clearer development intentions

### 16. Improve Test Coverage
**Files Missing Tests**:
- `cosmos_workflow/cli/completions.py` (0% coverage)
- `cosmos_workflow/ui/app.py` (limited coverage)
**Change**: Add comprehensive test coverage
**Risk Level**: **0% Risk** - Adding tests only
**Impact**: Better reliability, regression protection

### 17. Environment Variable Cleanup
**File**: `scripts/prompt_upsampler.py`
**Variables**: Several `TORCHELASTIC_*` environment variables
**Change**: Verify necessity and remove unused ones
**Risk Level**: **25% Risk** - May affect distributed training functionality
**Impact**: Cleaner environment setup, fewer variables

---

## Implementation Strategy

### Phase 1: Zero Risk Items (Items 1-2)
- Remove disabled functions and development scripts
- No testing required, pure cleanup

### Phase 2: Very Low Risk Items (Items 3-6)
- Remove unused functions with basic verification
- Quick smoke test after changes

### Phase 3: Low Risk Consolidation (Items 7-11)
- Consolidate duplicates and fix exports
- Requires import updates and testing

### Phase 4: Medium Risk Refactoring (Items 12-13)
- Optional dependency review and container logic consolidation
- Extensive testing required

### Phase 5: Maintenance (Items 14-17)
- Documentation, TODOs, and test coverage improvements
- Ongoing process

---

## Estimated Impact Summary

- **Lines of Code Reduction**: ~500-800 lines (5-10% reduction)
- **File Reduction**: 2-3 files
- **Import Updates Required**: ~10-15 files
- **Test Updates Required**: ~5-8 test files
- **Breaking Changes**: None (all dead code removal)
- **Performance Impact**: Negligible improvement
- **Maintenance Impact**: Significant improvement

---

## Notes

1. All recommendations maintain the architectural patterns defined in `CLAUDE.md`
2. No changes affect the core CosmosAPI interface
3. All wrapper usage patterns (SSHManager, DockerExecutor, etc.) are preserved
4. Risk assessments are conservative - actual risk may be lower with proper testing
5. Consider implementing changes incrementally with git commits for easy rollback

---

**Last Updated**: 2025-01-09
**Reviewer**: Claude Code Analysis
**Next Review**: After implementation of Phase 1-2 items