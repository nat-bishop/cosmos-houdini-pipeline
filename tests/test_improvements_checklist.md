# Test Improvements Checklist

## Comparison Against Both Guides

### From "Mocks & Higher-Signal Tests" Guide (mocks_better_tests_cosmos_transfer.md)

#### ✅ Completed:
1. **Mocks only at boundaries** - Created fakes for SSH, FileTransfer, Docker boundaries
2. **State-based tests** - Refactored tests to verify outputs/contracts
3. **Fake model objects** - Created FakeDockerExecutor, FakeWorkflowOrchestrator
4. **Contract tests at boundaries** - Added test_ssh_contract.py

#### ⚠️ Partially Done:
1. **Deterministic seams** - Need to add seed parameters and determinism controls
2. **Shape/dtype/range validation** - Need tests for control inputs validation
3. **Property-based tests** - Need to add hypothesis tests for invariants

#### ❌ Missing:
1. **GPU/VRAM leak tests** - No tests for memory leaks
2. **Performance regression tests** - No throughput guards
3. **Control modality tests** - No tests for segmentation, depth, edge, blur inputs
4. **Weight map validation** - No tests for spatiotemporal control weighting
5. **Metadata propagation tests** - No tests for fps, resolution, camera intrinsics
6. **Temporary directories fixture** - Not using tmp_path consistently
7. **Idempotence tests** - No tests for zero-weight invariants

### From TEST_SUITE_INVESTIGATION_REPORT.md

#### ✅ Completed:
1. **Replace mocks with fakes** - Created comprehensive fakes
2. **Test behavior not implementation** - Refactored key tests
3. **Contract tests at boundaries** - Added boundary tests
4. **Documentation** - Created BEHAVIOR_TESTING_GUIDE.md

#### ⚠️ Partially Done:
1. **Test isolation** - Still some shared state issues
2. **Remove all mock.assert_called()** - Only done in refactored files

#### ❌ Missing:
1. **Property-based testing with hypothesis** - Not implemented
2. **Performance benchmarks** - No pytest-benchmark tests
3. **Freezegun for time mocking** - Not implemented
4. **pytest-timeout** - Not configured
5. **Complete migration** - Many tests still use old patterns

### Additional Best Practices Not Implemented:

1. **Parametrized tests** - Could reduce test duplication
2. **Test data builders** - No builder pattern for complex test data
3. **Snapshot testing** - For configuration/output structure validation
4. **Mutation testing** - To validate test quality
5. **Test coverage by feature** - No feature-specific coverage tracking

## Priority Actions Needed:

### HIGH Priority (Core Functionality):
1. Add control modality validation tests
2. Add weight map alignment tests
3. Add deterministic execution tests
4. Add property-based tests for invariants
5. Fix test isolation issues

### MEDIUM Priority (Robustness):
1. Add GPU/VRAM leak detection
2. Add performance regression guards
3. Add metadata propagation tests
4. Complete migration of remaining mock-heavy tests

### LOW Priority (Nice to Have):
1. Add mutation testing
2. Add snapshot testing
3. Implement test data builders
4. Add feature coverage tracking
