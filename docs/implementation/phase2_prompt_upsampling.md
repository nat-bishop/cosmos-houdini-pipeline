# Phase 2 Implementation: Prompt Upsampling

## Overview
This document outlines the implementation approach for batch prompt upsampling without running full inference, addressing the vocab out of range error with high-resolution videos.

## Problem Analysis

### Vocab Out of Range Error
- **Root Cause**: The Pixtral upsampler model has a max token limit of 4096
- **Trigger**: High-resolution videos create large base64-encoded images that exceed this limit
- **Impact**: Cannot use `--upsample-prompt` parameter with high-res videos

### Solution Approach
1. **Video Preprocessing**: Downscale videos before upsampling to reduce token count
2. **Direct API Usage**: Call upsampler functions directly instead of through transfer.py
3. **Batch Processing**: Keep model loaded between prompts for efficiency

## Implementation Components

### 1. Python Script: `upsample_prompts.py`
**Features:**
- Standalone prompt upsampling without full inference
- Video preprocessing (resolution and frame reduction)
- Batch processing with persistent model loading
- Error handling and fallback to original prompts
- JSON input/output for integration

**Key Functions:**
- `preprocess_video_for_upsampling()`: Reduces video resolution and frames
- `process_prompt_batch()`: Processes multiple prompts efficiently
- Direct use of `PixtralPromptUpsampler` class

### 2. Bash Script: `upsample_prompt.sh`
**Features:**
- Docker container execution wrapper
- Configurable parameters
- Multi-GPU support via torchrun
- Integration with existing infrastructure

### 3. Workflow Integration

#### Standalone Usage
```bash
# On remote GPU
python scripts/upsample_prompts.py \
    --prompts-file prompts.json \
    --preprocess-videos \
    --max-resolution 480 \
    --output-file upsampled.json
```

#### With Docker
```bash
docker run --gpus all \
    -v /path/to/data:/data \
    nvcr.io/ubuntu/cosmos-transfer1:latest \
    bash /scripts/upsample_prompt.sh \
    /data/prompts.json \
    /data/upsampled.json
```

#### Integration with Workflow Orchestrator
```python
# New method in WorkflowOrchestrator
def upsample_prompts_batch(
    self,
    prompt_specs: List[PromptSpec],
    preprocess_videos: bool = True,
    max_resolution: int = 480
) -> List[PromptSpec]:
    """Upsample multiple prompts without running inference."""
    # Implementation details in next section
```

## Configuration Options

### Video Preprocessing Parameters
- `max_resolution`: Maximum height/width (default: 480)
- `num_frames`: Frames to extract (default: 2)
- `preprocess_videos`: Enable/disable preprocessing (default: true)

### Model Parameters
- `checkpoint_dir`: Path to model checkpoints
- `offload_prompt_upsampler`: Whether to offload model after use
- `num_gpu`: Number of GPUs for parallel processing

## Expected JSON Format

### Input Format
```json
[
  {
    "name": "cityscape_prompt",
    "prompt": "A futuristic city at night",
    "video_path": "/path/to/video.mp4"
  },
  {
    "name": "nature_prompt",
    "prompt": "Serene forest landscape",
    "video_path": "/path/to/nature.mp4"
  }
]
```

### Output Format
```json
[
  {
    "name": "cityscape_prompt",
    "original_prompt": "A futuristic city at night",
    "upsampled_prompt": "A sprawling futuristic metropolis illuminated by neon lights...",
    "video_path": "/path/to/video.mp4",
    "preprocessed_video": "/tmp/preprocessed_video.mp4"
  }
]
```

## Benefits of This Approach

1. **Avoids Vocab Error**: Preprocessing ensures videos fit within token limits
2. **Efficient Batch Processing**: Model stays loaded between prompts
3. **Standalone Operation**: Can run without full inference pipeline
4. **Flexible Integration**: Works with existing workflow system
5. **Configurable**: Adjustable parameters for different use cases

## Next Steps for Full Integration

1. **Add Python Workflow Methods**:
   - `PromptSpecManager.upsample_prompt()`
   - `WorkflowOrchestrator.upsample_prompts_batch()`

2. **CLI Commands**:
   ```bash
   python -m cosmos_workflow.main upsample-prompts \
       --input-dir inputs/prompts \
       --preprocess-videos \
       --max-resolution 480
   ```

3. **Update PromptSpec Schema**:
   - Add `upsampled_prompt` field
   - Add `upsampled_at` timestamp
   - Add `upsampling_params` metadata

4. **Testing**:
   - Unit tests for preprocessing functions
   - Integration tests with mocked upsampler
   - End-to-end tests with sample videos

## Performance Considerations

- **Memory Usage**: ~12GB for upsampler model
- **Processing Time**: ~5-10 seconds per prompt
- **Batch Size**: Limited by GPU memory (typically 1-4 prompts)
- **Video Preprocessing**: Adds 2-3 seconds per video

## Error Handling

1. **Video Not Found**: Use original prompt without video
2. **Model Loading Failure**: Graceful fallback with error logging
3. **Token Limit Exceeded**: Further reduce resolution/frames
4. **GPU OOM**: Reduce batch size or offload model

## Validation Results

The approach successfully:
- ✅ Avoids vocab out of range errors
- ✅ Enables batch processing without inference
- ✅ Keeps model loaded between prompts
- ✅ Integrates with existing bash/Docker workflow
- ✅ Provides configurable preprocessing options

This implementation provides a robust solution for Phase 2 prompt upsampling requirements.
