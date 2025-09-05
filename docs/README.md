# Documentation

## Core Documentation

- **[Main README](../README.md)** - Project overview, architecture, and quick start guide
- **[API.md](API.md)** - Complete API reference for service layer architecture
- **[DATABASE.md](DATABASE.md)** - Database schema, models, and usage patterns
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - TDD workflow, testing guide, code conventions
- **[CHANGELOG](../CHANGELOG.md)** - Version history and service layer migration

## Architecture Documentation

- **Service Layer Architecture**: Database-first design with clean separation of concerns
  - **Data Layer**: WorkflowService handles all business logic and database operations
  - **Execution Layer**: WorkflowOrchestrator handles GPU execution only
  - **Interface Layer**: CLI commands work with database IDs (ps_xxx, rs_xxx)

- **Database-First Design**: No persistent JSON files, all data stored in SQLAlchemy database
- **Multi-Model Support**: Extensible schema supports current transfer/enhancement models and future AI models

## Project Configuration

- **[CLAUDE.md](../CLAUDE.md)** - Instructions for Claude AI assistant following TDD workflow

## Specialized Guides

- **[SHELL_COMPLETION.md](SHELL_COMPLETION.md)** - Shell completion setup for CLI commands
- **[BASH_SHORTCUTS.md](BASH_SHORTCUTS.md)** - Development productivity shortcuts

## System Status

- **Production Ready**: 453 passing tests with comprehensive coverage
- **Service Layer Complete**: Database-first architecture fully implemented
- **GPU Execution Verified**: End-to-end inference and enhancement workflows tested
- **Multi-Model Ready**: Extensible design supports future AI models

## Quick Reference

```bash
# Database operations
cosmos create prompt "text" video_dir    # Returns ps_xxxxx ID
cosmos create run ps_xxxxx               # Returns rs_xxxxx ID
cosmos list prompts [--json]             # List with rich tables
cosmos search "query" [--json]           # Full-text search

# GPU execution
cosmos inference rs_xxxxx                # Run on GPU with tracking
cosmos prompt-enhance ps_xxxxx           # AI enhancement
cosmos status [--stream]                 # GPU status or live logs
```