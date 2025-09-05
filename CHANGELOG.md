# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Query and list functionality for service layer (Chunk 4)**
  - New `list_prompts()` method in WorkflowService with model type filtering and pagination
  - New `list_runs()` method in WorkflowService with status and prompt_id filtering
  - New `search_prompts()` method for full-text case-insensitive search
  - New `get_prompt_with_runs()` method for detailed prompt view with all associated runs
  - All query methods return dictionaries optimized for CLI display
  - Comprehensive error handling with graceful fallback to empty results

- **New CLI commands for data exploration**
  - `cosmos list prompts` - List all prompts with rich table display and filtering options
  - `cosmos list runs` - List all runs with color-coded status display
  - `cosmos search <query>` - Search prompts with highlighted text matches
  - `cosmos show <prompt_id>` - Show detailed prompt information with run history
  - All commands support `--json` flag for machine-readable JSON output
  - Pagination support with `--limit` option
  - Rich terminal UI with colored tables and formatted output

### Fixed
- Fixed WorkflowService query methods to match actual database schema (removed non-existent model_config and updated_at fields from Prompt model)

### Changed
- **BREAKING: Major service layer architecture refactoring (Chunk 3)**
  - **WorkflowOrchestrator simplified to ONLY handle GPU execution**
    - Removed all JSON file management and PromptSpec/RunSpec dependencies
    - New `execute_run()` method takes dictionaries and returns execution results
    - Simplified `run_prompt_upsampling()` to just take text and return enhanced text
    - Removed deprecated methods: `run()`, `run_full_cycle()`, `run_inference_only()`, `run_upscaling_only()`
    - Removed helper methods for video directories, workflow type detection, and completion logging
    - Clear separation: orchestrator handles ONLY inference, upscaling, and prompt enhancement

  - **CLI commands now use WorkflowService for all data operations**
    - All commands work with database IDs (ps_xxx for prompts, rs_xxx for runs) instead of JSON files
    - Database-first approach: no JSON files created except for dry-run preview
    - Prompt enhancement operations tracked as runs in the database with proper lifecycle management
    - Seamless integration between WorkflowService (data) and WorkflowOrchestrator (execution)

  - **Clear architectural boundaries established**
    - WorkflowService: Business logic, data persistence, validation, transaction safety
    - WorkflowOrchestrator: GPU execution, inference, upscaling, prompt enhancement (no data persistence)
    - CLI: User interface layer connecting service and orchestrator with database IDs
    - Complete separation of concerns with no mixed responsibilities

### Added
- **Service layer implementation for workflow operations**
  - New `WorkflowService` class providing business logic for prompt and run management
  - `create_prompt()` method with model type validation and input sanitization
  - `create_run()` method with UUID-based ID generation to prevent collisions
  - `get_prompt()` and `get_run()` methods for retrieving entities by ID
  - Custom `PromptNotFoundError` exception for better error handling
  - Security improvements: max prompt length (10,000 chars), null byte removal
  - Model type validation enforcing supported types: transfer, reason, predict
  - Transaction safety with flush/commit pattern for data consistency
  - Parameterized logging throughout for debugging and audit trails
  - Returns dictionaries optimized for CLI display instead of raw ORM objects
  - Complete test coverage with 27 unit tests following TDD principles

- **Database foundation with flexible AI model support**
  - New `cosmos_workflow/database/` module with SQLAlchemy-based models
  - Support for multiple AI models (transfer, reason, predict) through flexible JSON schema
  - `Prompt` model with configurable inputs and parameters for any AI model type
  - `Run` model for tracking execution lifecycle with real-time status updates
  - `Progress` model for granular progress tracking during uploading, inference, and downloading
  - Comprehensive security validation: path traversal protection, input sanitization
  - Connection management with automatic session handling and transaction safety
  - JSON column flexibility allows easy addition of future AI models without schema changes
  - Built-in validation for percentage ranges, required fields, and data integrity
  - Complete test coverage with 50+ unit tests following TDD principles

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
