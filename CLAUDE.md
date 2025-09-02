# CLAUDE.md — Cosmos Workflow Orchestrator

## 🔴 CRITICAL: Test-Driven Development
**YOU MUST follow EVERY step. Skip ANY step = TDD failure.**

### For EVERY Code Change:
1. **YOU MUST write test first** → Include edge cases & errors → Must fail
2. **YOU MUST verify failure** → `@subagent test-runner` → Red phase
3. **Commit tests** → Auto-handled by subagent
4. **Implement** → Keep in main thread
5. **YOU MUST verify pass** → `@subagent test-runner` → Green phase
6. **Parallel verification**:
   - `@subagent overfit-verifier` → Check implementation
   - `@subagent code-reviewer` → Review diff
7. **Update docs** → `@subagent doc-drafter` → Auto-updates:
   - ✅ CHANGELOG.md (ALWAYS, no exceptions)
   - ✅ README.md (if CLI/API changed)
   - ✅ docs/*.md (if needed)
8. **Commit implementation** → Auto-handled by subagent

## 📁 File Update Rules
**doc-drafter ALWAYS updates:** CHANGELOG.md (every change), README.md (if CLI/API changed)
**NEVER manually update:** `.claude/reports/*.json` (subagents only)

## 🤖 Subagent Rules
- **One-way only**: Subagents write → `.claude/reports/*.json` → Main reads
- **No sharing**: Subagents never read each other's output
- **Main orchestrates**: All coordination through main thread

## 📝 Workspace Rules
- **One scratch file**: `.claude/workspace/current-task.md`
- **YOU MUST delete** when task completes
- **Never committed** (gitignored)

## 📏 Critical Code Rules
- **Logging**: Use `%` formatting, NOT f-strings (performance)
- **Paths**: `pathlib.Path` only, NEVER `os.path` (cross-platform)
- **Tests**: MUST cover edge cases & errors, not just happy path
- **Temp Files**: DELETE `.claude/workspace/*` when task completes
- **SSH/Remote**: All GPU ops via WorkflowOrchestrator (never direct)

## 🚀 Frequent Commands
```bash
pytest tests/ -xvs               # Debug single test
pytest tests/ -q --tb=no         # Quick test summary
ruff format cosmos_workflow/      # Format code
ruff check cosmos_workflow/ --fix # Fix linting issues
gh pr create --title "feat: ..." # Create pull request
```

## 🔑 Core Settings
- **Model**: `/home/ubuntu/NatsFS/cosmos-transfer1`
- **Safe res**: 320×180 @ 2 frames
- **SSH**: 192.222.52.92

[Details: docs/](docs/)
