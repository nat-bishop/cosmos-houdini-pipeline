# ROADMAP - Cosmos Workflow Orchestrator

## Priority 1: Critical Issues

### Remote Environment Setup
- [ ] **Build Docker image on remote instance**
  - Run: `sudo docker build -f Dockerfile . -t nvcr.io/ubuntu/cosmos-transfer1:v1.0.0`
  - Update config.toml to use versioned image

- [ ] **Setup model checkpoints**
  - Download required checkpoints to `/home/ubuntu/NatsFS/cosmos-transfer1/checkpoints/`
  - Create manifest of checkpoint versions

- [ ] **Configure Hugging Face authentication**
  - Set up read-only HF token
  - Configure as environment variable or Docker secret

### Security & Version Control
- [ ] **Pin Docker image versions**
  - Stop using `:latest` tags
  - Create versioned tags (e.g., `cosmos-transfer1:v1.0.0`)
  - Update all references in code and config

- [ ] **Version control model checkpoints**
  - Document specific checkpoint versions/hashes
  - Create manifest file listing all checkpoints
  - Implement checkpoint validation

### Code Quality
- [x] **~~Fix hardcoded negative prompt~~** ✅ COMPLETED 2025-01-03
  - Changed default to more specific gaming/cartoon-focused prompt
  - Updated all code locations and test assertions
  - Users can still override via `--negative` CLI flag

- [ ] **Investigate Claude Code not following TDD no-mock instructions**
  - Claude Code is using mocks in TDD Gate 1 tests despite explicit instructions
  - CLAUDE.md clearly states "NO MOCKS" for Gate 1
  - Tests must call real functions even if they don't exist yet
  - Need to debug why instructions are being ignored

- [ ] **Fix doc-drafter agent overstepping boundaries**
  - doc-drafter agent is modifying code files, not just documentation
  - Agent has Bash access allowing it to make git commits
  - Agent added implementation code when it should only update docs
  - Need to restrict permissions: remove Bash access or limit to doc files only

## Priority 2: Features & Enhancements

### Performance Optimization
- [ ] **Implement batch processing**
  - Process multiple prompts in single session
  - Optimize GPU memory usage
  - Add queue management

- [ ] **Add caching for model loading**
  - Keep models loaded between runs
  - Implement memory management
  - Add cache configuration options

### Enhanced Video Processing
- [ ] **Add video interpolation features**
  - Frame interpolation for smoother output
  - Temporal consistency improvements
  - Motion smoothing options

- [ ] **Support for longer video sequences**
  - Currently limited to short clips
  - Implement chunking for longer videos
  - Add temporal coherence

### CLI Enhancement
- [ ] **Add interactive prompt creation interface**
  - CLI wizard for creating prompts
  - Template system for common scenarios
  - Prompt preview and validation

### Documentation
- [ ] **Create comprehensive user guide**
  - Step-by-step setup instructions
  - Common workflow examples
  - Troubleshooting guide

### Infrastructure
- [x] **~~Fix pre-commit hooks configuration~~** ✅ COMPLETED 2025-01-02
  - Simplified from 25+ hooks to 11 essential ones
  - Execution time: 30+ seconds → 2 seconds
  - Removed overengineered checks and false positives
  - Now focuses on: file hygiene + Python formatting/linting with Ruff

- [ ] **Setup Claude to interact with GitHub Actions**
  - Configure Claude Code to trigger and monitor GitHub Actions
  - Add ability to view CI/CD results directly

- [ ] **Fix GitHub Actions workflows**
  - Update CI/CD pipelines
  - Add automated testing on PR
  - Configure release automation

## Priority 3: Future Enhancements

### Advanced Features
- [ ] **Multi-modal control enhancement**
  - Better blending of control modalities
  - Adaptive weight adjustment
  - Control strength scheduling

- [ ] **Real-time preview system**
  - WebUI for monitoring progress
  - Live output streaming
  - Interactive parameter adjustment

### Architecture Improvements
- [ ] **Implement plugin system**
  - Extensible processing pipeline
  - Custom model support
  - Third-party integrations

- [ ] **Add distributed processing**
  - Multi-node GPU cluster support
  - Job scheduling and orchestration
  - Load balancing

### Monitoring & Analytics
- [ ] **Add telemetry and monitoring**
  - GPU usage tracking
  - Performance metrics
  - Error tracking and alerting
