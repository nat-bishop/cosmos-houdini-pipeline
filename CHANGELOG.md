# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 2025-08-30 (CLI Convert-Sequence Command)
- **New convert-sequence CLI command for PNG to video conversion**
  - Command: `python -m cosmos_workflow.cli convert-sequence <input_dir>`
  - Validates PNG sequences before conversion (detects gaps, naming patterns)
  - Converts PNG frames to MP4 video with configurable FPS
  - Optional resolution standardization (720p, 1080p, 4k, or custom WxH)
  - Optional AI-powered metadata generation with scene analysis
  - Generates both video file and metadata JSON
  - Comprehensive error handling and verbose output
  - Example: `python -m cosmos_workflow.cli convert-sequence ./renders/sequence/ --fps 30 --resolution 1080p --generate-metadata`

- **Comprehensive test suite for convert-sequence command**
  - Created `tests/test_cli_convert_sequence.py` with 14 tests
  - Tests cover all command options and error scenarios
  - Mock-based testing for VideoProcessor and VideoMetadataExtractor
  - Tests for validation failures, custom paths, resolution handling
  - CLI integration tests for argument parsing
  - All tests passing with good coverage

### Added - 2025-08-30 (PNG Sequence to Video Support)
- **Restored and Enhanced VideoProcessor Class**
  - Restored VideoProcessor from commit d0e2607 to `cosmos_workflow/local_ai/video_metadata.py`
  - Added `validate_sequence()` method to validate PNG sequences
    - Detects missing frames and gaps in sequence
    - Validates PNG file integrity
    - Supports multiple naming patterns (frame_000.png, image_0.png, etc.)
    - Returns detailed validation report with issues
  - Enhanced `create_video_from_frames()` for robust PNG to MP4 conversion
    - Handles mixed resolutions by resizing to first frame size
    - Continues processing even with some corrupted frames
    - Proper error handling and logging
  - Improved `standardize_video()` for FPS and resolution adjustments
    - Supports upscaling and downscaling
    - Handles edge cases in FPS conversion
  - Added `extract_frame()` for frame extraction with optional save
  
- **Comprehensive Test Coverage for VideoProcessor**
  - Created 24 comprehensive tests covering all methods
  - Edge case testing: corrupted files, missing frames, large gaps
  - Mixed resolution handling tests
  - Video standardization and upscaling tests
  - End-to-end workflow validation
  - All tests passing with good coverage
  
- **Module Export Updates**
  - Updated `cosmos_workflow/local_ai/__init__.py` to export VideoProcessor
  - VideoProcessor now available from main module import

### Changed - 2025-08-30 (Config Refactoring)
- **Removed backward compatibility from ConfigManager**
  - Removed deprecated `config` property that returned raw dictionary
  - All code now uses typed `RemoteConfig` and `LocalConfig` dataclasses
  - Cleaner, more maintainable configuration access pattern
  
- **Refactored UpsampleWorkflowMixin configuration access**
  - Updated to use `config_manager.get_remote_config()` and `get_local_config()`
  - Removed all raw dictionary access patterns (`self.config["paths"][...]`)
  - Improved type safety and IDE support
  
- **Updated test fixtures for new API**
  - Fixed `test_upsample_integration.py` to use correct DirectoryManager initialization
  - Updated PromptSpec usage to match current API (no metadata field)
  - Note: Some integration tests still need updating for full compatibility

- **Documentation reorganization**
  - Merged DEVELOPMENT_PLAN.md into CHANGELOG.md as primary change log
  - Moved PHASE2_IMPLEMENTATION.md to `docs/implementation/phase2_prompt_upsampling.md`
  - CHANGELOG.md now serves as comprehensive development history and planned work

- **Removed emoji indicators from CLI output**
  - Replaced emoji indicators (✅, ❌, 🚀, etc.) with text labels ([SUCCESS], [ERROR], [INFO], etc.)
  - Better compatibility with various terminal environments
  - More professional CLI output

## Development History

### 2025-08-30 - Phase 2 Completed: Prompt Upsampling Feature
**Implementation Summary:**
Successfully implemented decoupled prompt upsampling that works with high-resolution videos by preprocessing them to avoid vocab out of range errors.

**Core Components Added:**
1. **Scripts:**
   - `scripts/upsample_prompts.py` - Python batch upsampling with video preprocessing
   - `scripts/upsample_prompt.sh` - Bash wrapper for Docker execution

2. **WorkflowOrchestrator Integration:**
   - `cosmos_workflow/workflows/upsample_integration.py` - UpsampleWorkflowMixin
   - Three main methods: batch, single, and directory upsampling
   - Full SSH/Docker/FileTransfer integration

3. **CLI Command:**
   - `python -m cosmos_workflow.main upsample <input> [options]`
   - Supports single files and directories
   - Video preprocessing options (resolution, frames)
   - GPU configuration

4. **Test Coverage:**
   - `tests/test_upsample_prompts.py` - 8 unit tests (all passing)
   - Tests cover: video preprocessing, batch processing, error handling, CLI parsing

**Key Features:**
- Batch processing with model persistence for efficiency
- Video resolution downsampling (480p default) to avoid errors
- Frame reduction options (2 frames default)
- PromptSpecs with `upsampled=true` flag and original prompt stored
- Memory optimization with `--offload_prompt_upsampler` flag

**Outstanding Tasks:**
- Fix integration tests API mismatches
- Add end-to-end tests with mocked SSH/Docker

### 2025-08-29 - Phase 1 Completed: System Refactoring
**Implementation Summary:**
Complete modernization from bash scripts to Python orchestration with TOML configuration, comprehensive testing, and schema-based prompt management.

**Major Changes:**
- Migrated from bash scripts to Python orchestration
- Converted config from shell to TOML format
- Added comprehensive pytest test suite (3,264+ lines)
- Implemented modern schema-based prompt system (PromptSpec/RunSpec separation)
- Date-organized directory structure with hash-based IDs

## Planned Development Phases

### Phase 3: Add Batch Inference Support (Not Started)
**Goal**: Enable processing multiple PromptSpecs in a single inference run.

**Requirements:**
- Support Cosmos Transfer's batch inference options
- Handle multiple controlnet specs
- Optimize GPU memory usage for batch processing
- Track individual job status within batches

**Planned Tasks:**
- Study Cosmos Transfer batch inference implementation
- Modify inference.sh to support batch mode
- Create batch job specification schema
- Implement batch job orchestration
- Add progress tracking for batch jobs
- Handle partial failures in batch processing
- Create CLI commands for batch operations
- Write tests for batch inference

### Phase 4: Add Support for Running Batches of Jobs (Not Started)
**Goal**: Enable overnight batch processing with parameter randomization.

**Requirements:**
- Sequential job execution
- Parameter randomization options
- Support for testing single prompt with varied parameters
- Job scheduling and queue management
- Result aggregation and reporting

**Randomization Options:**
- Control weights (vis, edge, depth, seg)
- Inference parameters (num_steps, guidance, sigma_max)
- Seeds for reproducibility testing
- Control input combinations
- Blur strength and canny threshold variations

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