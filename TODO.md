# TODO - Cosmos Workflow Orchestrator
*Last Updated: 2025-08-31*

This document tracks planned features and improvements for the Cosmos Workflow Orchestrator project. Items are organized by category and priority, with effort estimates where applicable.

---

## 🔴 Priority 1: Critical Issues

### Test Suite Overhaul
- [ ] **Fix tests according to TEST_SUITE_INVESTIGATION_REPORT.md**
  - Replace internal mocks with fakes
  - Add contract tests at boundaries
  - Fix test isolation issues
  - Increase coverage of core components (WorkflowOrchestrator, PromptManager)
  - *Effort: 10-15 days*
  - *Reference: TEST_SUITE_INVESTIGATION_REPORT.md*

### Code Quality & Cleanup
- [ ] **Identify and fix cause of temporary directories proliferation**
  - Investigate temp directories in `inputs/videos/`
  - Clean up orphaned test_images files
  - Implement proper cleanup in tests and main code
  - Add automatic cleanup routines
  - *Effort: 2-3 days*

- [ ] **Fix hardcoded negative prompt**
  - Currently hardcoded as "bad quality, blurry, low resolution, cartoonish"
  - Make configurable via config.toml or command line
  - Add smart negative prompt generation based on input
  - *Effort: 1 day*

### Performance Issues
- [ ] **Investigate control weight zero optimization**
  - Check if control_weight=0 still passes params to controlnet
  - Could cause unnecessary inference slowdown
  - Implement conditional parameter passing
  - *Effort: 1-2 days*

---

## 🟡 Priority 2: Feature Enhancements

### Testing & Benchmarking
- [ ] **Complete upsampling performance testing**
  - Test maximum batch sizes without OOM
  - Test GPU RAM usage patterns with large batches
  - Identify exact resolution thresholds for vocab errors
  - Test impact of prompt text length on tokens
  - Document findings in `docs/TESTING_RESULTS.md`
  - *Effort: 2-3 days*
  - *Reference: docs/TESTING_RESULTS.md*

- [ ] **Fix Unicode encoding error in SSH output**
  - Affects upsampling output capture
  - Does not impact functionality but causes errors
  - Update SSHManager to handle Unicode properly
  - *Effort: 1 day*

### Workflow Improvements
- [ ] **Revamp cursor workflow using TDD and subagents**
  - Design new cursor workflow architecture
  - Implement with Test-Driven Development
  - Use subagents for modular processing
  - *Effort: 5-7 days*

### AI & Smart Features
- [ ] **Improve AI renaming and description generation**
  - Enhance prompt analysis for better names
  - Add context-aware description generation
  - Implement fallback strategies for edge cases
  - Train/fine-tune better naming model
  - *Effort: 3-4 days*

### Batch Processing
- [ ] **Implement batch inference support**
  - Allow multiple prompts in single run
  - Optimize GPU utilization for batches
  - Add progress tracking for batch jobs
  - *Effort: 3-5 days*

- [ ] **Add overnight batch processing with randomization**
  - Schedule batch runs for off-hours
  - Add parameter randomization for variations
  - Implement queue management
  - Add failure recovery and retry logic
  - *Effort: 4-5 days*

### CLI Enhancement
- [ ] **Merge prompt upsampling CLI with main CLI**
  - Consolidate all CLI commands
  - Ensure consistent interface
  - Update documentation
  - *Effort: 1-2 days*

- [ ] **Add interactive prompt creation interface**
  - CLI wizard for creating prompts
  - Template system for common scenarios
  - Prompt preview and validation
  - *Effort: 2-3 days*

---

## 🟢 Priority 3: Infrastructure & Documentation

### Dependencies & Build
- [ ] **Make dependencies in requirements.txt more specific**
  - Pin exact versions for production stability
  - Add requirements-dev.txt for development deps
  - Document minimum version requirements
  - *Effort: 1 day*

- [ ] **Fix GitHub Actions workflows**
  - Update CI/CD pipelines
  - Add automated testing on PR
  - Configure release automation
  - *Effort: 2 days*

### Documentation
- [ ] **Fix incorrect resolution and info in docs**
  - Audit all documentation for accuracy
  - Update resolution specifications
  - Correct model parameters
  - Add examples with correct values
  - *Effort: 1-2 days*

### Code Organization
- [ ] **Investigate cosmos_transfer1 repo usage**
  - Check if cosmos_transfer1 repo is being imported unnecessarily
  - Remove unused dependencies
  - Clarify separation between repos
  - *Effort: 1 day*

---

## 📋 Implementation Notes

### Quick Wins (Can do in <2 hours each)
1. Fix negative prompt hardcoding
2. Update requirements.txt with specific versions
3. Document correct resolution info

### Dependencies Between Tasks
- Test suite overhaul should be done before major new features
- CLI consolidation should happen before adding prompt creation interface
- Cleanup temp directories before implementing batch processing

### Testing Requirements
- All new features must have >80% test coverage
- Use TDD for cursor workflow revamp
- Add integration tests for batch processing

---

## 📊 Effort Summary

| Priority | Total Days | Items |
|----------|------------|-------|
| Priority 1 | 14-21 days | 4 items |
| Priority 2 | 18-27 days | 6 items |
| Priority 3 | 5-6 days | 4 items |
| **Total** | **37-54 days** | **14 items** |

---

## 🎯 Suggested Execution Order

### Phase 1: Foundation (Week 1-3)
1. Fix test suite (highest impact on code quality)
2. Clean up temp directories (prevents future issues)
3. Fix negative prompt hardcoding (quick win)

### Phase 2: Core Features (Week 4-6)
1. Investigate control weight optimization
2. Improve AI naming/description
3. Merge CLI commands

### Phase 3: Advanced Features (Week 7-9)
1. Implement batch inference
2. Add overnight processing
3. Revamp cursor workflow with TDD

### Phase 4: Polish (Week 10)
1. Fix documentation
2. Update dependencies
3. Fix GitHub Actions

---

## 📝 Notes for Future Items

Space for additional TODOs as they arise:

- [ ]
- [ ]
- [ ]
- [ ]
- [ ]

---

## ✅ Completed Items

Move completed items here with completion date:

<!-- Example:
- [x] **Item description** - Completed 2025-01-15
  - Notes about implementation
-->

---

*This document should be updated regularly as priorities change and new requirements emerge.*
