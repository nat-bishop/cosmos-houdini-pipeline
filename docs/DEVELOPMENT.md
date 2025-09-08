# Development Guide

## Setup

### Install Dependencies
```bash
# Basic usage
pip install -r requirements.txt

# Development (includes testing, linting, type checking)
pip install -r requirements-dev.txt
```

### Pre-commit Hooks

We use **read-only** pre-commit hooks that check but never modify files. This ensures predictability and prevents unexpected changes during commits.

```bash
# Install hooks (one-time setup)
pre-commit install

# Run manually on all files (checks only, no fixes)
pre-commit run --all-files
```

**Important:** Pre-commit hooks will fail if formatting or linting issues are found. Fix them manually before committing (see Code Quality section).

## Architecture Overview

### Facade Pattern Design

The Cosmos Workflow System uses a **facade pattern** with `CosmosAPI` as the primary interface. Understanding this architecture is critical for development.

```
┌────────────────────────────────────────────────┐
│          Your Code (CLI/UI/Scripts)           │
│                     ↓                          │
│         CosmosAPI (FACADE)            │
│      cosmos_workflow/api/workflow_operations.py│
│                     ↓                          │
│        ┌──────────────┬──────────────┐        │
│        │              │              │        │
│  DataRepository   GPUExecutor*      │
│    (Database)        (GPU Execution)          │
└────────────────────────────────────────────────┘

* Despite its name, GPUExecutor is NOT the main orchestrator
  It's the GPU execution component. Will be renamed to GPUExecutor in v2.0.
```

### Development Rules

**✅ ALWAYS Use CosmosAPI:**

```python
from cosmos_workflow.api import CosmosAPI

ops = CosmosAPI()
# Use ops for everything
```

**❌ NEVER Import Internal Components Directly:**

```python
# WRONG - These are internal components
from cosmos_workflow.services import DataRepository  # ❌
from cosmos_workflow.database import DatabaseConnection  # ❌
from cosmos_workflow.workflows import GPUExecutor  # ❌
```

### When to Use Low-Level Components

Only use low-level components for:
- Infrastructure tasks (SSH, Docker, file transfers)
- Writing tests for the components themselves
- Extending the facade with new functionality

Example infrastructure task:
```python
# OK for infrastructure/testing only
from cosmos_workflow.connection import SSHManager
from cosmos_workflow.config import ConfigManager
```

## Test-Driven Development (TDD)

Follow these 6 gates for every feature:

1. **Write Tests First** - Behavioral tests that define the contract, minimal mocking
2. **Verify Tests Fail** - They should fail initially
3. **Commit Tests** - Tests are the contract, commit them unchanged
4. **Make Tests Pass** - Implement minimal code to pass all tests
5. **Document & Commit** - Update documentation to reflect changes
6. **Code Review** - Comprehensive review including security and maintainability

**Current Testing Approach:**
- **Service Layer Focus**: Test business logic through DataRepository methods
- **Database Integration**: Test actual database operations with SQLAlchemy
- **CLI Behavior**: Test command behavior, not implementation details
- **Minimal Mocking**: Mock only external dependencies (SSH, Docker, file system)
- **No Test Stubs**: All tests are real, no placeholder or stub implementations

## Testing

The project uses a comprehensive testing strategy with 453 passing tests covering the service layer architecture:

```bash
# Run all tests
pytest

# With coverage (current: 80%+)
pytest --cov=cosmos_workflow --cov-report=html

# Run specific test categories
pytest tests/unit/database/          # Database model tests
pytest tests/unit/services/          # Service layer tests
pytest tests/unit/cli/               # CLI command tests
pytest tests/integration/            # Integration tests

# Fast unit tests only
pytest tests/unit/ -v

# Specific test file
pytest tests/unit/services/test_workflow_service.py -v
```

**Test Architecture:**
- **Database Tests**: 49 tests covering models, connections, validation
- **Service Tests**: 64 tests covering DataRepository business logic
- **CLI Tests**: Integration tests for database-first command behavior
- **Integration Tests**: End-to-end workflows including SSH and Docker execution

**Coverage Requirements:**
- Minimum: 80% overall coverage
- New features: 100% coverage requirement
- Critical paths: Database operations, CLI commands, GPU execution

## Code Quality

### Formatting & Linting Philosophy

We use a **manual formatting workflow** with read-only pre-commit hooks:
- Pre-commit hooks check but never modify files (no surprises)
- Developers format code manually or via editor integration
- This avoids the commit-stash-reapply churn of auto-fixing hooks

### Formatting Workflow

See [FORMATTING.md](FORMATTING.md) for detailed formatting guide.

**Quick Reference:**
```bash
# Before committing
ruff format .            # Format code
ruff check . --fix      # Fix linting
git commit              # Commit changes
```

**Editor Integration:** Configure format-on-save for best workflow (see [FORMATTING.md](FORMATTING.md))

### Other Quality Checks
```bash
# Type checking
mypy cosmos_workflow/

# Security scan
bandit -r cosmos_workflow/
```

### Code Conventions
- **Service Layer**: Use `DataRepository` for all data operations, not direct database access
- **Database-First**: Work with database IDs (ps_xxx, rs_xxx), not JSON files
- **Wrappers**: Use project wrappers: `SSHManager()` not `paramiko.SSHClient()`
- **Paths**: `Path(a) / b` not `os.path.join(a, b)`
- **Logging**: `logger.info("%s", var)` not f-strings (parameterized logging)
- **Type Hints**: Required for all public functions and methods
- **Docstrings**: Google-style docstrings with Args/Returns/Raises
- **Exceptions**: Catch specific exceptions, never bare `except:`
- **Architecture**: Clear separation - service layer (data) vs orchestrator (execution)

## Debugging

### Common Issues

**SSH Connection Failed:**
```bash
# Test connection
ssh -i ~/.ssh/key.pem ubuntu@192.222.52.92
```

**Import Errors:**
```bash
# Verify package is installed
python -c "import cosmos_workflow; print('✓ Package imported successfully')"

# Test database connection
python -c "from cosmos_workflow.database import init_database; init_database(); print('✓ Database initialized')"

# Test service layer
python -c "from cosmos_workflow.services import DataRepository; print('✓ Service layer imported')"
```

**Test Failures:**
```bash
# Run with verbose output
pytest -xvs tests/failing_test.py

# Debug with pdb
pytest --pdb tests/failing_test.py

# Test specific service methods
pytest -k "test_create_prompt" -v

# Test database operations only
pytest tests/unit/database/ -v

# Check test coverage for specific module
pytest --cov=cosmos_workflow.services --cov-report=term-missing
```

### Useful Commands
```bash
# Check what changed
git status
git diff

# Find TODOs
grep -r "TODO" cosmos_workflow/

# Count lines of code
find cosmos_workflow -name "*.py" | xargs wc -l
```

## Subagents

Use these for TDD workflow:
- `test-runner` - Run tests and analyze failures
- `overfit-verifier` - Check for test-specific logic
- `code-reviewer` - Review code quality
- `doc-drafter` - Update documentation
- `commit-handler` - Create clean commits

## Concurrent Verification Pattern

**Key Insight:** Implementation sessions develop "test-passing bias" - fresh verification catches what you've become blind to.

### Quick Start

In a NEW Claude Code session, use slash commands:
- `/verify-overfit` - Run independent overfit verification (Gate 4)
- `/verify-review` - Run independent code review (Gate 6)

Reports are saved to `.claude/workspace/verification/EXTERNAL_*.md` for the main session to check.

### Why It Works

In our database feature, concurrent verification found critical bugs the main session missed:
- Connection closing didn't actually prevent usage
- Missing input validation and security checks
- Tests modified to pass rather than fixing bugs
- Score: 3/10 vs biased 7/10

### When to Use

- **Always:** Security-sensitive code
- **Recommended:** Multi-file features
- **Optional:** Simple bug fixes

The main session checks for these external reports at Gates 4 and 6.

## Commit Messages

Use conventional commits:
- `test:` - Tests only
- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code changes
- `docs:` - Documentation
- `chore:` - Maintenance

Never mix tests and implementation in one commit.
