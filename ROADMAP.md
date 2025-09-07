# ROADMAP - Cosmos Workflow Orchestrator

## 🎯 Priority 0: Architecture Clarity & Future Refactoring

### Architecture Documentation Improvements ✅ COMPLETED 2025-01-07
- [x] Clarified WorkflowOperations as the main facade layer
- [x] Updated README.md to show correct architecture hierarchy
- [x] Documented that WorkflowOrchestrator is GPU execution component (not facade)
- [x] Removed old UI file that violated abstraction (app_old.py)

### Future Architecture Renaming Strategy (Version 2.0)
**Target: Major version release to avoid breaking changes**

Proposed renaming for clearer architecture understanding:
```
Current Name              →  Proposed Name           →  Role
─────────────────────────────────────────────────────────────────
WorkflowOperations        →  WorkflowOrchestrator    →  Main Facade (primary interface)
WorkflowOrchestrator      →  GPUExecutor             →  GPU execution component
WorkflowService           →  DataService             →  Database operations component
```

**Benefits of renaming:**
- `WorkflowOrchestrator` as facade name is more intuitive
- `GPUExecutor` clearly indicates its GPU-specific role
- `DataService` clearly indicates database focus
- Matches common architectural patterns

**Migration strategy:**
1. Version 1.x: Keep current names, use clear documentation
2. Version 2.0 planning:
   - Create deprecation warnings in 1.9.x
   - Provide migration script for existing code
   - Update all imports with compatibility layer
   - Full cutover in 2.0 with old names removed

**Implementation checklist for v2.0:**
- [ ] Create compatibility import layer
- [ ] Add deprecation warnings to old class names
- [ ] Update all internal references (148+ occurrences)
- [ ] Update all documentation (17+ files)
- [ ] Create migration guide for users
- [ ] Update test suite
- [ ] Coordinate with major feature release

## 🔧 Technical Debt: Architectural Coupling

### Issue: Cross-Cutting Concerns Not Properly Abstracted
The `--stream` flag represents a cross-cutting concern that violates separation of concerns:

**Current Problem:**
- `stream_logs` parameter passed through 5+ layers (CLI → API → Orchestrator → Executor)
- DockerExecutor knows about log streaming (violates single responsibility)
- 4x code duplication for streaming setup in DockerExecutor methods
- Mixing execution logic with monitoring/streaming logic

**Why Simple Refactoring Won't Work:**
- Adding helper methods in DockerExecutor increases coupling (makes it responsible for streaming)
- Moving streaming to orchestrator still leaves parameter passing through layers
- The core issue is architectural, not just code duplication

**Proper Architectural Solutions:**

1. **Event-Driven Architecture**
   - DockerExecutor publishes execution events
   - Streaming service subscribes to events independently
   - Complete decoupling of execution from monitoring

2. **Context Object Pattern**
   - Single ExecutionContext object with all cross-cutting concerns
   - Components query context for their needs
   - Reduces parameter proliferation

3. **Aspect-Oriented / Decorator Pattern**
   - Wrap execution methods with streaming decorator
   - Keep core logic unaware of streaming
   - Add/remove features without modifying core

4. **Configuration Service**
   - Centralized configuration that components can query
   - No need to pass flags through layers
   - Runtime feature toggles

**Current State:**
- Keeping duplication for now (explicit is better than wrong abstraction)
- DockerExecutor remains cohesive (only responsible for Docker execution)
- Streaming is optional and doesn't affect core execution logic
- Trade-off: Some duplication vs maintaining proper boundaries

## 🚀 Priority 1: Architecture Refactoring (Service-Oriented)

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

### Container Management Improvements
**Status:** Partially Complete (2025-01-07)

#### Completed:
- [x] Removed unused `cleanup_containers()` method
- [x] Added `kill_containers()` method to forcefully terminate running containers
- [x] Created `cosmos kill` CLI command for emergency container termination
- [x] Added kill_containers to WorkflowOperations API
- [x] **Centralized Container Detection (2025-09-07)**
  - Added `get_active_container()` method for single-source container detection
  - Eliminated duplicate `docker ps` calls throughout codebase
  - Single container paradigm with warnings when multiple containers detected
  - Structured container information with ID, name, status, image, and creation time
  - Improved `cosmos status` command with GPU detection via `get_gpu_info()` method

#### Future Improvements (Run-Specific Container Management):
**Target: Version 1.5**

1. **Container Labeling with Run IDs**
   - Add `--label run_id={run_id}` to container creation
   - Enables targeting specific runs for termination
   - Preserves other running jobs when killing one

2. **Kill Specific Runs**
   - New method: `kill_run(run_id: str)`
   - CLI: `cosmos kill --run <run_id>`
   - Finds container by run_id label
   - Downloads partial logs before killing
   - Updates database status to "cancelled"

3. **Add "cancelled" Status**
   - Update database model to include "cancelled" as valid status
   - Update WorkflowService validation to accept "cancelled"
   - Set completed_at timestamp when cancelling
   - Preserve partial outputs and logs

4. **Graceful Shutdown Option**
   - Add `--graceful` flag to kill command
   - Use `docker stop` (SIGTERM) instead of `docker kill` (SIGKILL)
   - Allow containers time to clean up before termination
   - Default timeout: 30 seconds before force kill

5. **Container Lifecycle Tracking**
   - Store container ID in database when run starts
   - Track container state changes
   - Auto-cleanup orphaned containers on startup
   - Periodic health checks for running containers

**Implementation Plan:**
- [ ] Add container labeling support to DockerCommandBuilder
- [ ] Update inference/upscaling to use run_id labels
- [ ] Implement kill_run() in DockerExecutor
- [ ] Add "cancelled" status to database schema
- [ ] Update WorkflowService to handle cancelled status
- [ ] Create run-specific kill CLI command
- [ ] Add container ID tracking to Run model
- [ ] Implement graceful shutdown options

### Critical: Log Recovery on Failure
- [ ] **Ensure logs always download even on Docker failure**
  - Currently logs may be lost if Docker execution fails
  - Add finally block to DockerExecutor methods (run_inference, run_upscaling, run_batch_inference)
  - Explicitly download remote log file before raising exceptions
  - Critical for debugging GPU errors (CUDA OOM, model loading failures, etc.)
  - Implementation: Add `_ensure_log_downloaded()` method and call in finally blocks
  - Test with intentional failures to verify log preservation

### Prompt Enhancement Tracking
- [ ] **Make prompt-enhance operations trackable**
  - Currently prompt-enhance creates an operation_id but no database run
  - Users cannot monitor enhancement progress in real-time
  - Option 1: Create "enhance" run type (may cause conceptual confusion - runs produce videos, not text)
  - Option 2: Create lightweight operations table for non-video operations
  - Option 3: Extend runs table to support text outputs for enhance operations
  - Recommended: Option 2 - cleaner separation of concerns
  - Note: Log streaming now available via `cosmos status --stream` for active containers

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

- [ ] **Implement Wrapper Compliance & Automatic Detection System**
  **Target: Version 1.3 - High Priority**

  **Current State:**
  - 7 files using f-string logging (violates parameterized logging rule)
  - No automated enforcement of wrapper patterns
  - Good news: No direct paramiko/docker/subprocess imports found

  **Phase 1: Immediate Fixes (1 hour)**
  - [ ] Fix f-string logging in 7 files:
    - cosmos_workflow/api/workflow_operations.py
    - cosmos_workflow/execution/docker_executor.py
    - cosmos_workflow/transfer/file_transfer.py
    - cosmos_workflow/workflows/workflow_orchestrator.py
    - cosmos_workflow/ui/app.py
    - cosmos_workflow/connection/ssh_manager.py
    - cosmos_workflow/services/workflow_service.py

  **Phase 2: Import-Linter Setup (2 hours)**
  - [ ] Install and configure import-linter
  - [ ] Create .importlinter configuration file with contracts:
    - Forbidden: CLI cannot import WorkflowService/DatabaseConnection directly
    - Layers: CLI → API → Service/Orchestrator → Infrastructure
    - Independence: Prevent circular dependencies between modules
  - [ ] Add to pre-commit hooks
  - [ ] Add to CI/CD pipeline

  **Phase 3: Architecture Tests (4-6 hours)**
  - [ ] Create tests/test_architecture.py with AST-based validation
  - [ ] Check for direct library imports (paramiko, docker, subprocess)
  - [ ] Validate logging uses parameterized format
  - [ ] Ensure JSON operations use appropriate wrappers
  - [ ] Check that CLI only uses WorkflowOperations

  **Phase 4: Documentation (2-3 hours)**
  - [ ] Create docs/ARCHITECTURE_ENFORCEMENT.md
  - [ ] Add wrapper usage examples to each wrapper module
  - [ ] Create wrapper cheat sheet for quick reference
  - [ ] Document violation examples and fixes

  **Expected Benefits:**
  - Prevents architectural drift (saves 10-20 hours/month)
  - Makes onboarding 50% faster with clear boundaries
  - Reduces bugs from improper wrapper usage
  - ROI: 10 hours investment pays for itself in first month

  **Implementation Notes:**
  - Start with warning mode, move to strict after cleanup
  - Use industry-standard import-linter (no custom tooling)
  - Leverage existing pre-commit infrastructure
  - Skip custom Ruff plugins (too complex, low ROI)

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

### Video Upscaling Implementation (4K Enhancement)
- [ ] **Implement upscaling as separate database run**
  - Upscaling must be a completely separate GPU execution after inference
  - Create new run type: "upscale" (distinct from "inference")
  - Link upscale run to parent inference run in database

- [ ] **Upscale controlnet specification**
  - Minimal JSON with only:
    ```json
    {
      "input_video_path": "outputs/{inference_run_id}/output.mp4",
      "upscale": {"control_weight": 0.5}
    }
    ```
  - No other controls (vis, edge, depth, seg) should be included

- [ ] **Upscale execution flow**
  1. Complete inference run successfully
  2. Create new "upscale" run in database
  3. Use inference output as upscale input
  4. Execute with dedicated upscale.sh script
  5. Track separately in database with own status/logs

- [ ] **CLI commands**
  - `cosmos upscale <run_id>` - Upscale a completed inference run
  - `cosmos inference --with-upscale` - Run inference then auto-upscale
  - Keep upscale weight configurable (default 0.5)

- [ ] **Technical requirements**
  - Separate DockerExecutor method for upscaling
  - Independent log file for upscale process
  - Proper error handling if inference output missing
  - Support for NUM_GPU=4 for faster upscaling

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
