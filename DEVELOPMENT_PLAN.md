# Development Plan for Cosmos-Houdini Experiments

## Overview
This document outlines the development plan for enhancing the Cosmos workflow orchestration system with new features and improvements.

## Phase 1: Refactoring
**Goal**: Identify and improve areas with tight coupling, repeated code, or monolithic design.

### Tasks:
- [ ] Audit existing codebase for code duplication
- [ ] Identify tightly coupled components
- [ ] Merge duplicated workflow_orchestration code into a single run command
- [ ] Extract common patterns into reusable utilities
- [ ] Improve separation of concerns between modules
- [ ] Add proper abstraction layers where needed

### Key Areas to Refactor:
- Workflow orchestration logic (remove duplication between run_full_cycle, run_inference_only, run_upscaling_only)
- SSH connection management (consolidate connection handling)
- File transfer operations (create unified transfer interface)
- Docker execution commands (standardize container management)

## Phase 2: Add Prompt Upsampling Feature
**Goal**: Implement decoupled prompt upsampling that works with high-resolution videos.

### Requirements:
- Create a Python script to be executed on the remote instance (like inference.sh)
- Support batch processing of prompts
- Keep model loaded between upsampling runs for efficiency
- Handle video resolution downsampling for prompt upsampling
- Support frame reduction options
- Create PromptSpecs with `upsampled=true` and original prompt stored

### Tasks:
- [ ] Research Cosmos Transfer prompt upsampling implementation
- [ ] Create `upsample_prompts.py` script for remote execution
- [ ] Implement batch prompt upsampling with model persistence
- [ ] Add video preprocessing options:
  - [ ] Resolution downsampling
  - [ ] Frame reduction
- [ ] Update PromptSpec handling for upsampled prompts
- [ ] Create workflow integration for prompt upsampling
- [ ] Add CLI commands for prompt upsampling
- [ ] Write comprehensive tests

### Implementation Notes:
- Reference: `cosmos_transfer1/diffusion/inference/` for upsampling methods
- Use `--offload_prompt_upsampler` flag for memory optimization
- Model: `Cosmos-UpsamplePrompt1-12B-Transfer`

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

## Questions/Clarifications Needed

1. **Prompt Upsampling**:
   - What specific resolution should we downsample to for prompt upsampling?
   - How many frames should we reduce to (e.g., every nth frame)?
   - Should upsampled prompts be stored separately or replace originals?

2. **Batch Processing**:
   - What's the preferred batch size for inference?
   - How should we handle OOM errors during batch processing?
   - Should failed jobs in a batch be automatically retried?

3. **Job Randomization**:
   - What parameter ranges are most useful for testing?
   - Should we support custom randomization strategies?
   - How should results be organized (by parameter, by timestamp)?

## Progress Tracking

### Phase 1: Refactoring ✅
- Status: **COMPLETED** (2024-08-30)
- Achievements:
  - Unified run() method in WorkflowOrchestrator
  - Created reusable utilities (WorkflowExecutor, ServiceManager)
  - Implemented command builder pattern
  - Added abstraction layers
  - 100+ tests passing

### Phase 2: Prompt Upsampling 🚧
- Status: In Progress
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

### Additional Completed Work:
- **AI Integration**: Added BLIP, ViT, DETR for video analysis
- **Negative Prompt Support**: Fixed cosmos_converter.py
- **Documentation**: Comprehensive README and REFERENCE updates
- **Testing Framework**: Extensive test coverage

## Next Steps

### Immediate (Current Session):
1. ✅ Complete refactoring
2. ✅ Fix negative_prompt support
3. ✅ Add AI-powered video analysis
4. ✅ Update all documentation
5. ⏳ Commit all changes

### Next Development Session:
1. Begin Phase 2: Prompt Upsampling
   - Research upsampling implementation
   - Create remote execution script
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