See @README.md for project overview. Most directorys also contain a README.md

## Test-Driven Development is Non-Negotiable and MUST BE followed

**Stop immediately if you're not following TDD.** Here are the six gates you must pass:

### Gate 1: Write Tests First
- We are doing Test Driven Development, this is very important
- Write tests based on expected input/output pairs, You will use these expectations to iterate on
- Real tests only - no mocks, even if code doesn't exist yet
- **PASS**: Tests are comprehensive, consider edge cases and error codes

### Gate 2: Verify Tests Fail
- Run tests - they should fail (that's good!)
- Don't write implementation code yet
- **PASS**: All tests failing

### Gate 3: Commit Failing Tests
- Tests are the contract - commit them once I am satisfied
- use the commit-handler subagent to commit tests
- **PASS**: Tests committed

### Gate 4: Make Tests Pass
- Now write implementation code
- Keep iterating: write the code → run the tests → adjust → run the tests again
- Run BOTH agents IN PARALLEL for faster feedback:
  - test-runner subagent: validates tests pass
  - overfit-verifier subagent: checks for overfitting (starts immediately, not after tests pass)
- Don't change tests - they're the spec
- Keep iterating until both agents pass
- **PASS**: 100% tests passing, tests verified for overfitting and tests unchanged

### Gate 5: Document and Commit
- Fully update all documentation with the doc-drafter subagent
- Commit the changes to github once I am satisfied with the commit-handler subagent
- **PASS**: Everything fully documented with clean commit

### Gate 6: Code Review
- Review code for high standards of code quality and security after every code commit
- Use the code-reviewer subagent
- **PASS**: Code of high standard with no Critical Issues

**Break a gate? STOP. ASK ME FOR REVIEW. No exceptions.**
**ALL GATES MUST PASS**

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

## Testing Rules
- 80% Code Coverage
- Consider edge cases and error codes
- Tests should follow TDD rules
# Run tests
pytest tests/ -m unit --cov=cosmos_workflow

# Full validation (if changing core logic)
pytest tests/ --cov=cosmos_workflow --cov-report=term-missing

## Documentation
- Gate 5 of TDD: Update documentation with doc-drafter subagent before commits
- Documentation must stay synchronized with code changes
- Never create new documentation files without explicit request
