# CLAUDE.md — Cosmos Workflow Orchestrator

## 🔴 ABSOLUTE RULE: Test-Driven Development

**NO CODE WITHOUT TESTS. STOP ALL WORK if TDD is violated.**

### The Six Gates (MUST pass in order)

1. **Test First** → Write failing tests before ANY implementation
2. **Commit Tests** → Commit while failing (`test: description`)
3. **Implement** → Code until ALL tests pass (never modify tests)
4. **Verify Quality** → No overfitting, no security risks, no forbidden patterns
5. **Update Docs** → CHANGELOG.md, docstrings, README if needed
6. **Commit Code** → Run linting, commit with `feat:`/`fix:` + test status

**Gate violation = IMMEDIATE STOP. No exceptions. No negotiations.**

## ⛔ Conventions (ENFORCED)

### NEVER Do This → ALWAYS Do This

```python
# ❌ FORBIDDEN                         # ✅ REQUIRED
paramiko.SSHClient()                   → SSHManager()
docker.run()                           → DockerExecutor()
{"config": "dict"}                     → ConfigManager()
json.dumps(prompt)                     → PromptSpecManager()
os.path.join(a, b)                     → Path(a) / b
logger.info(f"{var}")                  → logger.info("%s", var)
def func(x):                           → def func(x: type) -> type:
# Missing docstring                    → """Docstring with Args/Returns."""
```

### Security Blocks
- Hardcoded passwords/keys/secrets → Use environment variables
- Unvalidated user input → Validate everything
- Shell injection risks → Use subprocess with arrays
- Sensitive data in logs → Redact before logging

## 📂 Temporary Files

**DELETE all temporary files when done** - workspace files, test outputs, debug logs
- `.claude/workspace/` is for scratch work only (gitignored)
- Clean up ANY temp files you create anywhere

## 🚀 Commands

```bash
pytest tests/ -xvs                # Test with details (TDD Gate 1,3)
ruff format cosmos_workflow/      # Format code (Gate 6)
ruff check cosmos_workflow/ --fix # Lint check (Gate 6)
```

## 📝 CHANGELOG.md is MANDATORY

Every code change MUST update CHANGELOG.md under [Unreleased]. No exceptions.
