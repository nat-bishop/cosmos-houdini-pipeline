My name is NAT

**Purpose**
This file defines how Claude Code operates in this repository.
It specifies TDD workflow, best practices, and safety practices.
---

# **TDD Workflow**

All work follows a **gated TDD flow**. If a gate fails, stop and request review.

### **Gate 1 — Write Tests First**
- Tests are written before implementation.
- **No mocks.** All calls must be to real functions.
- Coverage target: ≥ 80%.
- Always test error paths and consider edge cases.
- Expected: all tests fail.

### **Gate 2 — Verify Tests Fail**
pytest path/to/new_test.py --tb=no -q

### **Gate 3 — Commit Failing Tests**
Tests are the contract. Commit them unchanged.

### **Gate 4 — Make Tests Pass**
- Implement minimal code to pass all tests.
- Do **not** modify tests, they are a contract.
- Run the `overfit-verifier` sub-agent to ensure generalization.
- **MUST** check for external verification at `.claude/workspace/verification/EXTERNAL_overfit_check.md`.
  - Only proceed if report exists and matches current changes. If missing/outdated, ask user first.

### **Gate 5 — Document**
- Update [README.md](README.md)
- Update [CHANGELOG.md](CHANGELOG.md)
- Update [docs/](docs/)
- Use `doc-drafter` for consistency.

### **Gate 6 — Review**
- Run `code-reviewer` agent.
- Check for external review at `.claude/workspace/verification/EXTERNAL_code_review.md`.
  - Only proceed if report exists and matches current changes. If missing/outdated, ask user first.
- Must pass lint, coverage, and security checks.

---

## **Project Structure**
- [cosmos_workflow/](cosmos_workflow/) — package root
  - [workflows/](cosmos_workflow/workflows/) — orchestration & GPU flows
  - [connection/](cosmos_workflow/connection/) — SSH & file transfer
  - [execution/](cosmos_workflow/execution/) — Docker & command exec
  - [config/](cosmos_workflow/config/) — config and `config.toml`
  - [prompts/](cosmos_workflow/prompts/) — prompt specs
  - [local_ai/](cosmos_workflow/local_ai/) — local AI utils
  - [cli/](cosmos_workflow/cli/) — CLI entry points
  - [utils/](cosmos_workflow/utils/) — helpers
- [tests/](tests/) — pytest suite
- [inputs/](inputs/) — inputs & prompt payloads
- [outputs/](outputs/) — generated artifacts
- [docs/](docs/) — documentation

---

## **Project Wrappers (MANDATORY)**

All core operations must go through wrappers.
**Never call raw libraries directly** (e.g., `paramiko`, `docker`, ad-hoc subprocess, or JSON validation).
If functionality is missing, extend the wrapper instead of bypassing it.

### **Canonical Wrappers**
```python
from cosmos_workflow.connection import SSHManager, RemoteCommandExecutor
from cosmos_workflow.execution import DockerExecutor, DockerCommandBuilder, BashScriptBuilder
from cosmos_workflow.config import ConfigManager, SchemaValidator
from cosmos_workflow.prompts import PromptSpecManager, RunSpecManager, CosmosConverter, CosmosSequenceValidator
from cosmos_workflow.transfer import FileTransferService
```

### **Responsibilities & Enforcement**

* **SSHManager** — create/manage SSH sessions.
  Always use for SSH connections. Never call `paramiko.SSHClient()` directly.

* **RemoteCommandExecutor** — run remote commands via SSH.
  Always use for remote command execution. Never call inline `ssh` or `subprocess`.

* **DockerExecutor** — execute containers, stream logs.
  Always pair with **DockerCommandBuilder**. Never call `docker.from_env()` or raw subprocess Docker commands.

* **DockerCommandBuilder** — construct valid `docker run/exec` commands.
  Always use for building Docker commands. Never hand-roll docker CLI strings.

* **BashScriptBuilder** — build safe, multi-step bash scripts.
  Always use for multi-step shell workflows. Never concatenate raw shell strings.

* **ConfigManager** — load/validate config files and environment.
  Always use with **SchemaValidator**. Never parse environment variables or JSON manually.

* **SchemaValidator** — enforce schema integrity for configs and specs.
  Always validate configs and specs here. Never skip schema validation.

* **PromptSpecManager / RunSpecManager** — manage prompt and run specifications.
  Always use for reading/writing specs. Never use free-form JSON files.

* **CosmosConverter** — convert specs to NVIDIA Cosmos format (normalize paths).
  Always use for Cosmos conversions. Never hand-convert JSON or paths.

* **CosmosSequenceValidator** — validate Cosmos control sequences.
  Always use for sequence validation. Never assume ordering or required fields manually.

* **FileTransferService** — upload/download files with integrity checks.
  Always use for file transfers. Never use ad-hoc SFTP or `scp`.

---

## **Agent Model**
 - Sub-agents run with least privilege. Each has a narrow scope.
 - Sub-agents follow same TDD gates
 - `overfit-verifier`: Detects overfitting, reports only.
 - `doc-drafter`: Keeps docs synchronized.
 - `code-reviewer`: Reviews code for quality, security, and maintainability.

---


## **Code Conventions**
 - Path ops: `Path(a) / b` (never `os.path.join`)
 - Logging: **parameterized logging** `logger.info("%s", var)` (no f-strings)
 - Type hints: **required** for all public functions
 - Docstrings: **Google-style** (`Args/Returns/Raises`)
 - Exceptions: **catch specific exceptions**; never bare `except:`
 - Encoding: **ASCII only** in code/logs; no emojis/unicode
 - Use our **wrappers** (SSHManager, DockerExecutor, ConfigManager, PromptSpecManager); never raw libs

---

## **Best Practices**
 - Small functions; **Single Responsibility Principle**
 - Avoid monoliths; **split modules** by responsibility
 - “**Zen of Python**” mindset (readability, explicitness, simplicity)

---

## **Error Handling & Resilience**
- Classify errors (validation, network, auth, execution)
- Retries with backoff for transient ops
- Fail with actionable error messages, no secrets in logs

---

## **Operating Procedures**
- All temporary/intermediary files go in → .claude/workspace/ only
- Delete temporary/debug/test artifacts after use
- Update [ROADMAP.md](ROADMAP.md) when completing a feature

---

## **Design & API surface**
 - **No global state**. Prefer dependency injection (pass clients/managers in constructors).
 - **Pure where possible**. Make helper functions deterministic and idempotent.

---

## **Commands**
Lint & Format:
`ruff format .`
`ruff check . --fix`

Cosmos CLI:
`cosmos create prompt "desc"`
`cosmos inference prompt.json`
`cosmos status`

---

## **Acceptance Checklist**
    ```
    - [ ] Gates 1–6 satisfied
    - [ ] Wrappers used exclusively (no raw libs)
    - [ ] Best Practices followed
    - [ ] No edits to tests from Gate 3
    - [ ] ruff clean
    - [ ] Coverage ≥ 80%
    - [ ] Docs updated
    - [ ] No secrets in code/logs/tests
    - [ ] Temp files removed from .claude/workspace/
    ```
---
