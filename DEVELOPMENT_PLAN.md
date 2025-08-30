# Development Plan - TODO List

## Core Principle: Test Real Execution First
**IMPORTANT**: Run the actual program first to confirm all steps work before focusing on tests. We need working functionality first, then tests that catch real issues.

## Phase 1: PNG Sequence to Video Conversion with AI Metadata

### ✅ COMPLETED - VideoProcessor Restored and Enhanced

**What was done:**
- ✅ VideoProcessor class restored to `cosmos_workflow/local_ai/video_metadata.py`
- ✅ Added `validate_sequence()` method for PNG validation (detects gaps, validates files)
- ✅ Implemented `create_video_from_frames()` for PNG to MP4 conversion
- ✅ Added `standardize_video()` for FPS/resolution adjustments
- ✅ Implemented `extract_frame()` for frame extraction
- ✅ Module exports updated in `__init__.py`
- ✅ Comprehensive test suite created (24 tests, all passing)
  - Sequence validation tests (gaps, corrupted files, edge cases)
  - Video creation tests (basic, mixed resolutions, partial corrupt)
  - Standardization tests (upscaling, FPS conversion)
  - Frame extraction tests
  - End-to-end workflow tests

### ✅ COMPLETED - Basic CLI Integration
**What was done:**
- ✅ Created convert-sequence CLI command
- ✅ Basic PNG to video conversion working
- ✅ Tested with real Houdini renders (v3 directory)
- ✅ Fixed Unicode/emoji issues for Windows
- ✅ Fixed parameter passing bugs
- ✅ Added 15 comprehensive tests

### 🔄 REFACTOR NEEDED - Cosmos-Specific Workflow

**Current Issues:**
- Generic PNG sequence handling instead of Cosmos control modalities
- Wrong output structure (single video vs multiple control videos)
- Unnecessary metadata (color histograms vs AI description)
- No timestamped directories to prevent conflicts
- Too permissive validation (should be strict)

**Refactoring Plan:**

#### Step 1: Create CosmosSequenceValidator
Replace generic validation with Cosmos-specific:
- **Required**: `color.XXXX.png` files
- **Optional**: `depth.XXXX.png`, `segmentation.XXXX.png`, `vis.XXXX.png`, `edge.XXXX.png`
- **Strict**: Fail if unexpected files exist
- **Validation**: Ensure frame numbers match across all modalities
- **Output**: Dict with found modalities and frame ranges

#### Step 2: Create CosmosVideoConverter
Replace single video creation with multi-modal:
- Process each modality separately
- Output exact names: `color.mp4`, `depth.mp4`, etc.
- Create timestamped output directory: `{name}_{timestamp}/`
- Handle all modalities in parallel for speed

#### Step 3: Simplify Metadata Generation
Create focused metadata for inference:
```json
{
  "id": "quick_hash",
  "name": "short_name_from_ai",
  "description": "AI generated description of the scene",
  "frame_count": 48,
  "fps": 24,
  "modalities": ["color", "depth", "segmentation"],
  "timestamp": "2025-08-30T16:00:00Z"
}
```

#### Step 4: Refactor CLI Command
New behavior:
```bash
# Validate and convert Cosmos sequences
cosmos-workflow prepare-inference ./renders/comp/v3 --name my_scene

# Output structure:
inputs/videos/my_scene_20250830_160000/
├── color.mp4
├── depth.mp4
├── segmentation.mp4
└── metadata.json
```

#### Step 5: Update Tests
- Test strict validation (reject bad directories)
- Test multi-modal video creation
- Test timestamped directory creation
- Test simplified metadata generation

### 2. Test Full Cosmos Transfer Inference Pipeline
**Goal**: Once PNG->video conversion works, test the full AI video generation pipeline.

**Prerequisite**: PNG to video conversion must be working with proper metadata/tags

**Steps:**
1. **Use the video from step 1 as input**
   - Create PromptSpec with the converted video
   - Add transformation prompt (e.g., "Transform to cyberpunk style")
   - Set up RunSpec with production parameters

2. **Execute inference in background**
   ```bash
   # Create specs and run
   python -m cosmos_workflow.main create-spec "inference_test" "Transform to cyberpunk style" --input-video <video_from_step1>
   python -m cosmos_workflow.main create-run <prompt_spec.json> --weights 0.3 0.4 0.2 0.1
   python -m cosmos_workflow.main run <run_spec.json> --num-gpu 2 &
   ```

3. **Monitor execution**
   - SSH connection stability
   - Docker container status
   - GPU memory usage
   - File transfer completion
   - Error messages

4. **Verify results**
   - Output video generated
   - Style transformation applied correctly
   - Quality is acceptable

### 3. Fix Issues and Update Tests
**Goal**: When failures occur, fix code and ensure tests would catch the issue.

**Process for each failure:**
1. **Analyze failure**
   - Why did it fail?
   - Why didn't existing tests catch this?
   - What was the expected vs actual behavior?

2. **Fix the code**
   - Implement minimal fix to make it work
   - Test the fix with real execution
   - Verify fix doesn't break other functionality

3. **Update tests**
   - Write test that reproduces the failure
   - Verify test fails without fix
   - Verify test passes with fix
   - Add edge cases around the failure mode

4. **Document the fix**
   - Update CHANGELOG.md with the fix
   - Add to known issues if partially resolved
   - Update relevant documentation

### 4. Fix Integration Test API Mismatches
**Current Issues:**
- ConfigManager initialization using old API
- PromptSpec metadata field removed but tests still reference it
- DirectoryManager initialization needs updating

**Files to fix:**
- `tests/test_upsample_integration.py`
- Any other integration tests with API mismatches

## Future Phase Tasks

### Phase 3: Batch Inference Support
**Goal**: Process multiple PromptSpecs in single run

**Implementation steps:**
1. Study `cosmos_transfer1/diffusion/inference/transfer.py` batch options
2. Modify `scripts/inference.sh` for batch mode:
   - Accept multiple controlnet specs
   - Handle batch memory optimization
   - Support partial failure recovery
3. Create BatchJobSpec schema:
   - List of PromptSpec IDs
   - Shared execution parameters
   - Individual overrides per job
4. Update WorkflowOrchestrator:
   - `run_batch_inference()` method
   - Progress tracking per job
   - Result aggregation
5. CLI commands:
   - `create-batch` command
   - `run-batch` with progress display
6. Tests for batch operations

### Phase 4: Overnight Batch Processing with Randomization
**Goal**: Test parameter variations automatically

**Implementation:**
1. Create parameter randomization system:
   ```python
   randomization_config = {
       "control_weights": {"min": 0.1, "max": 0.9, "step": 0.1},
       "num_steps": [1, 35, 50],
       "guidance_scale": {"min": 5.0, "max": 12.0},
       "seeds": "random" or [specific_seeds]
   }
   ```
2. Job queue manager:
   - Sequential execution
   - Retry on failure (max 3 attempts)
   - Resource monitoring
   - Email/webhook notifications
3. Result aggregation:
   - Comparison grid generation
   - Performance metrics
   - Best parameter discovery

### Phase 5: Houdini Pipeline Integration
**Goal**: Seamless Houdini to Cosmos workflow

**Components:**
1. File watcher service:
   - Monitor `art/houdini/renders/comp`
   - Detect complete sequences
   - Auto-trigger conversion
2. Houdini metadata extraction:
   - Parse .hip files for scene info
   - Extract camera data
   - Get frame range and FPS
3. PDG/TOPs integration:
   - Custom Cosmos Transfer TOP node
   - Parameter wedging support
   - Distributed processing

## Testing Requirements

### For Each Feature:
1. **Before writing tests:**
   - Run the actual feature
   - Document what breaks
   - Fix the breaks
   
2. **Test must:**
   - Reproduce the actual failure found
   - Pass only with the fix applied
   - Cover edge cases discovered during real use

### Critical Test Coverage:
- PNG sequence detection and validation
- Video encoding parameters
- SSH connection recovery
- Docker container lifecycle
- GPU memory management
- File transfer integrity
- Error message clarity

## Known Issues to Fix

### High Priority:
1. **Integration test API mismatches** - Blocking test suite
2. **No real execution validation** - Core functionality unverified

### Medium Priority:
- Batch job scheduling
- Parameter randomization system

### Low Priority:
- Performance optimizations
- Additional output formats
- Cloud storage integration

## Success Criteria

Each task is complete when:
- [ ] Feature works in real execution
- [ ] Tests would catch any bugs found
- [ ] Documentation updated
- [ ] No regression in existing features
- [ ] Error messages are helpful
- [ ] Performance is acceptable