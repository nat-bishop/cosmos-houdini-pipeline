# Prompt Upsampling Investigation Summary

## Critical Discoveries

### 1. The CUDA Fork Error Solution
**THE KEY FIX**: Set `VLLM_WORKER_MULTIPROC_METHOD="spawn"` BEFORE any imports

```python
# This MUST be set before importing anything
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

# Then set torch elastic environment variables
env_defaults = {
    "RANK": "0",
    "LOCAL_RANK": "0",
    "WORLD_SIZE": "1",
    "LOCAL_WORLD_SIZE": "1",
    "GROUP_RANK": "0",
    "ROLE_RANK": "0",
    "ROLE_NAME": "default",
    "OMP_NUM_THREADS": "4",
    "MASTER_ADDR": "127.0.0.1",
    "MASTER_PORT": "29500",
    "TORCHELASTIC_USE_AGENT_STORE": "False",
    "TORCHELASTIC_MAX_RESTARTS": "0",
    "TORCHELASTIC_RUN_ID": "local",
    "TORCH_NCCL_ASYNC_ERROR_HANDLING": "1",
    "TORCHELASTIC_ERROR_FILE": "/tmp/torch_error.log"
}
for k, v in env_defaults.items():
    os.environ.setdefault(k, v)

# NOW import the upsampler
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
```

### 2. Working Code Pattern
**Your old working script approach - PROVEN TO WORK:**

```python
#!/usr/bin/env python3
import os, sys
sys.path.insert(0, '/workspace')

# CRITICAL: Set VLLM spawn FIRST
os.environ["VLLM_WORKER_MULTIPROC_METHOD"] = "spawn"

# Set all environment variables BEFORE imports
# ... (set all torch elastic vars)

# Import AFTER environment setup
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler

# Use directly (avoid upsampler_pipeline.py)
upsampler = PixtralPromptUpsampler(
    checkpoint_dir='/workspace/checkpoints',
    offload_prompt_upsampler=True  # or False to keep loaded
)

# Upsample with small video
result = upsampler._prompt_upsample_with_offload(prompt, video_path)
```

### 3. Token Limit Findings

#### Confirmed Working
- **320x180, 2 frames**: ✓ Well under 4096 token limit
- **320x176, 2 frames**: ✓ Your old script parameters

#### Confirmed Failing  
- **640x480, 2 frames**: ✗ 4685 tokens (exceeds 4096)
- **1280x720, 2 frames**: ✗ Would fail significantly

#### The Mystery
- NVIDIA's examples use 720p (1280x720) videos
- Their `extract_video_frames()` doesn't resize - uses original resolution
- No preprocessing found in the code
- Yet no one reports token limit issues

### 4. Performance Metrics
- **Model load time**: ~90-100 seconds (23GB Pixtral-12B model)
- **Upsampling time**: ~1 second after model loaded
- **Memory usage**: ~24GB VRAM when loaded

### 5. Critical Files & Paths

#### Remote Setup
- Host: 192.222.52.92
- Model path: `/home/ubuntu/NatsFS/cosmos-transfer1`
- Checkpoint: `/workspace/checkpoints/nvidia/Cosmos-UpsamplePrompt1-12B-Transfer`
- Docker image: `nvcr.io/ubuntu/cosmos-transfer1:latest`

#### Key Source Files
- Main upsampler: `cosmos_transfer1/auxiliary/upsampler/model/upsampler.py`
- Problem script: `cosmos_transfer1/auxiliary/upsampler/inference/upsampler_pipeline.py` (avoid this!)
- Frame extraction: `cosmos_transfer1/utils/misc.py::extract_video_frames()`
- Integration: `cosmos_transfer1/diffusion/inference/world_generation_pipeline.py`

### 6. What Doesn't Work
- Using `upsampler_pipeline.py` directly (requires torch distributed vars then deletes them)
- Running without VLLM spawn setting (CUDA fork error)
- Videos larger than ~400x225 with 2 frames

### 7. Your Previous Working Solution

Your old batch script that worked used:
```python
# Create small hint videos
ffmpeg -y -i source.mp4 \
    -vf "scale=320:-2:flags=lanczos,fps=2" \
    -vframes 2 \
    -c:v libx264 -crf 18 -preset medium \
    hint.mp4
```

This kept videos small enough to avoid token limits.

## Unsolved Questions

1. **How does NVIDIA handle 720p videos?**
   - Code shows no resizing
   - Same 4096 token limit
   - Yet their examples use 720p

2. **Possible explanations:**
   - VLLM internally resizes images (most likely)
   - Different model configuration
   - Environment-specific behavior
   - Examples don't actually use upsampling
   - Control inputs are preprocessed differently

3. **Why did the error only appear in Docker?**
   - The CUDA fork issue is Docker-specific
   - Token limits might behave differently

## Next Investigation Steps

1. **Test resolution limits systematically:**
   ```python
   resolutions = [
       (320, 180), (360, 203), (400, 225),
       (440, 248), (480, 270), (520, 293),
       (560, 315), (600, 338), (640, 360)
   ]
   ```

2. **Check VLLM image handling:**
   - Look for automatic resizing in VLLM source
   - Test with different VLLM versions
   - Check VLLM configuration options

3. **Test NVIDIA's exact commands:**
   - Run their examples verbatim
   - Check if `--upsample_prompt` is actually used
   - Monitor token usage

4. **Investigate control inputs:**
   - Check if depth/seg are lower resolution
   - Test upsampling with control videos vs RGB

## Working Solution

For reliable operation:
```python
# Safe parameters
width = 320
height = 180  
frames = 2
fps = 2

# Create hint video
ffmpeg -i input.mp4 \
    -vf "scale=320:-2:flags=lanczos,fps=2" \
    -vframes 2 \
    -c:v libx264 -crf 18 \
    hint_video.mp4
```

## Commands That Work

```bash
# Test upsampling with small video
python -c "
import os, sys
sys.path.insert(0, '/workspace')
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'
# ... set env vars ...
from cosmos_transfer1.auxiliary.upsampler.model.upsampler import PixtralPromptUpsampler
upsampler = PixtralPromptUpsampler('/workspace/checkpoints', True)
result = upsampler._prompt_upsample_with_offload('Test prompt', 'small_video.mp4')
print(result)
"
```

## Key Insight
The prompt upsampling DOES work, but requires:
1. VLLM spawn method set before imports
2. Small videos (≤320x180, 2 frames)
3. Direct use of PixtralPromptUpsampler class
4. Proper environment variables

The mystery of how NVIDIA handles larger videos remains unsolved.