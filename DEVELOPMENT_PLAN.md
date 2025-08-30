# Development Plan for Cosmos-Houdini Experiments

## Overview
This document outlines the development plan for enhancing the Cosmos workflow orchestration system with new features and improvements.

## Phase 2: Add Prompt Upsampling Feature ✅ COMPLETED (2025-08-30)
**Goal**: Implement decoupled prompt upsampling that works with high-resolution videos.

### Requirements:
- Create a bash script for remote execution (similar to inference.sh) ✅
- Support batch processing of prompts ✅
- Keep model loaded between upsampling runs for efficiency ✅
- Handle video resolution downsampling for prompt upsampling ✅
- Support frame reduction options ✅
- Create PromptSpecs with `upsampled=true` and original prompt stored ✅

### Tasks COMPLETED:
- [x] Research Cosmos Transfer prompt upsampling implementation
- [x] Create `upsample_prompt.sh` script for remote execution
- [x] Implement batch prompt upsampling with model persistence
- [x] Add video preprocessing options:
  - [x] Resolution downsampling (480p default)
  - [x] Frame reduction (2 frames default)
- [x] Update PromptSpec handling for upsampled prompts
- [x] Create workflow integration for prompt upsampling
- [x] Add CLI commands for prompt upsampling
- [x] Write unit tests (8 passing tests in test_upsample_prompts.py)

### Implementation Completed:
1. **Core Scripts**:
   - `scripts/upsample_prompts.py` - Python batch upsampling with video preprocessing
   - `scripts/upsample_prompt.sh` - Bash wrapper for Docker execution

2. **WorkflowOrchestrator Integration**:
   - `cosmos_workflow/workflows/upsample_integration.py` - UpsampleWorkflowMixin
   - Three main methods: batch, single, and directory upsampling
   - Full SSH/Docker/FileTransfer integration

3. **CLI Command**:
   - `python -m cosmos_workflow.main upsample <input> [options]`
   - Supports single files and directories
   - Video preprocessing options
   - GPU configuration

4. **Tests**:
   - `tests/test_upsample_prompts.py` - 8 unit tests (all passing)
   - Tests cover: video preprocessing, batch processing, error handling, CLI parsing

### Tests Still Needed (for next session):
- [ ] Fix integration tests in `test_upsample_integration.py` (API mismatches)
- [ ] Fix workflow tests in `test_upsample_workflow.py` (API mismatches)
- [ ] Add integration tests for WorkflowOrchestrator methods
- [ ] Add end-to-end tests with mocked SSH/Docker

### Implementation Notes:
- Reference: `cosmos_transfer1/diffusion/inference/` for upsampling methods
- Use `--offload_prompt_upsampler` flag for memory optimization
- Model: `Cosmos-UpsamplePrompt1-12B-Transfer`
- Current Docker execution approach (bash scripts) is sufficient for this phase

## Phase 3: Add Batch Inference Support
**Goal**: Enable processing multiple PromptSpecs in a single inference run.

### Requirements:
- Support Cosmos Transfer's batch inference options
- Handle multiple controlnet specs
- Optimize GPU memory usage for batch processing
- Track individual job status within batches

### Tasks:
- [ ] Study Cosmos Transfer batch inference implementation
- [ ] Modify inference.sh to support batch mode
- [ ] Create batch job specification schema
- [ ] Implement batch job orchestration
- [ ] Add progress tracking for batch jobs
- [ ] Handle partial failures in batch processing
- [ ] Create CLI commands for batch operations
- [ ] Write tests for batch inference

### Implementation Notes:
- Use `--batch_size` parameter in Cosmos Transfer
- Consider memory constraints when setting batch sizes
- Implement job queuing system

## Phase 4: Add Support for Running Batches of Jobs
**Goal**: Enable overnight batch processing with parameter randomization.

### Requirements:
- Sequential job execution
- Parameter randomization options
- Support for testing single prompt with varied parameters
- Job scheduling and queue management
- Result aggregation and reporting

### Tasks:
- [ ] Design job queue system
- [ ] Implement parameter randomization:
  - [ ] Control weight variations
  - [ ] Inference parameter variations
  - [ ] Seed randomization
  - [ ] Control input combinations
- [ ] Create job scheduling system
- [ ] Add job monitoring and status tracking
- [ ] Implement result aggregation
- [ ] Create reporting system for batch results
- [ ] Add CLI commands for batch job management
- [ ] Write comprehensive tests

### Randomization Options:
- Control weights (vis, edge, depth, seg)
- Inference parameters (num_steps, guidance, sigma_max)
- Seeds for reproducibility testing
- Control input combinations
- Blur strength and canny threshold variations

## Development Guidelines

### Version Control:
- Make regular, atomic commits
- Use descriptive commit messages
- Follow conventional commit format
- Create feature branches for major changes

### Documentation (Continuous):
- **ALWAYS** update README.md when adding user-facing features
- **ALWAYS** update REFERENCE.md when adding technical components
- **ALWAYS** update CLAUDE.md when changing core workflows
- Add inline documentation for complex logic
- Create usage examples for new features
- Update documentation **BEFORE** committing code changes

### Testing (Continuous):
- Write tests **AS YOU CODE**, not after
- Add unit tests for all new functions
- Add integration tests for workflows
- Run tests before committing: `pytest tests/`
- Maintain >80% code coverage
- Test edge cases and error handling
- Fix failing tests immediately

### Code Quality:
- Follow existing code patterns
- Use type hints throughout
- Implement proper error handling
- Add logging for debugging
- Follow PEP 8 style guidelines

### Continuous Integration Workflow:
1. Write/modify code
2. Write/update tests
3. Update documentation
4. Run tests locally
5. Commit changes
6. Push to repository

## Docker Execution Approach

### Current Implementation (Bash Scripts)
The current approach of using bash scripts (inference.sh, upscale.sh) that are executed inside Docker containers via SSH is **perfectly adequate** for our needs:

**Advantages:**
- Simple and maintainable
- Easy to debug and modify
- Clear separation between orchestration and execution
- Minimal overhead
- Works well with the existing infrastructure

**When to Consider Alternatives:**
- If we need real-time streaming of results
- If we need bidirectional communication during execution
- If we implement a web UI requiring WebSocket connections
- If we need to manage long-running persistent containers

### Recommendation
Continue with the bash script approach for Phase 2 (Prompt Upsampling). This maintains consistency with the existing system and avoids unnecessary complexity.

## Progress Tracking

### Phase 1: Refactoring ✅
- Status: **COMPLETED** (2024-08-30)

### Phase 2: Prompt Upsampling 🚧
- Status: Ready to Start
- Estimated Time: 3-4 days
- Priority: High

### Phase 3: Batch Inference 📋
- Status: Not Started
- Estimated Time: 2-3 days
- Priority: Medium

### Phase 4: Batch Jobs 📋
- Status: Not Started
- Estimated Time: 3-4 days
- Priority: Medium

## Next Steps

### Immediate (Next Session):
1. Begin Phase 2: Prompt Upsampling
   - Research upsampling implementation
   - Create `upsample_prompt.sh` script
   - Add batch processing support
2. Continue with test-driven development
3. Update documentation as features are added

### Best Practices Going Forward:
- **Documentation-Driven Development**: Write docs first, then code
- **Test-Driven Development**: Write tests first, then implementation
- **Continuous Integration**: Test and document with every change
- **Regular Commits**: Commit working code frequently
- **Code Reviews**: Review changes before major commits

---

*Last Updated: 2025-08-30*