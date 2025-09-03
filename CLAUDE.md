See @README.md for project overview. Most directorys also contain a README.md

**Always run TDD (Test Driven Development) if requested**
**TDD PROCEDURE**
### Gate 1: Write Tests First
- Write tests based on expected input/output pairs
- Real tests only - no mocks, even if code doesn't exist yet
- **PASS**: Tests are comprehensive, consider edge cases and error codes

### Gate 2: Verify Tests Fail
- Run tests - they should fail (that's good!)
- **PASS**: All tests failing

### Gate 3: Commit Failing Tests
- Tests are the contract
- Commit the failing tests
- **PASS**: Tests committed

### Gate 4: Make Tests Pass
- Write implementation code iteratively until tests pass
- Run tests and verify for overfitting in parallel
- Don't change tests - they're the spec
- **PASS**: 100% tests passing, no overfitting, tests unchanged

### Gate 5: Document and Commit
- Update all documentation
- Commit the implementation
- **PASS**: Documentation updated and changes committed

### Gate 6: Code Review
- Review code for quality and security
- **PASS**: Code of high standard with no critical issues

**Break a gate during TDD? STOP. ASK ME FOR REVIEW. No exceptions.**
**ALL GATES MUST PASS for TDD**

## Project Structure
- Main package @cosmos_workflow/
- Orchestration and GPU workflows @cosmos_workflow/workflows/
- SSH and file transfer management @cosmos_workflow/connection/
- Docker and command execution @cosmos_workflow/execution/
- Configuration management (config.toml) @cosmos_workflow/config/
- Prompt specifications and schemas @cosmos_workflow/prompts/
- Local AI processing utilities @cosmos_workflow/local_ai/
- Command-line interface @cosmos_workflow/cli/
- Helper functions and utilities @cosmos_workflow/utils/

- Test suite @tests/

- Input data and prompts @inputs/
- Generated outputs @outputs/

- Documentation @docs/ and @README.md and @CHANGELOG.md, use doc-drafter subagent to write documentation

- NVIDIA Cosmos Transfer model source https://github.com/nvidia-cosmos/cosmos-transfer1 (runtime dependency on GPU instance, useful reference for model architecture)

## Code Conventions

### Use Our Wrappers, Not Raw Libraries, MUST FOLLOW
- SSH connections: Use `SSHManager()` @cosmos_workflow/connection/ssh_manager.py not `paramiko.SSHClient()`
- Docker operations: Use `DockerExecutor()` not `docker.run()`
- Config loading: Use `ConfigManager()` not raw dicts
- Prompt specs: Use `PromptSpecManager()` not manual JSON

### Python Best Practices
- Small functions, no monkey-patching
- Avoid Monolith structures
- Use Single Responsibility Principle
- Use Zen of Python rules
- Try to split up files where possible
- Path operations: Use `Path(a) / b` not `os.path.join(a, b)`
- Logging: Use `logger.info("%s", var)` not f-strings in logs
- Type hints: Always add them - `func(x: type) -> type:`
- Docstrings: Google-style with Args/Returns/Raises sections (one-line summary, then details)
- Exceptions: Catch specific ones - `except SpecificError:`

## Operating Procedures
- **MUST DO** Write all temporary files and reports to .claude/workspace/
**DELETE all temporary files when done** - workspace files, test outputs, debug logs
- When completing features from @ROADMAP.md, remove them from the file

## Quick Commands
# Formatting and Linting
ruff format cosmos_workflow/      # Format code
ruff check cosmos_workflow/ --fix # Fix linting

# Cosmos CLI
cosmos create prompt "desc"       # Create prompt spec
cosmos inference prompt.json      # Run on GPU
cosmos status                     # Check GPU status

## Smart Test Execution by TDD Gate

**Gate 2 (Verify Tests Fail):** Run only the new test file you created
**Gate 4 (Make Tests Pass):** Run the specific failing tests, stop on first failure
**Gate 5 (Pre-Commit):** Run unit tests for changed modules only
**PR/Full Validation:** Run complete test suite with coverage

## Testing Rules
- 80% Code Coverage (for full validation)
- Consider edge cases and error codes
- Tests should follow TDD rules
- Use focused testing during development for speed

# Focused test commands for TDD
pytest path/to/test_file.py -v           # Single test file
pytest path/to/test_file.py -x           # Stop on first failure
pytest tests/unit/module_name/ -v        # Module tests only
pytest -k "test_function_name"           # Specific test function

# Full validation (PR/CI)
pytest tests/ --cov=cosmos_workflow --cov-report=term-missing

## Documentation
- Gate 5 of TDD: Update documentation with doc-drafter subagent before commits
- Documentation must stay synchronized with code changes
- Never create new documentation files without explicit request
