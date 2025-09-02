# TDD Implementation Handover Document

## Executive Summary
This document captures the complete context and rationale for migrating Cosmos Workflow Orchestrator to Test-Driven Development with specialized subagents. Created after consolidating work from the `cosmos-claude-improvements` worktree into `feature/tdd-subagents` branch.

## Why We're Moving to TDD

### The Problem We're Solving
1. **Context Loss Between Sessions**: Claude sessions were making changes without understanding test implications
2. **Mock Drift**: Tests with complex mocks became disconnected from actual implementation
3. **Regression Cycles**: Features would break silently, discovered only during integration
4. **Documentation Lag**: Code changes weren't reflected in docs, causing confusion
5. **Overfitting Risk**: Implementations would pass specific tests but fail real-world scenarios

### The TDD Solution
- **Tests as Contracts**: Tests define behavior before implementation exists
- **Automated Verification**: Subagents provide consistent, deterministic checking
- **Parallel Quality Gates**: Multiple validation steps run simultaneously
- **Living Documentation**: Doc-drafter keeps documentation synchronized automatically

## Subagent Architecture

### Core Philosophy
Each subagent has **one job** and does it deterministically. They read code/tests directly, not chat history, ensuring consistent results across sessions.

### The Four Subagents

#### 1. test-runner
**Purpose**: Execute tests and report failures in machine-readable format
**When to Use**: After writing new tests (should fail) and after implementation (should pass)
**Output**: `.claude/reports/test-run.json` with structured failure data
**Key Feature**: Parses pytest output into actionable JSON for automation

#### 2. code-reviewer
**Purpose**: Review git diffs for critical issues after tests pass
**When to Use**: After implementation passes all tests
**Output**: `.claude/reports/code-review.json` with categorized issues
**Focus**: Security, resource leaks, breaking changes, not style

#### 3. overfit-verifier
**Purpose**: Detect when implementation is too specific to test cases
**When to Use**: After tests pass, in parallel with code-reviewer
**Output**: `.claude/reports/overfit-check.json` with suspicious patterns
**Example Detection**: Magic constants matching test data, hardcoded returns

#### 4. doc-drafter
**Purpose**: Update README, CHANGELOG, and API docs based on changes
**When to Use**: After implementation is complete and reviewed
**Output**: `.claude/reports/doc-updates.json` with change summary
**Prevents**: Documentation drift, outdated examples

## Cascading CLAUDE.md Vision

### Current State (Implemented)
```
CLAUDE.md (42 lines)
├── TDD workflow steps (8 steps)
├── Core mission statement
├── Essential rules (4 key points)
└── Links to detailed docs
```

### Target Architecture
```
CLAUDE.md (30-50 lines max)
├── docs/TDD_WORKFLOW.md (process)
├── docs/CONVENTIONS.md (code style)
├── docs/CONFIG.md (GPU, Docker settings)
├── docs/TROUBLESHOOTING.md (common issues)
└── docs/ai-context/*.md (detailed context)
```

### Benefits of Cascading
1. **Reduced Context Window Usage**: Claude loads only what's needed
2. **Easier Updates**: Change details without touching CLAUDE.md
3. **Better Organization**: Related information stays together
4. **Session Focus**: New sessions see priorities immediately

### Migration Plan
1. Move GPU/Docker parameters → `docs/CONFIG.md`
2. Move error solutions → `docs/TROUBLESHOOTING.md`
3. Keep only TDD steps and critical rules in CLAUDE.md
4. Add "See also:" links for details

## Current Implementation Status

### ✅ Completed
- Refactored CLAUDE.md to 42 lines with TDD focus
- Created all 4 subagent definitions
- Documented TDD workflow with parallel execution points
- Added GitHub CLI integration guide
- Created example TDD test (`test_example_tdd.py`)

### ⚠️ Needs Immediate Fix
- **9 failing CLI tests**: Mock patch location needs update
  - Current: `@patch("cosmos_workflow.cli.WorkflowOrchestrator")`
  - Should be: `@patch("cosmos_workflow.cli.base.WorkflowOrchestrator")`
  - Quick fix will restore green baseline

### 🔄 In Progress
- Subagent integration testing
- Cascading documentation structure
- Automated report aggregation

## Example TDD Workflow

### Scenario: Adding Token Calculation Feature

```python
# Step 1: Write failing test
def test_calculate_tokens():
    from cosmos_workflow.utils import calculate_tokens
    assert calculate_tokens(320, 180, 2) == 1990.08
```

```bash
# Step 2: Verify test fails
@subagent test-runner
Run: pytest tests/test_utils.py::test_calculate_tokens -xvs
# Output: ImportError - function doesn't exist ✓
```

```bash
# Step 3: Commit test
git add tests/test_utils.py
git commit -m "test: add token calculation test"
```

```python
# Step 4: Implement (in main thread)
def calculate_tokens(width: int, height: int, frames: int) -> float:
    return width * height * frames * 0.0173
```

```bash
# Step 5: Verify test passes
@subagent test-runner
Run: pytest tests/test_utils.py::test_calculate_tokens -xvs
# Output: PASSED ✓
```

```bash
# Step 6: Run parallel verification
@subagent overfit-verifier
Check: tests/test_utils.py against cosmos_workflow/utils.py

@subagent code-reviewer
Review current git diff
```

```bash
# Step 7: Update documentation
@subagent doc-drafter
Update documentation for recent changes
```

```bash
# Step 8: Commit implementation
git add -A
git commit -m "feat: implement token calculation"
```

## Concrete Next Steps (Priority Order)

### 1. Fix Failing Tests (Quick Win) - 30 minutes
```python
# In tests/test_cli.py, update all:
@patch("cosmos_workflow.cli.WorkflowOrchestrator")
# To:
@patch("cosmos_workflow.cli.base.WorkflowOrchestrator")
```
**Why First**: Restore green baseline, build confidence in TDD

### 2. Implement Missing Features Using TDD - 2-4 hours each
Priority order based on user impact:

a. **Dry-run validation for inference command**
   - Write test for `--dry-run` flag behavior
   - Implement validation without execution
   - Prevents accidental GPU usage

b. **Progress indicators for long operations**
   - Test progress callback integration
   - Implement Rich progress bars
   - Better UX for inference/upscaling

c. **Batch processing for multiple prompts**
   - Test queue management
   - Implement sequential processing
   - Enables production workflows

### 3. Complete Cascading Documentation - 2 hours
- Create `docs/CONFIG.md` with all GPU/Docker settings
- Create `docs/TROUBLESHOOTING.md` with error solutions
- Reduce CLAUDE.md to 30 lines
- Add cross-references

### 4. Subagent Enhancement - 4 hours
- Add `test-generator` subagent for creating tests from docstrings
- Add `coverage-analyzer` to identify untested code
- Create aggregator script to combine all reports

### 5. GitHub Actions Integration - 2 hours
- Add workflow that runs subagents on PR
- Post subagent reports as PR comments
- Block merge if critical issues found

## Patterns and Gotchas Discovered

### Successful Patterns
1. **Write multiple related tests at once** - Better context for implementation
2. **Use subagents in parallel** - Save time on verification
3. **Commit tests separately** - Clear history of TDD process
4. **Keep implementation in main thread** - Preserves context

### Gotchas to Avoid
1. **Don't let subagents modify code** - They observe and report only
2. **Don't skip the failing test step** - Critical for TDD discipline
3. **Don't trust mocks blindly** - They drift from reality
4. **Don't update CLAUDE.md for details** - Use cascading docs

## Session Context Preservation

### Key Decisions Made
1. **Subagents use Task tool** with `subagent_type: "general-purpose"`
2. **Reports go to `.claude/reports/`** for consistency
3. **JSON output** for all subagents enables automation
4. **Parallel execution** after tests pass saves time

### Architectural Insights
- Test-first forces better API design
- Machine-readable reports enable CI/CD integration
- Focused subagents reduce complexity vs. monolithic agents
- Cascading docs reduce context window pressure

## Questions Answered

**Q: What exactly is "cascading CLAUDE.md"?**
A: A hierarchical documentation structure where CLAUDE.md contains only essential information (30-50 lines) and links to detailed docs. Claude loads the main file first, then follows links as needed, reducing token usage.

**Q: Where should GPU settings live in new structure?**
A: Create `docs/CONFIG.md` with sections for GPU, Docker, SSH, and model parameters. CLAUDE.md should only mention "safe resolution: 320×180" as a quick reference.

**Q: What's the priority for new features?**
A: 1) Features blocking users (dry-run), 2) UX improvements (progress bars), 3) Automation (batch processing), 4) Developer tools (more subagents)

**Q: Any specific patterns discovered?**
A: Subagents work best when given exact commands/files, not general instructions. Always specify output format explicitly. Use parallel execution after implementation, not during.

## For the New Session

### Setup Commands
```bash
# Start from correct branch
git checkout feature/tdd-subagents

# Verify subagents are present
ls -la .claude/subagents/

# Run tests to see current state
pytest tests/test_cli.py -xvs
```

### First Task
Fix the 9 failing tests by updating mock patches. This provides:
- Immediate success to build momentum
- Verification that environment is correct
- Practice with the codebase

### Reading Order
1. `CLAUDE.md` - Get TDD process
2. This document - Understand context
3. `docs/TDD_WORKFLOW.md` - Learn workflow
4. Start fixing tests

## Handover Complete
The TDD foundation is solid. The subagents are defined. The workflow is documented. The next steps are clear. Time to build with confidence.

---
*Document created: 2024-09-01 19:30 UTC*
*Branch: feature/tdd-subagents*
*Commit: 9c10c7f*
