# Development Plan - TODO List

## Core Principle: Test Real Execution First
**IMPORTANT**: Run the actual program first to confirm all steps work before focusing on tests. We need working functionality first, then tests that catch real issues.

## Phase 1: PNG Sequence to Video Conversion with AI Metadata

### Background & Context
**Previous Investigation Found:**
- VideoProcessor class was implemented in commit d0e2607 with `create_video_from_frames` method
- Class was later removed from `cosmos_workflow/local_ai/video_metadata.py`
- VideoMetadataExtractor exists for AI analysis (BLIP captions, ViT tags, DETR object detection)
- video_metadata.py has standalone CLI: `python -m cosmos_workflow.local_ai.video_metadata`
- No current CLI integration for PNG sequence conversion

### Step 1: Restore VideoProcessor Class
**File:** `cosmos_workflow/local_ai/video_metadata.py`

**Add back the VideoProcessor class with these methods:**
```python
class VideoProcessor:
    def create_video_from_frames(frame_paths: List[Path], output_path: Path, fps: int = 24) -> bool:
        """Convert PNG sequence to MP4 video using OpenCV"""
        # Read first frame for dimensions
        # Setup VideoWriter with mp4v codec
        # Write all frames to video
        # Return success status
    
    def validate_sequence(input_dir: Path) -> dict:
        """Validate PNG sequence before conversion"""
        # Find all PNG files in directory
        # Check naming pattern (frame_000.png, frame_001.png, etc.)
        # Detect missing frames/gaps in sequence
        # Verify each file is valid PNG
        # Return validation report with any issues
    
    def standardize_video(input_path: Path, output_path: Path, target_fps: int = 24) -> bool:
        """Standardize video FPS and resolution if needed"""
```

### Step 2: Create CLI Integration
**File:** `cosmos_workflow/cli.py`

**Add new command:**
```python
def convert_sequence_command(args):
    """Convert PNG sequence to video with AI metadata"""
    # 1. Initialize VideoProcessor
    # 2. Validate PNG sequence
    # 3. Convert to video
    # 4. Initialize VideoMetadataExtractor(use_ai=True)
    # 5. Extract metadata with AI analysis
    # 6. Save video and metadata JSON
    # 7. Print results

# Add to argparse:
convert_parser = subparsers.add_parser('convert-sequence')
convert_parser.add_argument('input_dir', help='Directory containing PNG sequence')
convert_parser.add_argument('--output', help='Output video path')
convert_parser.add_argument('--fps', type=int, default=24)
convert_parser.add_argument('--use-ai', action='store_true', help='Generate AI metadata')
```

### Step 3: Update Module Exports
**File:** `cosmos_workflow/local_ai/__init__.py`

```python
from .video_metadata import VideoMetadataExtractor, VideoMetadata, VideoProcessor

__all__ = [
    "VideoMetadataExtractor",
    "VideoMetadata", 
    "VideoProcessor"  # Add this
]
```

### Step 4: Testing Workflow
**Location:** `art/houdini/renders/comp`

**Test Process:**
1. List available PNG sequences in the directory
2. Ask user which sequence to test (they know expected output)
3. Run: `python -m cosmos_workflow.cli convert-sequence <dir> --use-ai --fps 24`
4. Verify outputs:
   - MP4 video created successfully
   - Proper codec, resolution, framerate
   - AI metadata JSON created with:
     - Caption from BLIP model
     - Tags from ViT classifier
     - Detected objects from DETR
   - Validate metadata accuracy
5. Test edge cases:
   - Missing frames in sequence
   - Different naming conventions
   - Various resolutions

### Step 5: Integration Points
**Ensure compatibility with existing system:**
- Output format matches what Cosmos Transfer expects
- Metadata JSON follows established schema
- File paths follow project conventions (`inputs/videos/`, `outputs/`)
- Works with existing SSH/Docker workflow for inference

### Success Criteria for Phase 1
- [ ] PNG sequences convert to valid MP4 videos
- [ ] AI metadata accurately describes content
- [ ] CLI command works seamlessly
- [ ] Handles missing frames gracefully
- [ ] Proper error messages for invalid inputs
- [ ] Documentation updated in README.md
- [ ] Tests added for new functionality

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