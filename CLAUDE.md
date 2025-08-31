# CLAUDE.md — Project Memory (Cosmos Workflow Orchestrator)

## 0) Scope
This file defines how to work in this repo: goals, constraints, commands, code style, run/test/doc rules. Details in linked docs.

## 1) Mission
Build a Python orchestrator that prepares inputs and executes NVIDIA Cosmos-Transfer video generation on remote GPU via SSH + Docker. Deterministic, recoverable, observable.

## 2) Ground Rules (STRICT)

### Security & Config
1. **Never hardcode** secrets, IPs, usernames, or paths. Use `cosmos_workflow/config/config.toml` or ENV vars.
2. **SSH/SFTP only** - no rsync (Windows compatibility). Use `SSHManager` context managers.

### Code Quality
3. **Small functions** with full type hints. No dynamic monkey-patching.
4. **Use `pathlib.Path`** (never `os.path`). All datetimes are UTC with `timezone.utc`.
5. **Logging**: Lazy % formatting (NOT f-strings). No print debugging.
   ```python
   logger.info("Processing %s", filename)  # Good
   logger.info(f"Processing {filename}")   # Bad
   ```

### Robustness
6. **Fail fast** on invalid specs. Provide actionable error codes.
7. **Idempotency**: Reruns must resume or no-op. Never corrupt artifacts.
8. **Resource cleanup**: Always use context managers. Clean up Docker containers.

## 3) Documentation Rules

### When You Change Code
1. **CHANGELOG.md**: Log ALL changes chronologically
2. **README.md**: Update if user-facing features change
3. **docs/implementation/**: Add detailed docs for new features
4. **CLAUDE.md**: Only update for workflow/structure changes

### Docstring Requirements
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

## 4) Testing Rules

### Test Coverage
- **Minimum 80%** coverage required
- **Unit tests** must run in <1s
- Mark tests: `@pytest.mark.unit/integration/system`
- Use fixtures from `conftest.py`

### Before Committing
```bash
# 1. Format & lint
ruff format cosmos_workflow/
ruff check cosmos_workflow/ --fix

# 2. Run tests
pytest tests/ -m unit --cov=cosmos_workflow

# 3. Full validation (if changing core logic)
pytest tests/ --cov=cosmos_workflow --cov-report=term-missing
```

## 5) Quick Reference

### Key Commands
```bash
# Create prompt with AI naming
python -m cosmos_workflow.cli create-spec "name" "prompt text" --input-video video.mp4

# Execute on GPU (default 2 GPUs)
python -m cosmos_workflow.cli run prompt_spec.json --num-gpu 2

# Convert PNG sequence to video
python -m cosmos_workflow.cli convert-sequence /path/to/pngs --fps 24

# Prepare video for inference
python -m cosmos_workflow.cli prepare-inference input.mp4 --target-res 720
```

### Project Structure
```
cosmos_workflow/
├── cli.py                 # Entry point - all commands
├── config/config.toml     # SSH, paths, Docker config
├── connection/            # SSHManager (SFTP/SSH)
├── execution/             # DockerExecutor
├── prompts/               # PromptSpec, RunSpec schemas
├── workflows/             # WorkflowOrchestrator
└── local_ai/             # Video processing, smart naming
```

### Core Abstractions
- **PromptSpec**: Prompt definition → `inputs/prompts/{date}/{name}_ps_{hash}.json`
- **RunSpec**: Execution config → `inputs/runs/{date}/{name}_rs_{hash}.json`
- **WorkflowOrchestrator**: Main pipeline (workflows/workflow_orchestrator.py)
- **SSHManager**: Remote ops with SFTP (connection/ssh_manager.py)

## 6) Environment

### Local Dev
- **OS**: Windows 11 (MINGW64)
- **Python**: 3.10+ required
- **Formatter**: Ruff (NOT Black), line length 100

### Remote GPU
- **Config**: See `cosmos_workflow/config/config.toml`
- **Model**: Cosmos-Transfer1-7B at `/home/ubuntu/NatsFS/cosmos-transfer1`
- **Docker**: `nvcr.io/ubuntu/cosmos-transfer1:latest`
- **Requirements**: CUDA 12.4+, 24GB+ VRAM

## 7) Critical Known Issues

### Blockers (with workarounds)
1. **Vocab error** on high-res videos + prompt upsampling
   - Fix: Use manual upsampling or reduce resolution first
2. **SFTP timeout** on files >1GB
   - Fix: Increase timeout in SSHManager to 1800s
3. **Docker cleanup** after failures
   - Fix: Run `docker container prune` on remote

### Important Parameters
- `num_steps`: 35 (quality) or 1 (distilled/fast)
- `guidance_scale`: 8.0 (CFG default)
- `num_gpu`: 1-2 recommended
- `offload_models`: True for memory optimization

Details: `docs/ai-context/KNOWN_ISSUES.md`

## 8) Control Modalities
- **vis/blur**: Visual blur (0.0-1.0)
- **edge**: Canny edge detection
- **depth**: Depth estimation
- **segmentation**: Semantic segmentation
- Default weights: [0.3, 0.3, 0.2, 0.2]

## 9) Common Debugging

### SSH/SFTP Issues
```bash
# Check key permissions
chmod 600 ~/.ssh/key.pem
# Test connection
ssh -i key.pem ubuntu@192.222.52.92
```

### Error Patterns
- "Connection refused" → SSH down or firewall
- "Permission denied" → Key permissions or wrong user
- "No such file" → Remote dir not mounted
- "CUDA out of memory" → Enable offloading or reduce batch

## 10) References
- [Cosmos GitHub](https://github.com/nvidia-cosmos/cosmos-transfer1)
- [Model Weights](https://huggingface.co/collections/nvidia/cosmos-transfer1-67c9d328196453be6e568d3e)
- Conventions: `docs/ai-context/CONVENTIONS.md`
- Issues: `docs/ai-context/KNOWN_ISSUES.md`
