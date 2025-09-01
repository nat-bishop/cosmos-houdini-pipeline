# CLAUDE.md — Cosmos Workflow Orchestrator

## 🔴 CRITICAL: Documentation & Commit Policy
**ALWAYS after ANY change:**
1. Update `CHANGELOG.md` with dated entry
2. Update `README.md` if user-facing
3. Commit changes immediately with clear message
4. **Never delay commits** - commit as you complete each feature

## Mission
Python orchestrator for NVIDIA Cosmos-Transfer video generation on remote GPU via SSH + Docker.

## Core Rules

### Security
- **Never hardcode** secrets/IPs/paths → Use `config.toml`
- **SSH/SFTP only** (Windows compatible) → Use `SSHManager`

### Code Standards
- **Small functions** with type hints
- **Use `pathlib.Path`** (not `os.path`)
- **Logging**: `logger.info("Processing %s", file)` (NOT f-strings)
- **Tests**: Run before commits, 80% coverage minimum

### Quick Commands
```bash
# Test before commit
pytest tests/ -q --tb=no

# Core CLI commands
cosmos create prompt "text"           # Create prompt
cosmos inference prompt.json          # Run inference + upscale
cosmos prepare ./renders/              # Convert sequences
cosmos prompt-enhance *.json          # AI enhancement
cosmos status                          # Check GPU status
```

## Project Structure
```
cosmos_workflow/
├── cli/                   # Modular CLI (refactored from 935-line file)
│   ├── base.py           # Core utilities
│   ├── create.py         # Create commands
│   ├── inference.py      # Run inference
│   ├── prepare.py        # Video prep
│   └── enhance.py        # AI enhancement
├── config/config.toml     # All configuration
├── workflows/             # Main orchestrator
└── connection/            # SSH/SFTP handling
```

## Key Files
- **PromptSpec**: `inputs/prompts/{date}/{name}_ps_{hash}.json`
- **RunSpec**: `inputs/runs/{date}/{name}_rs_{hash}.json`
- **Config**: `cosmos_workflow/config/config.toml`

## Environment
- **Local**: Windows 11, Python 3.10+, Ruff formatter
- **Remote**: Ubuntu GPU, CUDA 12.4+, 24GB+ VRAM
- **Docker**: `nvcr.io/ubuntu/cosmos-transfer1:latest`

## Known Issues & Fixes
1. **High-res vocab error** → Reduce to 320×180
2. **SFTP timeout** → Increase to 1800s
3. **Docker cleanup** → Run `docker container prune`

## Critical Parameters
- Resolution limit: 940×529 (497k pixels)
- Safe resolution: 320×180 @ 2 frames
- Default steps: 35 (quality) or 1 (fast)
- GPU: Always 1 GPU (CUDA device 0)

## Testing Requirements
```bash
# Before ANY commit:
1. pytest tests/ -q --tb=no          # Must pass
2. Update CHANGELOG.md                # Document changes
3. git add -A && git commit -m "..."  # Commit immediately
```

## References
- [Model Weights](https://huggingface.co/collections/nvidia/cosmos-transfer1-67c9d328196453be6e568d3e)
- Details: `docs/ai-context/` for conventions & issues