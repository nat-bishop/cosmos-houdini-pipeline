# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
