My name is NAT

**Purpose**
This file defines how Claude Code operates in this repository.
It specifies TDD workflow, best practices, and safety practices.
---

# **TDD Workflow**

All work follows a **gated TDD flow**. If a gate fails, stop and request review.

### **Gate 1 — Write Tests First**
- **Test the behavior of the system, not its implementation details.**
- **Generalization pressure**: add enough behavioral cases (happy path + boundaries + error paths) that only a general solution can pass.
- Control nondeterminism via our wrappers (**no third-party mocking**):
  - Prefer fakes that implement wrapper interfaces where determinism is required (e.g., FakeClock, FixedRNG(seed), loopback/no-op network/SSH/Docker).
  - Apply the same approach to filesystem/env access when needed.
- Always consider edge cases.
- **Prohibited**: raw mocks of core domain behavior; global state; bypassing wrappers.
- Expected: all tests fail.

### **Gate 2 — Verify Tests Fail**
 - Verify tests introduced or modified in this TDD cycle fail.
 - The pre-existing suite remains unchanged (no legacy tests were modified).
 - **Do Not** run coverage of the full test suite in this gate
 - Run the following in parallel when verifying:
   - pytest for newly introduced/modified test files
   - verify no existing tests were accidentally modified

### **Gate 3 — Commit Failing Tests**
Tests are the contract. Commit them unchanged.

### **Gate 4 — Make Tests Pass**
- Implement minimal code to pass all tests.
- Do **not** modify tests, they are a contract.
- **Must** Run the `overfit-verifier` sub-agent to ensure generalization before proceeding.
- Run the following in parallel to verify success:
  - pytest (for the tests you just made pass)
  - overfit-verifier agent (to ensure generalization)

### **Gate 5 — Document**
- Update [README.md](README.md)
- Update [CHANGELOG.md](CHANGELOG.md)
- Update [docs/](docs/)
- Use `doc-drafter` for consistency.

### **Gate 6 — Review**
- Run the following checks in parallel:
  - code-reviewer agent
  - ruff check (lint)
  - pytest --cov (coverage)

---

## **Project Structure**
- [cosmos_workflow/](cosmos_workflow/) — package root
  - [services/](cosmos_workflow/services/) — business logic & data operations
  - [database/](cosmos_workflow/database/) — SQLAlchemy models & connection
  - [workflows/](cosmos_workflow/workflows/) — orchestration & GPU flows
  - [connection/](cosmos_workflow/connection/) — SSH & file transfer
  - [execution/](cosmos_workflow/execution/) — Docker & command exec
  - [transfer/](cosmos_workflow/transfer/) — File Transfer
  - [config/](cosmos_workflow/config/) — config and `config.toml`
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
from cosmos_workflow.config import ConfigManager
from cosmos_workflow.transfer import FileTransferService
from cosmos_workflow.services import WorkflowService
from cosmos_workflow.database import DatabaseConnection, init_database
from cosmos_workflow.utils import nvidia_format
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
  Always use for configuration. Never parse environment variables manually.

* **WorkflowService** — manage all prompts and runs in database.
  Always use for data operations. Never create JSON files for data storage.

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
 - Use our **wrappers** (SSHManager, DockerExecutor, ConfigManager, WorkflowService); never raw libs

---

## **Best Practices**
 - Small functions; **Single Responsibility Principle**
 - Avoid monoliths; **split modules** by responsibility
 - "**Zen of Python**" mindset (readability, explicitness, simplicity)
 - Avoid Over-Engineering
 - Batch independent read operations and validation checks

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
`cosmos create prompt "desc" video_dir`  # Returns ps_xxxxx ID
`cosmos create run ps_xxxxx`            # Returns rs_xxxxx ID
`cosmos inference rs_xxxxx`             # Execute run on GPU
`cosmos list prompts`                   # List all prompts
`cosmos status`                         # Check GPU status

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
