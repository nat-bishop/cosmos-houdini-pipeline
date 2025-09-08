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
- Use `doc-drafter` agent to update documentation

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
  - [execution/](cosmos_workflow/execution/) — GPU execution & Docker commands
  - [connection/](cosmos_workflow/connection/) — SSH & file transfer
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

### **Responsibilities & Enforcement** (wrappers to use)
**Always use the appropriate APIs/wrappers, never call raw libraries directly** (e.g., `paramiko`, `docker`, ad-hoc subprocess, or JSON validation).
**'cosmos' CLI and gradio app should only use CosmosAPI, never the low level wrappers**

* **CosmosAPI** — **PRIMARY INTERFACE for all workflow operations**
  Always use for prompts, runs, inference, queries. This is the main facade.
  Never bypass this to use DataRepository or GPUExecutor directly.

* **SSHManager** — create/manage SSH sessions (infrastructure only).
  Use only for low-level SSH tasks. Never call `paramiko.SSHClient()` directly.
  **ALWAYS use as context manager**: `with ssh_manager:` ensures connection/cleanup.

* **RemoteCommandExecutor** — run remote commands via SSH (infrastructure only).
  Use only for low-level remote execution. Never call inline `ssh` or `subprocess`.

* **DockerExecutor** — execute containers, stream logs (infrastructure only).
  Always pair with **DockerCommandBuilder**. Never call `docker.from_env()` or raw subprocess Docker commands.

* **DockerCommandBuilder** — construct valid `docker run/exec` commands.
  Always use for building Docker commands. Never hand-roll docker CLI strings.

* **BashScriptBuilder** — build safe, multi-step bash scripts.
  Always use for multi-step shell workflows. Never concatenate raw shell strings.

* **ConfigManager** — load/validate config files and environment.
  Always use for configuration. Never parse environment variables manually.

* **FileTransferService** — upload/download files with integrity checks (infrastructure only).
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
 - Use our **wrappers**; never raw libs

---

## **Best Practices**
 - You must follow the "Zen of Python" mindset
 - Small functions; **Single Responsibility Principle**
 - Avoid monoliths; **split modules** by responsibility
 - Avoid Over-Engineering and overly complex solutions
 - Write a high quality, general purpose solution.
 - Focus on understanding the problem requirements and implementing the correct algorithm
 - Try different methods if your first approach doesn't work
 - For maximum efficiency, whenever you need to perform multiple independent operations, invoke all relevant tools simultaneously rather than sequentially.

---

## **Error Handling & Resilience**
- Classify errors (validation, network, auth, execution)
- Fail with actionable error messages, no secrets in logs
- Fail loudly rather than using fallbacks or failing silently

---

## **Operating Procedures**
- All temporary/intermediary files go in → .claude/workspace/ only
- If you create any temporary new files, scripts, or helper files for iteration, clean up these files by removing them at the end of the task.
- After receiving tool results, carefully reflect on their quality and determine optimal next steps before proceeding. Use your thinking to plan and iterate based on this new information, and then take the best next action.
- Update [ROADMAP.md](ROADMAP.md) when completing a feature
- Prefer running single tests, and not the whole test suite, for performance
- Avoid technical debt; prefer to delete old code rather than maintain legacy solutions
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
`cosmos inference ps_xxxxx`             # Execute inference on GPU (creates run internally)
`cosmos list prompts`                   # List all prompts
`cosmos status`                         # Check GPU status

Use `cosmos --help` to understand CLI features.

---