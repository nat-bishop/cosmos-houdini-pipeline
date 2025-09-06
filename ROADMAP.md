# ROADMAP - Cosmos Workflow Orchestrator

## 🚀 Priority 0: Architecture Refactoring (NEW)

### Service-Oriented Architecture
- [ ] **Phase 0: Foundation (Week 1)**
  - [ ] Create SQLite database schema with SQLAlchemy models
  - [ ] Implement service layer (WorkflowService, PromptService)
  - [ ] Refactor CLI to use services instead of direct orchestrator calls
  - [ ] Add unit tests for service layer

- [ ] **Phase 1: Core Features (Week 2)**
  - [ ] Implement unified `cosmos run` command (single-step workflow)
  - [ ] Add `cosmos list` command to view recent runs
  - [ ] Add `cosmos search` command for full-text prompt search
  - [ ] Add smart defaults and auto-discovery

- [ ] **Phase 2: API & UI (Week 3, Optional)**
  - [ ] Create FastAPI application with endpoints
  - [ ] Implement WebSocket for real-time progress
  - [ ] Build simple web dashboard (HTML + Alpine.js)
  - [ ] Add gallery view for outputs

**See `docs/COSMOS_REFACTORING_PLAN.md` for full implementation details**

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

- [ ] **Investigate test-runner subagent test specificity**
  - Verify if test-runner subagent runs specific tests vs entire suite
  - Ensure it follows TDD gate-specific testing (e.g., only new test file in Gate 2)
  - Optimize test execution for focused development workflow
  - Document expected test-runner behavior for different scenarios

- [ ] **Investigate dead code analysis with tools like Vulture**
  - Analyze codebase for unused functions, classes, and imports
  - Configure Vulture or deadcode for CLI-centric architecture
  - Integrate with CI/CD pipeline for ongoing maintenance
  - Focus on single entry point (CLI) to identify truly unused code

- [ ] **Review and standardize CLI defaults architecture**
  - Audit all CLI commands for sensible defaults (e.g., --resolution behavior)
  - Determine whether defaults should be at CLI level vs business logic level
  - Check other system defaults beyond CLI (config files, environment variables)
  - Ensure consistent user experience across all commands
  - Document default value rationale and override mechanisms

- [x] **Fixed overfit-verifier agent scope and clarified TDD workflow**

  **Changes Made (2025-09-04):**
  - Updated Gate 1 to emphasize behavioral testing and real implementations
  - Clarified overfit-verifier to only check for hardcoded test values via static analysis
  - Added explicit "do NOT generate test scripts" to both agent and command
  - Removed "Suggest Edge Cases" section that was expanding scope
  - Made clear distinction: overfitting = memorized tests, not missing features

  **Original Issues:**
  - Internal vs external verification not clearly distinguished in workflow
  - Claude mistakenly tries to write EXTERNAL reports (should only check if they exist)
  - Agent name doesn't clarify it's for internal self-checking only
  - CLAUDE.md workflow unclear about who creates EXTERNAL_overfit_check.md

  **Scope Creep Problems:**
  - Agent definition includes non-overfitting concerns:
    - Line 13: "Missing edge case handling" (feature completeness, not overfitting)
    - Line 26: "Missing validation/error handling" (code quality, not overfitting)
    - Lines 27-32: "Suggest Edge Cases" (test improvement, not overfitting)
  - Claude's prompts to agent expand scope further (transaction handling, session management)
  - Agent performing general code review instead of focused overfitting detection

  **What Agent SHOULD Check:**
  - Hardcoded test values (e.g., `if input == "test": return expected`)
  - Conditional logic for specific test cases
  - Solutions that memorize rather than compute
  - Code that would fail with slight input variations

  **What Agent Should NOT Check:**
  - Best practices (import placement)
  - Performance considerations (hash length, concurrency)
  - Missing features not tested
  - Code style issues
  - Database transaction patterns

  **External Verifier Behavior:**
  - Currently generates custom Python test scripts to detect overfitting
  - Question: Is generating test scripts best practice vs just analyzing code?
  - Scripts left in workspace - should they be cleaned up?
  - May be overengineering - static analysis might suffice

  **Recommended Solutions:**
  - Rename internal agent to `tdd-overfitting-detector` (clarify internal role)
  - Remove scope creep from agent definition (edge cases, validation, etc.)
  - Add explicit "You do NOT evaluate" section to agent
  - Clarify: Internal agent for self-check, external human verification separate
  - External verifier should consider static analysis over test generation
  - Add workflow clarification: Claude checks for report, never creates it

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
