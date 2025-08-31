# Project State

This file tracks the current state of the project for AI assistants.

## 🎯 Current Focus
- **Working on**: Documentation reorganization and linting setup
- **Branch**: feature/new-developments
- **Status**: Active development
- **Priority**: Code quality and documentation

## 📅 Recent Changes (Last 7 Days)

### 2024-12-30
- ✅ Added comprehensive linting with Ruff (replaced flake8, black, isort)
- ✅ Fixed 473+ linting issues automatically
- ✅ Added MyPy, Bandit, Safety for code quality
- ✅ Reorganized all documentation
- ✅ Created professional README with quickstart

### 2024-12-31
- ✅ Comprehensive test suite reorganization
- ✅ Fixed 400+ failing tests
- ✅ Added CI/CD configuration

### 2024-12-29
- ✅ Windows-compatible SFTP implementation
- ✅ AI-powered smart naming system
- ✅ Video processing pipeline

## 🚧 Next Steps

1. [ ] Fix remaining 22 imports inside functions
2. [ ] Address remaining linting issues (152 total)
3. [ ] Increase test coverage to 90%
4. [ ] Add integration tests for GPU workflows
5. [ ] Create deployment documentation

## ⚡ Quick Context

### Environment
- **Development OS**: Windows 11 with MINGW64
- **Python Version**: 3.10+
- **GPU Instance**: 192.222.52.92 (Ubuntu, CUDA 12.4+)
- **Model Location**: `/home/ubuntu/NatsFS/cosmos-transfer1`
- **Docker Image**: `nvcr.io/ubuntu/cosmos-transfer1:latest`

### Key Paths
- **Config**: `cosmos_workflow/config/config.toml`
- **Prompts**: `inputs/prompts/`
- **Videos**: `inputs/videos/`
- **Outputs**: `outputs/`

### Recent Issues Resolved
- ✅ SFTP replacing rsync for Windows compatibility
- ✅ Circular imports in schema modules
- ✅ Datetime timezone issues
- ✅ Logging f-string performance

## 🐛 Known Issues

### High Priority
1. **Vocab out of range error** - Occurs with high-res videos + prompt upsampling
   - Workaround: Use manual upsampling functions

2. **Large file transfers timeout** - SFTP can timeout on files >1GB
   - Workaround: Increase timeout in SSHManager

### Medium Priority
1. **Docker cleanup** - Containers not always cleaned after errors
   - Workaround: Manual `docker container prune`

2. **Import organization** - 22 imports still inside functions
   - Status: Intentional for lazy loading

### Low Priority
1. **Line length violations** - 13 lines exceed 100 chars
2. **Missing docstrings** - Some internal functions lack docs

## 💡 Important Notes for AI

### When Modifying Code
1. **Always run**: `ruff check --fix` before committing
2. **Test with**: `pytest tests/ -m unit` for quick validation
3. **Update**: This PROJECT_STATE.md file with changes

### Code Style
- Formatter: Ruff (not Black)
- Line length: 100
- Imports: Sorted by Ruff rules
- Logging: Use lazy % formatting, not f-strings

### Testing
- Unit tests: Must be fast (<1s)
- Use fixtures from conftest.py
- Mark tests appropriately (@pytest.mark.unit/integration/system)

### Common Commands
```bash
# Linting
ruff check cosmos_workflow/ --fix
ruff format cosmos_workflow/

# Testing
pytest tests/ -m unit
pytest --cov=cosmos_workflow

# Running
python -m cosmos_workflow.cli create-spec "name" "prompt"
python -m cosmos_workflow.cli run spec.json
```

## 📊 Metrics

- **Test Coverage**: 80%
- **Linting Issues**: 152 (down from 625)
- **Python Files**: 29
- **Test Files**: 24
- **Documentation Files**: 8

## 🔄 Last Updated
2024-12-30 by Claude (automated update)