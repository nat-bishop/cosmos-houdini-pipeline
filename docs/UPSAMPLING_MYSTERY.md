# The Prompt Upsampling Resolution Mystery

## The Paradox

1. **Our tests show**: The prompt upsampler fails with videos larger than ~400x225 pixels (2 frames), hitting the 4096 token limit
2. **But NVIDIA's examples**: Use it with 720p (1280x720) and even higher resolution videos
3. **No reported issues**: Despite thousands of users, no one reports this problem

## What We Found

### The Code Path
1. `extract_video_frames()` extracts 2 frames at **original resolution** - no resizing
2. Frames are converted to base64 and sent to VLLM
3. VLLM has `max_model_len=4096` hard-coded in the upsampler

### Our Test Results
- 320x180 (2 frames) = ✓ Works
- 640x480 (2 frames) = ✗ Fails (4685 tokens)
- 1280x720 (2 frames) = ✗ Would definitely fail

## Possible Explanations

### Theory 1: VLLM Internal Resizing
VLLM (the underlying LLM library) might automatically resize images internally before tokenization. This would explain why larger images work for others but fail in our Docker setup.

### Theory 2: Different Model Configuration
The model checkpoint we're using might be different from what NVIDIA uses internally. Perhaps there's a configuration that increases the context window.

### Theory 3: Environment-Specific Issue
Our Docker environment might be missing something that enables proper image handling. The VLLM library might behave differently based on certain environment variables or dependencies.

### Theory 4: They Don't Actually Use Prompt Upsampling
In the examples, `--upsample_prompt` might be False by default, and users might not be using this feature as much as we think.

### Theory 5: Control Input Preprocessing
When using control inputs (depth, segmentation, etc.), those might be at lower resolution, making the upsampling work. But the code shows they use the same video path.

## What NVIDIA's Code Shows

```python
# In world_generation_pipeline.py
if self.upsample_prompt:
    # They use the control input video directly
    prompt = self.prompt_upsampler._prompt_upsample_with_offload(
        prompt=prompt, 
        video_path=input_control_path
    )
```

No resizing is done before calling the upsampler.

## The Key Question

**Why does the same code work for NVIDIA's examples with 720p videos but fail for us with 640x480?**

## Next Steps to Investigate

1. **Check VLLM version**: Different versions might handle images differently
2. **Test with official Docker image directly**: Run their exact example commands
3. **Check if control inputs are preprocessed**: Maybe depth/seg videos are lower resolution
4. **Look for hidden configuration**: There might be environment variables or configs we're missing
5. **Test without Docker**: Run directly on the GPU to see if Docker is the issue

## Working Workaround

For now, the solution is clear:
- Create "hint clips" at 320x180 or smaller
- Use 2 frames maximum
- This reliably stays under the 4096 token limit

But the mystery remains: How does NVIDIA's code work with larger videos?