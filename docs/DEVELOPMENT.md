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

## Test-Driven Development (TDD)

Follow these 6 gates for every feature:

1. **Write Tests First** - Real tests, no mocks
2. **Verify Tests Fail** - They should fail initially
3. **Commit Tests** - Use commit-handler subagent
4. **Make Tests Pass** - Write implementation
5. **Document & Commit** - Use doc-drafter & commit-handler
6. **Code Review** - Use code-reviewer subagent

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=cosmos_workflow

# Fast unit tests only
pytest -m unit

# Specific file
pytest tests/unit/test_ssh_manager.py
```

Coverage requirement: 80% minimum

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
- Use project wrappers: `SSHManager()` not `paramiko.SSHClient()`
- Paths: `Path(a) / b` not `os.path.join(a, b)`
- Logging: `logger.info("%s", var)` not f-strings
- Always add type hints and docstrings
- Catch specific exceptions

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
python -c "import cosmos_workflow"
```

**Test Failures:**
```bash
# Run with verbose output
pytest -xvs tests/failing_test.py

# Debug with pdb
pytest --pdb tests/failing_test.py
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

## Commit Messages

Use conventional commits:
- `test:` - Tests only
- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code changes
- `docs:` - Documentation
- `chore:` - Maintenance

Never mix tests and implementation in one commit.
