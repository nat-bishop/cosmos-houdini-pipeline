# TODO - Cosmos Workflow Orchestrator
*Last Updated: 2025-09-01*

This document tracks planned features and improvements for the Cosmos Workflow Orchestrator project. Items are organized by category and priority.

---

## 🔴 Priority 1: Critical Issues

### Remote Environment Setup
- [ ] **Build Docker image on remote instance**
  - Run: `sudo docker build -f Dockerfile . -t nvcr.io/ubuntu/cosmos-transfer1:v1.0.0`
  - Verify image exists with `sudo docker images`
  - Update config.toml to use versioned image
  - *Effort: 1 day*

- [ ] **Setup model checkpoints**
  - Download all required checkpoints to `/home/ubuntu/NatsFS/cosmos-transfer1/checkpoints/`
  - Verify directory structure
  - Create manifest of checkpoint versions
  - *Effort: 1-2 days*

- [ ] **Configure Hugging Face authentication**
  - Set up read-only HF token
  - Configure as environment variable or Docker secret
  - Test model access
  - *Effort: 1 day*

### Security & Version Control
- [ ] **Pin Docker image versions**
  - Stop using `:latest` tags everywhere
  - Create versioned tags (e.g., `cosmos-transfer1:v1.0.0`)
  - Update all references in code and config
  - Document version in deployment notes
  - *Effort: 1 day*

- [ ] **Version control model checkpoints**
  - Document specific checkpoint versions/hashes
  - Create manifest file listing all checkpoints
  - Implement checkpoint validation
  - *Effort: 1-2 days*

### Code Quality
- [ ] **Fix hardcoded negative prompt**
  - Currently hardcoded as "bad quality, blurry, low resolution, cartoonish"
  - Make configurable via config.toml or command line
  - Add smart negative prompt generation based on input
  - *Effort: 1 day*

### CLI Migration (CRITICAL - Discovered Issue)
- [ ] **Migrate to cli_new module structure** (CRITICAL)
  - cli_new already exists with modular structure!
  - Need to port --dry-run features from old cli.py
  - Switch application to use cli_new
  - Update all tests to test new structure
  - *Effort: 5-6 hours*
  - *Reference: CLI_TEST_PROGRESS.md*

### Code Architecture Investigation
- [ ] **Investigate and refactor architecture issues**
  - Analyze if ContextManager and ConfigManager are both necessary
  - Review if resolution_tester.py is still needed
  - Evaluate upsample_integration.py mixin pattern
  - Assess if WorkflowOrchestrator is becoming monolithic
  - Consider splitting into smaller services (InferenceService, etc.)
  - *Effort: 2-3 days*
  - *Reference: CLI_TEST_PROGRESS.md - Architecture Questions*

### Documentation Structure
- [ ] **Reorganize documentation for clarity**
  - Too many scattered .md files causing confusion
  - Create clear structure: docs/, architecture/, guides/, _temp/
  - One README per directory for technical details
  - Move CHANGELOG to docs/
  - Create _temp/ folder for ephemeral reports (gitignored)
  - Establish clear guidelines for what goes where
  - *Effort: 1 day*
  - *Reference: CLI_TEST_PROGRESS.md - Documentation Structure*

### Performance Issues
- [ ] **Investigate control weight zero optimization**
  - Check if control_weight=0 still passes params to controlnet
  - Could cause unnecessary inference slowdown
  - Implement conditional parameter passing
  - *Effort: 1-2 days*

---

## 🟡 Priority 2: Feature Enhancements

### CLI Improvements (NEW)
- [ ] **Complete test coverage for all CLI commands**
  - Add tests for `create run` command
  - Add non-dry-run tests for `prompt-enhance`
  - *Effort: 1 hour*
  - *Reference: tests/test_cli.py*

- [ ] **Improve error messages with actionable suggestions**
  - Add "did you mean?" for typos
  - Show examples on invalid usage
  - Include relevant documentation links
  - *Effort: 1 hour*

- [ ] **Add --output-format option**
  - Support json/table/plain output formats
  - Useful for scripting and automation
  - *Effort: 2 hours*

- [ ] **Add command aliases**
  - `cosmos prompt` → `cosmos create prompt`
  - `cosmos run` → `cosmos inference`
  - *Effort: 30 mins*

- [ ] **Create config command group**
  - `cosmos config get/set/list`
  - Manage settings from CLI
  - *Effort: 2 hours*

### Testing & Benchmarking
- [ ] **Complete additional upsampling performance testing**
  - Test maximum batch sizes without OOM
  - Test GPU RAM usage patterns with large batches
  - Test impact of prompt text length on tokens
  - Expand on findings in `docs/TESTING_RESULTS.md`
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

- [ ] **Implement automatic video preprocessing**
  - Auto-resize videos exceeding token limits
  - Create hint videos at 320×180 for upsampling
  - Add resolution validation before processing
  - *Effort: 2 days*

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

### AI & Smart Features
- [ ] **Improve AI naming and description generation**
  - Enhance prompt analysis for better names
  - Add context-aware description generation
  - Implement fallback strategies for edge cases
  - *Effort: 3-4 days*

---

## 🟢 Priority 3: Nice to Have

### UI/Dashboard (NEW - FUTURE)
- [ ] **Create web dashboard for analytics and control**
  - Real-time job monitoring
  - Performance analytics and metrics
  - Model version management
  - Resource usage tracking
  - Remote control interface
  - *Effort: Significant project (2-4 weeks)*
  - *Note: Should be separate project/repository*

### CLI Enhancement
- [ ] **Add interactive prompt creation interface**
  - CLI wizard for creating prompts
  - Template system for common scenarios
  - Prompt preview and validation
  - *Effort: 2-3 days*

### Documentation
- [ ] **Create comprehensive user guide**
  - Step-by-step setup instructions
  - Common workflow examples
  - Troubleshooting guide
  - *Effort: 2 days*

### Infrastructure
- [ ] **Fix pre-commit hooks configuration**
  - Fix "look-behind requires fixed-width pattern" error
  - Resolve bandit toml parser issue
  - Configure hooks to work with Windows line endings
  - Update pyproject.toml for better compatibility
  - *Effort: 1 day*

- [ ] **Setup Claude to interact with GitHub Actions**
  - Configure Claude Code to trigger and monitor GitHub Actions
  - Add ability to view CI/CD results directly
  - Enable automated PR checks and feedback
  - Create integration for release automation
  - *Effort: 2-3 days*

- [ ] **Fix GitHub Actions workflows**
  - Update CI/CD pipelines
  - Add automated testing on PR
  - Configure release automation
  - *Effort: 2 days*

---

## 📊 Effort Summary

| Priority | Total Days | Items |
|----------|------------|-------|
| Priority 1 | 12-16 days | 11 items |
| Priority 2 | 16-21 days | 10 items |
| Priority 3 | 6-10 days + future | 5 items |
| **Total** | **34-47 days** | **26 items** |

---

## 🎯 Next Steps (In Order)

1. **CRITICAL: Migrate to cli_new** - Port --dry-run, switch over, update tests (5-6 hours)
2. **Complete CLI test coverage** - Add missing tests (1 hour)
3. **Reorganize documentation** - Create clear structure (1 day)
4. **Investigate architecture** - Assess if refactoring needed (2-3 days)
5. **Setup remote environment** - Build Docker image, download checkpoints
6. **Configure authentication** - Set up HF token
7. **Pin versions** - Move away from `:latest` tags

---

## ✅ Completed Items

### 2025-09-01 Session
- [x] **CLI test infrastructure** - Completed 2025-09-01
  - Created comprehensive test suite with CliRunner
  - 23 tests covering all major commands
  - Tests run in ~0.32s

- [x] **--dry-run implementation** - Completed 2025-09-01
  - Added to inference, prepare, and prompt-enhance commands
  - Prevents expensive operations (GPU, file creation, API calls)
  - Full test coverage with TDD approach

### 2025-08-31 Session
- [x] **Prompt upsampling integration** - Completed 2025-08-31
  - Integrated upsampling into WorkflowOrchestrator
  - Added CLI `upsample` command
  - Created resolution testing utilities
  - Documented token limits (320×180 safe resolution)

- [x] **Script cleanup** - Completed 2025-08-31
  - Removed 24 redundant upsampling scripts
  - Kept 4 essential scripts
  - Removed 15+ outdated documentation files
  - Cleaned Python cache files

- [x] **Test suite improvements** - Completed 2025-08-31
  - Reverted to real implementations (no fakes)
  - Fixed schema mismatches
  - Tests now verify actual code behavior

- [x] **Documentation cleanup** - Completed 2025-08-31
  - Removed all outdated test planning docs
  - Updated CHANGELOG with recent changes
  - Consolidated upsampling documentation

---

*This document should be updated regularly as priorities change and new requirements emerge.*
