# Project Conventions

This document defines the coding standards and conventions for the Cosmos Workflow project.

## 🎨 Code Style

### Formatting
- **Tool**: Ruff (v0.12.11+)
- **Line Length**: 100 characters
- **Indentation**: 4 spaces
- **String Quotes**: Double quotes preferred
- **Line Endings**: LF (Unix-style)

### Imports
```python
# Order (enforced by Ruff):
# 1. Standard library
import os
import sys
from pathlib import Path

# 2. Third-party
import paramiko
import toml

# 3. Local application
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.prompts import PromptSpec
```

### Naming Conventions
- **Classes**: `PascalCase` (e.g., `WorkflowOrchestrator`)
- **Functions/Methods**: `snake_case` (e.g., `run_inference`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
- **Private**: Leading underscore (e.g., `_internal_method`)
- **Files**: `snake_case.py`

## 📝 Documentation

### Docstrings (Google Style)
```python
def process_video(input_path: Path, fps: int = 24) -> VideoMetadata:
    """Process a video file and extract metadata.

    Args:
        input_path: Path to the input video file
        fps: Target frame rate (default: 24)

    Returns:
        VideoMetadata object containing extracted information

    Raises:
        FileNotFoundError: If input file doesn't exist
        ValueError: If fps is invalid

    Example:
        >>> metadata = process_video(Path("video.mp4"), fps=30)
        >>> print(metadata.duration)
    """
```

### Comments
```python
# Use comments sparingly - code should be self-documenting
# NO: x = x + 1  # Increment x by 1
# YES: # Apply exponential backoff for retry logic
```

### Type Hints
```python
# Required for all public functions
def transfer_files(
    files: list[Path],
    destination: str,
    timeout: int = 300
) -> dict[str, Any]:
    ...

# Optional for internal/private functions
def _helper(data):  # Type hints optional
    ...
```

## 🧪 Testing

### Test Organization
```
tests/
├── unit/          # Fast, isolated tests
├── integration/   # Component interaction tests
└── system/        # End-to-end tests
```

### Test Naming
```python
# Pattern: test_<what>_<condition>_<expected>
def test_ssh_connect_invalid_host_raises_error():
    ...

def test_prompt_spec_creation_with_defaults_succeeds():
    ...
```

### Test Markers
```python
@pytest.mark.unit
def test_fast_operation():
    ...

@pytest.mark.integration
@pytest.mark.slow  # Takes >1 second
def test_file_transfer():
    ...
```

## 🔄 Git Conventions

### Branch Names
- `feature/<description>` - New features
- `fix/<issue-or-description>` - Bug fixes
- `docs/<description>` - Documentation only
- `refactor/<description>` - Code refactoring
- `test/<description>` - Test additions/fixes

### Commit Messages
```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Maintenance tasks
- `perf`: Performance improvements

Examples:
```
feat: add smart naming for video sequences

fix: resolve SFTP timeout on large files

docs: update API reference for schemas
```

## 📁 Project Structure

### Directory Organization
```
cosmos_workflow/
├── config/          # Configuration management
├── connection/      # External connections (SSH, etc.)
├── execution/       # Command execution
├── prompts/         # Schema definitions
├── transfer/        # File transfer operations
├── local_ai/        # AI/ML features
├── utils/           # Utility functions
└── workflows/       # High-level orchestration
```

### File Naming
- Python modules: `snake_case.py`
- Test files: `test_<module>.py`
- Config files: `config.toml`, `pyproject.toml`
- Documentation: `UPPER_CASE.md` for root, `lower-case.md` for docs/

## 🚀 Development Workflow

### Before Committing
1. **Format code**: `ruff format cosmos_workflow/`
2. **Check linting**: `ruff check cosmos_workflow/ --fix`
3. **Run tests**: `pytest tests/ -m unit`
4. **Update docs**: If API changes

### Code Review Checklist
- [ ] Follows naming conventions
- [ ] Has appropriate type hints
- [ ] Includes docstrings for public functions
- [ ] Has corresponding tests
- [ ] Updates documentation if needed
- [ ] Passes linting checks
- [ ] No hardcoded credentials

## 🔒 Security

### Never Commit
- Passwords, API keys, tokens
- SSH private keys
- Personal information
- Large binary files (>1MB)

### Use Instead
```python
# Bad
password = "secret123"

# Good
password = os.environ.get("API_PASSWORD")
password = config.get("auth.password")
```

## 📊 Performance

### Logging
```python
# Bad - f-strings in logging
logger.info(f"Processing {filename}")

# Good - lazy % formatting
logger.info("Processing %s", filename)
```

### File Operations
```python
# Bad - loading entire file
content = Path("large_file.json").read_text()

# Good - streaming for large files
with open("large_file.json") as f:
    for line in f:
        process(line)
```

## 🎯 Best Practices

### Error Handling
```python
# Be specific with exceptions
try:
    ssh_manager.connect()
except ConnectionError as e:
    logger.error("SSH connection failed: %s", e)
    raise
except Exception as e:
    logger.error("Unexpected error: %s", e)
    # Re-raise or handle appropriately
```

### Resource Management
```python
# Always use context managers
with SSHManager(config) as ssh:
    result = ssh.execute_command("ls")

# Not
ssh = SSHManager(config)
ssh.connect()
result = ssh.execute_command("ls")
ssh.disconnect()
```

### Configuration
```python
# Use dataclasses for configs
@dataclass
class RemoteConfig:
    host: str
    user: str
    ssh_key: Path
    port: int = 22
```

## 📋 TODO When These Conventions Change

1. Update this document
2. Update `.pre-commit-config.yaml`
3. Update `pyproject.toml`
4. Run formatter on entire codebase
5. Update CI/CD configs
6. Notify team/update PR template
