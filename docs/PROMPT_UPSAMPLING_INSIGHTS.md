# Prompt Upsampling Investigation - Complete Insights

## Executive Summary
Investigation into running NVIDIA Cosmos-Transfer1 prompt upsampling on remote GPU instance. The prompt upsampler uses the Pixtral-12B vision-language model to generate detailed descriptions from video frames and text prompts. We encountered a fundamental incompatibility between VLLM (the underlying LLM library) and Docker's process model that prevents standalone execution.

## System Architecture

### Components
1. **Pixtral-12B Model** (`/workspace/checkpoints/nvidia/Cosmos-UpsamplePrompt1-12B-Transfer`)
   - Vision-language model for prompt enhancement
   - Uses VLLM for inference
   - ~15GB VRAM requirement

2. **Key Files**
   - Main upsampler: `cosmos_transfer1/auxiliary/upsampler/model/upsampler.py`
   - Pipeline script: `cosmos_transfer1/auxiliary/upsampler/inference/upsampler_pipeline.py`
   - Integration: `cosmos_workflow/workflows/upsample_integration.py`
   - CLI: `cosmos_workflow/cli.py` (upsample command)

3. **Remote Setup**
   - Host: 192.222.52.92
   - GPU: NVIDIA H100 80GB
   - Docker: `nvcr.io/ubuntu/cosmos-transfer1:latest`
   - Model path: `/home/ubuntu/NatsFS/cosmos-transfer1`

## The Core Problem

### CUDA Fork Error
```
RuntimeError: Cannot re-initialize CUDA in forked subprocess.
To use CUDA with multiprocessing, you must use the 'spawn' start method
```

### Root Cause
1. VLLM internally uses multiprocessing with 'fork' method
2. CUDA cannot be re-initialized in forked processes
3. Docker containers inherit the fork behavior
4. Even setting `multiprocessing.set_start_method('spawn')` doesn't help because VLLM creates subprocesses after CUDA is already initialized

## How NVIDIA's Code Works

### Integration Pattern (from `world_generation_pipeline.py`)
```python
# 1. Save distributed training environment variables
dist_keys = ["RANK", "LOCAL_RANK", "WORLD_SIZE", ...]
saved_env = {k: os.environ[k] for k in dist_keys if k in os.environ}

# 2. Delete them (required by upsampler script)
for key in dist_keys:
    del os.environ[key]

# 3. Run upsampler
upsampler = PixtralPromptUpsampler(checkpoint_dir, offload_prompt_upsampler=True)
upsampled = upsampler._prompt_upsample_with_offload(prompt, video_path)

# 4. Restore environment
for key, value in saved_env.items():
    os.environ[key] = value
```

### The upsampler_pipeline.py Problem
```python
if __name__ == "__main__":
    rank = int(os.environ["RANK"])  # REQUIRES this to exist

    # Delete all distributed training vars
    for dist_key in dist_keys:
        del os.environ[dist_key]  # Fails if not present

    if rank == 0:
        main()  # Only runs on rank 0
```

## Required Environment Variables

When running with `torchrun --nproc_per_node=1` (single GPU), these are set:

```python
env_defaults = {
    "RANK": "0",                    # Global rank
    "LOCAL_RANK": "0",               # Local rank on node
    "WORLD_SIZE": "1",               # Total processes
    "LOCAL_WORLD_SIZE": "1",         # Processes on node
    "GROUP_RANK": "0",               # Node rank
    "ROLE_RANK": "0",                # Role rank
    "ROLE_NAME": "default",          # Role name
    "OMP_NUM_THREADS": "1",          # OpenMP threads
    "MASTER_ADDR": "127.0.0.1",      # Master address
    "MASTER_PORT": "29500",          # Master port
    "TORCHELASTIC_USE_AGENT_STORE": "False",
    "TORCHELASTIC_MAX_RESTARTS": "0",
    "TORCHELASTIC_RUN_ID": "none",
    "TORCH_NCCL_ASYNC_ERROR_HANDLING": "1",
    "TORCHELASTIC_ERROR_FILE": "/tmp/torch_error.log"
}
```

## Working CLI Commands

### Create Prompt Spec
```bash
python -m cosmos_workflow.cli create-spec \
    "golden_hour_test" \
    "Warm low-angle sunlight grazing facades" \
    --video-path "F:/Art/cosmos-houdini-experiments/inputs/videos/city_scene_20250830_203504/color.mp4"
```

### Attempt Upsampling (fails due to CUDA fork issue)
```bash
python -m cosmos_workflow.cli upsample \
    "inputs/prompts/2025-08-31/golden_hour_test_*.json" \
    --save-dir outputs/upsampled_test \
    --verbose
```

## Solutions Attempted

### 1. Direct Docker Execution ❌
- Set all required environment variables
- Still hits CUDA fork error in VLLM

### 2. NVIDIA-style Wrapper ❌
- Mimicked their save/delete/restore pattern
- Same CUDA fork error

### 3. Force Spawn Method ❌
```python
import multiprocessing
multiprocessing.set_start_method('spawn', force=True)
```
- Doesn't help because VLLM creates processes after CUDA init

### 4. Simpler Script Without Deletion ❌
- Created standalone script setting all defaults
- VLLM still internally uses fork

## Key Insights

### What Works
- File uploads to remote via SFTP ✓
- Docker container launches ✓
- Environment variables properly set ✓
- Model starts loading ✓

### What Breaks
- VLLM's internal multiprocessing architecture
- Incompatibility with Docker's process model
- Cannot override VLLM's fork behavior

### NVIDIA's Approach
- They run upsampling as part of the full inference pipeline
- Uses torchrun for proper distributed setup
- Only runs on rank 0 in multi-GPU setups
- Handles environment variable cleanup carefully

## Test Prompts Provided

16 atmospheric lighting prompts for testing:
- pre_dawn_blue_hour_calm
- golden_hour_warmth
- overcast_noon_softness
- just_after_rain_sheen
- steady_light_drizzle
- morning_condensation_on_glass
- foggy_early_morning
- light_snow_flurries_thin_settling
- hot_dry_midday_heat_shimmer
- cleaned_glass_polished_reflections
- rain_darkened_stone_concrete
- subtle_metal_patina
- urban_haze_at_dusk
- night_active_practicals
- night_after_rain_reflective_pavements
- dry_to_wet_progression

## Remaining Questions

1. **User's Previous Success**: User mentioned getting this working with a local script that "set defaults for the environment variables to avoid the problem of them being deleted." This suggests there might be a way to run it that we haven't found.

2. **Alternative Approaches**:
   - Run the full inference pipeline with `--upsample_prompt` flag
   - Modify the Docker image to fix VLLM's multiprocessing
   - Run upsampling locally if GPU available
   - Use the model server approach from `server/model_server.py`

## Code Structure Summary

```
cosmos_workflow/
├── cli.py                          # Entry point, upsample command
├── workflows/
│   ├── workflow_orchestrator.py    # Main orchestrator
│   └── upsample_integration.py     # UpsampleWorkflowMixin
├── config/
│   └── config.toml                 # SSH and remote settings
└── prompts/
    └── schemas.py                   # PromptSpec definition

cosmos_transfer1/
├── auxiliary/upsampler/
│   ├── model/
│   │   └── upsampler.py            # PixtralPromptUpsampler class
│   └── inference/
│       └── upsampler_pipeline.py   # Problematic main script
└── diffusion/inference/
    ├── transfer.py                  # Main inference entry
    └── world_generation_pipeline.py # Shows proper integration
```

## Next Session Recommendations

1. **Check Model Server Approach**: The `server/model_server.py` uses torchrun properly and might be a better entry point

2. **Try Full Pipeline**: Instead of standalone upsampling, run the complete inference with upsampling enabled:
   ```bash
   python -m cosmos_transfer1.diffusion.inference.transfer \
       --controlnet_specs control_spec.json \
       --upsample_prompt \
       --offload_prompt_upsampler
   ```

3. **Investigate Local Execution**: If the user got it working locally, the issue might be Docker-specific. Try running directly on the remote without Docker.

4. **Contact NVIDIA**: The VLLM fork issue seems fundamental and might require their input or a patched version.

## Files Created During Investigation

1. `testing/upsample_test_plan.md` - Comprehensive test plan
2. `testing/create_test_videos.py` - Generate test videos at different resolutions
3. `testing/create_test_prompts.py` - Create prompt specs from atmospheric prompts
4. `testing/run_upsample_tests.py` - Automated test runner
5. `scripts/simple_prompt_upsampler.py` - Simplified upsampler without distributed complexity
6. `scripts/nvidia_style_upsampler.py` - Following NVIDIA's patterns
7. `scripts/standalone_upsampler.py` - With all environment defaults
8. `scripts/force_spawn_upsampler.py` - Attempting to force spawn method

## Conclusion

The prompt upsampling feature is architecturally sound but has a fundamental incompatibility between VLLM's multiprocessing model and Docker's process handling. The issue appears to be that VLLM uses fork() internally after CUDA has been initialized, which is not allowed. This requires either:
1. Running as part of the full inference pipeline where the environment is properly managed
2. Modifying VLLM to use spawn instead of fork
3. Running outside of Docker where process management might be different
4. Finding the exact configuration the user previously used that worked
