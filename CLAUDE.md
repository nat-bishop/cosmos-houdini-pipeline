My name is Nat
---

## System Overview
Orchestrates AI inference workflows on remote GPU infrastructure via SSH. Provides both CLI (`cosmos`) and Gradio web interface for managing prompts and inference runs. Abstracts remote execution, file transfers, and Docker management complexity.

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
  - [ui/](cosmos_workflow/ui/) — Gradio UI app
  - [utils/](cosmos_workflow/utils/) — helpers
- [tests/](tests/) — pytest suite
- [inputs/](inputs/) — inputs & prompt payloads
- [outputs/](outputs/) — generated artifacts
- [docs/](docs/) — documentation

---

### **Responsibilities & Enforcement** (wrappers to use)
**Always use the appropriate APIs/wrappers, never call raw libraries directly** (e.g., `paramiko`, `docker`, ad-hoc subprocess, or JSON validation).
**'cosmos' CLI and gradio app should only use CosmosAPI, never the low level wrappers**

## Key Design Principle
Infrastructure details (location, provider, models) are configuration, not code. The system works identically whether running on cloud GPU or local workstation. CosmosAPI provides the stable interface that both CLI and Gradio use.

* **CosmosAPI** — **PRIMARY INTERFACE for all workflow operations**
  Always use for prompts, runs, inference, queries. This is the main facade.
  Never bypass this to use DataRepository or GPUExecutor directly.

* **SimplifiedQueueService** — **UI-ONLY job queue management (wraps CosmosAPI)**
  Provides simplified, reliable queuing capabilities for Gradio UI while CLI uses direct CosmosAPI calls.
  Database-first design using SQLite with atomic job claiming. Prevents GPU conflicts through container checks.
  Replaces legacy QueueService with simpler, more reliable architecture.

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

## **Common Mistakes to Avoid**
 - Writing `ssh.exec_command()` → Use RemoteCommandExecutor
 - Writing `docker run` strings → Use DockerCommandBuilder
 - Parsing JSON manually → Use ConfigManager validators

---

## **Agent Model**
 - Sub-agents run with least privilege. Each has a narrow scope.
 - Sub-agents have specific responsibilities and quality gates
 - `overfit-verifier`: Detects overfitting, reports only.
 - `doc-drafter`: Keeps docs synchronized.
 - `code-reviewer`: Reviews code for quality, security, and maintainability.

---


## **Code Conventions**
 - Path ops: `use pathlib.Path instead of os.path (ex, Path(a) / b rather than os.path.join)`
 - Logging: **parameterized logging** `logger.info("%s", var)` (no f-strings)
 - Type hints: **required** for all public functions
 - Docstrings: **Google-style** (`Args/Returns/Raises`)
 - Exceptions: **catch specific exceptions**; never bare `except:`
 - Encoding: **ASCII only** in code/logs; no emojis/unicode

---

## **Best Practices**
 - You must follow the "Zen of Python" mindset
 - DRY code: Extract common patterns into helpers, don't copy-paste
 - Small functions; **Single Responsibility Principle**
 - Avoid monoliths; **split modules** by responsibility
 - Avoid Over-Engineering and overly complex solutions
 - Avoid Over-Abstraction; KISS - keep it simple, stupid
 - Write a high quality, general purpose solution.
 - Focus on understanding the problem requirements and implementing the correct algorithm
 - Try different methods if your first approach doesn't work
 - Analyze your work after each step to see if is correct
 - YAGNI - Do not add functionality until it is necessary
 - For maximum efficiency, whenever you need to perform multiple independent operations, invoke all relevant tools simultaneously rather than sequentially

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

## **Quick Reference**

**Lint & Format:**
```bash
ruff format . && ruff check . --fix
```

**CLI Operations:**
```bash
cosmos create prompt "desc" video_dir  # Create prompt (returns ps_xxxxx ID)
cosmos inference ps_xxxxx              # Run inference on GPU
cosmos list prompts                    # List all prompts
cosmos status                          # Check GPU status
cosmos --help                          # See all CLI features
```

**Web Interface:**
```bash
cosmos ui                              # Launch Gradio web interface
```

**SSH Access:**
```bash
./scripts/ssh_lambda.ssh               # Direct SSH to workstation
```

---

## **Interfaces**
**CLI**: `cosmos` - Command-line interface for all operations
**Web UI**: `cosmos ui` - Gradio interface with same functionality as CLI
Both interfaces use CosmosAPI exclusively - never access low-level wrappers directly.