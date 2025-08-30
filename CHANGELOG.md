# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 2025-08-30 (Part 2 - WorkflowOrchestrator Integration)
- **Integrated Upsampling into WorkflowOrchestrator**
  - Created `cosmos_workflow/workflows/upsample_integration.py` - Mixin for upsampling
    - `run_prompt_upsampling()` - Batch upsampling with remote GPU execution
    - `run_single_prompt_upsampling()` - Single prompt convenience method
    - `run_prompt_upsampling_from_directory()` - Directory batch processing
    - Full integration with file transfer and Docker execution
  - Updated `WorkflowOrchestrator` to inherit from `UpsampleWorkflowMixin`
  - Added CLI command `upsample` with options:
    - Input file or directory support
    - Video preprocessing controls (resolution, frames)
    - GPU configuration (num-gpu, cuda-devices)
    - Save directory for upsampled prompts
  - Added `run_prompt_upsampling()` function in CLI for command handling

### Added - 2025-08-30 (Part 1 - Core Implementation)
- **Phase 2: Prompt Upsampling System**
  - Created `scripts/upsample_prompts.py` - Python script for batch prompt upsampling
    - Video preprocessing to avoid vocab out of range errors (downscales to 480p)
    - Batch processing with persistent model loading
    - JSON input/output for integration
    - Error handling with fallback to original prompts
    - Direct usage of PixtralPromptUpsampler without full inference
  - Created `scripts/upsample_prompt.sh` - Bash wrapper for Docker execution
    - Multi-GPU support via torchrun
    - Configurable preprocessing parameters
    - Integration with existing Docker infrastructure
  - Created `PHASE2_IMPLEMENTATION.md` - Complete implementation documentation
    - Detailed problem analysis and solution approach
    - Configuration options and JSON formats
    - Integration points with existing workflow
  - Created comprehensive test suite for upsampling system:
    - `tests/test_upsample_prompts.py` - Unit tests (8 tests, all passing)
      - Video preprocessing and downscaling tests
      - Batch processing logic tests
      - Error handling and recovery tests
      - CLI interface tests
      - Environment variable handling for torchrun
      - Refactored to work without torch/cosmos dependencies
    - `tests/test_upsample_integration.py` - Integration tests (template for future)
      - PromptSpec system integration patterns
      - Docker executor integration patterns
      - File transfer integration patterns
      - Workflow orchestrator integration patterns
      - Error recovery scenarios
    - `tests/test_upsample_workflow.py` - End-to-end workflow tests (template for future)
      - Complete workflow from prompt creation to upsampling
      - RunSpec creation with upsampled prompts
      - Bash script execution tests
      - CLI workflow tests
      - Large batch and parallel processing tests
      - Video preprocessing workflow tests
- **Documentation System**
  - Created `CHANGELOG.md` - Comprehensive change tracking
    - Following Keep a Changelog format
    - Semantic versioning adherence
    - Clear documentation type distinctions

### Changed - 2025-08-30
- **Documentation Updates**
  - Slimmed down `CLAUDE.md` from 395 to 134 lines for better efficiency
  - Added known issues section documenting vocab out of range error
  - Added documentation guidelines distinguishing between:
    - `CHANGELOG.md` - Track code changes (this file)
    - `README.md` - User-facing documentation
    - `REFERENCE.md` - Technical API documentation
    - `CLAUDE.md` - AI assistant guidance

## [1.0.0] - 2025-08-29

### Added
- **Complete System Modernization** (commit b281e94)
  - Migrated from bash scripts to Python orchestration
  - Converted config from shell to TOML format
  - Added comprehensive pytest test suite (3,264+ lines)
  - Implemented modern schema-based prompt system

### Changed
- **Prompt System Refactor**
  - Separated PromptSpec from RunSpec for reusability
  - Added hash-based unique IDs for traceability
  - Implemented date-organized directory structure
  - Added schema validation and type safety

### Added
- **Testing Infrastructure**
  - Unit tests for all components
  - Integration tests with mocked SSH/Docker
  - High code coverage targets (>80%)
  - Pre-push testing hooks

## Documentation Types

### When to Update Each Document:
- **CHANGELOG.md**: Every code change, feature addition, or bug fix
- **README.md**: User-facing features, installation steps, usage examples
- **REFERENCE.md**: API changes, new functions, technical specifications
- **CLAUDE.md**: Workflow changes, project structure updates, new conventions