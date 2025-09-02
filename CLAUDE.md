# CLAUDE.md — Cosmos Workflow Orchestrator

## 🔴 CRITICAL: Test-Driven Development
**Follow TDD strictly** → See [docs/TDD_WORKFLOW.md](docs/TDD_WORKFLOW.md)
1. Write tests first (must fail)
2. `@subagent test-runner` to verify failure
3. Commit tests
4. Implement (keep in main thread)
5. `@subagent test-runner` to verify pass
6. `@subagent overfit-verifier` + `@subagent code-reviewer` (parallel)
7. `@subagent doc-drafter` to update docs
8. Commit implementation

## Mission
Python orchestrator for NVIDIA Cosmos-Transfer video generation on remote GPU via SSH + Docker.

## Core Rules
- **Security**: No hardcoded secrets → `config.toml` or ENV
- **Quality**: Type hints, `pathlib.Path`, proper logging
- **Testing**: 80% coverage, <1s unit tests
- **Conventions**: See [docs/ai-context/CONVENTIONS.md](docs/ai-context/CONVENTIONS.md)

## Quick Commands
```bash
# Testing & Quality
pytest tests/ -q --tb=no
ruff format cosmos_workflow/
ruff check cosmos_workflow/ --fix

# Subagent reports location
.claude/reports/
```

## Key Parameters
- **Safe resolution**: 320×180 @ 2 frames (940×529 max)
- **Inference steps**: 35 (quality) or 1 (distilled)
- **Model path**: `/home/ubuntu/NatsFS/cosmos-transfer1`

## Documentation
- [Project Details](docs/ai-context/PROJECT_STATE.md)
- [Known Issues](docs/ai-context/KNOWN_ISSUES.md)
- [Conventions](docs/ai-context/CONVENTIONS.md)
