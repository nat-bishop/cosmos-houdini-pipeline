# CLAUDE.md — Cosmos Workflow Orchestrator

## 🔴 CRITICAL: Test-Driven Development is MANDATORY

**YOU MUST follow TDD for all code changes. Skip ANY step = TDD failure.**

## ⚠️ Test-Driven Development Workflow

**We are doing test-driven development (TDD)** - tests ALWAYS come first, implementation second.

### Phase 1: Write Tests & Commit
1. **Write tests based on expected input/output pairs**
   - Be explicit that we're doing TDD to avoid mock implementations
   - DO NOT create mocks even if functionality doesn't exist yet

2. **Run tests and confirm they fail**
   - Use the **test-runner** agent to verify failures
   - DO NOT write any implementation code at this stage

3. **Commit the tests** when satisfied
   - Use the **commit-handler** agent for test commits

### Phase 2: Code, Iterate & Commit
4. **Write code that passes the tests**
   - DO NOT modify the tests - they are the specification
   - Keep going until all tests pass (expect multiple iterations)
   - Use the **test-runner** agent repeatedly to check progress

5. **Verify implementation quality** (run in parallel):
   - Use the **overfit-verifier** agent to ensure not overfitting to tests
   - Use the **code-reviewer** agent for security and conventions

6. **Update documentation** before committing
   - Use the **doc-drafter** agent to update CHANGELOG, README, docstrings

7. **Commit the implementation**
   - Use the **commit-handler** agent for implementation commits

## 🏗️ Core Architecture

### Key Classes
- **WorkflowOrchestrator**: Main orchestrator for remote GPU operations
- **SSHManager**: Handles SSH connections to GPU instances
- **DockerExecutor**: Manages Docker container execution
- **PromptSpecManager**: Creates and manages prompt specifications
- **ConfigManager**: Handles configuration (see `config.toml`)

### Project Conventions
- **Paths**: Use `pathlib.Path` only (NEVER `os.path`)
- **Logging**: Use `%` formatting (NOT f-strings) for performance
- **Docstrings**: Triple quotes with Args/Returns/Raises sections
- **Tests**: MUST cover edge cases, not just happy paths
- **Remote ops**: All GPU operations via WorkflowOrchestrator only

## 🚀 Frequent Commands

```bash
# Cosmos CLI
cosmos create prompt "A futuristic city"  # Create prompt spec
cosmos inference prompt.json              # Run inference
cosmos status                             # Check GPU status

# Development
pytest tests/ -xvs                       # Run tests with details
pytest tests/ -q --tb=no                 # Quick test summary
ruff format cosmos_workflow/             # Format code
ruff check cosmos_workflow/ --fix        # Fix linting issues
gh pr create --title "feat: ..."        # Create pull request
```

## 📝 Workspace Rules
- Use `.claude/workspace/current-task.md` for scratch work
- DELETE workspace files when task completes
- Never commit workspace files (gitignored)

[Details: docs/](docs/)
