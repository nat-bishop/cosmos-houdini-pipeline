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

### Documentation:
- Update README.md with new features
- Update REFERENCE.md with technical details
- Add inline documentation for complex logic
- Create usage examples for new features

### Testing:
- Write unit tests for all new functions
- Add integration tests for workflows
- Maintain >80% code coverage
- Test edge cases and error handling

### Code Quality:
- Follow existing code patterns
- Use type hints throughout
- Implement proper error handling
- Add logging for debugging
- Follow PEP 8 style guidelines

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

### Phase 1: Refactoring
- Status: Not Started
- Estimated Time: 2-3 days
- Priority: High

### Phase 2: Prompt Upsampling
- Status: Not Started
- Estimated Time: 3-4 days
- Priority: High

### Phase 3: Batch Inference
- Status: Not Started
- Estimated Time: 2-3 days
- Priority: Medium

### Phase 4: Batch Jobs
- Status: Not Started
- Estimated Time: 3-4 days
- Priority: Medium

## Next Steps

1. Commit current changes
2. Begin Phase 1 refactoring
3. Create tests for refactored code
4. Update documentation
5. Move to Phase 2 after refactoring is complete

---

*Last Updated: 2025-08-30*