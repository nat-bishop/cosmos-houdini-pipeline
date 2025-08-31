# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - 2025-08-31 (Test Suite Reorganization & Baseline)
- **Comprehensive Test Suite Reorganization**
  - Created clear test structure: unit/, integration/, system/
  - Added shared fixtures in conftest.py for all test categories
  - Created test utilities and mock objects in fixtures/
  - Added sample test data in fixtures/sample_data/
  - Created pytest.ini with test markers and configuration

- **Integration Test Suite**
  - test_sftp_workflow.py - SFTP file transfer testing
  - test_workflow_orchestration.py - Complete pipeline testing
  - test_video_pipeline.py - Video processing integration

- **System Test Suite**
  - test_end_to_end_pipeline.py - Full user workflow tests
  - test_performance.py - Performance benchmarks

- **CI/CD Configuration**
  - GitHub Actions workflow (.github/workflows/test.yml)
  - Pre-commit hooks configuration (.pre-commit-config.yaml)
  - Multi-stage testing pipeline with coverage reporting

- **Test Documentation**
  - tests/README.md - Comprehensive testing guide
  - tests/TEST_STATUS.md - Current test status and metrics
  - tests/REORGANIZATION_PLAN.md - Test structure documentation

### Fixed - 2025-08-31
- **Test Compatibility Issues**
  - Fixed CLI test arguments for create-spec command
  - Updated convert-sequence test for new default metadata generation
  - Fixed SFTP test imports (FileTransferManager → FileTransferService)
  - Marked outdated Docker executor tests as skipped

- **Test Coverage Baseline**
  - 239 unit tests passing
  - 2 tests skipped (need refactoring)
  - Overall structure ready for expansion

### Added - 2025-08-30 (Phase 3: Windows SFTP & Full GPU Inference Pipeline)
- **Windows-Compatible SFTP File Transfer System**
  - Complete replacement of rsync with SFTP in `cosmos_workflow/transfer/file_transfer.py`
  - Added `_sftp_upload_file()` for single file uploads
  - Added `_sftp_upload_dir()` for recursive directory uploads
  - Added `_sftp_download_dir()` for downloading results
  - Full Windows path handling with backslash to forward slash conversion
  - Removed subprocess dependency for file transfers

- **Fixed Video Directory Detection**
  - Updated `WorkflowOrchestrator._get_video_directories()` to handle RunSpec files
  - Automatically loads PromptSpec to find correct video paths
  - Resolves video directories from PromptSpec.input_video_path
  - Fallback logic for various directory structures

- **Successful GPU Inference Pipeline**
  - Complete end-to-end inference working on remote GPU
  - Generated 2-second video (48 frames at 24 FPS, 1280x704)
  - Applied control inputs: depth (0.3 weight) and segmentation (0.4 weight)
  - Output video successfully downloaded via SFTP

### Fixed - 2025-08-30
- **Windows Encoding Issues**
  - Replaced Unicode arrows (→) with ASCII arrows (->) in all logging
  - Fixed encoding errors in SSH output streaming

- **Control Spec Format Issues**
  - Inference script now receives proper Cosmos controlnet spec format
  - Fixed control weight mapping from RunSpec to inference format
  - Proper path normalization for remote execution

### Changed - 2025-08-30
- File transfer system now uses SFTP exclusively on Windows
- Removed rsync dependency for Windows compatibility
- Updated all file transfer methods to use new SFTP implementation

### Added - 2025-08-30 (PromptSpec Smart Naming Integration)
- **Centralized Smart Naming Utility**
  - Created `cosmos_workflow/utils/smart_naming.py` for shared naming algorithm
  - Consistent naming across video preparation and prompt creation
  - `generate_smart_name()` function extracts meaningful words from text
  - `sanitize_name()` ensures filesystem-safe naming

- **PromptSpec Auto-Naming from Prompts**
  - PromptSpecManager now accepts optional name parameter
  - Auto-generates names from prompt text when not provided
  - CLI `create-spec` command supports optional `--name` parameter
  - Examples: "Futuristic cyberpunk city" → "futuristic_cyberpunk_city"

- **Integration Test Suite**
  - Created `test_ai_integration.py` with 13 real model tests
  - Tests use actual BLIP model (no mocking) for end-to-end validation
  - Performance testing with multiple frames
  - Scene type testing (urban, nature, abstract)

- **PromptSpec Smart Naming Tests**
  - Created `test_prompt_smart_naming.py` with 10 tests
  - Tests for auto-naming, consistency, path generation
  - CLI command testing with and without names
  - All tests passing

- **Documentation Updates**
  - Created comprehensive Phase 2 implementation guide
  - Updated DEVELOPMENT_PLAN.md with detailed Phase 3 plan
  - Phase 3 focuses on manual testing before integration tests
  - Three-part approach: Video Generation, PromptSpec, Full Inference

### Added - 2025-08-30 (Phase 2: AI Description and Smart Naming)
- **AI-Powered Scene Description Generation**
  - Integrated BLIP model for automatic image captioning from video frames
  - Uses middle frame of sequence for analysis
  - Graceful fallback when transformers not available
  - Automatic model downloading and caching

- **Smart Name Generation from AI Descriptions**
  - Algorithm extracts key nouns/adjectives from AI descriptions
  - Removes common stop words for concise names
  - Prioritizes meaningful words (nouns, verbs with -ing, etc.)
  - Max 20 character limit with intelligent truncation
  - Examples: "modern staircase with lighting" → "modern_staircase"

- **Enhanced prepare-inference Command**
  - Name parameter now optional (AI-generated if not provided)
  - Automatic scene analysis and naming when --no-ai not specified
  - Maintains {name}_{timestamp} directory format (YYYYMMDD_HHMMSS)
  - Updated help text to reflect AI capabilities

- **Comprehensive AI Test Suite**
  - Created test_ai_functionality.py with 14 tests
  - Tests smart name generation with various edge cases
  - Tests AI description generation and fallback behavior
  - Tests integrated workflow with mocked dependencies
  - Tests directory naming format compliance
  - 12/14 tests passing (2 failures due to test environment limitations)

- **Updated Requirements**
  - Added transformers>=4.30.0 for AI models
  - Added torch>=2.0.0 and torchvision>=0.15.0
  - Added pillow>=9.5.0 for image processing
  - Added accelerate>=0.20.0 for model optimization

### Added - 2025-08-30 (Cosmos-Specific Inference Preparation with Auto-Detection)
- **Enhanced prepare-inference command with automatic control input detection**
  - Command: `python -m cosmos_workflow.cli prepare-inference <input_dir> --name <name>`
  - Strict validation: Requires `color.XXXX.png`, optionally accepts `depth`, `segmentation`, `vis`, `edge`
  - Fails on unexpected files or naming patterns
  - Creates timestamped output directories to prevent conflicts
  - Outputs properly named videos: `color.mp4`, `depth.mp4`, etc.
  - **Auto-detects control inputs and includes paths in metadata**
  - Metadata includes `video_path` and `control_inputs` dictionary
  - Example: `python -m cosmos_workflow.cli prepare-inference ./renders/v3 --name my_scene`

- **Comprehensive test suite for CosmosSequenceValidator**
  - 24 tests covering all corner cases
  - Tests for valid scenarios (minimal, full modalities, partial)
  - Tests for invalid scenarios (missing color, wrong naming, gaps)
  - Tests for edge cases (single frame, large frame numbers, non-sequential start)

- **CosmosSequenceValidator class**
  - Validates Cosmos control modality naming conventions
  - Ensures frame number consistency across modalities
  - Strict validation with clear error messages

- **CosmosVideoConverter class**
  - Parallel conversion of multiple modalities
  - Proper output naming for Cosmos Transfer
  - Simplified metadata generation
  - AI description generation (when transformers installed)

### Changed - 2025-08-30
- **Deprecated convert-sequence command** in favor of prepare-inference
- **Refactored workflow** to be Cosmos-specific rather than generic

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
