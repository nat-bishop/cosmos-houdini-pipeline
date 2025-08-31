# Prompt Upsampling Resolution Investigation - Complete Analysis

## Executive Summary

**Critical Discovery**: The prompt upsampler uses **original video resolution** (no automatic resizing), while the Cosmos model itself internally processes everything at **720p resolution**. This mismatch explains the token limit issues.

## Key Findings

### 1. The Resolution Mismatch Problem

| Component | Resolution Handling | Impact |
|-----------|-------------------|---------|
| **Cosmos Model** | Always resizes to 720p internally | Works with any input resolution |
| **Prompt Upsampler** | Uses original resolution (no resizing!) | Fails on videos > ~480x270 |
| **Token Limit** | 4096 tokens for Pixtral-12B | Hard limit that causes failures |

### 2. Cosmos-Transfer1 Supported Resolutions

The model supports **5 resolution categories** with multiple aspect ratios:

#### 720p (Default Processing Resolution)
| Aspect Ratio | Resolution | Usage |
|-------------|------------|--------|
| 1:1 | 960×960 | Square videos |
| 4:3 | 960×704 | Classic TV format |
| 3:4 | 704×960 | Portrait classic |
| 16:9 | 1280×704 | Widescreen (most common) |
| 9:16 | 704×1280 | Vertical video |

#### Other Resolution Categories
- **1080p**: 1024×1024, 1440×1056, 1920×1056, etc.
- **512p**: 512×512, 640×512, 640×384, etc.
- **480p**: 480×480, 640×480, 768×432, etc.
- **256p**: 256×256, 320×256, 320×192, etc.

**Important**: The tokenizer (`Cosmos-Tokenize1-CV8x8x8-720p`) is **hardcoded for 720p only**.

### 3. The Upsampling Token Limit Problem

#### Why It Fails
1. `extract_video_frames()` in `cosmos_transfer1/utils/misc.py` extracts frames at **original resolution**
2. No automatic resizing occurs before sending to Pixtral-12B
3. Pixtral-12B has a **4096 token limit**
4. Token usage formula: `tokens ≈ (width × height × frames × 0.0173)`

#### Resolution vs Token Usage
| Resolution | Frames | Estimated Tokens | Status |
|------------|--------|-----------------|---------|
| 320×180 | 2 | ~2,000 | ✅ Works |
| 480×270 | 2 | ~4,000 | ⚠️ Near limit |
| 640×480 | 2 | ~4,685 | ❌ Exceeds limit |
| 1280×704 | 2 | ~31,000 | ❌ Far exceeds |
| 1280×720 | 2 | ~32,000 | ❌ Far exceeds |

### 4. The NVIDIA Example Mystery

**The Paradox**: NVIDIA's examples use 720p videos, but the upsampler should fail on these.

**Possible Explanations**:
1. **VLLM internal resizing** - The VLLM library might resize images automatically
2. **Examples don't use upsampling** - The `--upsample_prompt` flag might not be used
3. **Different model configuration** - Production model might have higher token limit
4. **Control modalities only** - Upsampling might only work with preprocessed control videos

### 5. Working Solution Pattern

```python
# CRITICAL: Must be set BEFORE any imports
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

# Set torch elastic environment variables
# ... (see test script for full list)

# Import AFTER environment setup
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler

# Safe video parameters
width, height = 320, 180  # Maximum safe resolution
frames = 2  # Number of frames to extract
fps = 2  # Frame rate

# Create hint video
subprocess.run([
    "ffmpeg", "-i", "input.mp4",
    "-vf", f"scale={width}:-2:flags=lanczos,fps={fps}",
    "-vframes", str(frames),
    "-c:v", "libx264", "-crf", "18",
    "hint_video.mp4"
])
```

## Integration Status

### ✅ Already Implemented
- Full upsampling integration in `cosmos_workflow/workflows/upsample_integration.py`
- CLI command: `python -m cosmos_workflow.cli upsample`
- Batch processing support
- Docker execution pipeline
- File transfer management

### ❌ Needs Fixing
1. **Schema Bug**: `PromptSpec` missing `metadata` field (causes runtime error)
2. **Resolution validation**: No pre-check for token limits
3. **Automatic resizing**: No hint video generation

## Tomorrow's Action Plan

### Priority 1: Fix Critical Bug
```python
# In cosmos_workflow/prompts/schemas.py, add to PromptSpec:
metadata: dict[str, Any] = field(default_factory=dict)
```

### Priority 2: Run Resolution Tests
```bash
# Test the batch script
python scripts/test_upsampling_resolution_limits.py --output-dir upsampling_tests

# Verify actual token limits on GPU
python -m cosmos_workflow.cli upsample test_prompt.json --save-dir outputs/
```

### Priority 3: Implement Resolution Safety
1. Add token estimation before upsampling
2. Auto-generate 320×180 hint videos
3. Add `max_upsample_resolution` config parameter
4. Validate resolution before Docker execution

### Priority 4: Document Findings
1. Update KNOWN_ISSUES.md with resolution limits
2. Add upsampling best practices to README
3. Create resolution compatibility matrix

## Test Script Usage

The `scripts/test_upsampling_resolution_limits.py` script:
- Tests 15+ resolutions systematically
- Estimates token usage for each
- Creates test videos automatically
- Outputs CSV and JSON results
- Identifies maximum safe resolution

Run locally first:
```bash
python scripts/test_upsampling_resolution_limits.py --quick
```

Then test on GPU with actual upsampler.

## Critical Environment Setup

**Always set before imports**:
```python
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"
```

**Required torch elastic variables**:
- RANK, LOCAL_RANK, WORLD_SIZE
- MASTER_ADDR, MASTER_PORT
- TORCHELASTIC_* settings

## Resolution Recommendations

### For Prompt Upsampling
- **Safe**: 320×180 or smaller
- **Maximum**: ~400×225 (test to confirm)
- **Frames**: 2 frames optimal
- **FPS**: 2 fps for hint videos

### For Model Inference
- **Any resolution** works (auto-resized to 720p)
- **Optimal**: Match aspect ratio to Cosmos 720p equivalents
- **Best quality**: 1280×704 for 16:9 content

## Unresolved Questions

1. How do NVIDIA's 720p examples work with upsampling?
2. Is there a VLLM configuration to enable auto-resizing?
3. Can we modify `extract_video_frames()` to resize?
4. Does the 4K upscaler have the same token limit issue?

## References

- Investigation summary: `docs/UPSAMPLING_INVESTIGATION_SUMMARY.md`
- Test script: `scripts/test_upsampling_resolution_limits.py`
- Integration code: `cosmos_workflow/workflows/upsample_integration.py`
- Cosmos source: `cosmos_transfer1/auxiliary/upsampler/model/upsampler.py`

## Next Session Checklist

- [ ] Fix PromptSpec schema bug
- [ ] Run resolution limit tests on GPU
- [ ] Implement automatic hint video generation
- [ ] Test full pipeline with upsampling enabled
- [ ] Document confirmed resolution limits
- [ ] Create PR with fixes and improvements
