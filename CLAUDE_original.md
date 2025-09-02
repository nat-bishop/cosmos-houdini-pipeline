# CLAUDE.md — Cosmos Workflow Orchestrator

## 🔴 CRITICAL: Documentation & Commit Policy
**After completing each feature:**
1. Update `CHANGELOG.md` with dated entry
2. Update `README.md` if user-facing changes
3. Run tests: `pytest tests/ -q --tb=no`
4. **Commit all changes together** with clear message
5. **Document changes, then commit** - never commit incomplete work

## Mission
Python orchestrator for NVIDIA Cosmos-Transfer video generation on remote GPU via SSH + Docker. Deterministic, recoverable, observable.

## Core Rules

### Security & Config
- **Never hardcode** secrets/IPs/paths → Use `config.toml` or ENV vars
- **SSH/SFTP only** (Windows compatible) → Use `SSHManager` contexts
- **Resource cleanup** → Always use context managers, clean Docker containers

### Code Quality
- **Small functions** with full type hints, no monkey-patching
- **Use `pathlib.Path`** (never `os.path`), UTC with `timezone.utc`
- **Logging**: `logger.info("Processing %s", file)` (NOT f-strings)
- **Fail fast** on invalid specs with actionable errors
- **Idempotency**: Reruns must resume or no-op safely

### Testing
- **80% coverage minimum**, unit tests must run <1s
- Mark: `@pytest.mark.unit/integration/system`
- Use fixtures from `conftest.py`

## Quick Commands
```bash
# Core CLI commands
cosmos create prompt "text"           # Create prompt with AI naming
cosmos inference prompt.json          # Run inference + upscale
cosmos prepare ./renders/              # Convert sequences to videos
cosmos prompt-enhance *.json          # AI prompt enhancement
cosmos status                          # Check GPU status

# Testing before commit
pytest tests/ -q --tb=no              # Quick test run
ruff format cosmos_workflow/           # Format code
ruff check cosmos_workflow/ --fix      # Fix linting issues
```

## Project Structure
```
cosmos_workflow/
├── cli_new/               # Modular CLI (refactored from 935-line file)
│   ├── base.py           # Core utilities & context
│   ├── create.py         # Create commands (prompt, run)
│   ├── inference.py      # Run inference + upscaling
│   ├── prepare.py        # Video preparation
│   ├── enhance.py        # AI enhancement
│   └── status.py         # GPU status check
├── config/config.toml     # All configuration
├── workflows/             # WorkflowOrchestrator
├── connection/            # SSHManager (SFTP/SSH)
├── prompts/               # PromptSpec, RunSpec schemas
└── local_ai/             # Video processing, AI naming
```

## Key Files & Paths
- **PromptSpec**: `inputs/prompts/{date}/{name}_ps_{hash}.json`
- **RunSpec**: `inputs/runs/{date}/{name}_rs_{hash}.json`
- **Videos**: `inputs/videos/{name}/{color|depth|segmentation}.mp4`
- **Outputs**: `outputs/{name}_{run_id}/`
- **Config**: `cosmos_workflow/config/config.toml`

## Environment & Configuration

### Local Dev
- **OS**: Windows 11, Python 3.10+
- **Formatter**: Ruff (line length 100)
- **CLI**: Click + Rich for modern interface

### Remote GPU
- **Model**: Cosmos-Transfer1-7B at `/home/ubuntu/NatsFS/cosmos-transfer1`
- **Docker**: `nvcr.io/ubuntu/cosmos-transfer1:latest`
- **Requirements**: CUDA 12.4+, 24GB+ VRAM
- **GPU**: Always 1 GPU (CUDA device 0)

## Critical Parameters & Limits
- **Resolution limit**: 940×529 (497k pixels max)
- **Safe resolution**: 320×180 @ 2 frames
- **Inference steps**: 35 (quality) or 1 (fast/distilled)
- **Guidance scale**: 7.0-8.0 (CFG default)
- **Control weights**: [vis=0.3, edge=0.3, depth=0.2, seg=0.2]
- **Upscale weight**: 0.5 (default for 4K upscaling)
- **Token formula**: width × height × frames × 0.0173

## Known Issues & Fixes

### Critical Issues
1. **High-res vocab error** → Reduce to 320×180 or preprocess
2. **SFTP timeout >1GB** → Increase timeout to 1800s in SSHManager
3. **Docker cleanup** → Run `docker container prune` on remote
4. **Pre-commit hooks failing** → Use `--no-verify` temporarily (fix in TODO)

### Common Errors
- "Connection refused" → SSH down or firewall issue
- "Permission denied" → Fix: `chmod 600 ~/.ssh/key.pem`
- "No such file" → Remote directory not mounted
- "CUDA out of memory" → Enable `offload_models: true`
- "Vocab size error" → Video resolution too high

## Docstring Standard
```python
def process_video(input_path: Path, fps: int = 24) -> VideoMetadata:
    """Process video and extract metadata.

    Args:
        input_path: Path to input video
        fps: Target frame rate

    Returns:
        VideoMetadata with extracted info

    Raises:
        FileNotFoundError: If input missing
    """
```

## Development Workflow
1. **Start**: Pull latest, check `TODO.md` for priorities
2. **Develop**: Write tests first (TDD), small commits
3. **Test**: Run `pytest tests/ -q --tb=no`
4. **Document**: Update CHANGELOG.md and relevant docs
5. **Commit**: All related changes together with clear message
6. **Push**: To feature branch, create PR if ready

## Control Modalities
- **vis/blur**: Visual blur (0.0-1.0)
- **edge**: Canny edge detection
- **depth**: Depth estimation
- **segmentation**: Semantic segmentation

## SSH/Debug Quick Reference
```bash
# Test SSH connection
ssh -i ~/.ssh/key.pem ubuntu@<ip>

# Check Docker on remote
docker ps
docker images | grep cosmos

# Clean up failed containers
docker container prune -f
```

## References
- [Model Weights](https://huggingface.co/collections/nvidia/cosmos-transfer1-67c9d328196453be6e568d3e)
- [Cosmos GitHub](https://github.com/nvidia-cosmos/cosmos-transfer1)
- Detailed docs: `docs/ai-context/` for conventions & issues
