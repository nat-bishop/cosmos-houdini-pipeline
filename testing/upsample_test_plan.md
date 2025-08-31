# Prompt Upsampling Test Plan

## Overview
Comprehensive testing plan for prompt upsampling functionality, including vocab error investigation and batch optimization.

## Test Setup

### 1. CLI Integration ✅
- **Status**: COMPLETE
- **Entry Point**: `python -m cosmos_workflow.cli upsample`
- **Verified**: All commands integrated into main CLI

### 2. Test Data Preparation

#### Video Resolution Test Matrix
Create test videos at different resolutions to identify vocab error cutoff:

```bash
# Resolution test cases
360p  (640x360)   - Expected: PASS
480p  (854x480)   - Expected: PASS (default)
720p  (1280x720)  - Expected: UNCERTAIN
1080p (1920x1080) - Expected: FAIL (vocab error)
1440p (2560x1440) - Expected: FAIL (vocab error)
4K    (3840x2160) - Expected: FAIL (vocab error)
```

#### Sample Prompts for Testing
```json
{
  "simple": "A serene landscape",
  "medium": "A cyberpunk city at night with neon lights reflecting on wet streets",
  "complex": "An intricate steampunk clockwork mechanism with brass gears, copper pipes, and steam valves operating in perfect synchronization"
}
```

## Testing Phases

### Phase 1: Single Prompt Upsampling

#### Test 1.1: Basic Functionality
```bash
# Create test prompt spec
python -m cosmos_workflow.cli create-spec \
  "test_basic" \
  "A simple test scene" \
  --video-path inputs/videos/test_480p.mp4

# Run upsampling
python -m cosmos_workflow.cli upsample \
  inputs/prompts/[date]/test_basic_ps_[hash].json \
  --save-dir outputs/upsampled \
  --verbose
```

#### Test 1.2: Resolution Testing
```bash
# Test each resolution
for res in 360p 480p 720p 1080p 1440p 4k; do
  echo "Testing resolution: $res"
  
  # Create prompt spec with video at this resolution
  python -m cosmos_workflow.cli create-spec \
    "test_${res}" \
    "Test prompt for ${res} video" \
    --video-path inputs/videos/test_${res}.mp4
  
  # Attempt upsampling WITHOUT preprocessing
  python -m cosmos_workflow.cli upsample \
    inputs/prompts/*/test_${res}_ps_*.json \
    --preprocess-videos false \
    --save-dir outputs/upsampled/${res}_raw \
    --verbose
  
  # Attempt upsampling WITH preprocessing
  python -m cosmos_workflow.cli upsample \
    inputs/prompts/*/test_${res}_ps_*.json \
    --preprocess-videos true \
    --max-resolution 480 \
    --save-dir outputs/upsampled/${res}_preprocessed \
    --verbose
done
```

### Phase 2: Vocab Error Investigation

#### Test 2.1: Find Resolution Cutoff
```bash
# Binary search for exact resolution where vocab error occurs
# Test resolutions: 480, 540, 600, 660, 720, 780, 840, 900, 960

for height in 480 540 600 660 720 780 840 900 960; do
  width=$((height * 16 / 9))
  echo "Testing ${width}x${height}"
  
  # Create test video at this resolution
  # (Use ffmpeg to resize existing video)
  
  python -m cosmos_workflow.cli upsample \
    test_prompt_${height}p.json \
    --preprocess-videos false \
    --verbose 2>&1 | tee logs/vocab_test_${height}p.log
done
```

#### Test 2.2: Frame Count Impact
```bash
# Test if number of frames affects vocab error
for frames in 1 2 4 8 16; do
  echo "Testing with $frames frames"
  
  python -m cosmos_workflow.cli upsample \
    test_prompt_720p.json \
    --num-frames $frames \
    --preprocess-videos false \
    --verbose 2>&1 | tee logs/vocab_frames_${frames}.log
done
```

### Phase 3: Batch Upsampling Optimization

#### Test 3.1: Batch Size Testing
```bash
# Create test batches of different sizes
for batch_size in 1 5 10 20 50 100; do
  echo "Testing batch size: $batch_size"
  
  # Create directory with N prompt specs
  mkdir -p inputs/batch_test_${batch_size}
  
  # Copy/create prompt specs
  for i in $(seq 1 $batch_size); do
    python -m cosmos_workflow.cli create-spec \
      "batch_test_${i}" \
      "Test prompt number ${i}" \
      --video-path inputs/videos/test_480p.mp4
  done
  
  # Time the batch processing
  time python -m cosmos_workflow.cli upsample \
    inputs/batch_test_${batch_size}/ \
    --save-dir outputs/batch_${batch_size} \
    --verbose
done
```

#### Test 3.2: GPU Scaling
```bash
# Test multi-GPU performance
for num_gpu in 1 2; do
  echo "Testing with $num_gpu GPUs"
  
  time python -m cosmos_workflow.cli upsample \
    inputs/batch_test_20/ \
    --num-gpu $num_gpu \
    --cuda-devices $(seq -s, 0 $((num_gpu-1))) \
    --save-dir outputs/gpu_test_${num_gpu} \
    --verbose
done
```

### Phase 4: Memory and Performance Monitoring

#### Test 4.1: Memory Usage
```bash
# Monitor GPU memory during upsampling
nvidia-smi dmon -s mu -d 1 -o T > memory_log.csv &
NVIDIA_PID=$!

python -m cosmos_workflow.cli upsample \
  inputs/batch_test_10/ \
  --verbose

kill $NVIDIA_PID
```

#### Test 4.2: Model Offloading Impact
```bash
# Test with and without model offloading
# (Requires modification to expose offload parameter)

# Without offloading (model stays in memory)
time python -m cosmos_workflow.cli upsample \
  inputs/batch_test_20/ \
  --no-offload \
  --verbose

# With offloading (model loaded/unloaded per batch)
time python -m cosmos_workflow.cli upsample \
  inputs/batch_test_20/ \
  --offload \
  --verbose
```

## Expected Results & Analysis

### Vocab Error Resolution Cutoff
- **Hypothesis**: Error occurs above 720p (1280x720)
- **Test**: Binary search between 480p-1080p
- **Metrics**: Success/failure, exact resolution threshold

### Optimal Batch Size
- **Hypothesis**: 10-20 prompts per batch optimal
- **Test**: Measure time per prompt across batch sizes
- **Metrics**: Total time, time per prompt, memory usage

### Preprocessing Impact
- **Test**: Compare success rates with/without preprocessing
- **Metrics**: Success rate, quality of upsampled prompts

## Output Structure
```
testing/
├── upsample_test_plan.md (this file)
├── logs/
│   ├── vocab_test_*.log
│   ├── batch_test_*.log
│   └── memory_*.csv
├── results/
│   ├── resolution_cutoff.json
│   ├── batch_optimization.json
│   └── performance_metrics.json
└── test_videos/
    ├── test_360p.mp4
    ├── test_480p.mp4
    ├── test_720p.mp4
    └── ...
```

## Commands Quick Reference

```bash
# Single file upsampling
python -m cosmos_workflow.cli upsample prompt.json --save-dir outputs/

# Batch directory upsampling
python -m cosmos_workflow.cli upsample inputs/prompts/ --save-dir outputs/

# With preprocessing (avoid vocab errors)
python -m cosmos_workflow.cli upsample prompt.json \
  --preprocess-videos \
  --max-resolution 480 \
  --save-dir outputs/

# Multi-GPU batch processing
python -m cosmos_workflow.cli upsample inputs/prompts/ \
  --num-gpu 2 \
  --cuda-devices "0,1" \
  --save-dir outputs/

# Custom frame extraction
python -m cosmos_workflow.cli upsample prompt.json \
  --num-frames 4 \
  --save-dir outputs/
```

## Next Steps
1. Create test videos at various resolutions
2. Generate test prompt specs
3. Run Phase 1 tests for basic functionality
4. Investigate vocab error threshold (Phase 2)
5. Optimize batch processing (Phase 3)
6. Document findings and optimal parameters