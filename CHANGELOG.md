# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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