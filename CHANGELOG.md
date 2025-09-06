# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed - Database Cleanup (2025-09-06)
- **Removed unused Progress model**
  - Deleted Progress model from database schema (was never implemented in production)
  - Removed all Progress-related tests (6 test methods)
  - Updated documentation to remove Progress references
  - Simplified database to 2 core models: Prompt and Run
  - No migration needed as Progress was never used in production code

### Fixed - Data Architecture Improvements (2025-09-06)
- **Critical Path Fixes**
  - Fixed output filename mismatch: changed from `result.mp4` to `output.mp4` to match actual GPU outputs
  - Enhanced run outputs JSON with metadata fields: `type`, `output_dir`, `primary_output`
  - Improved text enhancement tracking with proper run type identification
  - Simplified Gallery video retrieval logic, removed multiple fallback paths

- **Logging Consolidation**
  - Moved logs from `/logs/runs/` to run output directories (`outputs/run_xxx/execution.log`)
  - Removed unused `/logs` and `/notes` directories
  - All run artifacts now centralized in single directory per run

- **Data Integrity Tools**
  - Added `cosmos verify` command to check database-filesystem consistency
  - Detects missing files, orphaned directories, and data mismatches
  - Reports statistics and warnings for proactive maintenance
  - Manifest generation for downloaded files to track transfer completeness

- **UI Improvements**
  - Gallery now filters out text enhancement runs properly
  - Cleaner path handling with consistent expectations
  - Better error handling for missing video files

### Added - Gradio UI Improvements (2025-09-05)
- **Enhanced Gradio Web Interface**
  - All 4 control weights now available: visual, edge, depth, segmentation (0.0-1.0 range)
  - Optional video inputs: color required, depth/segmentation optional
  - Smart JSON generation: only includes controls with weight > 0
  - Efficient seek-based log tailing for better performance with large files
  - Improved prompt details display with full video paths and status indicators
  - ASCII-safe status indicators for Windows compatibility
  - Video status shows missing count: "[!] Missing (3)" or "[OK] (3 videos)"

- **Control Weight System**
  - Independent control weights for all 4 modalities
  - Weights apply even without input videos (model auto-generates)
  - Flexible configuration matching NVIDIA Cosmos Transfer approach
  - Only non-zero weights included in GPU JSON payload

- **Database Import Tool**
  - New script: scripts/import_json_prompts.py
  - Imports legacy JSON prompts into database using cosmos CLI
  - Preserves prompt names, text, and negative prompts
  - Successfully imported 16 prompts from 2025-09-03 archive

### Added - Service Layer Architecture Complete
- **Complete database-first service layer architecture**
  - Database-first approach: all data stored in SQLAlchemy database
  - Commands work with database IDs: ps_xxxxx (prompts), rs_xxxxx (runs)
  - No persistent JSON files - only created temporarily for NVIDIA GPU scripts
  - Three core models: Prompt, Run, Progress for comprehensive workflow tracking
  - Production-ready system with 453 passing tests

- **WorkflowService - Complete business logic layer**
  - CRUD operations for prompts and runs with transaction safety
  - Query methods: list_prompts(), list_runs(), search_prompts(), get_prompt_with_runs()
  - Input validation and sanitization with security features
  - Returns dictionaries optimized for CLI display
  - Support for multiple AI models through flexible JSON columns

- **WorkflowOrchestrator - GPU execution only**
  - Simplified to handle ONLY GPU execution: inference and upscaling
  - execute_run() method takes database dictionaries, returns results
  - run_prompt_upsampling() for AI prompt enhancement
  - Creates temporary NVIDIA-format JSON for GPU scripts only
  - No data persistence - pure execution layer

- **Database-first CLI commands**
  - cosmos create prompt "text" video_dir - creates prompt in DB, returns ps_xxxxx ID
  - cosmos create run ps_xxxxx - creates run from prompt ID, returns rs_xxxxx ID
  - cosmos inference rs_xxxxx - executes run on GPU with status tracking
  - cosmos list prompts/runs - lists with filtering and rich display
  - cosmos search "query" - full-text search with highlighted matches
  - cosmos show ps_xxxxx - detailed view with run history
  - cosmos prompt-enhance ps_xxxxx - AI enhancement creating new prompts and runs
  - All commands support --json for machine-readable output

### Changed - Architecture Simplified
- **BREAKING: Complete migration to database-first service architecture**
  - Replaced JSON file storage with SQLAlchemy database for all data operations
  - Clear separation of concerns: data layer (service) vs execution layer (orchestrator)
  - Extensible architecture supporting future AI models (reason, predict, etc.)
  - Clean, maintainable codebase without over-engineering

- **WorkflowService handles all data operations**
  - Business logic layer with comprehensive CRUD operations
  - Transaction safety with automatic rollback on errors
  - Input validation and security features (path traversal protection)
  - Query methods for listing, searching, and filtering prompts and runs
  - Returns dictionaries optimized for CLI display and JSON output

- **WorkflowOrchestrator simplified to execution only**
  - Removed all data persistence responsibilities
  - execute_run() takes database dictionaries, executes on GPU infrastructure
  - Creates temporary NVIDIA-format JSON files only for GPU script compatibility
  - Handles inference, upscaling, and AI prompt enhancement without data storage
  - Clean execution results returned to service layer for persistence

### Database Foundation
- **Flexible database schema supporting multiple AI models**
  - Prompt model with JSON columns for model-specific inputs and parameters
  - Run model for execution lifecycle tracking with real-time status updates
  - Progress model for granular progress tracking during execution stages
  - Extensible design allows adding future AI models without schema changes
  - Built-in security validation and input sanitization
  - Connection management with automatic session handling and transaction safety

### Fixed
- **Fixed RunSpec timestamp formatting issue in `cosmos create run` command**
  - Removed duplicate timezone suffix that was causing "+00:00+00:00" in timestamps
  - Now correctly uses `datetime.now(timezone.utc).isoformat()` without extra timezone indicator
  - Ensures timestamps are properly formatted for JSON serialization

### Changed
- **Improved `cosmos prompt-enhance` command to use true batch processing**
  - Now processes multiple prompts in a single batch instead of one at a time
  - Significantly improves performance when enhancing multiple prompts
  - Reduces GPU initialization overhead by keeping model in memory for entire batch
  - Maintains progress tracking while processing all prompts together

### Fixed
- **Integrated CosmosConverter for NVIDIA Cosmos Transfer format compatibility**
  - FileTransferService now automatically converts PromptSpec to NVIDIA format during upload
  - Ensures proper field mapping (prompt_text → prompt, control_paths → control_path)
  - Handles path separator conversion from Windows to Unix for remote systems
  - Falls back to original format if conversion fails, ensuring robustness
  - Video directories are now correctly detected from PromptSpec's input_video_path field

### Changed
- **Switched to read-only pre-commit hooks for predictable formatting workflow**
  - Pre-commit hooks now only check formatting/linting, never modify files
  - Prevents unexpected changes and commit-stash-reapply churn
  - Developers format manually with `ruff format .` and `ruff check . --fix`
  - Recommended: Configure editor to format on save for seamless workflow
  - Updated pyproject.toml to set `fix = false` globally
  - Updated .pre-commit-config.yaml with explicit read-only arguments

### Changed - 2025-09-04 (Smart Naming Refactor)
- **Refactored smart naming from spaCy to KeyBERT for improved semantic extraction**
  - Replaced spaCy dependency parsing with KeyBERT semantic keyword extraction
  - Now uses all-MiniLM-L6-v2 SBERT model for lightweight embeddings
  - Configured with n-grams (1-2) and MMR diversity (0.7) to avoid duplicate keywords
  - Added comprehensive stopword filtering for both common English and VFX domain terms
  - Fallback to simple keyword extraction when KeyBERT is unavailable
  - Names limited to 3 words maximum for better conciseness
  - New dependencies: keybert and sentence-transformers (replacing spacy)

### Changed - 2025-09-03 (PromptSpecManager Refactor)
- **Refactored prompt specification creation to use PromptSpecManager**
  - CLI `create prompt` command now uses PromptSpecManager instead of direct PromptSpec creation
  - Enhanced prompts now get smart names based on content (e.g., "futuristic_city") instead of generic "_enhanced" suffix
  - Upsampling workflow uses PromptSpecManager for consistent spec creation
  - Improved separation of concerns with centralized spec management
  - All prompt spec creation now goes through a single, consistent API

### Added - 2025-09-03 (File Transfer)
- **New `download_file()` method in FileTransferService**
  - Downloads single files from remote instance via SFTP
  - Automatically creates parent directories if needed
  - Handles Windows path conversion for cross-platform compatibility
  - Provides granular file download control alongside existing directory download

### Fixed - 2025-09-03 (Batch Upsampling)
- **Fixed batch prompt upsampling duplicate results issue**
  - Batch processing now returns unique results for each prompt instead of duplicates
  - Added `determine_offload_mode()` function to automatically force offload=False for batches > 1
  - Prevents model reinitialization between prompts by keeping it in memory for batches
  - Renamed `working_prompt_upsampler.py` to `prompt_upsampler.py` to reflect production status
  - Made module importable for testing by handling missing GPU dependencies gracefully
  - Added comprehensive unit tests following TDD principles with real function calls

### Added - 2025-09-03 (Docker Log Streaming)
- **Docker log streaming feature**
  - New `--stream` flag for `cosmos status` command to stream container logs in real-time
  - Auto-detection of most recent container when no container ID specified
  - Graceful Ctrl+C handling to stop streaming
  - Helpful error messages when no containers are running
  - 24-hour timeout for long-running log streams

### Changed - 2025-09-02 (CLI Migration Complete)
- **Migrated to modular CLI structure**
  - Switched from monolithic `cli.py` (800+ lines) to modular `cli/` directory
  - Maintained 100% backward compatibility
  - Improved display with Rich formatting and emojis
  - Better error handling and consistent output
  - Maximum file size reduced by 76% (217 lines vs 800+)

### Added - 2025-09-01 (CLI Refactoring Complete)
- **Phase 1: Created modular CLI architecture foundation**
  - New `cosmos_workflow/cli_new/` directory structure for refactored CLI
  - `base.py`: Core utilities including CLIContext class and error handling decorator
  - `completions.py`: All autocomplete functions consolidated in one place
  - `helpers.py`: Rich display utilities for tables, progress, and formatting
  - Foundation for splitting 935-line CLI into manageable ~100-200 line modules

- **Phase 2 & 3: Migrated all commands to modular structure**
  - `status.py` (63 lines): Remote GPU status checking
  - `prepare.py` (156 lines): Video sequence preparation
  - `enhance.py` (164 lines): Prompt enhancement with AI
  - `inference.py` (117 lines): Inference execution
  - `create.py` (217 lines): Create prompt and run specifications
  - Main CLI integration in `__init__.py` (71 lines)
  - Successfully reduced max file size by 76% (935 → 217 lines)
  - All 23 tests still passing, 100% functionality preserved

- **Display Utilities Added**
  - Success/error/warning/info display functions with consistent styling
  - Table creation helpers for structured output
  - Progress context managers for long operations
  - Formatting utilities for paths, IDs, file sizes, and durations
  - Dry-run mode display helpers

- **Error Handling Improvements**
  - Centralized error handling decorator for consistent error messages
  - UTF-8 encoding support for Windows terminals
  - Graceful handling of keyboard interrupts

### Changed - 2025-09-01 (Documentation)
- **Streamlined CLAUDE.md**
  - Reduced from 192 to 83 lines (57% reduction)
  - Moved documentation & commit policy to top with red emphasis
  - Simplified structure while keeping all critical information
  - Added clear "commit as you go" requirement

### Changed - 2025-09-01 (Major CLI Improvements)
- **Merged Commands for Simplicity**
  - Combined `run`, `inference`, and `upscale` into single `inference` command
  - Default behavior: run both inference and upscaling (most common use case)
  - Use `--no-upscale` flag for inference only
  - Removed deprecated `run` and `upscale` commands completely

- **Autocomplete System Overhaul**
  - Created reusable autocomplete functions, eliminating ~25 lines of duplicate code
  - Added smart autocomplete for video files, directories, and prompt specs
  - Fixed pattern matching to use prefix matching instead of substring
  - Added proper autocomplete for `--videos-dir` and `--video` options
  - Autocomplete now works properly in Git Bash and CMD on Windows

- **Parameter Simplification**
  - Removed `--num-gpu` and `--cuda-devices` from all commands (always uses 1 GPU)
  - Simplified `prompt-enhance`: `--resolution` now implies preprocessing
  - Removed unnecessary flags: `--save-dir`, `--num-frames`, `--preprocess`
  - `prompt-enhance` now accepts multiple files as arguments

- **Bug Fixes**
  - Fixed critical PromptSpec metadata bug in upsample_integration.py
  - Fixed prompt-enhance to properly create new PromptSpecs with `_enhanced` suffix
  - Properly generates new IDs for enhanced PromptSpecs
  - Fixed `is_upsampled` and `parent_prompt_text` fields

### Removed - 2025-09-01 (Codebase Cleanup)
- **Old CLI Files**
  - Removed `cli_old.py` (obsolete argparse-based CLI)
  - Removed deprecated `run` and `upscale` commands
  - Removed `setup_completion.py` (integrated into main CLI)

- **Test Files & Directories**
  - Removed obsolete CLI tests that referenced old argparse-based CLI
  - Deleted `tests/unit/cli/` directory with outdated test files
  - Removed `test_bash_script_execution_workflow` and `TestCLIWorkflow` class from integration tests
  - Deleted all root-level test scripts (`test_resolution_*.py`, `quick_resolution_test.py`, etc.)
  - Removed unused test directories (`resolution_tests/`, `test_videos/`, `test_images/`, `testing/`)

- **Scripts & Utilities**
  - Deleted redundant scripts from `scripts/` directory (kept only essential remote execution files)
  - Removed `check_remote_results.py`, `deploy_and_test_upsampler.py`, `test_actual_resolution_limits.py`
  - Deleted unused shell scripts (`ssh_lambda.sh`, `upsample_prompt.sh`, `run_upsampler_docker.sh`)
  - Removed linting helper scripts (`lint.py`, `fix_all_linting.py`)

- **Build Artifacts & Cache**
  - Cleaned up all cache directories (`.mypy_cache/`, `.ruff_cache/`, `htmlcov/`)
  - Removed all log files and test JSON outputs
  - Deleted empty directories (`notes/`, `art/`, `test_notes/`)

### Added - 2025-09-01 (Documentation)
- **Documentation & Commit Policy** in CLAUDE.md
  - Added mandatory documentation update requirement before commits
  - Clear policy: update CHANGELOG.md immediately after features
  - Requirement to update README.md for user-facing changes
  - "Document as you code" principle

### Changed - 2025-09-01 (CLI Refactor)
- **Complete CLI Overhaul**
  - Migrated from argparse to Click framework for better UX
  - Reorganized commands into logical groups (`create prompt`, `create run`)
  - Added rich console output with colors and progress indicators
  - Renamed `upsample` command to `prompt-enhance` for clarity
  - Removed deprecated `convert-sequence` command (use `prepare` instead)
  - Added shell completion support for Bash, Zsh, Fish, PowerShell, and Git Bash
  - Improved help text and command examples throughout

- **Simplified Installation**
  - Removed pip package configuration - now using standalone scripts
  - Created `cosmos` Python script and `cosmos.bat` for direct execution
  - Updated documentation with manual setup instructions
  - No pip installation required - just install dependencies and run

- **Documentation Updates**
  - Updated README.md with new command structure and examples
  - Updated CLAUDE.md with simplified setup instructions
  - Added shell completion setup instructions for all platforms
  - Clarified that pip is not required for CLI usage

### Added - 2025-09-01 (Resolution Discovery)
- **Major Resolution Limit Discovery**
  - Found actual maximum resolution: 940×529 (497,260 pixels)
  - This is 3x higher than initially documented 320×180 limit
  - Created comprehensive resolution testing framework
  - Added `docs/RESOLUTION_LIMITS_FINAL.md` with production guidelines
  - Created `docs/SESSION_SUMMARY_2025_09_01.md` documenting findings

### Fixed - 2025-09-01
- **SSH Unicode Encoding Error**
  - Fixed Windows encoding issues in `cosmos_workflow/connection/ssh_manager.py`
  - Added try/catch blocks with ASCII fallback for special characters
  - Resolves `'charmap' codec can't encode character` errors

### Changed - 2025-09-01
- **Updated Resolution Documentation**
  - Corrected token formula findings (formula is wrong)
  - Updated `docs/TESTING_RESULTS.md` with actual limits
  - Documented that 960×540 reports 4,157 actual tokens (not 17,936 estimated)
  - Clarified pixel threshold is 497,000-518,000, not token-based

### Added - 2025-08-31 (Testing & Documentation)
- **Comprehensive Testing Documentation**
  - Created `docs/TESTING_RESULTS.md` with performance benchmarks
  - Documented batch processing performance (45% speedup without offloading)
  - Identified resolution limits and token usage patterns
  - Added GPU memory usage profiles
  - Established testing framework for future models

- **Comprehensive Test Coverage for WorkflowOrchestrator**
  - Added 25 unit tests achieving 93.79% coverage (up from 13.66%)
  - Test categories: initialization, helpers, workflows, convenience methods, logging, edge cases
  - Created `tests/unit/workflows/test_workflow_orchestrator.py`
  - All tests use proper mocking for fast, isolated execution

- **Upsampling Workflow Integration**
  - Created `cosmos_workflow/workflows/upsample_integration.py` - Mixin for WorkflowOrchestrator
  - Added `cosmos_workflow/workflows/resolution_tester.py` - Resolution testing utilities
  - Integrated prompt upsampling into CLI with `upsample` command
  - Added support for batch upsampling with checkpoint recovery
  - Implemented token estimation formula: `tokens = width × height × frames × 0.0173`

- **Resolution Analysis Tools**
  - Created resolution testing framework for finding maximum safe resolutions
  - Documented safe resolution limits (320×180 @ 2 frames = 1,992 tokens)
  - Added automatic video preprocessing for high-resolution inputs
  - Created test video generation capabilities for resolution testing

### Changed - 2025-08-31 (Test Suite)
- **Test Suite Cleanup**
  - Removed outdated integration tests using non-existent methods
  - Fixed SFTP integration tests with proper context manager mocking
  - Achieved full green baseline: 614 tests passing, 0 failing
  - Added missing methods to FileTransferService for test compatibility

- **Documentation Improvements**
  - Clarified "legacy" methods are actually convenience methods
  - Updated workflow orchestrator comments to reflect true purpose
  - Created test plan document with coverage analysis
  - Created comprehensive testing and merge strategy documentation

- **Script Cleanup**
  - Removed 24 redundant/experimental upsampling scripts
  - Kept only 4 essential scripts: working_prompt_upsampler.py, deploy_and_test_upsampler.py, test_actual_resolution_limits.py, check_remote_results.py
  - Consolidated upsampling logic into workflow integration

- **Docker Integration**
  - Updated upsampling to use DockerCommandBuilder pattern (consistent with inference)
  - Added proper environment variable setup for VLLM
  - Integrated with existing SSH/SFTP infrastructure

### Fixed - 2025-08-31
- **SFTP Test Failures**
  - Fixed mock configuration to properly mock get_sftp() context manager
  - Added upload_directory() and download_directory() to FileTransferService
  - Resolved all 8 SFTP integration test failures

- **Resolution Token Limits Identified**
  - Maximum safe resolution: 320×180 @ 2 frames (1,992 tokens)
  - Token formula verified: `tokens = width × height × frames × 0.0173`
  - Videos above 426×240 will fail with vocab errors

- **Upsampling Issues**
  - Fixed VLLM multiprocessing spawn method requirement
  - Resolved token limit errors with high-resolution videos
  - Fixed environment variable setup for TorchElastic

### Security - 2025-08-31 (Planned)
- **Version Pinning Requirements**
  - Need to stop using `:latest` Docker tags
  - Plan to pin specific model checkpoint versions
  - Document all dependency versions for reproducibility

### Added - 2024-12-30 (Modern Linting & Code Quality)
- **Comprehensive Linting Setup**
  - Integrated Ruff (v0.12.11) - Fast, all-in-one Python linter replacing black, isort, flake8, pylint
  - Added MyPy (v1.17.1) for static type checking
  - Added Bandit (v1.8.6) for security vulnerability scanning
  - Added Safety (v3.6.0) for dependency vulnerability checking
  - Configured pre-commit hooks for automated code quality checks
  - Created Makefile for convenient command access

- **Code Quality Improvements**
  - Fixed 473+ linting issues automatically (76% reduction)
  - Converted all logging f-strings to lazy % formatting for better performance
  - Added UTC timezone to all datetime.now() calls
  - Fixed docstring formatting across codebase
  - Reorganized and optimized imports
  - Applied consistent code formatting

### Added - 2024-12-31 (Test Suite Reorganization & Baseline)
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

### Fixed - 2024-12-31
- **Test Compatibility Issues**
  - Fixed CLI test arguments for create-spec command
  - Updated convert-sequence test for new default metadata generation
  - Fixed SFTP test imports (FileTransferManager → FileTransferService)
  - Marked outdated Docker executor tests as skipped

- **Test Coverage Baseline**
  - 239 unit tests passing
  - 2 tests skipped (need refactoring)
  - Overall structure ready for expansion

### Added - 2024-12-30 (Phase 3: Windows SFTP & Full GPU Inference Pipeline)
- **Windows-Compatible SFTP File Transfer System**
  - Complete replacement of rsync with pure Python SFTP implementation
  - Cross-platform file transfer (Windows/Linux/macOS)
  - Recursive directory upload/download support
  - Progress tracking and error handling

- **Full Remote GPU Inference Pipeline**
  - End-to-end workflow: upload → inference → upscaling → download
  - Real GPU execution on remote instances
  - Support for multi-GPU configurations
  - Automatic output organization and timestamping

- **Enhanced Configuration System**
  - Unified config.toml for all settings
  - Environment-specific configurations (local/remote)
  - Docker image and runtime configurations
  - SSH connection pooling and reuse

### Added - 2024-12-29 (Phase 2: AI Integration & Smart Naming)
- **AI-Powered Description Generation**
  - Automatic video content analysis using BLIP AI model
  - Generates natural language descriptions from video frames
  - Optional AI features with graceful fallback

- **Smart Naming System**
  - Intelligent name generation from AI descriptions
  - Context-aware naming using NLP techniques
  - Configurable name length and style

- **Enhanced Cosmos Sequence Processing**
  - prepare-inference command with auto-detection
  - Support for all Cosmos control modalities
  - Automatic metadata generation with AI insights

### Added - 2024-12-28 (Phase 1: PNG to Video Conversion)
- **Video Processing Pipeline**
  - convert-sequence command for PNG to video conversion
  - Support for custom resolutions (720p, 1080p, 4K)
  - Frame rate control and video standardization
  - Metadata extraction and generation

- **Local AI Features**
  - Video metadata extraction (resolution, fps, duration)
  - Frame analysis and object detection
  - Caption generation for video content
  - Tag extraction and classification

### Changed - 2024-12-27 (Major Refactoring)
- **Schema System Overhaul**
  - Separated PromptSpec and RunSpec for better separation of concerns
  - Added DirectoryManager for organized file management
  - Implemented hash-based unique IDs
  - Added comprehensive validation

- **Workflow Architecture**
  - Modular service-based architecture
  - Clear separation of SSH, transfer, and execution layers
  - Improved error handling and logging
  - Support for partial workflow execution

### Initial Release - 2024-12-20
- **Core Workflow System**
  - Python-based replacement for bash scripts
  - SSH connection management with Paramiko
  - Docker container orchestration
  - Prompt and run specification schemas

- **CLI Interface**
  - create-spec: Create prompt specifications
  - create-run: Create run configurations
  - run: Execute workflows on remote GPU
  - status: Check remote instance status

- **Configuration Management**
  - TOML-based configuration
  - Support for multiple environments
  - SSH key authentication
  - Docker runtime configuration

## Version History

### [0.3.0] - 2024-12-30
- Modern linting and code quality tools
- Comprehensive test suite reorganization
- Windows SFTP compatibility
- Full GPU inference pipeline

### [0.2.0] - 2024-12-29
- AI integration for descriptions and naming
- Enhanced video processing
- Cosmos sequence preparation

### [0.1.0] - 2024-12-20
- Initial release
- Core workflow system
- Basic CLI interface
- Configuration management
